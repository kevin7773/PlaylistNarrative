from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.elicitation import (
    ArtistQuestionnaireObjective,
    ArtistQuestionnaireRequest,
    ArtistQuestionnaireSeedGenerator,
    ArtistSeedEvidence,
)
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.objective_assessment import (
    DiscoveryPercentEvidence,
    DurationMinutesEvidence,
    EndingEnergyEvidence,
    ListeningContextEvidence,
    Objective,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
    StartingEnergyEvidence,
)
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    SequentialPlaylistConstructor,
    TrackScorer,
)
from playlist_narrative_engine.track_evidence import (
    TRACK_EVIDENCE_SCHEMA_VERSION,
    EvidenceSnapshot,
    EvidenceSnapshotRecord,
    TrackEvidenceIssueCode,
    TrackEvidenceValidationArtifact,
    TrackEvidenceValidationRequest,
    TrackEvidenceValidator,
    serialize_track_evidence_validation,
)


OBJECTIVE_ID = "coding-focus"
OBJECTIVE_STATEMENT = "Support a focused coding session."


def objective_assessment():
    request = ObjectiveAssessmentRequest(
        objective=Objective(
            objective_id=OBJECTIVE_ID,
            statement=OBJECTIVE_STATEMENT,
        ),
        evidence=(
            ListeningContextEvidence(
                evidence_id="context",
                dimension="listening_context",
                value="Focused coding",
            ),
            DurationMinutesEvidence(
                evidence_id="duration",
                dimension="duration_minutes",
                value=90,
            ),
            StartingEnergyEvidence(
                evidence_id="start",
                dimension="starting_energy",
                value="medium",
            ),
            EndingEnergyEvidence(
                evidence_id="end",
                dimension="ending_energy",
                value="low",
            ),
            DiscoveryPercentEvidence(
                evidence_id="discovery",
                dimension="discovery_percent",
                value=20,
            ),
        ),
    )
    return ObjectiveAssessor().assess(request)


def questionnaire(*artists: str):
    request = ArtistQuestionnaireRequest(
        objective=ArtistQuestionnaireObjective(
            objective_id=OBJECTIVE_ID,
            statement=OBJECTIVE_STATEMENT,
        ),
        seed_evidence=tuple(
            ArtistSeedEvidence(
                evidence_id=f"artist-{index}",
                artist_name=artist,
                source="manual_scope",
                rationale=f"{artist} was supplied as an inspection boundary.",
            )
            for index, artist in enumerate(artists, start=1)
        ),
    )
    return ArtistQuestionnaireSeedGenerator().generate(request)


def payload(
    track_id: str,
    artist_name: str,
    *,
    title: str = "Track",
    duration_seconds: int = 240,
    source_type: str = "manual_evidence",
) -> str:
    return json.dumps(
        {
            "track_id": track_id,
            "title": title,
            "artist_name": artist_name,
            "duration_seconds": duration_seconds,
            "provenance": {
                "source_type": source_type,
                "source_reference": f"source:{track_id}",
                "rationale": "Serialized evidence supplied this track record.",
            },
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def validation_request(
    records: tuple[EvidenceSnapshotRecord, ...],
    *,
    artists: tuple[str, ...] = ("Björk", "Kraftwerk"),
) -> TrackEvidenceValidationRequest:
    return TrackEvidenceValidationRequest(
        objective_assessment=objective_assessment(),
        artist_questionnaire=questionnaire(*artists),
        snapshot=EvidenceSnapshot(snapshot_id="snapshot-001", records=records),
    )


def test_mixed_snapshot_is_partitioned_without_suppressing_valid_records() -> None:
    malformed = json.dumps(
        {
            "track_id": "broken",
            "title": "Incomplete",
            "artist_name": "Björk",
            "provenance": {
                "source_type": "imported_evidence",
                "source_reference": "row:7",
                "rationale": "Imported row omitted duration.",
            },
        },
        separators=(",", ":"),
    )
    request = validation_request(
        (
            EvidenceSnapshotRecord(
                record_id="record-c",
                payload_json=payload("track-c", "Kraftwerk"),
            ),
            EvidenceSnapshotRecord(record_id="record-b", payload_json=malformed),
            EvidenceSnapshotRecord(
                record_id="record-a",
                payload_json=payload("track-a", "Björk"),
            ),
        )
    )

    artifact = TrackEvidenceValidator().validate(request)

    assert artifact.summary.input_record_count == 3
    assert artifact.summary.validated_record_count == 2
    assert artifact.summary.rejected_record_count == 1
    assert tuple(item.record_id for item in artifact.validated_records) == (
        "record-a",
        "record-c",
    )
    assert tuple(item.record_id for item in artifact.rejected_records) == ("record-b",)
    assert artifact.rejected_records[0].issues[0].code is (
        TrackEvidenceIssueCode.TRACK_DURATION_MISSING
    )


def test_rejected_payload_is_preserved_losslessly() -> None:
    original = '{ "track_id": "broken", "title": null }\r\n'
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="lossless", payload_json=original),)
        )
    )

    assert artifact.rejected_records[0].source_payload_json == original


def test_invalid_json_is_a_record_level_rejection_when_record_is_identifiable() -> None:
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="bad-json", payload_json="{oops"),)
        )
    )

    assert artifact.summary.rejected_record_count == 1
    assert artifact.rejected_records[0].issues[0].code is (
        TrackEvidenceIssueCode.RECORD_INVALID_JSON
    )


def test_snapshot_level_duplicate_record_ids_fail_closed() -> None:
    with pytest.raises(ValidationError, match="snapshot record IDs must be unique"):
        EvidenceSnapshot(
            snapshot_id="duplicate-envelope",
            records=(
                EvidenceSnapshotRecord(record_id="same", payload_json="{}"),
                EvidenceSnapshotRecord(record_id="same", payload_json="[]"),
            ),
        )


def test_snapshot_level_objective_correspondence_fails_closed() -> None:
    other_questionnaire = ArtistQuestionnaireSeedGenerator().generate(
        ArtistQuestionnaireRequest(
            objective=ArtistQuestionnaireObjective(
                objective_id="other",
                statement=OBJECTIVE_STATEMENT,
            ),
            seed_evidence=(),
        )
    )
    with pytest.raises(ValidationError, match="must correspond exactly"):
        TrackEvidenceValidationRequest(
            objective_assessment=objective_assessment(),
            artist_questionnaire=other_questionnaire,
            snapshot=EvidenceSnapshot(snapshot_id="snapshot", records=()),
        )


def test_snapshot_level_clarification_required_assessment_fails_closed() -> None:
    insufficient = ObjectiveAssessor().assess(
        ObjectiveAssessmentRequest(
            objective=Objective(
                objective_id=OBJECTIVE_ID,
                statement=OBJECTIVE_STATEMENT,
            ),
            evidence=(),
        )
    )
    with pytest.raises(ValidationError, match="assessment must be sufficient"):
        TrackEvidenceValidationRequest(
            objective_assessment=insufficient,
            artist_questionnaire=questionnaire("Björk"),
            snapshot=EvidenceSnapshot(snapshot_id="snapshot", records=()),
        )


def test_empty_snapshot_produces_a_complete_empty_partition() -> None:
    artifact = TrackEvidenceValidator().validate(validation_request(()))

    assert artifact.input_record_ids == ()
    assert artifact.validated_records == ()
    assert artifact.rejected_records == ()
    assert artifact.summary.input_record_count == 0


def test_all_duplicate_track_id_participants_are_rejected() -> None:
    incomplete_duplicate = json.dumps(
        {
            "track_id": "duplicate",
            "title": "Second",
            "artist_name": "Björk",
            "provenance": {
                "source_type": "local_metadata",
                "source_reference": "local:2",
                "rationale": "Second record has no duration.",
            },
        },
        separators=(",", ":"),
    )
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (
                EvidenceSnapshotRecord(
                    record_id="first",
                    payload_json=payload("duplicate", "Björk"),
                ),
                EvidenceSnapshotRecord(
                    record_id="second",
                    payload_json=incomplete_duplicate,
                ),
            )
        )
    )

    assert artifact.validated_records == ()
    assert tuple(item.record_id for item in artifact.rejected_records) == (
        "first",
        "second",
    )
    assert all(
        TrackEvidenceIssueCode.DUPLICATE_TRACK_ID
        in tuple(issue.code for issue in item.issues)
        for item in artifact.rejected_records
    )


def test_exact_artist_scope_is_enforced_without_normalization() -> None:
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (
                EvidenceSnapshotRecord(
                    record_id="case-variant",
                    payload_json=payload("case-track", "björk"),
                ),
            ),
            artists=("Björk",),
        )
    )

    assert artifact.rejected_records[0].issues[0].code is (
        TrackEvidenceIssueCode.TRACK_ARTIST_OUT_OF_SCOPE
    )
    assert artifact.preference_established is False
    assert artifact.eligibility_established is False
    assert artifact.suitability_established is False
    assert artifact.familiarity_established is False


@pytest.mark.parametrize(
    "source_type",
    (
        "provider_metadata",
        "local_metadata",
        "acoustic_analysis",
        "manual_evidence",
        "imported_evidence",
        "future_source_not_known_to_validator",
    ),
)
def test_source_type_is_preserved_but_does_not_change_validation(
    source_type: str,
) -> None:
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (
                EvidenceSnapshotRecord(
                    record_id="source-neutral",
                    payload_json=payload(
                        "source-neutral-track",
                        "Björk",
                        source_type=source_type,
                    ),
                ),
            )
        )
    )

    assert artifact.validated_records[0].provenance.source_type == source_type


def test_issue_precedence_is_fixed_and_extra_fields_use_utf8_order() -> None:
    malformed = json.dumps(
        {"zeta": 1, "alpha": 2, "track_id": " invalid "},
        separators=(",", ":"),
    )
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="many-issues", payload_json=malformed),)
        )
    )

    issues = artifact.rejected_records[0].issues
    assert tuple((issue.code, issue.field_path) for issue in issues) == (
        (TrackEvidenceIssueCode.RECORD_EXTRA_FIELD, "$.alpha"),
        (TrackEvidenceIssueCode.RECORD_EXTRA_FIELD, "$.zeta"),
        (TrackEvidenceIssueCode.TRACK_ID_INVALID, "$.track_id"),
        (TrackEvidenceIssueCode.TRACK_TITLE_MISSING, "$.title"),
        (TrackEvidenceIssueCode.TRACK_ARTIST_MISSING, "$.artist_name"),
        (TrackEvidenceIssueCode.TRACK_DURATION_MISSING, "$.duration_seconds"),
        (TrackEvidenceIssueCode.EVIDENCE_PROVENANCE_MISSING, "$.provenance"),
    )


def test_reordered_snapshots_produce_equal_artifacts_and_identical_bytes() -> None:
    records = (
        EvidenceSnapshotRecord(
            record_id="z-record",
            payload_json=payload("z-track", "Kraftwerk"),
        ),
        EvidenceSnapshotRecord(
            record_id="a-record",
            payload_json=payload("a-track", "Björk"),
        ),
    )
    first = TrackEvidenceValidator().validate(validation_request(records))
    second = TrackEvidenceValidator().validate(
        validation_request(tuple(reversed(records)))
    )

    assert first == second
    assert serialize_track_evidence_validation(first) == (
        serialize_track_evidence_validation(second)
    )


def test_every_identifiable_input_record_appears_exactly_once() -> None:
    records = (
        EvidenceSnapshotRecord(record_id="valid", payload_json=payload("one", "Björk")),
        EvidenceSnapshotRecord(record_id="invalid", payload_json="[]"),
    )
    artifact = TrackEvidenceValidator().validate(validation_request(records))

    partition_ids = tuple(item.record_id for item in artifact.validated_records) + tuple(
        item.record_id for item in artifact.rejected_records
    )
    assert set(partition_ids) == set(artifact.input_record_ids)
    assert len(partition_ids) == len(set(partition_ids)) == 2


def test_artifact_schema_rejects_partition_tampering() -> None:
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="valid", payload_json=payload("one", "Björk")),)
        )
    )
    tampered = artifact.model_dump(mode="json")
    tampered["validated_records"] = []

    with pytest.raises(ValidationError, match="exactly one partition"):
        TrackEvidenceValidationArtifact.model_validate(tampered)


def test_artifact_schema_rejects_validated_provenance_tampering() -> None:
    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="valid", payload_json=payload("one", "Björk")),)
        )
    )
    tampered = artifact.model_dump(mode="json")
    tampered["validated_records"][0]["provenance"]["source_type"] = " "

    with pytest.raises(ValidationError, match="provenance strings must be nonblank"):
        TrackEvidenceValidationArtifact.model_validate(tampered)


def test_inputs_and_outputs_are_immutable_and_schema_is_explicit() -> None:
    request = validation_request(
        (EvidenceSnapshotRecord(record_id="valid", payload_json=payload("one", "Björk")),)
    )
    artifact = TrackEvidenceValidator().validate(request)

    assert request.schema_version == TRACK_EVIDENCE_SCHEMA_VERSION
    assert artifact.schema_version == TRACK_EVIDENCE_SCHEMA_VERSION
    with pytest.raises(ValidationError):
        request.snapshot.snapshot_id = "changed"
    with pytest.raises(ValidationError):
        artifact.snapshot_id = "changed"


def test_validation_is_isolated_from_downstream_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("track evidence validation called a downstream layer")

    monkeypatch.setattr(TrackScorer, "score", unexpected_call)
    monkeypatch.setattr(CandidateSelector, "select", unexpected_call)
    monkeypatch.setattr(SequentialPlaylistConstructor, "construct", unexpected_call)
    monkeypatch.setattr(PlaylistJourneyEvaluator, "evaluate", unexpected_call)

    artifact = TrackEvidenceValidator().validate(
        validation_request(
            (EvidenceSnapshotRecord(record_id="valid", payload_json=payload("one", "Björk")),)
        )
    )

    assert artifact.validated_records[0].track_id == "one"
    assert artifact.scoring_performed is False
    assert artifact.selection_performed is False
    assert artifact.playlist_construction_performed is False

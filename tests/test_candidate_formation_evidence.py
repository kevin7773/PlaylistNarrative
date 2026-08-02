from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.candidate_formation import (
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    ContextInputEvidence,
    EvidenceObservation,
    EvidenceState,
    FamiliarityEvidenceArtifact,
    FamiliarityEvidenceRecord,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    ObjectiveContextEvidenceRecord,
    TasteEvidenceRecord,
    TrackFeatureEvidenceArtifact,
    TrackFeatureEvidenceRecord,
    UnitIntervalEvidence,
    serialize_candidate_source_evidence,
)
from playlist_narrative_engine.taste.ratings import Rating


def observation(
    evidence_id: str,
    payload_json: str = '{"value":0.75}',
) -> EvidenceObservation:
    return EvidenceObservation(
        evidence_id=evidence_id,
        source_type="manual_evidence",
        source_reference=f"source:{evidence_id}",
        payload_json=payload_json,
    )


def measured(value: float = 0.75, evidence_id: str = "evidence-1") -> UnitIntervalEvidence:
    return UnitIntervalEvidence(
        state=EvidenceState.MEASURED,
        value=value,
        observations=(observation(evidence_id),),
    )


def test_measured_numeric_evidence_requires_value_and_provenance() -> None:
    evidence = measured()

    assert evidence.value == 0.75
    assert evidence.state is EvidenceState.MEASURED

    with pytest.raises(ValidationError, match="requires a value and observations"):
        UnitIntervalEvidence(state="measured", observations=())


@pytest.mark.parametrize(
    ("state", "observations"),
    (
        (EvidenceState.UNAVAILABLE, ()),
        (
            EvidenceState.CONFLICTING,
            (observation("a"), observation("b", '{"value":0.25}')),
        ),
        (EvidenceState.UNSUPPORTED, (observation("unsupported"),)),
        (
            EvidenceState.EXPLICITLY_INAPPLICABLE,
            (observation("inapplicable", '{"reason":"not applicable"}'),),
        ),
    ),
)
def test_non_available_states_are_distinct_and_cannot_carry_resolved_values(
    state: EvidenceState,
    observations: tuple[EvidenceObservation, ...],
) -> None:
    evidence = UnitIntervalEvidence(state=state, observations=observations)

    assert evidence.state is state
    assert evidence.value is None

    with pytest.raises(ValidationError, match="cannot contain a resolved value"):
        UnitIntervalEvidence(state=state, value=0.5, observations=observations)


def test_state_specific_observation_requirements_are_enforced() -> None:
    with pytest.raises(ValidationError, match="cannot contain observations"):
        UnitIntervalEvidence(
            state="unavailable",
            observations=(observation("unexpected"),),
        )
    with pytest.raises(ValidationError, match="at least two observations"):
        UnitIntervalEvidence(
            state="conflicting",
            observations=(observation("only-one"),),
        )
    with pytest.raises(ValidationError, match="requires observations"):
        UnitIntervalEvidence(state="unsupported", observations=())
    with pytest.raises(ValidationError, match="requires observations"):
        UnitIntervalEvidence(state="explicitly_inapplicable", observations=())


def test_observations_are_canonicalized_and_require_unique_evidence_ids() -> None:
    reordered = UnitIntervalEvidence(
        state="conflicting",
        observations=(observation("z"), observation("a")),
    )
    canonical = UnitIntervalEvidence(
        state="conflicting",
        observations=(observation("a"), observation("z")),
    )

    assert reordered == canonical
    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        UnitIntervalEvidence(
            state="conflicting",
            observations=(observation("same"), observation("same")),
        )


def test_taste_evidence_preserves_unknown_without_numeric_preference_claim() -> None:
    artifact = LocalTasteEvidenceArtifact(
        artifact_id="taste-001",
        profile_id="profile-001",
        records=(
            TasteEvidenceRecord(
                artist_name="Björk",
                state="measured",
                rating=Rating.UNKNOWN,
                observations=(observation("rating-bjork", '{"rating":"Unknown"}'),),
            ),
        ),
    )

    assert artifact.records[0].rating is Rating.UNKNOWN
    assert artifact.numeric_preference_established is False
    assert artifact.eligibility_established is False
    assert artifact.candidate_formation_performed is False


def test_taste_artifact_canonicalizes_exact_unique_artist_identity() -> None:
    record = TasteEvidenceRecord(
        artist_name="Björk",
        state="measured",
        rating=Rating.LOVE,
        observations=(observation("love"),),
    )
    with pytest.raises(ValidationError, match="must be unique"):
        LocalTasteEvidenceArtifact(
            artifact_id="taste",
            profile_id="profile",
            records=(record, record),
        )
    zulu = TasteEvidenceRecord(
        artist_name="Zulu",
        state="unavailable",
        observations=(),
    )
    alpha = TasteEvidenceRecord(
        artist_name="Alpha",
        state="unavailable",
        observations=(),
    )
    reordered = LocalTasteEvidenceArtifact(
        artifact_id="taste",
        profile_id="profile",
        records=(zulu, alpha),
    )
    canonical = LocalTasteEvidenceArtifact(
        artifact_id="taste",
        profile_id="profile",
        records=(alpha, zulu),
    )
    assert reordered == canonical


def test_exact_identity_does_not_fold_case_punctuation_or_unicode_form() -> None:
    composed = "Björk"
    decomposed = "Bjo\u0308rk"
    identities = (composed, decomposed, "björk", "Björk!")

    artifact = LocalTasteEvidenceArtifact(
        artifact_id="exact-identities",
        profile_id="profile",
        records=tuple(
            TasteEvidenceRecord(
                artist_name=artist_name,
                state="unavailable",
                observations=(),
            )
            for artist_name in reversed(identities)
        ),
    )

    assert len(artifact.records) == 4
    assert {record.artist_name for record in artifact.records} == set(identities)
    assert composed != decomposed
    with pytest.raises(ValidationError, match="nonblank and exact"):
        TasteEvidenceRecord(
            artist_name=" Björk",
            state="unavailable",
            observations=(),
        )


def test_familiarity_artifact_is_snapshot_scoped_and_deterministic() -> None:
    artifact = FamiliarityEvidenceArtifact(
        artifact_id="familiarity-001",
        profile_id="profile-001",
        track_snapshot_id="snapshot-001",
        records=(
            FamiliarityEvidenceRecord(
                track_id="track-a",
                artist_name="Björk",
                familiarity=measured(0.8, "play-history-a"),
            ),
            FamiliarityEvidenceRecord(
                track_id="track-b",
                artist_name="Kraftwerk",
                familiarity=UnitIntervalEvidence(
                    state="unavailable",
                    observations=(),
                ),
            ),
        ),
    )

    assert artifact.track_snapshot_id == "snapshot-001"
    assert tuple(record.track_id for record in artifact.records) == (
        "track-a",
        "track-b",
    )
    assert artifact.candidate_formation_performed is False

    with pytest.raises(ValidationError, match="nonblank and exact"):
        FamiliarityEvidenceRecord(
            track_id="track-a",
            artist_name="björk ",
            familiarity=measured(),
        )


def test_track_feature_artifact_owns_only_feature_dimensions() -> None:
    record = TrackFeatureEvidenceRecord(
        track_id="track-a",
        artist_name="Björk",
        energy=measured(0.7, "energy"),
        instrumentalness=measured(0.9, "instrumentalness"),
        lyrical_distraction=measured(0.1, "lyrics"),
        groove=measured(0.6, "groove"),
    )
    artifact = TrackFeatureEvidenceArtifact(
        artifact_id="features-001",
        track_snapshot_id="snapshot-001",
        records=(record,),
    )

    assert record.model_fields_set == {
        "track_id",
        "artist_name",
        "energy",
        "instrumentalness",
        "lyrical_distraction",
        "groove",
    }
    assert artifact.candidate_formation_performed is False


def test_context_evidence_preserves_measured_fit_and_rule_inputs() -> None:
    original = '{ "activity": "focused coding", "interruptions": false }\r\n'
    artifact = ObjectiveContextEvidenceArtifact(
        artifact_id="context-001",
        objective_id="coding-focus",
        objective_statement="Support a focused coding session.",
        context_id="workstation",
        journey_id="journey-001",
        track_snapshot_id="snapshot-001",
        records=(
            ObjectiveContextEvidenceRecord(
                track_id="track-a",
                artist_name="Björk",
                context_fit=measured(0.85, "context-fit"),
                inputs=(
                    ContextInputEvidence(
                        input_name="listening_context",
                        state="measured",
                        resolved_payload_json=original,
                        observations=(observation("context", original),),
                    ),
                ),
            ),
        ),
    )

    assert artifact.records[0].inputs[0].resolved_payload_json == original
    assert artifact.records[0].context_fit.value == 0.85
    assert artifact.candidate_formation_performed is False
    assert artifact.scoring_performed is False
    assert artifact.eligibility_established is False
    assert artifact.ranking_performed is False
    assert artifact.recommendation_claims is False

    with pytest.raises(ValidationError, match="nonblank and exact"):
        ObjectiveContextEvidenceArtifact(
            artifact_id="context-001",
            objective_id="coding-focus",
            objective_statement="Support a focused coding session.",
            journey_id=" journey-001",
            context_id="workstation",
            track_snapshot_id="snapshot-001",
            records=(),
        )


def test_context_inputs_require_valid_json_and_are_canonicalized() -> None:
    with pytest.raises(ValidationError, match="must be valid JSON"):
        ContextInputEvidence(
            input_name="context",
            state="measured",
            resolved_payload_json="{broken",
            observations=(observation("context"),),
        )
    zeta = ContextInputEvidence(
        input_name="zeta",
        state="unavailable",
        observations=(),
    )
    alpha = ContextInputEvidence(
        input_name="alpha",
        state="unavailable",
        observations=(),
    )
    reordered = ObjectiveContextEvidenceRecord(
        track_id="track",
        artist_name="Artist",
        context_fit=UnitIntervalEvidence(
            state="unavailable",
            observations=(),
        ),
        inputs=(zeta, alpha),
    )
    canonical = ObjectiveContextEvidenceRecord(
        track_id="track",
        artist_name="Artist",
        context_fit=UnitIntervalEvidence(
            state="unavailable",
            observations=(),
        ),
        inputs=(alpha, zeta),
    )

    assert reordered == canonical


def test_artifacts_are_frozen_and_reject_extra_fields() -> None:
    artifact = FamiliarityEvidenceArtifact(
        artifact_id="familiarity",
        profile_id="profile",
        track_snapshot_id="snapshot",
        records=(),
    )

    assert artifact.schema_version == CANDIDATE_EVIDENCE_SCHEMA_VERSION
    with pytest.raises(ValidationError):
        artifact.artifact_id = "changed"
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FamiliarityEvidenceArtifact.model_validate(
            {
                **artifact.model_dump(mode="json"),
                "unexpected": True,
            }
        )


def test_every_source_artifact_is_explicitly_versioned() -> None:
    artifacts = (
        LocalTasteEvidenceArtifact(
            artifact_id="taste",
            profile_id="profile",
            records=(),
        ),
        FamiliarityEvidenceArtifact(
            artifact_id="familiarity",
            profile_id="profile",
            track_snapshot_id="snapshot",
            records=(),
        ),
        TrackFeatureEvidenceArtifact(
            artifact_id="features",
            track_snapshot_id="snapshot",
            records=(),
        ),
        ObjectiveContextEvidenceArtifact(
            artifact_id="context",
            objective_id="objective",
            objective_statement="Support the requested experience.",
            journey_id="journey",
            context_id="context",
            track_snapshot_id="snapshot",
            records=(),
        ),
    )

    assert all(
        artifact.schema_version == CANDIDATE_EVIDENCE_SCHEMA_VERSION
        for artifact in artifacts
    )
    assert all(artifact.candidate_formation_performed is False for artifact in artifacts)


def test_cf1_source_artifacts_remain_free_of_cf2_fields() -> None:
    source_artifacts = (
        LocalTasteEvidenceArtifact,
        FamiliarityEvidenceArtifact,
        TrackFeatureEvidenceArtifact,
        ObjectiveContextEvidenceArtifact,
    )
    forbidden_fields = {
        "policy",
        "formed",
        "withheld",
        "candidate",
        "field_evidence",
        "withholding_reasons",
    }

    assert all(
        forbidden_fields.isdisjoint(artifact_type.model_fields)
        for artifact_type in source_artifacts
    )


def test_canonical_serialization_is_stable_utf8_and_schema_ordered() -> None:
    artifact = LocalTasteEvidenceArtifact(
        artifact_id="taste-001",
        profile_id="profile-001",
        records=(
            TasteEvidenceRecord(
                artist_name="Björk",
                state="measured",
                rating=Rating.LIKE,
                observations=(observation("rating"),),
            ),
        ),
    )

    first = serialize_candidate_source_evidence(artifact)
    second = serialize_candidate_source_evidence(artifact)
    parsed = json.loads(first)

    assert first == second
    assert "Björk".encode("utf-8") in first
    assert tuple(parsed) == (
        "schema_version",
        "artifact_kind",
        "artifact_id",
        "profile_id",
        "ordering_rule",
        "records",
        "eligibility_established",
        "numeric_preference_established",
        "scoring_performed",
        "ranking_performed",
        "candidate_formation_performed",
        "recommendation_claims",
    )


def test_equivalent_collection_order_produces_equal_objects_and_bytes() -> None:
    caller_observations = [observation("z"), observation("a")]
    alpha = TasteEvidenceRecord(
        artist_name="Alpha",
        state="conflicting",
        observations=caller_observations,
    )
    zulu = TasteEvidenceRecord(
        artist_name="Zulu",
        state="unavailable",
        observations=(),
    )
    caller_records = [zulu, alpha]
    first = LocalTasteEvidenceArtifact(
        artifact_id="taste",
        profile_id="profile",
        records=caller_records,
    )
    second = LocalTasteEvidenceArtifact(
        artifact_id="taste",
        profile_id="profile",
        records=(
            TasteEvidenceRecord(
                artist_name="Alpha",
                state="conflicting",
                observations=(observation("a"), observation("z")),
            ),
            zulu,
        ),
    )

    assert first == second
    assert serialize_candidate_source_evidence(first) == (
        serialize_candidate_source_evidence(second)
    )
    assert [item.evidence_id for item in caller_observations] == ["z", "a"]
    assert [item.artist_name for item in caller_records] == ["Zulu", "Alpha"]

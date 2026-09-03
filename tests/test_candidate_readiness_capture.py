from __future__ import annotations

import json
import threading
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
from journey_authority_helpers import journey_authority
from playlist_narrative_engine.candidate_readiness import (
    AUTHORITY_DEFINITION_SHA256, VOCABULARY_SHA256,
    ActiveFocusCandidateReadinessAuthorityArtifact,
    ActiveFocusCandidateReadinessDeclaration,
    ActiveFocusCandidateReadinessProducer,
    ActiveFocusCandidateReadinessVerifier,
    CandidateReadinessInvalidInput,
    CandidateReadinessOccurrenceRepository,
    occurrence_sha256,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionProducer,
    PennyLocalITunesXMLAcquisitionVerifier,
    PennyLocalITunesXMLIntakeProducer,
)
from playlist_narrative_engine.local_authorization import LocalPrincipalAuthorityProducer, LocalPrincipalAuthorityRepository
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.track_evidence import (
    EvidenceProvenance, TrackEvidenceValidationArtifact,
    TrackEvidenceValidationSummary, ValidatedTrackEvidence,
)
from playlist_narrative_engine.candidate_readiness.schemas import _bind_occurrence_recorder


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"


def governed_declaration(producer, track_id, **measurements):
    payload = {"schema_version": "1.0", "track_id": track_id}
    for field in (
        "familiarity", "energy", "instrumentalness", "lyrical_distraction",
        "groove", "active_focus_context_fit",
    ):
        if field in measurements:
            payload[field] = measurements[field]
    return producer.capture_declaration(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def build_readiness(monkeypatch, session, *, declarations=None, rating=Rating.LOVE, extra_ratings=()):
    principal = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    principal.create_initial()
    intake = PennyLocalITunesXMLIntakeProducer(principal.verifier)
    request = intake.create_request()
    monkeypatch.setattr(intake_module, "_native_windows_single_file_selection", lambda: FIXTURE)
    evidence = intake.capture_selected_file(request)
    acquisition = PennyLocalITunesXMLAcquisitionProducer(intake.verifier).produce_authoritative(evidence)
    objective = Objective(objective_id="active-focus-readiness-proof", statement="Support a focused thirty-minute listening journey.")
    _, accepted, journey = journey_authority(objective, duration_minutes=30)
    validation = validation_for(acquisition, accepted)
    artist = validation.validated_records[0].artist_name
    if rating is not None:
        ArtistRepository(session).set_rating(artist, rating)
    for name, extra_rating in extra_ratings:
        ArtistRepository(session).set_rating(name, extra_rating)
    occurrences = CandidateReadinessOccurrenceRepository()
    acquisition_verifier = PennyLocalITunesXMLAcquisitionVerifier(intake.verifier)
    producer = ActiveFocusCandidateReadinessProducer(
        principal_verifier=principal.verifier,
        acquisition_verifier=acquisition_verifier,
        artist_repository=ArtistRepository(session),
        occurrence_repository=occurrences,
    )
    if declarations is None:
        declarations = (
            governed_declaration(
                producer,
                validation.validated_records[0].track_id,
                familiarity="LEVEL_4", energy="LEVEL_2", instrumentalness="LEVEL_1",
                lyrical_distraction="LEVEL_1", groove="LEVEL_3", active_focus_context_fit="LEVEL_4",
            ),
        )
    else:
        declarations = tuple(
            governed_declaration(
                producer,
                item["track_id"],
                **{key: value for key, value in item.items() if key != "track_id"},
            )
            if isinstance(item, dict)
            else item
            for item in declarations
        )
    occurrence = producer.capture(acquisition_authority=acquisition, track_validation=validation, accepted_objective=accepted, journey_plan=journey, declarations=declarations)
    verifier = ActiveFocusCandidateReadinessVerifier(principal_verifier=principal.verifier, acquisition_verifier=acquisition_verifier, occurrence_repository=occurrences)
    return principal, producer, verifier, occurrences, acquisition, validation, accepted, journey, occurrence


def validation_for(acquisition, accepted):
    snapshot = acquisition.source_neutral_acquisition_result.evidence_snapshot
    validated = []
    for index, item in enumerate(sorted(snapshot.records, key=lambda row: row.record_id.encode("utf-8")), 1):
        payload = json.loads(item.payload_json)
        validated.append(ValidatedTrackEvidence(
            ordinal=index, record_id=item.record_id, source_payload_json=item.payload_json,
            track_id=payload["track_id"], title=payload["title"], artist_name=payload["artist_name"],
            duration_seconds=payload["duration_seconds"], provenance=EvidenceProvenance.model_validate(payload["provenance"]),
        ))
    return TrackEvidenceValidationArtifact(
        snapshot_id=snapshot.snapshot_id,
        objective_id=accepted.objective.objective_id,
        objective_statement=accepted.objective.statement,
        artist_inspection_scope=tuple(sorted({item.artist_name for item in validated}, key=lambda text: text.encode("utf-8"))),
        input_record_ids=tuple(item.record_id for item in validated),
        validated_records=tuple(validated), rejected_records=(),
        summary=TrackEvidenceValidationSummary(input_record_count=len(validated), validated_record_count=len(validated), rejected_record_count=0),
    )


def test_current_tip_capture_and_historical_verification(monkeypatch, session) -> None:
    principal, _, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    assert verifier.verify(occurrence)
    assert occurrence.vocabulary_sha256 == VOCABULARY_SHA256
    assert occurrence.authority_definition_version == "1.1"
    assert occurrence.authority_definition_sha256 == AUTHORITY_DEFINITION_SHA256
    assert occurrence.observations[0].artist_name == occurrence.track_validation.validated_records[0].artist_name
    assert occurrence.observations[0].title == occurrence.track_validation.validated_records[0].title
    principal.create_successor(occurrence.principal_authority)
    assert verifier.verify(occurrence)


def test_stale_principal_and_historical_authority_cannot_capture(monkeypatch, session) -> None:
    principal, producer, _, _, acquisition, validation, accepted, journey, occurrence = build_readiness(monkeypatch, session)
    principal.create_successor(occurrence.principal_authority)
    with pytest.raises(CandidateReadinessInvalidInput, match="current principal"):
        producer.capture(acquisition_authority=acquisition, track_validation=validation, accepted_objective=accepted, journey_plan=journey, declarations=(ActiveFocusCandidateReadinessDeclaration(track_id=validation.validated_records[1].track_id, energy="LEVEL_2"),))


def test_reconstructed_objects_and_substitution_have_no_authority(monkeypatch, session) -> None:
    principal, _, verifier, _, acquisition, _, _, _, occurrence = build_readiness(monkeypatch, session)
    reconstructed = ActiveFocusCandidateReadinessAuthorityArtifact.model_validate(occurrence.model_dump(mode="json"))
    empty_verifier = ActiveFocusCandidateReadinessVerifier(
        principal_verifier=principal.verifier,
        acquisition_verifier=verifier._acquisition_verifier,
        occurrence_repository=CandidateReadinessOccurrenceRepository(),
    )
    assert not empty_verifier.verify(reconstructed)
    for update in (
        {"artifact_id":"substituted"}, {"vocabulary_sha256":"0"*64},
        {"authority_definition_version":"1.0"}, {"track_validation_sha256":"0"*64},
        {"journey_sha256":"0"*64}, {"acquisition_authority_artifact_id":"other"},
        {"occurrence_sha256":"0"*64},
    ):
        assert not verifier.verify(occurrence.model_copy(update=update))
    changed = occurrence.observations[0].model_copy(update={"artist_name":"Replacement"})
    assert not verifier.verify(occurrence.model_copy(update={"observations": (changed,)}))
    assert acquisition.media_inspection_performed is False


def test_duplicate_or_all_missing_declarations_do_not_gain_measurements(monkeypatch, session) -> None:
    principal, producer, _, _, acquisition, validation, accepted, journey, _ = build_readiness(monkeypatch, session)
    empty = governed_declaration(
        producer,
        "itunes-windows-library:9C9E2747D29AB9A8/track:60F3F28BD78BD511",
    )
    occurrence = producer.capture(
        acquisition_authority=acquisition,
        track_validation=validation,
        accepted_objective=accepted,
        journey_plan=journey,
        declarations=(empty,),
    )
    assert occurrence.observations == ()
    assert occurrence.familiarity_evidence.records == ()
    with pytest.raises(ValidationError):
        ActiveFocusCandidateReadinessDeclaration(track_id=validation.validated_records[0].track_id, energy=0.5)


def test_duplicate_track_declarations_fail_closed(monkeypatch, session) -> None:
    principal, producer, _, _, acquisition, validation, accepted, journey, _ = build_readiness(monkeypatch, session)
    item = governed_declaration(producer, validation.validated_records[1].track_id, energy="LEVEL_2")
    with pytest.raises(CandidateReadinessInvalidInput, match="unique track"):
        producer.capture(acquisition_authority=acquisition, track_validation=validation, accepted_objective=accepted, journey_plan=journey, declarations=(item, item))


@pytest.mark.parametrize(
    "payload",
    (
        '{"schema_version":"1.0","track_id":"track-1","energy":"LEVEL_1","energy":"LEVEL_2"}',
        '{"schema_version":"1.0","track_id":"track-1","energy":null}',
        '{"schema_version":"1.0","track_id":"track-1","unknown":"LEVEL_2"}',
        '{"schema_version":"1.0","track_id":"track-1","title":"replacement"}',
        '{"schema_version":"1.0","track_id":"track-1","artist_name":"replacement"}',
        '{"schema_version":"1.0","track_id":"track-1","provider":"replacement"}',
        '{"schema_version":"1.0","track_id":"track-1","path":"replacement"}',
        '{"schema_version":"1.0","track_id":"track-1","media_bytes":"replacement"}',
    ),
)
def test_exact_declaration_capture_rejects_ambiguous_null_and_extra_fields(
    monkeypatch, session, payload,
) -> None:
    _, producer, *_ = build_readiness(monkeypatch, session)
    with pytest.raises(CandidateReadinessInvalidInput, match="not exact"):
        producer.capture_declaration(payload)


def test_exact_declaration_capture_preserves_omission_and_rejects_unowned_models(
    monkeypatch, session,
) -> None:
    _, producer, _, _, acquisition, validation, accepted, journey, _ = build_readiness(
        monkeypatch, session
    )
    track_id = validation.validated_records[1].track_id
    exact = governed_declaration(producer, track_id, energy="LEVEL_2")
    assert exact.energy.value == "LEVEL_2"
    assert "familiarity" not in exact.model_fields_set
    direct = ActiveFocusCandidateReadinessDeclaration(track_id=track_id, energy="LEVEL_2")
    hidden = exact.model_copy(update={"artist_name": "replacement", "title": "replacement"})
    for declaration in (direct, hidden):
        with pytest.raises(CandidateReadinessInvalidInput, match="not captured"):
            producer.capture(
                acquisition_authority=acquisition,
                track_validation=validation,
                accepted_objective=accepted,
                journey_plan=journey,
                declarations=(declaration,),
            )


@pytest.mark.parametrize("field", ("duration_seconds", "title", "artist_name", "track_id"))
def test_structured_track_data_must_replay_from_exact_serialized_payload(
    monkeypatch, session, field,
) -> None:
    _, producer, _, _, acquisition, validation, accepted, journey, _ = build_readiness(
        monkeypatch, session
    )
    record = validation.validated_records[0]
    replacements = {
        "duration_seconds": record.duration_seconds + 1,
        "title": record.title + " replacement",
        "artist_name": record.artist_name + " replacement",
        "track_id": record.track_id + "replacement",
    }
    changed = record.model_copy(update={field: replacements[field]})
    changed_validation = validation.model_copy(
        update={"validated_records": (changed, *validation.validated_records[1:])}
    )
    declaration = governed_declaration(producer, record.track_id, energy="LEVEL_2")
    with pytest.raises(CandidateReadinessInvalidInput, match="not exact|does not replay"):
        producer.capture(
            acquisition_authority=acquisition,
            track_validation=changed_validation,
            accepted_objective=accepted,
            journey_plan=journey,
            declarations=(declaration,),
        )


def test_equivalent_looking_reencoded_source_payload_is_not_substitutable(
    monkeypatch, session,
) -> None:
    _, producer, _, _, acquisition, validation, accepted, journey, _ = build_readiness(
        monkeypatch, session
    )
    record = validation.validated_records[0]
    changed = record.model_copy(
        update={"source_payload_json": json.dumps(json.loads(record.source_payload_json))}
    )
    changed_validation = validation.model_copy(
        update={"validated_records": (changed, *validation.validated_records[1:])}
    )
    declaration = governed_declaration(producer, record.track_id, energy="LEVEL_2")
    with pytest.raises(CandidateReadinessInvalidInput, match="exact acquisition snapshot"):
        producer.capture(
            acquisition_authority=acquisition,
            track_validation=changed_validation,
            accepted_objective=accepted,
            journey_plan=journey,
            declarations=(declaration,),
        )


def test_occurrence_provenance_is_repository_local_opaque_and_copy_resistant(
    monkeypatch, session,
) -> None:
    principal, producer, verifier, repository, _, _, _, _, occurrence = build_readiness(
        monkeypatch, session
    )
    copied_repository = deepcopy(repository)
    copied_verifier = ActiveFocusCandidateReadinessVerifier(
        principal_verifier=principal.verifier,
        acquisition_verifier=verifier._acquisition_verifier,
        occurrence_repository=copied_repository,
    )
    assert not copied_verifier.verify(occurrence)

    fresh = CandidateReadinessOccurrenceRepository()
    fresh._artifacts.append(occurrence)
    forged_verifier = ActiveFocusCandidateReadinessVerifier(
        principal_verifier=principal.verifier,
        acquisition_verifier=verifier._acquisition_verifier,
        occurrence_repository=fresh,
    )
    forged = occurrence.model_copy(update={"occurrence_sha256": None})
    object.__setattr__(forged, "occurrence_sha256", occurrence_sha256(forged))
    fresh._artifacts.append(forged)
    assert not forged_verifier.verify(occurrence)
    assert not forged_verifier.verify(forged)
    assert not hasattr(repository, "_record")
    assert not hasattr(repository, "_record_authoritative")
    assert not hasattr(producer, "_recording_capability")
    with pytest.raises(TypeError, match="cannot be copied"):
        deepcopy(producer)
    with pytest.raises(TypeError, match="concrete readiness producer"):
        _bind_occurrence_recorder(CandidateReadinessOccurrenceRepository(), object())
    with pytest.raises(ValueError, match="already has a producer"):
        _bind_occurrence_recorder(CandidateReadinessOccurrenceRepository(), producer)
    assert verifier.verify(occurrence)


def test_record_time_successor_injection_is_not_an_accepted_repository(
    monkeypatch, session,
) -> None:
    class InterleavingRepository(CandidateReadinessOccurrenceRepository):
        pass

    principal, _, verifier, _, _, _, _, _, _ = build_readiness(monkeypatch, session)
    with pytest.raises(TypeError, match="concrete readiness occurrence repository"):
        ActiveFocusCandidateReadinessProducer(
            principal_verifier=principal.verifier,
            acquisition_verifier=verifier._acquisition_verifier,
            artist_repository=ArtistRepository(session),
            occurrence_repository=InterleavingRepository(),
        )


def test_principal_succession_cannot_interleave_at_occurrence_record_time(
    monkeypatch, session,
) -> None:
    principal, producer, verifier, _, acquisition, validation, accepted, journey, first = (
        build_readiness(monkeypatch, session)
    )
    declaration = governed_declaration(
        producer,
        validation.validated_records[1].track_id,
        energy="LEVEL_2",
    )
    successor_started = threading.Event()
    successor_completed = threading.Event()
    failures: list[BaseException] = []
    attribute = "_ActiveFocusCandidateReadinessProducer__record_occurrence"
    original_recorder = getattr(producer, attribute)

    def succeed() -> None:
        try:
            successor_started.set()
            principal.create_successor(first.principal_authority)
            successor_completed.set()
        except BaseException as exc:  # pragma: no cover - diagnostic capture
            failures.append(exc)

    def instrumented_recorder(artifact) -> None:
        thread = threading.Thread(target=succeed)
        thread.start()
        assert successor_started.wait(5)
        assert not successor_completed.wait(0.1)
        original_recorder(artifact)
        instrumented_recorder.thread = thread

    setattr(producer, attribute, instrumented_recorder)
    second = producer.capture(
        acquisition_authority=acquisition,
        track_validation=validation,
        accepted_objective=accepted,
        journey_plan=journey,
        declarations=(declaration,),
    )
    instrumented_recorder.thread.join(5)
    assert not failures
    assert successor_completed.is_set()
    assert verifier.verify(second)

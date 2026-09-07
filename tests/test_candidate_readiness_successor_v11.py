from __future__ import annotations

import hashlib
import inspect
import json
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
import playlist_narrative_engine.candidate_readiness.verifier_v11 as verifier_v11_module
from journey_authority_helpers import journey_authority
from playlist_narrative_engine.candidate_readiness import (
    AUTHORITY_DEFINITION_JSON,
    AUTHORITY_DEFINITION_SHA256,
    AUTHORITY_DEFINITION_V12_JSON,
    AUTHORITY_DEFINITION_V12_SHA256,
    PREFERENCE_POLICY_JSON,
    PREFERENCE_POLICY_SHA256,
    VOCABULARY_JSON,
    VOCABULARY_SHA256,
    ActiveFocusCandidateReadinessAuthorityArtifact,
    ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ActiveFocusCandidateReadinessProducerV11,
    ActiveFocusCandidateReadinessVerifier,
    ActiveFocusCandidateReadinessVerifierV11,
    CandidateReadinessInvalidInput,
    CandidateReadinessOccurrenceRepository,
    CandidateReadinessOccurrenceRepositoryV11,
    GuardedActiveFocusCandidateFormationBridge,
    GuardedActiveFocusCandidateFormationBridgeV11,
    VerifiedActiveFocusCandidateReadinessV11,
    verify_frozen_definitions,
    verify_frozen_definitions_v12,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionProducerV11,
    PennyLocalITunesXMLAcquisitionVerifier,
    PennyLocalITunesXMLAcquisitionVerifierV11,
    PennyLocalITunesXMLIntakeProducerV11,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from test_candidate_readiness_capture import (
    build_readiness,
    governed_declaration,
    validation_for,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)


def build_readiness_v11(monkeypatch, session, *, declarations=None):
    principal = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    principal.create_initial()
    intake = PennyLocalITunesXMLIntakeProducerV11(principal.verifier)
    request = intake.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: FIXTURE,
    )
    evidence = intake.capture_selected_file(request)
    acquisition = PennyLocalITunesXMLAcquisitionProducerV11(
        intake.verifier
    ).produce_authoritative(evidence)
    acquisition_verifier = PennyLocalITunesXMLAcquisitionVerifierV11(intake.verifier)
    objective = Objective(
        objective_id="active-focus-readiness-v11-proof",
        statement="Support a focused thirty-minute listening journey.",
    )
    _, accepted, journey = journey_authority(objective, duration_minutes=30)
    validation = validation_for(acquisition, accepted)
    ArtistRepository(session).set_rating(
        validation.validated_records[0].artist_name,
        Rating.LOVE,
    )
    occurrences = CandidateReadinessOccurrenceRepositoryV11()
    producer = ActiveFocusCandidateReadinessProducerV11(
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
                familiarity="LEVEL_4",
                energy="LEVEL_2",
                instrumentalness="LEVEL_1",
                lyrical_distraction="LEVEL_1",
                groove="LEVEL_3",
                active_focus_context_fit="LEVEL_4",
            ),
        )
    occurrence = producer.capture(
        acquisition_authority=acquisition,
        track_validation=validation,
        accepted_objective=accepted,
        journey_plan=journey,
        declarations=declarations,
    )
    verifier = ActiveFocusCandidateReadinessVerifierV11(
        principal_verifier=principal.verifier,
        acquisition_verifier=acquisition_verifier,
        occurrence_repository=occurrences,
    )
    return (
        principal,
        producer,
        verifier,
        occurrences,
        acquisition,
        validation,
        accepted,
        journey,
        occurrence,
    )


def test_successor_canonical_authority_and_declaration_version_are_exact() -> None:
    assert hashlib.sha256(VOCABULARY_JSON.encode()).hexdigest() == VOCABULARY_SHA256
    assert hashlib.sha256(AUTHORITY_DEFINITION_JSON.encode()).hexdigest() == (
        AUTHORITY_DEFINITION_SHA256
    )
    assert len(AUTHORITY_DEFINITION_V12_JSON.encode()) == 1778
    assert hashlib.sha256(AUTHORITY_DEFINITION_V12_JSON.encode()).hexdigest() == (
        AUTHORITY_DEFINITION_V12_SHA256
    )
    assert hashlib.sha256(PREFERENCE_POLICY_JSON.encode()).hexdigest() == (
        PREFERENCE_POLICY_SHA256
    )
    assert verify_frozen_definitions()
    assert verify_frozen_definitions_v12()
    authority = json.loads(AUTHORITY_DEFINITION_V12_JSON)
    assert authority["predecessor_authority_definition_sha256"] == (
        AUTHORITY_DEFINITION_SHA256
    )
    assert authority["source_acquisition_authority_schema"].endswith("/1.1")
    assert authority["wrapper_schema"].endswith("/1.1")
    assert authority["producer"].endswith("/1.1")
    assert authority["verifier"].endswith("/1.1")
    assert authority["declaration_schema"].endswith("/1.0")


def test_successor_happy_path_verifies_and_reaches_guarded_bridge(
    monkeypatch, session
) -> None:
    *_, verifier, _, acquisition, _, _, _, occurrence = build_readiness_v11(
        monkeypatch, session
    )
    assert occurrence.schema_version == "1.1"
    assert occurrence.authority_definition_version == "1.2"
    assert occurrence.authority_definition_sha256 == AUTHORITY_DEFINITION_V12_SHA256
    assert occurrence.acquisition_authority is acquisition
    assert verifier.verify(occurrence)
    verified = verifier.verify_authority(occurrence)
    request = GuardedActiveFocusCandidateFormationBridgeV11(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    ).assemble(verified_readiness=verified, request_id="successor-v11")
    assert request.track_validation.snapshot_id == (
        acquisition.source_neutral_acquisition_result.evidence_snapshot.snapshot_id
    )
    assert request.familiarity_evidence == occurrence.familiarity_evidence
    assert request.track_feature_evidence == occurrence.track_feature_evidence
    assert request.objective_context_evidence == occurrence.objective_context_evidence
    assert request.taste_evidence == occurrence.local_taste_evidence


def test_historical_chain_remains_exactly_operational(monkeypatch, session) -> None:
    *_, verifier, _, acquisition, _, _, _, occurrence = build_readiness(
        monkeypatch, session
    )
    assert occurrence.schema_version == "1.0"
    assert occurrence.authority_definition_version == "1.1"
    assert occurrence.authority_definition_sha256 == AUTHORITY_DEFINITION_SHA256
    assert verifier.verify(occurrence)
    request = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    ).assemble(
        verified_readiness=verifier.verify_authority(occurrence),
        request_id="historical-v10",
    )
    assert request.track_validation.snapshot_id == (
        acquisition.source_neutral_acquisition_result.evidence_snapshot.snapshot_id
    )


def test_cross_version_producer_inputs_fail_closed(monkeypatch, session) -> None:
    old = build_readiness(monkeypatch, session)
    new = build_readiness_v11(monkeypatch, session)
    old_producer, old_acquisition = old[1], old[4]
    new_producer, new_acquisition = new[1], new[4]
    with pytest.raises(CandidateReadinessInvalidInput, match="acquisition authority"):
        old_producer.capture(
            acquisition_authority=new_acquisition,
            track_validation=new[5],
            accepted_objective=new[6],
            journey_plan=new[7],
            declarations=(),
        )
    with pytest.raises(CandidateReadinessInvalidInput, match="acquisition 1.1"):
        new_producer.capture(
            acquisition_authority=old_acquisition,
            track_validation=old[5],
            accepted_objective=old[6],
            journey_plan=old[7],
            declarations=(),
        )


def test_cross_version_wrappers_and_relabeling_fail_closed(monkeypatch, session) -> None:
    old = build_readiness(monkeypatch, session)
    new = build_readiness_v11(monkeypatch, session)
    old_verifier, old_occurrence = old[2], old[8]
    new_verifier, new_occurrence = new[2], new[8]
    assert not old_verifier.verify(new_occurrence)
    assert not new_verifier.verify(old_occurrence)
    with pytest.raises(ValidationError):
        ActiveFocusCandidateReadinessAuthorityArtifact.model_validate(
            new_occurrence.model_dump(mode="json")
        )
    with pytest.raises(ValidationError):
        ActiveFocusCandidateReadinessAuthorityArtifactV11.model_validate(
            old_occurrence.model_dump(mode="json")
        )
    assert not old_verifier.verify(
        new_occurrence.model_copy(update={"schema_version": "1.0"})
    )
    assert not new_verifier.verify(
        old_occurrence.model_copy(update={"schema_version": "1.1"})
    )
    old_relabelled = old_occurrence.model_copy(
        update={
            "authority_definition_version": "1.2",
            "authority_definition_json": AUTHORITY_DEFINITION_V12_JSON,
            "authority_definition_sha256": AUTHORITY_DEFINITION_V12_SHA256,
        }
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert not old_verifier.verify(old_relabelled)
        assert not new_verifier.verify(old_relabelled)


@pytest.mark.parametrize(
    "update",
    (
        {"authority_definition_version": "1.1"},
        {"authority_definition_sha256": "0" * 64},
        {"authority_definition_json": AUTHORITY_DEFINITION_JSON},
        {"schema_version": "1.0"},
        {"acquisition_authority_sha256": "0" * 64},
        {"occurrence_sha256": "0" * 64},
    ),
)
def test_successor_authority_and_digest_substitution_fails(
    monkeypatch, session, update
) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness_v11(
        monkeypatch, session
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert not verifier.verify(occurrence.model_copy(update=update))


def test_acquisition_verifier_substitution_fails_closed(monkeypatch, session) -> None:
    old = build_readiness(monkeypatch, session)
    new = build_readiness_v11(monkeypatch, session)
    with pytest.raises(TypeError, match="acquisition 1.1 verifier"):
        ActiveFocusCandidateReadinessVerifierV11(
            principal_verifier=new[0].verifier,
            acquisition_verifier=old[2]._acquisition_verifier,
            occurrence_repository=CandidateReadinessOccurrenceRepositoryV11(),
        )
    with pytest.raises(TypeError, match="acquisition 1.1 verifier"):
        ActiveFocusCandidateReadinessProducerV11(
            principal_verifier=new[0].verifier,
            acquisition_verifier=old[2]._acquisition_verifier,
            artist_repository=ArtistRepository(session),
            occurrence_repository=CandidateReadinessOccurrenceRepositoryV11(),
        )
    historical_with_new_verifier = ActiveFocusCandidateReadinessVerifier(
        principal_verifier=old[0].verifier,
        acquisition_verifier=new[2]._acquisition_verifier,
        occurrence_repository=old[3],
    )
    assert not historical_with_new_verifier.verify(old[8])


def test_occurrence_provenance_cannot_cross_generations_or_repositories(
    monkeypatch, session
) -> None:
    old = build_readiness(monkeypatch, session)
    new = build_readiness_v11(monkeypatch, session)
    reconstructed = ActiveFocusCandidateReadinessAuthorityArtifactV11.model_validate(
        new[8].model_dump(mode="json")
    )
    fresh_verifier = ActiveFocusCandidateReadinessVerifierV11(
        principal_verifier=new[0].verifier,
        acquisition_verifier=new[2]._acquisition_verifier,
        occurrence_repository=CandidateReadinessOccurrenceRepositoryV11(),
    )
    assert not fresh_verifier.verify(reconstructed)
    with pytest.raises(ValueError, match="genuine verified-readiness 1.1"):
        new[2].recover_verified(old[2].verify_authority(old[8]))


@pytest.mark.parametrize(
    "field,replacement",
    (
        ("title", "Replacement title"),
        ("artist_name", "Replacement artist"),
        ("duration_seconds", 999),
        ("provenance", None),
    ),
)
def test_successor_replays_exact_serialized_source_payload(
    monkeypatch, session, field, replacement
) -> None:
    setup = build_readiness_v11(monkeypatch, session)
    producer, acquisition, validation, accepted, journey = (
        setup[1],
        setup[4],
        setup[5],
        setup[6],
        setup[7],
    )
    record = validation.validated_records[0]
    if field == "provenance":
        replacement = record.provenance.model_copy(
            update={"source_reference": "substituted"}
        )
    changed = record.model_copy(update={field: replacement})
    changed_validation = validation.model_copy(
        update={"validated_records": (changed, *validation.validated_records[1:])}
    )
    declaration = governed_declaration(producer, record.track_id, energy="LEVEL_2")
    with pytest.raises(CandidateReadinessInvalidInput, match="not exact|replay"):
        producer.capture(
            acquisition_authority=acquisition,
            track_validation=changed_validation,
            accepted_objective=accepted,
            journey_plan=journey,
            declarations=(declaration,),
        )


def test_successor_bridge_rejects_wrong_verifier_and_forged_result(
    monkeypatch, session
) -> None:
    class AlwaysTrueVerifier:
        def verify(self, artifact):
            return True

    setup = build_readiness_v11(monkeypatch, session)
    verifier, occurrence = setup[2], setup[8]
    with pytest.raises(TypeError, match="readiness 1.1 verifier"):
        GuardedActiveFocusCandidateFormationBridgeV11(
            AlwaysTrueVerifier(),
            accepted_objective=occurrence.accepted_objective,
            journey_plan=occurrence.journey_plan,
        )
    bridge = GuardedActiveFocusCandidateFormationBridgeV11(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    )
    forged = object.__new__(VerifiedActiveFocusCandidateReadinessV11)
    with pytest.raises(ValueError, match="genuine verified-readiness 1.1"):
        bridge.assemble(verified_readiness=forged, request_id="forged")


def test_successor_projection_semantics_are_unchanged(monkeypatch, session) -> None:
    old = build_readiness(monkeypatch, session)[8]
    new = build_readiness_v11(monkeypatch, session)[8]
    assert old.observations[0].model_dump() == new.observations[0].model_dump()
    assert (
        old.familiarity_evidence.records[0].familiarity.value
        == new.familiarity_evidence.records[0].familiarity.value
        == 1.0
    )
    assert (
        old.track_feature_evidence.records[0].energy.value
        == new.track_feature_evidence.records[0].energy.value
        == 0.5
    )
    assert old.local_taste_evidence.records[0].rating is Rating.LOVE
    assert new.local_taste_evidence.records[0].rating is Rating.LOVE


def test_successor_constant_failure_does_not_change_historical_verification(
    monkeypatch, session
) -> None:
    old = build_readiness(monkeypatch, session)
    new = build_readiness_v11(monkeypatch, session)
    monkeypatch.setattr(
        verifier_v11_module,
        "AUTHORITY_DEFINITION_V12_JSON",
        AUTHORITY_DEFINITION_V12_JSON.replace('"schema_version":"1.2"', '"schema_version":"9.9"', 1),
    )
    assert old[2].verify(old[8])
    assert not new[2].verify(new[8])


def test_successor_runtime_has_no_media_network_or_producer_import_in_verifier() -> None:
    import playlist_narrative_engine.candidate_readiness.producer_v11 as producer_module

    source = inspect.getsource(producer_module) + inspect.getsource(verifier_v11_module)
    assert "open(" not in source
    assert "read_bytes" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "producer_v11" not in inspect.getsource(verifier_v11_module)

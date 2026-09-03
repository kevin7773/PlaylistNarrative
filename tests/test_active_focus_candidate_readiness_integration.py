from __future__ import annotations

import hashlib
import inspect
import json

import pytest

import playlist_narrative_engine.candidate_readiness.producer as readiness_producer_module
import playlist_narrative_engine.candidate_readiness.verifier as readiness_verifier_module
from playlist_narrative_engine.candidate_formation import CandidateFormer, derive_formed_candidate_pool
from playlist_narrative_engine.candidate_formation.request_assembler import FormationRequestAssemblyInput
from playlist_narrative_engine.candidate_readiness import (
    ActiveFocusCandidateReadinessDeclaration, ActiveFocusCandidateReadinessProducer,
    ActiveFocusCandidateReadinessVerifier, CandidateReadinessOccurrenceRepository,
    GuardedActiveFocusCandidateFormationBridge,
    VerifiedActiveFocusCandidateReadiness,
)
from playlist_narrative_engine.evidence_acquisition import SourceNeutralAcquisitionResult, serialize_acquisition_result, serialize_evidence_snapshot
from playlist_narrative_engine.itunes_windows_xml_acquisition import PennyLocalITunesXMLAcquisitionAuthorityArtifact
from playlist_narrative_engine.sequencing import ConstructionState, SequentialPlaylistConstructor
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.track_evidence import EvidenceSnapshot, EvidenceSnapshotRecord
from test_candidate_readiness_capture import build_readiness, governed_declaration, validation_for


class _SyntheticConformanceAcquisitionVerifier:
    def __init__(self, exact) -> None:
        self._exact = exact

    def verify(self, artifact) -> bool:
        return artifact == self._exact


def _synthetic_multi_artist_authority(acquisition, accepted):
    source = acquisition.source_neutral_acquisition_result
    payload_by_track = {json.loads(item.payload_json)["track_id"]: item for item in source.evidence_snapshot.records}
    longest = sorted(
        (json.loads(item.payload_json) for item in source.evidence_snapshot.records),
        key=lambda item: (-item["duration_seconds"], item["track_id"].encode("utf-8")),
    )[:7]
    artists = {
        item["track_id"]: (
            "Synthetic Conformance Shared Artist"
            if index <= 3
            else f"Synthetic Conformance Artist {index:02d}"
        )
        for index, item in enumerate(longest, 1)
    }
    records = []
    for item in source.evidence_snapshot.records:
        payload = json.loads(item.payload_json)
        if payload["track_id"] in artists:
            payload["artist_name"] = artists[payload["track_id"]]
        records.append(EvidenceSnapshotRecord(record_id=item.record_id, payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":"))))
    snapshot = EvidenceSnapshot(snapshot_id=source.evidence_snapshot.snapshot_id, records=tuple(records))
    snapshot_sha = hashlib.sha256(serialize_evidence_snapshot(snapshot)).hexdigest()
    source_data = source.model_dump(mode="json")
    source_data.update(evidence_snapshot=snapshot.model_dump(mode="json"), evidence_snapshot_sha256=snapshot_sha)
    synthetic_source = SourceNeutralAcquisitionResult.model_validate(source_data)
    acquisition_data = acquisition.model_dump(mode="json")
    acquisition_data.update(
        evidence_snapshot=snapshot.model_dump(mode="json"), evidence_snapshot_sha256=snapshot_sha,
        source_neutral_acquisition_result=synthetic_source.model_dump(mode="json"),
        source_neutral_acquisition_result_sha256=hashlib.sha256(serialize_acquisition_result(synthetic_source)).hexdigest(),
        canonical_sha256=None,
    )
    synthetic = PennyLocalITunesXMLAcquisitionAuthorityArtifact.model_validate(acquisition_data)
    validation = validation_for(synthetic, accepted)
    selected = tuple(item for item in validation.validated_records if item.track_id in artists)
    return synthetic, validation, selected


def test_synthetic_conformance_path_reaches_cf3_and_constructor_deterministically(monkeypatch, session) -> None:
    principal, _, _, _, acquisition, _, accepted, journey, _ = build_readiness(monkeypatch, session)
    synthetic, validation, selected = _synthetic_multi_artist_authority(acquisition, accepted)
    for item in selected:
        ArtistRepository(session).set_rating(item.artist_name, Rating.LOVE)
    repository = CandidateReadinessOccurrenceRepository()
    acquisition_verifier = _SyntheticConformanceAcquisitionVerifier(synthetic)
    producer = ActiveFocusCandidateReadinessProducer(
        principal_verifier=principal.verifier, acquisition_verifier=acquisition_verifier,
        artist_repository=ArtistRepository(session), occurrence_repository=repository,
    )
    declarations = tuple(
        governed_declaration(
            producer,
            item.track_id,
            familiarity="LEVEL_4" if index != 1 else "LEVEL_1",
            energy=("LEVEL_1", "LEVEL_2", "LEVEL_3", "LEVEL_4", "LEVEL_3", "LEVEL_2", "LEVEL_1")[index],
            instrumentalness="LEVEL_3", lyrical_distraction="LEVEL_1",
            groove="LEVEL_3", active_focus_context_fit="LEVEL_4",
        )
        for index, item in enumerate(selected)
    )
    occurrence = producer.capture(acquisition_authority=synthetic, track_validation=validation, accepted_objective=accepted, journey_plan=journey, declarations=declarations)
    verifier = ActiveFocusCandidateReadinessVerifier(
        principal_verifier=principal.verifier, acquisition_verifier=acquisition_verifier,
        occurrence_repository=repository,
    )
    bridge = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    )
    request = bridge.assemble(
        verified_readiness=verifier.verify_authority(occurrence),
        request_id="synthetic-active-focus-conformance",
    )
    formation_a = CandidateFormer().form(request)
    formation_b = CandidateFormer().form(request)
    assert formation_a == formation_b
    assert formation_a.summary.formed_count == 7
    assert formation_a.summary.withheld_count == 52
    formed_a = derive_formed_candidate_pool(formation_a)
    formed_b = derive_formed_candidate_pool(formation_b)
    assert formed_a == formed_b
    assert {item.track_id for item in formed_a.candidates} == {item.candidate.track_id for item in formation_a.formed}
    result_a = SequentialPlaylistConstructor().construct(journey_plan=journey, formed_pool=formed_a, state=ConstructionState(), requested_track_count=6)
    result_b = SequentialPlaylistConstructor().construct(journey_plan=journey, formed_pool=formed_b, state=ConstructionState(), requested_track_count=6)
    assert result_a == result_b
    assert len(result_a.tracks) == 6
    assert result_a.summary.total_duration_seconds >= 1800
    assert len({item.phase_name for item in result_a.tracks}) == 3
    assert all(count <= 2 for _, count in result_a.summary.artist_counts)
    assert ("Synthetic Conformance Shared Artist", 2) in result_a.summary.artist_counts
    capped = SequentialPlaylistConstructor().construct(
        journey_plan=journey, formed_pool=formed_a,
        state=ConstructionState(), requested_track_count=7,
    )
    assert capped.summary.achieved_track_count == 6
    assert ("artist_repetition_limit", 1) in capped.summary.rejection_counts


def test_guarded_bridge_rejects_caller_projection_substitution(monkeypatch, session) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    bad = occurrence.model_copy(update={"familiarity_evidence": occurrence.familiarity_evidence.model_copy(update={"artifact_id":"caller-built"})})
    try:
        GuardedActiveFocusCandidateFormationBridge(
            verifier,
            accepted_objective=occurrence.accepted_objective,
            journey_plan=occurrence.journey_plan,
        ).assemble(verified_readiness=bad, request_id="bypass")
    except ValueError as exc:
        assert "verified" in str(exc)
    else:
        raise AssertionError("caller-built CF-1 evidence bypassed readiness authority")


def test_guarded_bridge_rejects_duck_verifier_and_forged_verified_result(
    monkeypatch, session,
) -> None:
    class AlwaysTrueVerifier:
        def verify(self, artifact):
            return True

    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    with pytest.raises(TypeError, match="concrete governed readiness verifier"):
        GuardedActiveFocusCandidateFormationBridge(
            AlwaysTrueVerifier(),
            accepted_objective=occurrence.accepted_objective,
            journey_plan=occurrence.journey_plan,
        )
    bridge = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    )
    forged = object.__new__(VerifiedActiveFocusCandidateReadiness)
    with pytest.raises(ValueError, match="genuine verified-readiness"):
        bridge.assemble(verified_readiness=forged, request_id="forged")


def test_bridge_rejects_caller_built_assembly_input_and_wrong_binding(
    monkeypatch, session,
) -> None:
    *_, verifier, _, _, _, _, _, occurrence = build_readiness(monkeypatch, session)
    verified = verifier.verify_authority(occurrence)
    caller_input = FormationRequestAssemblyInput(
        request_id="caller-built",
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
        acquisition=occurrence.acquisition_authority.source_neutral_acquisition_result,
        track_validation=occurrence.track_validation,
        taste_evidence=occurrence.local_taste_evidence,
        familiarity_evidence=occurrence.familiarity_evidence,
        track_feature_evidence=occurrence.track_feature_evidence,
        objective_context_evidence=occurrence.objective_context_evidence,
        policy=readiness_producer_module.active_focus_candidate_formation_policy(),
    )
    bridge = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective,
        journey_plan=occurrence.journey_plan,
    )
    with pytest.raises(ValueError, match="genuine verified-readiness"):
        bridge.assemble(verified_readiness=caller_input, request_id="caller-built")

    wrong_binding = GuardedActiveFocusCandidateFormationBridge(
        verifier,
        accepted_objective=occurrence.accepted_objective.model_copy(
            update={"artifact_id": "another-objective"}
        ),
        journey_plan=occurrence.journey_plan,
    )
    with pytest.raises(ValueError, match="bound objective and journey"):
        wrong_binding.assemble(verified_readiness=verified, request_id="wrong-binding")


def test_sisters_fixture_remains_infeasible_for_real_thirty_minute_proof(monkeypatch, session) -> None:
    occurrence = build_readiness(monkeypatch, session)[-1]
    tracks = sorted(occurrence.track_validation.validated_records, key=lambda item: item.duration_seconds, reverse=True)
    assert len({item.artist_name for item in tracks}) == 1
    assert sum(item.duration_seconds for item in tracks[:2]) == 1272
    assert sum(item.duration_seconds for item in tracks[:3]) == 1796
    assert sum(item.duration_seconds for item in tracks[:2]) < 1800


def test_readiness_runtime_has_no_media_or_network_access_path() -> None:
    source = inspect.getsource(readiness_producer_module) + inspect.getsource(readiness_verifier_module)
    assert "open(" not in source
    assert "read_bytes" not in source
    assert "requests" not in source
    assert "urllib" not in source
    assert "from .producer" not in inspect.getsource(readiness_verifier_module)

from __future__ import annotations

import hashlib
import json
import math
import threading
import weakref

from playlist_narrative_engine.candidate_formation import (
    ContextInputEvidence, EvidenceObservation, EvidenceState,
    FamiliarityEvidenceArtifact, FamiliarityEvidenceRecord,
    LocalTasteEvidenceArtifact, ObjectiveContextEvidenceArtifact,
    ObjectiveContextEvidenceRecord, TasteEvidenceRecord,
    TrackFeatureEvidenceArtifact, TrackFeatureEvidenceRecord, UnitIntervalEvidence,
)
from playlist_narrative_engine.evidence_acquisition import serialize_acquisition_result
from playlist_narrative_engine.itunes_windows_xml_acquisition import PennyLocalITunesXMLAcquisitionVerifier
from playlist_narrative_engine.journey import journey_plan_matches_accepted_objective
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.local_authorization import LocalPrincipalAuthorityVerifier
from playlist_narrative_engine.track_evidence import serialize_track_evidence_validation

from .schemas import (
    ActiveFocusCandidateReadinessAuthorityArtifact,
    CandidateReadinessOccurrenceRepository,
    occurrence_sha256,
    replay_validated_track_payload,
)
from .vocabulary import (
    AUTHORITY_DEFINITION_JSON, AUTHORITY_DEFINITION_SHA256,
    AUTHORITY_DEFINITION_VERSION, VOCABULARY_ID, VOCABULARY_JSON,
    VOCABULARY_SHA256, VOCABULARY_VERSION, ReadinessField, ReadinessLevel,
    project_level, verify_frozen_definitions,
)


class VerifiedActiveFocusCandidateReadiness:
    """Opaque process-local proof issued only by the genuine verifier."""

    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("verified readiness results are verifier-issued only")


_VERIFIED_RESULTS: weakref.WeakKeyDictionary[
    VerifiedActiveFocusCandidateReadiness,
    tuple[ActiveFocusCandidateReadinessVerifier, ActiveFocusCandidateReadinessAuthorityArtifact],
] = weakref.WeakKeyDictionary()
_VERIFIED_RESULTS_LOCK = threading.RLock()


class ActiveFocusCandidateReadinessVerifier:
    """Recover producer authority and independently replay all readiness outputs."""

    def __init__(self, *, principal_verifier: LocalPrincipalAuthorityVerifier, acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifier, occurrence_repository: CandidateReadinessOccurrenceRepository) -> None:
        self._principal_verifier = principal_verifier
        self._acquisition_verifier = acquisition_verifier
        self._occurrences = occurrence_repository

    def verify(self, artifact: ActiveFocusCandidateReadinessAuthorityArtifact) -> bool:
        return self._verify_occurrence(artifact)

    def verify_authority(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifact,
    ) -> VerifiedActiveFocusCandidateReadiness:
        if not self._verify_occurrence(artifact):
            raise ValueError("candidate-readiness occurrence authority does not verify")
        result = object.__new__(VerifiedActiveFocusCandidateReadiness)
        with _VERIFIED_RESULTS_LOCK:
            _VERIFIED_RESULTS[result] = (self, artifact)
        return result

    def recover_verified(
        self,
        result: VerifiedActiveFocusCandidateReadiness,
    ) -> ActiveFocusCandidateReadinessAuthorityArtifact:
        if type(result) is not VerifiedActiveFocusCandidateReadiness:
            raise ValueError("genuine verified-readiness authority is required")
        with _VERIFIED_RESULTS_LOCK:
            authority = _VERIFIED_RESULTS.get(result)
        if authority is None or authority[0] is not self:
            raise ValueError("genuine verified-readiness authority is required")
        if not self._verify_occurrence(authority[1]):
            raise ValueError("verified-readiness authority is no longer applicable")
        return authority[1]

    def _verify_occurrence(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifact,
    ) -> bool:
        if not isinstance(artifact, ActiveFocusCandidateReadinessAuthorityArtifact):
            return False
        try:
            value = artifact
            reparsed = ActiveFocusCandidateReadinessAuthorityArtifact.model_validate(
                artifact.model_dump(mode="json")
            )
            if reparsed != artifact or set(artifact.__dict__) != set(artifact.__class__.model_fields):
                return False
            if not verify_frozen_definitions():
                return False
            if (
                _sha(VOCABULARY_JSON.encode("utf-8")) != VOCABULARY_SHA256
                or _sha(AUTHORITY_DEFINITION_JSON.encode("utf-8"))
                != AUTHORITY_DEFINITION_SHA256
            ):
                return False
            if self._occurrences._recover_authoritative(value) is not value:
                return False
            if self._has_conflicting_occurrence(value):
                return False
            if value.vocabulary_json != VOCABULARY_JSON or value.vocabulary_sha256 != VOCABULARY_SHA256:
                return False
            if value.authority_definition_version != AUTHORITY_DEFINITION_VERSION or value.authority_definition_json != AUTHORITY_DEFINITION_JSON or value.authority_definition_sha256 != AUTHORITY_DEFINITION_SHA256:
                return False
            principal = value.principal_authority
            if not self._principal_verifier.verify(principal):
                return False
            if value.principal_lineage_prefix_sha256 != self._principal_verifier.verified_lineage_prefix_sha256(principal):
                return False
            if not self._acquisition_verifier.verify(value.acquisition_authority):
                return False
            if not self._bindings_match(value):
                return False
            expected = _reconstruct(value)
            return (
                value.familiarity_evidence == expected[0]
                and value.track_feature_evidence == expected[1]
                and value.objective_context_evidence == expected[2]
                and value.local_taste_evidence == expected[3]
                and value.occurrence_sha256 == occurrence_sha256(value)
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False

    def _has_conflicting_occurrence(self, value) -> bool:
        keys = {item.track_id for item in value.observations}
        for other in self._occurrences._authoritative_artifacts():
            if other.artifact_id == value.artifact_id:
                continue
            if (other.objective_id, other.journey_id, other.snapshot_id) == (value.objective_id, value.journey_id, value.snapshot_id) and keys & {item.track_id for item in other.observations}:
                return True
        return False

    def _bindings_match(self, value) -> bool:
        acquisition = value.acquisition_authority
        source = acquisition.source_neutral_acquisition_result
        validation = value.track_validation
        accepted = value.accepted_objective
        journey = value.journey_plan
        tracks = {item.track_id: item for item in validation.validated_records}
        source_records = {
            item.record_id: item.payload_json
            for item in source.evidence_snapshot.records
        }
        partition = {
            item.record_id: item.source_payload_json
            for item in validation.validated_records
        } | {
            item.record_id: item.source_payload_json
            for item in validation.rejected_records
        }
        try:
            replayed_tracks = {
                item.track_id: replay_validated_track_payload(item)
                for item in validation.validated_records
            }
        except (json.JSONDecodeError, TypeError, ValueError):
            return False
        return all((
            value.principal_authority_artifact_id == value.principal_authority.artifact_id,
            value.principal_authority_sha256 == value.principal_authority.canonical_sha256,
            value.installation_id == value.principal_authority.installation_id,
            value.acquisition_authority_artifact_id == acquisition.artifact_id,
            value.acquisition_authority_sha256 == acquisition.canonical_sha256,
            value.acquisition_id == source.acquisition_id,
            value.acquisition_sha256 == _sha(serialize_acquisition_result(source)),
            value.snapshot_id == source.evidence_snapshot.snapshot_id == validation.snapshot_id,
            value.snapshot_sha256 == source.evidence_snapshot_sha256,
            value.track_validation_sha256 == _sha(serialize_track_evidence_validation(validation)),
            source_records == partition,
            len(replayed_tracks) == len(validation.validated_records),
            all(
                item.provenance.source_type == source.source_type
                and item.provenance.source_reference == source.source_reference
                for item in validation.validated_records
            ),
            accepted.schema_version == "2.0",
            value.accepted_objective_artifact_id == accepted.artifact_id,
            value.accepted_objective_sha256 == accepted.canonical_sha256,
            value.objective_id == accepted.objective.objective_id == validation.objective_id,
            value.objective_statement == accepted.objective.statement == validation.objective_statement,
            journey.schema_version == value.journey_schema_version == "2.0",
            journey.plan.context is JourneyContext.ACTIVE_FOCUS,
            journey_plan_matches_accepted_objective(journey, accepted),
            value.journey_id == journey.journey_id,
            value.journey_sha256 == journey.canonical_sha256,
            all(
                item.track_id in tracks
                and item.track_id in replayed_tracks
                and item.title == replayed_tracks[item.track_id]["title"]
                and item.artist_name == replayed_tracks[item.track_id]["artist_name"]
                and item.duration_seconds == replayed_tracks[item.track_id]["duration_seconds"]
                for item in value.observations
            ),
            len({item.track_id for item in value.observations}) == len(value.observations),
            tuple(item.artist_name for item in value.artist_ratings) == tuple(sorted({item.artist_name for item in validation.validated_records}, key=lambda text: text.encode("utf-8"))),
            _numeric_projection_forms_are_exact(value),
        ))


def _numeric_projection_forms_are_exact(
    value: ActiveFocusCandidateReadinessAuthorityArtifact,
) -> bool:
    units = []
    units.extend(item.familiarity for item in value.familiarity_evidence.records)
    for item in value.track_feature_evidence.records:
        units.extend((item.energy, item.instrumentalness, item.lyrical_distraction, item.groove))
    units.extend(item.context_fit for item in value.objective_context_evidence.records)
    for unit in units:
        if unit.value is None:
            continue
        if type(unit.value) is not float or not math.isfinite(unit.value):
            return False
        if unit.value == 0.0 and math.copysign(1.0, unit.value) < 0:
            return False
    return True


def _unit(artifact_id: str, track_id: str, field: str, level: ReadinessLevel | None) -> UnitIntervalEvidence:
    if level is None:
        return UnitIntervalEvidence(state=EvidenceState.UNAVAILABLE, value=None, observations=())
    payload = json.dumps({"track_id":track_id,"field":field,"category":level.value,"vocabulary_id":VOCABULARY_ID,"vocabulary_version":VOCABULARY_VERSION,"vocabulary_sha256":VOCABULARY_SHA256}, ensure_ascii=False, separators=(",", ":"))
    obs = EvidenceObservation(evidence_id="readiness-evidence:" + _sha(f"{artifact_id}\0{track_id}\0{field}".encode()), source_type="manual_active_focus_candidate_readiness", source_reference=artifact_id, payload_json=payload)
    return UnitIntervalEvidence(state=EvidenceState.MEASURED, value=project_level(ReadinessField(field), level), observations=(obs,))


def _reconstruct(value):
    aid, observations = value.artifact_id, value.observations
    familiar = FamiliarityEvidenceArtifact(artifact_id=aid+":familiarity", profile_id=value.installation_id, track_snapshot_id=value.snapshot_id, records=tuple(FamiliarityEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, familiarity=_unit(aid,item.track_id,"familiarity",item.familiarity)) for item in observations))
    features = TrackFeatureEvidenceArtifact(artifact_id=aid+":features", track_snapshot_id=value.snapshot_id, records=tuple(TrackFeatureEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, energy=_unit(aid,item.track_id,"energy",item.energy), instrumentalness=_unit(aid,item.track_id,"instrumentalness",item.instrumentalness), lyrical_distraction=_unit(aid,item.track_id,"lyrical_distraction",item.lyrical_distraction), groove=_unit(aid,item.track_id,"groove",item.groove)) for item in observations))
    binding = json.dumps({"accepted_objective_artifact_id":value.accepted_objective.artifact_id,"accepted_objective_sha256":value.accepted_objective.canonical_sha256,"objective_id":value.objective_id,"objective_statement":value.objective_statement,"journey_id":value.journey_id,"journey_schema_version":value.journey_schema_version,"journey_sha256":value.journey_sha256,"journey_context":"Active Focus","occurrence_id":aid}, ensure_ascii=False, separators=(",", ":"))
    context = ObjectiveContextEvidenceArtifact(artifact_id=aid+":context", objective_id=value.objective_id, objective_statement=value.objective_statement, journey_id=value.journey_id, context_id="Active Focus", track_snapshot_id=value.snapshot_id, records=tuple(ObjectiveContextEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, context_fit=_unit(aid,item.track_id,"active_focus_context_fit",item.active_focus_context_fit), inputs=(ContextInputEvidence(input_name="active_focus_authority_binding", state=EvidenceState.MEASURED, resolved_payload_json=binding, observations=(EvidenceObservation(evidence_id="context-binding:"+_sha(f"{aid}\0{item.track_id}".encode()), source_type="manual_active_focus_candidate_readiness", source_reference=aid, payload_json=binding),)),)) for item in observations))
    taste_records=[]
    for item in value.artist_ratings:
        if item.rating is None:
            taste_records.append(TasteEvidenceRecord(artist_name=item.artist_name,state=EvidenceState.UNAVAILABLE,rating=None,observations=()))
        else:
            payload=json.dumps({"artist_name":item.artist_name,"rating":item.rating.value,"persisted_row_id":item.persisted_row_id},ensure_ascii=False,separators=(",",":"))
            taste_records.append(TasteEvidenceRecord(artist_name=item.artist_name,state=EvidenceState.MEASURED,rating=item.rating,observations=(EvidenceObservation(evidence_id="taste-evidence:"+_sha(f"{aid}\0{item.artist_name}".encode()),source_type="maestro_persisted_artist_rating",source_reference=f"maestro-artist-row:{item.persisted_row_id}",payload_json=payload),)))
    taste=LocalTasteEvidenceArtifact(artifact_id=aid+":taste",profile_id=value.installation_id,records=tuple(taste_records))
    return familiar,features,context,taste


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

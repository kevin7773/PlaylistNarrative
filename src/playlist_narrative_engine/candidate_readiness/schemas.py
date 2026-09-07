from __future__ import annotations

import hashlib
import json
import threading
import weakref
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation import (
    FamiliarityEvidenceArtifact,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    TrackFeatureEvidenceArtifact,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifact,
    PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact
from playlist_narrative_engine.local_authorization import LocalPrincipalAuthorityArtifact
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.track_evidence import (
    TrackEvidenceValidationArtifact,
    ValidatedTrackEvidence,
)

from .vocabulary import ReadinessLevel


class FrozenReadinessModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


_CATEGORY_FIELDS = (
    "familiarity", "energy", "instrumentalness", "lyrical_distraction",
    "groove", "active_focus_context_fit",
)


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("readiness identity must be nonblank and exact")
    return value


def _strict_category(value: Any) -> Any:
    if value is None or isinstance(value, ReadinessLevel):
        return value
    if type(value) is not str or value not in {item.value for item in ReadinessLevel}:
        raise ValueError("readiness category must be an exact governed token")
    return value


class ActiveFocusCandidateReadinessDeclaration(FrozenReadinessModel):
    schema_version: Literal["1.0"] = "1.0"
    track_id: str = Field(min_length=1, max_length=500)
    familiarity: ReadinessLevel | None = None
    energy: ReadinessLevel | None = None
    instrumentalness: ReadinessLevel | None = None
    lyrical_distraction: ReadinessLevel | None = None
    groove: ReadinessLevel | None = None
    active_focus_context_fit: ReadinessLevel | None = None

    _track = field_validator("track_id")(_exact)
    _categories = field_validator(*_CATEGORY_FIELDS, mode="before")(_strict_category)


class TrackReadinessObservation(FrozenReadinessModel):
    track_id: str
    title: str
    artist_name: str
    duration_seconds: int = Field(gt=0)
    familiarity: ReadinessLevel | None = None
    energy: ReadinessLevel | None = None
    instrumentalness: ReadinessLevel | None = None
    lyrical_distraction: ReadinessLevel | None = None
    groove: ReadinessLevel | None = None
    active_focus_context_fit: ReadinessLevel | None = None

    _text = field_validator("track_id", "title", "artist_name")(_exact)


class ArtistRatingObservation(FrozenReadinessModel):
    artist_name: str
    rating: Rating | None
    persisted_row_id: int | None = Field(default=None, gt=0)

    _artist = field_validator("artist_name")(_exact)

    @model_validator(mode="after")
    def bind_availability(self) -> ArtistRatingObservation:
        if (self.rating is None) != (self.persisted_row_id is None):
            raise ValueError("persisted rating authority must be complete or absent")
        return self


class ActiveFocusCandidateReadinessAuthorityArtifact(FrozenReadinessModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["active_focus_candidate_readiness_authority"] = "active_focus_candidate_readiness_authority"
    artifact_id: str
    principal_authority: LocalPrincipalAuthorityArtifact
    principal_authority_artifact_id: str
    principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_lineage_prefix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    installation_id: str
    acquisition_authority: PennyLocalITunesXMLAcquisitionAuthorityArtifact
    acquisition_authority_artifact_id: str
    acquisition_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquisition_id: str
    acquisition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    snapshot_id: str
    snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    track_validation: TrackEvidenceValidationArtifact
    track_validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    vocabulary_id: Literal["pne.active-focus.candidate-readiness"] = "pne.active-focus.candidate-readiness"
    vocabulary_version: Literal["1.0"] = "1.0"
    vocabulary_json: str
    vocabulary_sha256: Literal["63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d"]
    authority_definition_id: Literal["pne.candidate-readiness-authority.active-focus"] = "pne.candidate-readiness-authority.active-focus"
    authority_definition_version: Literal["1.1"] = "1.1"
    authority_definition_json: str
    authority_definition_sha256: Literal["a90b57643243966aa5ccbeb0ebb045794967b0ae322c74ad57a543ba32e5e6f1"]
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_artifact_id: str
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_id: str
    objective_statement: str
    journey_plan: JourneyPlanArtifact
    journey_id: str
    journey_schema_version: Literal["2.0"] = "2.0"
    journey_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    journey_context: Literal["Active Focus"] = "Active Focus"
    observations: tuple[TrackReadinessObservation, ...]
    artist_ratings: tuple[ArtistRatingObservation, ...]
    familiarity_evidence: FamiliarityEvidenceArtifact
    track_feature_evidence: TrackFeatureEvidenceArtifact
    objective_context_evidence: ObjectiveContextEvidenceArtifact
    local_taste_evidence: LocalTasteEvidenceArtifact
    occurrence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    _identities = field_validator(
        "artifact_id", "principal_authority_artifact_id", "installation_id",
        "acquisition_authority_artifact_id", "acquisition_id", "snapshot_id",
        "accepted_objective_artifact_id", "objective_id", "objective_statement",
        "journey_id",
    )(_exact)

    @field_validator("observations", mode="before")
    @classmethod
    def order_observations(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=lambda item: _field(item, "track_id").encode("utf-8")))

    @field_validator("artist_ratings", mode="before")
    @classmethod
    def order_ratings(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=lambda item: _field(item, "artist_name").encode("utf-8")))

    @model_validator(mode="after")
    def validate_digest(self) -> ActiveFocusCandidateReadinessAuthorityArtifact:
        digest = occurrence_sha256(self)
        if self.occurrence_sha256 is None:
            object.__setattr__(self, "occurrence_sha256", digest)
        elif self.occurrence_sha256 != digest:
            raise ValueError("readiness occurrence digest mismatch")
        return self


class ActiveFocusCandidateReadinessAuthorityArtifactV11(
    ActiveFocusCandidateReadinessAuthorityArtifact
):
    schema_version: Literal["1.1"] = "1.1"
    acquisition_authority: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11
    authority_definition_version: Literal["1.2"] = "1.2"
    authority_definition_sha256: Literal[
        "6d18b572ebbcd984b431440ce039bcf58a1736ccfd39cf66f7a7c3b9b897f5ba"
    ]


def _field(item: object, name: str) -> str:
    value = item.get(name) if isinstance(item, dict) else getattr(item, name, "")
    return value if isinstance(value, str) else ""


def canonical_bytes(value: object, *, exclude: set[str] | None = None) -> bytes:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json", exclude=exclude or set())
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def occurrence_sha256(value: ActiveFocusCandidateReadinessAuthorityArtifact) -> str:
    content = canonical_bytes(value, exclude={"occurrence_sha256"})
    return hashlib.sha256(b"pne.active-focus-candidate-readiness-occurrence/1.0\x00" + content).hexdigest()


class _OccurrenceState:
    def __init__(self) -> None:
        self.owner: object | None = None
        self.records: dict[str, tuple[ActiveFocusCandidateReadinessAuthorityArtifact, object]] = {}


_OCCURRENCE_STATES: weakref.WeakKeyDictionary[
    CandidateReadinessOccurrenceRepository, _OccurrenceState
] = weakref.WeakKeyDictionary()
_BOUND_OCCURRENCE_PRODUCERS: weakref.WeakKeyDictionary[
    object, CandidateReadinessOccurrenceRepository
] = weakref.WeakKeyDictionary()
_OCCURRENCE_STATES_LOCK = threading.RLock()


class CandidateReadinessOccurrenceRepository:
    __slots__ = ("_artifacts", "__weakref__")

    def __init__(self) -> None:
        self._artifacts: list[ActiveFocusCandidateReadinessAuthorityArtifact] = []
        with _OCCURRENCE_STATES_LOCK:
            _OCCURRENCE_STATES[self] = _OccurrenceState()

    @property
    def artifacts(self) -> tuple[ActiveFocusCandidateReadinessAuthorityArtifact, ...]:
        return tuple(self._artifacts)

    def _recover_authoritative(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifact,
    ) -> ActiveFocusCandidateReadinessAuthorityArtifact | None:
        with _OCCURRENCE_STATES_LOCK:
            state = _OCCURRENCE_STATES.get(self)
            if state is None:
                return None
            recorded = state.records.get(artifact.artifact_id)
            if recorded is None or recorded[0] is not artifact:
                return None
            return recorded[0]

    def _authoritative_artifacts(
        self,
    ) -> tuple[ActiveFocusCandidateReadinessAuthorityArtifact, ...]:
        with _OCCURRENCE_STATES_LOCK:
            state = _OCCURRENCE_STATES.get(self)
            if state is None:
                return ()
            return tuple(record[0] for record in state.records.values())


def _bind_occurrence_recorder(
    repository: CandidateReadinessOccurrenceRepository,
    owner: object,
) -> Callable[[ActiveFocusCandidateReadinessAuthorityArtifact], None]:
    from .producer import ActiveFocusCandidateReadinessProducer

    if type(owner) is not ActiveFocusCandidateReadinessProducer:
        raise TypeError("the concrete readiness producer is required")
    with _OCCURRENCE_STATES_LOCK:
        state = _OCCURRENCE_STATES[repository]
        if state.owner is not None or owner in _BOUND_OCCURRENCE_PRODUCERS:
            raise ValueError("readiness occurrence repository already has a producer")
        state.owner = owner
        _BOUND_OCCURRENCE_PRODUCERS[owner] = repository
        capability = object()

    def record(artifact: ActiveFocusCandidateReadinessAuthorityArtifact) -> None:
        with _OCCURRENCE_STATES_LOCK:
            current = _OCCURRENCE_STATES.get(repository)
            if current is None or current.owner is not owner or capability is None:
                raise ValueError("readiness producer authority is unavailable")
            if artifact.artifact_id in current.records:
                raise ValueError("readiness occurrence identity already exists")
            current.records[artifact.artifact_id] = (artifact, object())
            repository._artifacts.append(artifact)

    return record


class _OccurrenceStateV11:
    def __init__(self) -> None:
        self.owner: object | None = None
        self.records: dict[
            str, tuple[ActiveFocusCandidateReadinessAuthorityArtifactV11, object]
        ] = {}


_OCCURRENCE_STATES_V11: weakref.WeakKeyDictionary[
    CandidateReadinessOccurrenceRepositoryV11, _OccurrenceStateV11
] = weakref.WeakKeyDictionary()
_BOUND_OCCURRENCE_PRODUCERS_V11: weakref.WeakKeyDictionary[
    object, CandidateReadinessOccurrenceRepositoryV11
] = weakref.WeakKeyDictionary()


class CandidateReadinessOccurrenceRepositoryV11:
    __slots__ = ("_artifacts", "__weakref__")

    def __init__(self) -> None:
        self._artifacts: list[ActiveFocusCandidateReadinessAuthorityArtifactV11] = []
        with _OCCURRENCE_STATES_LOCK:
            _OCCURRENCE_STATES_V11[self] = _OccurrenceStateV11()

    @property
    def artifacts(
        self,
    ) -> tuple[ActiveFocusCandidateReadinessAuthorityArtifactV11, ...]:
        return tuple(self._artifacts)

    def _recover_authoritative(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ) -> ActiveFocusCandidateReadinessAuthorityArtifactV11 | None:
        with _OCCURRENCE_STATES_LOCK:
            state = _OCCURRENCE_STATES_V11.get(self)
            if state is None:
                return None
            recorded = state.records.get(artifact.artifact_id)
            if recorded is None or recorded[0] is not artifact:
                return None
            return recorded[0]

    def _authoritative_artifacts(
        self,
    ) -> tuple[ActiveFocusCandidateReadinessAuthorityArtifactV11, ...]:
        with _OCCURRENCE_STATES_LOCK:
            state = _OCCURRENCE_STATES_V11.get(self)
            if state is None:
                return ()
            return tuple(record[0] for record in state.records.values())


def _bind_occurrence_recorder_v11(
    repository: CandidateReadinessOccurrenceRepositoryV11,
    owner: object,
) -> Callable[[ActiveFocusCandidateReadinessAuthorityArtifactV11], None]:
    from .producer_v11 import ActiveFocusCandidateReadinessProducerV11

    if type(owner) is not ActiveFocusCandidateReadinessProducerV11:
        raise TypeError("the concrete readiness 1.1 producer is required")
    with _OCCURRENCE_STATES_LOCK:
        state = _OCCURRENCE_STATES_V11[repository]
        if state.owner is not None or owner in _BOUND_OCCURRENCE_PRODUCERS_V11:
            raise ValueError("readiness 1.1 occurrence repository already has a producer")
        state.owner = owner
        _BOUND_OCCURRENCE_PRODUCERS_V11[owner] = repository
        capability = object()

    def record(artifact: ActiveFocusCandidateReadinessAuthorityArtifactV11) -> None:
        with _OCCURRENCE_STATES_LOCK:
            current = _OCCURRENCE_STATES_V11.get(repository)
            if current is None or current.owner is not owner or capability is None:
                raise ValueError("readiness 1.1 producer authority is unavailable")
            if artifact.artifact_id in current.records:
                raise ValueError("readiness 1.1 occurrence identity already exists")
            current.records[artifact.artifact_id] = (artifact, object())
            repository._artifacts.append(artifact)

    return record


def replay_validated_track_payload(record: ValidatedTrackEvidence) -> dict[str, object]:
    """Recover exact structured track evidence from its serialized authority."""

    def reject_constant(value: str) -> None:
        raise ValueError(f"unsupported JSON constant: {value}")

    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("serialized track evidence contains a duplicate key")
            result[key] = value
        return result

    payload = json.loads(
        record.source_payload_json,
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    expected_keys = {"track_id", "title", "artist_name", "duration_seconds", "provenance"}
    if type(payload) is not dict or set(payload) != expected_keys:
        raise ValueError("serialized track evidence structure is not exact")
    provenance = payload["provenance"]
    expected_provenance_keys = {"source_type", "source_reference", "rationale"}
    if type(provenance) is not dict or set(provenance) != expected_provenance_keys:
        raise ValueError("serialized track provenance structure is not exact")
    expected = {
        "track_id": record.track_id,
        "title": record.title,
        "artist_name": record.artist_name,
        "duration_seconds": record.duration_seconds,
        "provenance": record.provenance.model_dump(mode="json"),
    }
    if payload != expected:
        raise ValueError("structured track evidence disagrees with serialized authority")
    if any(type(payload[name]) is not str for name in ("track_id", "title", "artist_name")):
        raise ValueError("serialized track identity fields are not exact strings")
    if type(payload["duration_seconds"]) is not int or payload["duration_seconds"] <= 0:
        raise ValueError("serialized track duration is not an exact positive integer")
    if any(type(provenance[name]) is not str for name in expected_provenance_keys):
        raise ValueError("serialized track provenance fields are not exact strings")
    return payload

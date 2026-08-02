from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.taste.ratings import Rating


CANDIDATE_EVIDENCE_SCHEMA_VERSION = "1.0"


class FrozenCandidateEvidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceState(StrEnum):
    MEASURED = "measured"
    UNAVAILABLE = "unavailable"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"
    EXPLICITLY_INAPPLICABLE = "explicitly_inapplicable"


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def _input_field(value: object, field_name: str) -> str:
    if isinstance(value, dict):
        field_value = value.get(field_name)
    else:
        field_value = getattr(value, field_name, None)
    return field_value if isinstance(field_value, str) else ""


def _canonical_order(values: Any, field_name: str) -> tuple[object, ...]:
    return tuple(
        sorted(
            tuple(values),
            key=lambda item: _utf8_key(_input_field(item, field_name)),
        )
    )


def _require_exact_text(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("identity and provenance text must be nonblank and exact")
    return value


def _validate_observations(
    state: EvidenceState,
    observations: tuple[EvidenceObservation, ...],
    *,
    has_resolved_value: bool,
) -> None:
    evidence_ids = tuple(item.evidence_id for item in observations)
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("observation evidence IDs must be unique")
    if evidence_ids != tuple(sorted(evidence_ids, key=_utf8_key)):
        raise ValueError("observations must use UTF-8 evidence-ID order")

    if state is EvidenceState.MEASURED:
        if not has_resolved_value or not observations:
            raise ValueError("measured evidence requires a value and observations")
        return
    if has_resolved_value:
        raise ValueError("non-available evidence cannot contain a resolved value")
    if state is EvidenceState.UNAVAILABLE and observations:
        raise ValueError("unavailable evidence cannot contain observations")
    if state is EvidenceState.CONFLICTING and len(observations) < 2:
        raise ValueError("conflicting evidence requires at least two observations")
    if state in {
        EvidenceState.UNSUPPORTED,
        EvidenceState.EXPLICITLY_INAPPLICABLE,
    } and not observations:
        raise ValueError(f"{state.value} evidence requires observations")


class EvidenceObservation(FrozenCandidateEvidenceModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    payload_json: str = Field(max_length=100_000)

    @field_validator("evidence_id", "source_type", "source_reference")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _require_exact_text(value)


class UnitIntervalEvidence(FrozenCandidateEvidenceModel):
    state: EvidenceState
    value: float | None = Field(default=None, ge=0.0, le=1.0, strict=True)
    observations: tuple[EvidenceObservation, ...]

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @model_validator(mode="after")
    def enforce_state_contract(self) -> UnitIntervalEvidence:
        _validate_observations(
            self.state,
            self.observations,
            has_resolved_value=self.value is not None,
        )
        return self


class TasteEvidenceRecord(FrozenCandidateEvidenceModel):
    artist_name: str = Field(min_length=1, max_length=200)
    state: EvidenceState
    rating: Rating | None = None
    observations: tuple[EvidenceObservation, ...]

    @field_validator("artist_name")
    @classmethod
    def require_exact_artist_name(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @model_validator(mode="after")
    def enforce_state_contract(self) -> TasteEvidenceRecord:
        _validate_observations(
            self.state,
            self.observations,
            has_resolved_value=self.rating is not None,
        )
        return self


class LocalTasteEvidenceArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    artifact_kind: Literal["local_taste_evidence"] = "local_taste_evidence"
    artifact_id: str = Field(min_length=1, max_length=200)
    profile_id: str = Field(min_length=1, max_length=200)
    ordering_rule: Literal["artist_name_utf8_bytes"] = "artist_name_utf8_bytes"
    records: tuple[TasteEvidenceRecord, ...]
    eligibility_established: Literal[False] = False
    numeric_preference_established: Literal[False] = False
    scoring_performed: Literal[False] = False
    ranking_performed: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    recommendation_claims: Literal[False] = False

    @field_validator("artifact_id", "profile_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("records", mode="before")
    @classmethod
    def canonicalize_records(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "artist_name")

    @model_validator(mode="after")
    def enforce_record_order(self) -> LocalTasteEvidenceArtifact:
        identities = tuple(item.artist_name for item in self.records)
        _require_unique_ordered(identities, "taste artist identities")
        return self


class FamiliarityEvidenceRecord(FrozenCandidateEvidenceModel):
    track_id: str = Field(min_length=1, max_length=500)
    artist_name: str = Field(min_length=1, max_length=200)
    familiarity: UnitIntervalEvidence

    @field_validator("track_id", "artist_name")
    @classmethod
    def require_exact_track_id(cls, value: str) -> str:
        return _require_exact_text(value)


class FamiliarityEvidenceArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    artifact_kind: Literal["familiarity_evidence"] = "familiarity_evidence"
    artifact_id: str = Field(min_length=1, max_length=200)
    profile_id: str = Field(min_length=1, max_length=200)
    track_snapshot_id: str = Field(min_length=1, max_length=200)
    ordering_rule: Literal["track_id_utf8_bytes"] = "track_id_utf8_bytes"
    records: tuple[FamiliarityEvidenceRecord, ...]
    eligibility_established: Literal[False] = False
    scoring_performed: Literal[False] = False
    ranking_performed: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    recommendation_claims: Literal[False] = False

    @field_validator("artifact_id", "profile_id", "track_snapshot_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("records", mode="before")
    @classmethod
    def canonicalize_records(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "track_id")

    @model_validator(mode="after")
    def enforce_record_order(self) -> FamiliarityEvidenceArtifact:
        identities = tuple(item.track_id for item in self.records)
        _require_unique_ordered(identities, "familiarity track identities")
        return self


class TrackFeatureEvidenceRecord(FrozenCandidateEvidenceModel):
    track_id: str = Field(min_length=1, max_length=500)
    artist_name: str = Field(min_length=1, max_length=200)
    energy: UnitIntervalEvidence
    instrumentalness: UnitIntervalEvidence
    lyrical_distraction: UnitIntervalEvidence
    groove: UnitIntervalEvidence

    @field_validator("track_id", "artist_name")
    @classmethod
    def require_exact_track_id(cls, value: str) -> str:
        return _require_exact_text(value)


class TrackFeatureEvidenceArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    artifact_kind: Literal["track_feature_evidence"] = "track_feature_evidence"
    artifact_id: str = Field(min_length=1, max_length=200)
    track_snapshot_id: str = Field(min_length=1, max_length=200)
    ordering_rule: Literal["track_id_utf8_bytes"] = "track_id_utf8_bytes"
    records: tuple[TrackFeatureEvidenceRecord, ...]
    eligibility_established: Literal[False] = False
    scoring_performed: Literal[False] = False
    ranking_performed: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    recommendation_claims: Literal[False] = False

    @field_validator("artifact_id", "track_snapshot_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("records", mode="before")
    @classmethod
    def canonicalize_records(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "track_id")

    @model_validator(mode="after")
    def enforce_record_order(self) -> TrackFeatureEvidenceArtifact:
        identities = tuple(item.track_id for item in self.records)
        _require_unique_ordered(identities, "feature track identities")
        return self


class ContextInputEvidence(FrozenCandidateEvidenceModel):
    input_name: str = Field(min_length=1, max_length=200)
    state: EvidenceState
    resolved_payload_json: str | None = Field(default=None, max_length=100_000)
    observations: tuple[EvidenceObservation, ...]

    @field_validator("input_name")
    @classmethod
    def require_exact_input_name(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @field_validator("resolved_payload_json")
    @classmethod
    def require_valid_resolved_json(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            json.loads(value, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("resolved context input must be valid JSON") from exc
        return value

    @model_validator(mode="after")
    def enforce_state_contract(self) -> ContextInputEvidence:
        _validate_observations(
            self.state,
            self.observations,
            has_resolved_value=self.resolved_payload_json is not None,
        )
        return self


class ObjectiveContextEvidenceRecord(FrozenCandidateEvidenceModel):
    track_id: str = Field(min_length=1, max_length=500)
    artist_name: str = Field(min_length=1, max_length=200)
    context_fit: UnitIntervalEvidence
    inputs: tuple[ContextInputEvidence, ...] = Field(min_length=1)

    @field_validator("track_id", "artist_name")
    @classmethod
    def require_exact_track_id(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("inputs", mode="before")
    @classmethod
    def canonicalize_inputs(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "input_name")

    @model_validator(mode="after")
    def enforce_input_order(self) -> ObjectiveContextEvidenceRecord:
        names = tuple(item.input_name for item in self.inputs)
        _require_unique_ordered(names, "context input names")
        return self


class ObjectiveContextEvidenceArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_EVIDENCE_SCHEMA_VERSION
    artifact_kind: Literal["objective_context_evidence"] = (
        "objective_context_evidence"
    )
    artifact_id: str = Field(min_length=1, max_length=200)
    objective_id: str = Field(min_length=1, max_length=100)
    objective_statement: str = Field(min_length=1, max_length=500)
    journey_id: str = Field(min_length=1, max_length=200)
    context_id: str = Field(min_length=1, max_length=200)
    track_snapshot_id: str = Field(min_length=1, max_length=200)
    ordering_rule: Literal["track_id_utf8_bytes"] = "track_id_utf8_bytes"
    input_ordering_rule: Literal["input_name_utf8_bytes"] = "input_name_utf8_bytes"
    records: tuple[ObjectiveContextEvidenceRecord, ...]
    eligibility_established: Literal[False] = False
    scoring_performed: Literal[False] = False
    ranking_performed: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    recommendation_claims: Literal[False] = False

    @field_validator(
        "artifact_id",
        "objective_id",
        "objective_statement",
        "journey_id",
        "context_id",
        "track_snapshot_id",
    )
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _require_exact_text(value)

    @field_validator("records", mode="before")
    @classmethod
    def canonicalize_records(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "track_id")

    @model_validator(mode="after")
    def enforce_record_order(self) -> ObjectiveContextEvidenceArtifact:
        identities = tuple(item.track_id for item in self.records)
        _require_unique_ordered(identities, "context track identities")
        return self


CandidateSourceEvidenceArtifact = (
    LocalTasteEvidenceArtifact
    | FamiliarityEvidenceArtifact
    | TrackFeatureEvidenceArtifact
    | ObjectiveContextEvidenceArtifact
)


def _require_unique_ordered(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")
    if values != tuple(sorted(values, key=_utf8_key)):
        raise ValueError(f"{label} must use UTF-8 byte order")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")

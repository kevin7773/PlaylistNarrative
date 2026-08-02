from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    Objective,
    ObjectiveAssessment,
)


OBJECTIVE_SAFETY_SCHEMA_VERSION = "1.0"


class FrozenObjectiveSafetyModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SafetyDecision(StrEnum):
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ObjectiveSafetyReasonCode(StrEnum):
    OBJECTIVE_INTENT_NOT_PERMITTED = "OBJECTIVE_INTENT_NOT_PERMITTED"
    REQUIRED_CONTEXT_MISSING = "REQUIRED_CONTEXT_MISSING"
    OBJECTIVE_INTENT_UNDETERMINED = "OBJECTIVE_INTENT_UNDETERMINED"


SAFETY_REASON_PRECEDENCE = tuple(ObjectiveSafetyReasonCode)
SAFETY_REASON_EXPLANATIONS = {
    ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED: (
        "The applicable safety policy does not permit the supplied objective intent."
    ),
    ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING: (
        "Required context for a deterministic safety decision is unavailable."
    ),
    ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED: (
        "The supplied evidence cannot deterministically establish objective intent."
    ),
}


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("safety identity text must be nonblank and exact")
    return value


def _input_key(value: object) -> bytes:
    if isinstance(value, dict):
        key = value.get("key")
    else:
        key = getattr(value, "key", None)
    return _utf8_key(key if isinstance(key, str) else "")


class SafetyMetadataEntry(FrozenObjectiveSafetyModel):
    key: str = Field(min_length=1, max_length=200)
    payload_json: str = Field(max_length=100_000)

    @field_validator("key")
    @classmethod
    def require_exact_key(cls, value: str) -> str:
        return _exact(value)

    @field_validator("payload_json")
    @classmethod
    def require_valid_json(cls, value: str) -> str:
        try:
            json.loads(value, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("safety metadata payload must be valid JSON") from exc
        return value


class ObjectiveSafetyRequest(FrozenObjectiveSafetyModel):
    schema_version: Literal["1.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    objective_assessment: ObjectiveAssessment
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    safety_policy_id: str = Field(min_length=1, max_length=200)
    safety_policy_version: str = Field(min_length=1, max_length=100)

    @field_validator(
        "request_id", "safety_policy_id", "safety_policy_version"
    )
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def require_sufficient_objective_and_unique_metadata(self) -> ObjectiveSafetyRequest:
        if self.objective_assessment.outcome is not AssessmentOutcome.SUFFICIENT:
            raise ValueError("Objective Safety requires a sufficient assessment")
        _require_unique_metadata(self.objective_metadata, "objective metadata")
        _require_unique_metadata(self.context_metadata, "context metadata")
        return self


class ObjectiveSafetyReason(FrozenObjectiveSafetyModel):
    code: ObjectiveSafetyReasonCode
    field_path: str = Field(min_length=1, max_length=500)
    explanation: str

    @field_validator("field_path")
    @classmethod
    def require_exact_field_path(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_fixed_explanation(self) -> ObjectiveSafetyReason:
        if self.explanation != SAFETY_REASON_EXPLANATIONS[self.code]:
            raise ValueError("safety reason explanation must match its fixed contract")
        return self


class AcceptedObjectiveArtifact(FrozenObjectiveSafetyModel):
    schema_version: Literal["1.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    artifact_kind: Literal["accepted_objective"] = "accepted_objective"
    artifact_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    objective: Objective
    safety_policy_id: str = Field(min_length=1, max_length=200)
    safety_policy_version: str = Field(min_length=1, max_length=100)
    decision: Literal[SafetyDecision.ACCEPTED] = SafetyDecision.ACCEPTED
    decision_explanation: str = Field(min_length=1, max_length=1_000)
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    journey_planning_authorized: Literal[True] = True
    musical_content_evaluated: Literal[False] = False
    candidate_formation_performed: Literal[False] = False

    @field_validator(
        "artifact_id",
        "request_id",
        "safety_policy_id",
        "safety_policy_version",
        "decision_explanation",
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def require_unique_metadata(self) -> AcceptedObjectiveArtifact:
        _require_unique_metadata(self.objective_metadata, "objective metadata")
        _require_unique_metadata(self.context_metadata, "context metadata")
        return self


class DeclinedObjectiveArtifact(FrozenObjectiveSafetyModel):
    schema_version: Literal["1.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    artifact_kind: Literal["declined_objective"] = "declined_objective"
    artifact_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    objective: Objective
    safety_policy_id: str = Field(min_length=1, max_length=200)
    safety_policy_version: str = Field(min_length=1, max_length=100)
    decision: Literal[SafetyDecision.DECLINED] = SafetyDecision.DECLINED
    reasons: tuple[ObjectiveSafetyReason, ...] = Field(min_length=1)
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    journey_planning_authorized: Literal[False] = False
    musical_content_evaluated: Literal[False] = False
    candidate_formation_performed: Literal[False] = False

    @field_validator(
        "artifact_id", "request_id", "safety_policy_id", "safety_policy_version"
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def enforce_reason_and_metadata_contract(self) -> DeclinedObjectiveArtifact:
        precedence = {code: index for index, code in enumerate(SAFETY_REASON_PRECEDENCE)}
        expected = tuple(
            sorted(
                self.reasons,
                key=lambda reason: (precedence[reason.code], _utf8_key(reason.field_path)),
            )
        )
        if self.reasons != expected:
            raise ValueError("safety reasons must use fixed precedence")
        reason_keys = tuple((reason.code, reason.field_path) for reason in self.reasons)
        if len(reason_keys) != len(set(reason_keys)):
            raise ValueError("safety reasons must be unique by code and field path")
        _require_unique_metadata(self.objective_metadata, "objective metadata")
        _require_unique_metadata(self.context_metadata, "context metadata")
        return self


ObjectiveSafetyArtifact = AcceptedObjectiveArtifact | DeclinedObjectiveArtifact


def _require_unique_metadata(
    entries: tuple[SafetyMetadataEntry, ...], label: str
) -> None:
    keys = tuple(entry.key for entry in entries)
    if len(keys) != len(set(keys)):
        raise ValueError(f"{label} keys must be unique")
    if keys != tuple(sorted(keys, key=_utf8_key)):
        raise ValueError(f"{label} must use UTF-8 key order")


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")

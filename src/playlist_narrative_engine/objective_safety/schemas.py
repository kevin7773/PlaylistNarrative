from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    Objective,
    ObjectiveAssessment,
)


OBJECTIVE_SAFETY_SCHEMA_VERSION = "2.0"
OBJECTIVE_INTENT_DECLARATION_SCHEMA_VERSION = "1.0"
OBJECTIVE_SAFETY_POLICY_ID = "pne.objective-safety.playlist-intent"
OBJECTIVE_SAFETY_POLICY_VERSION = "1.0"
OBJECTIVE_SAFETY_POLICY_SHA256 = (
    "eb3f69d3a84b107b21344ce25264476f012a76ae7f7aee2116d710d9c768f592"
)
OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION = (
    "Objective Safety policy pne.objective-safety.playlist-intent/1.0 "
    "authorizes this established LISTENING_JOURNEY_EXPRESSION intent to "
    "proceed to Journey Planning."
)


class FrozenObjectiveSafetyModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class SafetyDecision(StrEnum):
    ACCEPTED = "accepted"
    DECLINED = "declined"


class ObjectiveIntentEvidenceState(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTING = "CONFLICTING"
    UNVERIFIABLE = "UNVERIFIABLE"
    UNSUPPORTED = "UNSUPPORTED"


class ObjectiveIntentCategory(StrEnum):
    LISTENING_JOURNEY_EXPRESSION = "LISTENING_JOURNEY_EXPRESSION"
    NON_PLAYLIST_ACTION_OR_OUTPUT = "NON_PLAYLIST_ACTION_OR_OUTPUT"
    PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL = (
        "PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL"
    )
    CLINICAL_OR_CRISIS_SUBSTITUTION = "CLINICAL_OR_CRISIS_SUBSTITUTION"


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


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude={"canonical_sha256"})
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"unsupported objective-safety canonical value: {type(value)!r}")


def _sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _verify_or_set_digest(model: BaseModel) -> None:
    supplied = getattr(model, "canonical_sha256")
    expected = _sha256(model)
    if supplied is not None and supplied != expected:
        raise ValueError("canonical SHA-256 must match objective-safety content")
    object.__setattr__(model, "canonical_sha256", expected)


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


class ObjectiveIntentDeclarationArtifact(FrozenObjectiveSafetyModel):
    schema_version: Literal["1.0"] = OBJECTIVE_INTENT_DECLARATION_SCHEMA_VERSION
    artifact_kind: Literal["objective_intent_declaration"] = (
        "objective_intent_declaration"
    )
    declaration_id: str = Field(min_length=1, max_length=200)
    objective_id: str = Field(min_length=1, max_length=100)
    objective_statement_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_type: Literal["OBJECTIVE_OWNER_ATTESTATION"] = (
        "OBJECTIVE_OWNER_ATTESTATION"
    )
    authority_reference: str = Field(min_length=1, max_length=1_000)
    state: ObjectiveIntentEvidenceState
    intent_category: ObjectiveIntentCategory | None = None
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("declaration_id", "objective_id", "authority_reference")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_state_contract(self) -> ObjectiveIntentDeclarationArtifact:
        if self.state is ObjectiveIntentEvidenceState.ESTABLISHED:
            if self.intent_category is None:
                raise ValueError("ESTABLISHED intent requires an exact category")
        elif self.intent_category is not None:
            raise ValueError("non-established intent cannot contain a category")
        _verify_or_set_digest(self)
        return self


class ObjectiveSafetyRequest(FrozenObjectiveSafetyModel):
    schema_version: Literal["2.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    objective_assessment: ObjectiveAssessment
    objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration: ObjectiveIntentDeclarationArtifact | None = None
    intent_declaration_id: str | None = None
    intent_declaration_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    safety_policy_id: Literal["pne.objective-safety.playlist-intent"] = (
        OBJECTIVE_SAFETY_POLICY_ID
    )
    safety_policy_version: Literal["1.0"] = OBJECTIVE_SAFETY_POLICY_VERSION
    safety_policy_sha256: Literal[
        "eb3f69d3a84b107b21344ce25264476f012a76ae7f7aee2116d710d9c768f592"
    ] = OBJECTIVE_SAFETY_POLICY_SHA256
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("request_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def require_authority_correspondence(self) -> ObjectiveSafetyRequest:
        if self.objective_assessment.outcome is not AssessmentOutcome.SUFFICIENT:
            raise ValueError("Objective Safety requires a sufficient assessment")
        if self.objective_sha256 != _sha256(self.objective_assessment.objective):
            raise ValueError("objective SHA-256 must bind the assessed objective")
        if self.objective_assessment_sha256 != _sha256(self.objective_assessment):
            raise ValueError("assessment SHA-256 must bind the exact assessment")
        declaration = self.intent_declaration
        declaration_binding = (
            self.intent_declaration_id,
            self.intent_declaration_sha256,
        )
        if declaration is None:
            if declaration_binding != (None, None):
                raise ValueError("absent intent declaration cannot have bindings")
        else:
            if declaration.objective_id != self.objective_assessment.objective.objective_id:
                raise ValueError("intent declaration must bind the assessed objective")
            statement_sha256 = hashlib.sha256(
                self.objective_assessment.objective.statement.encode("utf-8")
            ).hexdigest()
            if declaration.objective_statement_sha256 != statement_sha256:
                raise ValueError("intent declaration must bind the objective statement")
            if declaration_binding != (
                declaration.declaration_id,
                declaration.canonical_sha256,
            ):
                raise ValueError("intent declaration bindings must match exactly")
        _require_unique_metadata(self.objective_metadata, "objective metadata")
        _require_unique_metadata(self.context_metadata, "context metadata")
        _verify_or_set_digest(self)
        return self


class ObjectiveSafetyInputBinding(FrozenObjectiveSafetyModel):
    schema_version: Literal["1.0"] = "1.0"
    request_id: str
    request_schema_version: str
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_id: str
    objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_schema_version: str
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration_id: str | None
    intent_declaration_schema_version: str | None
    intent_declaration_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    safety_policy_id: str
    safety_policy_version: str
    safety_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "request_id",
        "request_schema_version",
        "objective_id",
        "assessment_schema_version",
        "safety_policy_id",
        "safety_policy_version",
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_complete_optional_declaration(self) -> ObjectiveSafetyInputBinding:
        values = (
            self.intent_declaration_id,
            self.intent_declaration_schema_version,
            self.intent_declaration_sha256,
        )
        if any(value is not None for value in values) and not all(
            value is not None for value in values
        ):
            raise ValueError("intent declaration binding must be complete or absent")
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
    schema_version: Literal["2.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    artifact_kind: Literal["accepted_objective"] = "accepted_objective"
    artifact_id: str = Field(min_length=1, max_length=200)
    input_binding: ObjectiveSafetyInputBinding
    request_id: str = Field(min_length=1, max_length=200)
    objective: Objective
    safety_policy_id: Literal["pne.objective-safety.playlist-intent"] = (
        OBJECTIVE_SAFETY_POLICY_ID
    )
    safety_policy_version: Literal["1.0"] = OBJECTIVE_SAFETY_POLICY_VERSION
    safety_policy_sha256: Literal[
        "eb3f69d3a84b107b21344ce25264476f012a76ae7f7aee2116d710d9c768f592"
    ] = OBJECTIVE_SAFETY_POLICY_SHA256
    decision: Literal[SafetyDecision.ACCEPTED] = SafetyDecision.ACCEPTED
    decision_explanation: Literal[
        "Objective Safety policy pne.objective-safety.playlist-intent/1.0 authorizes this established LISTENING_JOURNEY_EXPRESSION intent to proceed to Journey Planning."
    ] = OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    journey_planning_authorized: Literal[True] = True
    musical_content_evaluated: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id", "request_id")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def require_binding_consistency(self) -> AcceptedObjectiveArtifact:
        _require_result_binding_consistency(self)
        _verify_or_set_digest(self)
        return self


class DeclinedObjectiveArtifact(FrozenObjectiveSafetyModel):
    schema_version: Literal["2.0"] = OBJECTIVE_SAFETY_SCHEMA_VERSION
    artifact_kind: Literal["declined_objective"] = "declined_objective"
    artifact_id: str = Field(min_length=1, max_length=200)
    input_binding: ObjectiveSafetyInputBinding
    request_id: str = Field(min_length=1, max_length=200)
    objective: Objective
    safety_policy_id: Literal["pne.objective-safety.playlist-intent"] = (
        OBJECTIVE_SAFETY_POLICY_ID
    )
    safety_policy_version: Literal["1.0"] = OBJECTIVE_SAFETY_POLICY_VERSION
    safety_policy_sha256: Literal[
        "eb3f69d3a84b107b21344ce25264476f012a76ae7f7aee2116d710d9c768f592"
    ] = OBJECTIVE_SAFETY_POLICY_SHA256
    decision: Literal[SafetyDecision.DECLINED] = SafetyDecision.DECLINED
    reasons: tuple[ObjectiveSafetyReason, ...] = Field(min_length=1)
    objective_metadata: tuple[SafetyMetadataEntry, ...] = ()
    context_metadata: tuple[SafetyMetadataEntry, ...] = ()
    journey_planning_authorized: Literal[False] = False
    musical_content_evaluated: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id", "request_id")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("objective_metadata", "context_metadata", mode="before")
    @classmethod
    def canonicalize_metadata(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=_input_key))

    @model_validator(mode="after")
    def enforce_reason_and_binding_contract(self) -> DeclinedObjectiveArtifact:
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
        _require_result_binding_consistency(self)
        _verify_or_set_digest(self)
        return self


ObjectiveSafetyArtifact = AcceptedObjectiveArtifact | DeclinedObjectiveArtifact


def create_objective_safety_input_binding(
    request: ObjectiveSafetyRequest,
) -> ObjectiveSafetyInputBinding:
    declaration = request.intent_declaration
    return ObjectiveSafetyInputBinding(
        request_id=request.request_id,
        request_schema_version=request.schema_version,
        request_sha256=request.canonical_sha256,
        objective_id=request.objective_assessment.objective.objective_id,
        objective_sha256=request.objective_sha256,
        assessment_schema_version=request.objective_assessment.schema_version,
        assessment_sha256=request.objective_assessment_sha256,
        intent_declaration_id=(declaration.declaration_id if declaration else None),
        intent_declaration_schema_version=(
            declaration.schema_version if declaration else None
        ),
        intent_declaration_sha256=(
            declaration.canonical_sha256 if declaration else None
        ),
        safety_policy_id=request.safety_policy_id,
        safety_policy_version=request.safety_policy_version,
        safety_policy_sha256=request.safety_policy_sha256,
    )


def canonical_objective_sha256(objective: Objective) -> str:
    return _sha256(objective)


def canonical_assessment_sha256(assessment: ObjectiveAssessment) -> str:
    return _sha256(assessment)


def verify_objective_safety_request(request: ObjectiveSafetyRequest) -> bool:
    try:
        return ObjectiveSafetyRequest.model_validate(
            request.model_dump(mode="json")
        ) == request
    except (TypeError, ValueError):
        return False


def verify_objective_safety_artifact(
    artifact: ObjectiveSafetyArtifact,
    *,
    request: ObjectiveSafetyRequest,
) -> bool:
    if not verify_objective_safety_request(request):
        return False
    try:
        validated = type(artifact).model_validate(artifact.model_dump(mode="json"))
    except (TypeError, ValueError):
        return False
    if validated != artifact:
        return False
    if artifact.input_binding != create_objective_safety_input_binding(request):
        return False
    if (
        artifact.request_id != request.request_id
        or artifact.objective != request.objective_assessment.objective
        or artifact.objective_metadata != request.objective_metadata
        or artifact.context_metadata != request.context_metadata
    ):
        return False
    expected = _expected_decision(request)
    if expected[0] is SafetyDecision.ACCEPTED:
        return isinstance(artifact, AcceptedObjectiveArtifact)
    if not isinstance(artifact, DeclinedObjectiveArtifact):
        return False
    return artifact.reasons == expected[1]


def _expected_decision(
    request: ObjectiveSafetyRequest,
) -> tuple[SafetyDecision, tuple[ObjectiveSafetyReason, ...]]:
    declaration = request.intent_declaration
    if declaration is None:
        return SafetyDecision.DECLINED, (
            _reason(
                ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
                "$.intent_declaration",
            ),
        )
    state = declaration.state
    if state is ObjectiveIntentEvidenceState.ESTABLISHED:
        if declaration.intent_category is ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION:
            return SafetyDecision.ACCEPTED, ()
        return SafetyDecision.DECLINED, (
            _reason(
                ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED,
                "$.intent_declaration.intent_category",
            ),
        )
    if state is ObjectiveIntentEvidenceState.UNAVAILABLE:
        return SafetyDecision.DECLINED, (
            _reason(
                ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
                "$.intent_declaration.intent_category",
            ),
        )
    field_path = (
        "$.intent_declaration.authority_reference"
        if state is ObjectiveIntentEvidenceState.UNVERIFIABLE
        else "$.intent_declaration.intent_category"
    )
    return SafetyDecision.DECLINED, (
        _reason(ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED, field_path),
    )


def _reason(code: ObjectiveSafetyReasonCode, field_path: str) -> ObjectiveSafetyReason:
    return ObjectiveSafetyReason(
        code=code,
        field_path=field_path,
        explanation=SAFETY_REASON_EXPLANATIONS[code],
    )


def _require_result_binding_consistency(
    artifact: AcceptedObjectiveArtifact | DeclinedObjectiveArtifact,
) -> None:
    if (
        artifact.request_id != artifact.input_binding.request_id
        or artifact.objective.objective_id != artifact.input_binding.objective_id
        or _sha256(artifact.objective) != artifact.input_binding.objective_sha256
        or artifact.safety_policy_id != artifact.input_binding.safety_policy_id
        or artifact.safety_policy_version != artifact.input_binding.safety_policy_version
        or artifact.safety_policy_sha256 != artifact.input_binding.safety_policy_sha256
    ):
        raise ValueError("objective-safety result bindings must match exactly")
    _require_unique_metadata(artifact.objective_metadata, "objective metadata")
    _require_unique_metadata(artifact.context_metadata, "context metadata")


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

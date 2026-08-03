from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import (
    serialize_objective_safety_artifact,
)


EVIDENCE_AUTHENTICATION_SCHEMA_VERSION = "1.0"
CHARACTERISTIC_VALUE_SCHEMA_ID = "penny.crossing_characteristic"
CHARACTERISTIC_VALUE_SCHEMA_VERSION = "1.0"
AUTHENTICATION_POLICY_ID = "ea1.authentication"
AUTHENTICATION_POLICY_VERSION = "1.0"
AUTHENTICATION_RULE_SET_ID = "ea1.authentication_rules"
AUTHENTICATION_RULE_SET_VERSION = "1.0"


class FrozenAuthenticationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CharacteristicRole(StrEnum):
    ENDING = "ending"
    BEGINNING = "beginning"


class AuthenticationMethod(StrEnum):
    EXACT_USER_CONFIRMATION = "exact_user_confirmation"
    VERSIONED_DERIVATION = "versioned_derivation"


class ObservationType(StrEnum):
    USER_CONFIRMATION = "user_confirmation"
    STRUCTURED_FACT = "structured_fact"
    GENERIC_STATEMENT = "generic_statement"


class ObservationSourceType(StrEnum):
    USER = "user"
    VALIDATED_RECORD = "validated_record"


class ObservationState(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


class AuthenticationReasonCode(StrEnum):
    CONFIRMATION_TYPE_NOT_AUTHORIZED = "CONFIRMATION_TYPE_NOT_AUTHORIZED"
    CONFIRMATION_VALUE_MISMATCH = "CONFIRMATION_VALUE_MISMATCH"
    CHARACTERISTIC_SCHEMA_UNSUPPORTED = "CHARACTERISTIC_SCHEMA_UNSUPPORTED"
    DERIVATION_RULE_NOT_APPROVED = "DERIVATION_RULE_NOT_APPROVED"
    DERIVATION_RULE_VERSION_UNSUPPORTED = "DERIVATION_RULE_VERSION_UNSUPPORTED"
    DERIVATION_INPUT_UNAVAILABLE = "DERIVATION_INPUT_UNAVAILABLE"
    DERIVATION_INPUT_UNSUPPORTED = "DERIVATION_INPUT_UNSUPPORTED"
    DERIVATION_INPUT_CONFLICTING = "DERIVATION_INPUT_CONFLICTING"
    DERIVATION_INPUT_MISMATCH = "DERIVATION_INPUT_MISMATCH"
    DERIVATION_OUTPUT_MISMATCH = "DERIVATION_OUTPUT_MISMATCH"
    AUTHENTICATION_PROVENANCE_INCOMPLETE = "AUTHENTICATION_PROVENANCE_INCOMPLETE"


AUTHENTICATION_REASON_PRECEDENCE = tuple(AuthenticationReasonCode)
AUTHENTICATION_REASON_EXPLANATIONS = {
    AuthenticationReasonCode.CONFIRMATION_TYPE_NOT_AUTHORIZED: (
        "The referenced observation is not an authorized exact user confirmation."
    ),
    AuthenticationReasonCode.CONFIRMATION_VALUE_MISMATCH: (
        "The confirmation payload does not reproduce the proposed characteristic exactly."
    ),
    AuthenticationReasonCode.CHARACTERISTIC_SCHEMA_UNSUPPORTED: (
        "The proposed characteristic is not part of the governed characteristic schema."
    ),
    AuthenticationReasonCode.DERIVATION_RULE_NOT_APPROVED: (
        "The requested derivation rule is not part of the approved authentication rule set."
    ),
    AuthenticationReasonCode.DERIVATION_RULE_VERSION_UNSUPPORTED: (
        "The requested derivation-rule version is not approved."
    ),
    AuthenticationReasonCode.DERIVATION_INPUT_UNAVAILABLE: (
        "A required derivation input is unavailable."
    ),
    AuthenticationReasonCode.DERIVATION_INPUT_UNSUPPORTED: (
        "A required derivation input is unsupported."
    ),
    AuthenticationReasonCode.DERIVATION_INPUT_CONFLICTING: (
        "A required derivation input is conflicting."
    ),
    AuthenticationReasonCode.DERIVATION_INPUT_MISMATCH: (
        "A derivation input does not match the approved rule contract exactly."
    ),
    AuthenticationReasonCode.DERIVATION_OUTPUT_MISMATCH: (
        "The proposed characteristic does not match the approved rule output exactly."
    ),
    AuthenticationReasonCode.AUTHENTICATION_PROVENANCE_INCOMPLETE: (
        "The authentication attempt does not contain complete required provenance."
    ),
}


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


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("authentication identity text must be nonblank and exact")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def canonicalize_json_value(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def _require_canonical_json(value: str) -> str:
    try:
        parsed = json.loads(
            value,
            parse_constant=_reject_json_constant,
            object_pairs_hook=_unique_json_object,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("payload must be valid duplicate-free JSON") from exc
    if canonicalize_json_value(parsed) != value:
        raise ValueError("payload JSON must use the canonical encoding")
    return value


def _canonical_model_bytes(model: BaseModel) -> bytes:
    return json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class GovernedCharacteristicDefinition(FrozenAuthenticationModel):
    characteristic_id: str = Field(min_length=1, max_length=200)
    role: CharacteristicRole
    canonical_value_json: str = Field(max_length=10_000)

    @field_validator("characteristic_id")
    @classmethod
    def require_exact_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("canonical_value_json")
    @classmethod
    def require_canonical_value(cls, value: str) -> str:
        return _require_canonical_json(value)


GOVERNED_CHARACTERISTICS = (
    GovernedCharacteristicDefinition(
        characteristic_id="role.established",
        role=CharacteristicRole.ENDING,
        canonical_value_json=canonicalize_json_value("established role"),
    ),
    GovernedCharacteristicDefinition(
        characteristic_id="role.unproven",
        role=CharacteristicRole.BEGINNING,
        canonical_value_json=canonicalize_json_value("unproven role"),
    ),
    GovernedCharacteristicDefinition(
        characteristic_id="identity.anchored_in_departed_role_or_relationship",
        role=CharacteristicRole.ENDING,
        canonical_value_json=canonicalize_json_value(
            "identity anchored in a departed role or relationship"
        ),
    ),
    GovernedCharacteristicDefinition(
        characteristic_id="identity.not_established_after_departure",
        role=CharacteristicRole.BEGINNING,
        canonical_value_json=canonicalize_json_value(
            "identity not yet established after departure"
        ),
    ),
    GovernedCharacteristicDefinition(
        characteristic_id="context.away_from_familiar",
        role=CharacteristicRole.ENDING,
        canonical_value_json=canonicalize_json_value(
            "life away from a familiar place, practice, or relationship"
        ),
    ),
    GovernedCharacteristicDefinition(
        characteristic_id="context.return_to_changed_familiar",
        role=CharacteristicRole.BEGINNING,
        canonical_value_json=canonicalize_json_value(
            "return to a familiar context changed by time or experience"
        ),
    ),
)
GOVERNED_CHARACTERISTIC_BY_KEY = {
    (item.role, item.characteristic_id): item for item in GOVERNED_CHARACTERISTICS
}


def confirmation_payload(
    definition: GovernedCharacteristicDefinition,
) -> str:
    return canonicalize_json_value(
        {
            "characteristic_id": definition.characteristic_id,
            "role": definition.role.value,
            "value": json.loads(definition.canonical_value_json),
            "value_schema_id": CHARACTERISTIC_VALUE_SCHEMA_ID,
            "value_schema_version": CHARACTERISTIC_VALUE_SCHEMA_VERSION,
        }
    )


class AuthenticationSourceObservation(FrozenAuthenticationModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    observation_type: ObservationType
    source_type: ObservationSourceType
    source_reference: str = Field(min_length=1, max_length=1_000)
    state: ObservationState
    payload_json: str | None = Field(default=None, max_length=100_000)

    @field_validator("evidence_id", "source_reference")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("payload_json")
    @classmethod
    def require_canonical_payload(cls, value: str | None) -> str | None:
        return _require_canonical_json(value) if value is not None else None

    @model_validator(mode="after")
    def enforce_state_contract(self) -> AuthenticationSourceObservation:
        if self.state is ObservationState.AVAILABLE:
            if self.payload_json is None:
                raise ValueError("available observations require a canonical payload")
        elif self.payload_json is not None:
            raise ValueError("non-available observations cannot carry substitute payloads")
        return self


class CharacteristicProposal(FrozenAuthenticationModel):
    role: CharacteristicRole
    characteristic_id: str = Field(min_length=1, max_length=200)
    canonical_value_json: str = Field(max_length=10_000)

    @field_validator("characteristic_id")
    @classmethod
    def require_exact_characteristic_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("canonical_value_json")
    @classmethod
    def require_canonical_characteristic_value(cls, value: str) -> str:
        return _require_canonical_json(value)


class ExactConfirmationAttempt(FrozenAuthenticationModel):
    attempt_id: str = Field(min_length=1, max_length=200)
    method: Literal["exact_user_confirmation"] = "exact_user_confirmation"
    proposal: CharacteristicProposal
    confirmation_evidence_id: str = Field(min_length=1, max_length=200)

    @field_validator("attempt_id", "confirmation_evidence_id")
    @classmethod
    def require_exact_ids(cls, value: str) -> str:
        return _exact(value)


class VersionedDerivationAttempt(FrozenAuthenticationModel):
    attempt_id: str = Field(min_length=1, max_length=200)
    method: Literal["versioned_derivation"] = "versioned_derivation"
    proposal: CharacteristicProposal
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    input_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("attempt_id", "rule_id", "rule_version")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("input_evidence_ids", mode="before")
    @classmethod
    def canonicalize_input_ids(cls, value: Any) -> tuple[str, ...]:
        items = tuple(value)
        for item in items:
            _exact(item)
        if len(items) != len(set(items)):
            raise ValueError("derivation input evidence IDs must be unique")
        return tuple(sorted(items, key=_utf8_key))


AuthenticationAttempt = Annotated[
    ExactConfirmationAttempt | VersionedDerivationAttempt,
    Field(discriminator="method"),
]


class RuleInputRequirement(FrozenAuthenticationModel):
    observation_type: ObservationType
    source_type: ObservationSourceType
    payload_json: str = Field(max_length=100_000)

    @field_validator("payload_json")
    @classmethod
    def require_canonical_payload(cls, value: str) -> str:
        return _require_canonical_json(value)


class AuthenticationRule(FrozenAuthenticationModel):
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    input_requirements: tuple[RuleInputRequirement, ...] = Field(min_length=1)
    output: GovernedCharacteristicDefinition

    @field_validator("rule_id", "rule_version")
    @classmethod
    def require_exact_rule_identity(cls, value: str) -> str:
        return _exact(value)


class AuthenticationRuleSet(FrozenAuthenticationModel):
    rule_set_id: Literal["ea1.authentication_rules"] = AUTHENTICATION_RULE_SET_ID
    rule_set_version: Literal["1.0"] = AUTHENTICATION_RULE_SET_VERSION
    rules: tuple[AuthenticationRule, ...] = Field(min_length=1)

    @field_validator("rules", mode="before")
    @classmethod
    def canonicalize_rules(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "rule_id")

    @model_validator(mode="after")
    def enforce_rule_set_uniqueness(self) -> AuthenticationRuleSet:
        rule_ids = tuple(rule.rule_id for rule in self.rules)
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("authentication rule identities must be unique")
        output_keys = tuple(
            (rule.output.role, rule.output.characteristic_id) for rule in self.rules
        )
        if len(output_keys) != len(set(output_keys)):
            raise ValueError("authentication rule output grants must be unique")
        input_contracts = tuple(
            tuple(
                (item.observation_type, item.source_type, item.payload_json)
                for item in rule.input_requirements
            )
            for rule in self.rules
        )
        if len(input_contracts) != len(set(input_contracts)):
            raise ValueError("authentication rule input contracts must be unique")
        return self


def _fact_payload(fact_id: str, value: str) -> str:
    return canonicalize_json_value({"fact_id": fact_id, "value": value})


def _rule(
    rule_id: str,
    fact_id: str,
    fact_value: str,
    output_key: tuple[CharacteristicRole, str],
) -> AuthenticationRule:
    return AuthenticationRule(
        rule_id=rule_id,
        rule_version="1.0",
        input_requirements=(
            RuleInputRequirement(
                observation_type=ObservationType.STRUCTURED_FACT,
                source_type=ObservationSourceType.VALIDATED_RECORD,
                payload_json=_fact_payload(fact_id, fact_value),
            ),
        ),
        output=GOVERNED_CHARACTERISTIC_BY_KEY[output_key],
    )


APPROVED_AUTHENTICATION_RULE_SET = AuthenticationRuleSet(
    rules=(
        _rule(
            "ea1.derive_role_established",
            "role_status",
            "established",
            (CharacteristicRole.ENDING, "role.established"),
        ),
        _rule(
            "ea1.derive_role_unproven",
            "role_status",
            "unproven",
            (CharacteristicRole.BEGINNING, "role.unproven"),
        ),
        _rule(
            "ea1.derive_identity_anchored_departed",
            "identity_status",
            "anchored_in_departed_role_or_relationship",
            (
                CharacteristicRole.ENDING,
                "identity.anchored_in_departed_role_or_relationship",
            ),
        ),
        _rule(
            "ea1.derive_identity_not_established_after_departure",
            "identity_status",
            "not_established_after_departure",
            (
                CharacteristicRole.BEGINNING,
                "identity.not_established_after_departure",
            ),
        ),
        _rule(
            "ea1.derive_context_away_from_familiar",
            "context_status",
            "away_from_familiar",
            (CharacteristicRole.ENDING, "context.away_from_familiar"),
        ),
        _rule(
            "ea1.derive_context_return_to_changed_familiar",
            "context_status",
            "return_to_changed_familiar",
            (
                CharacteristicRole.BEGINNING,
                "context.return_to_changed_familiar",
            ),
        ),
    )
)


def serialize_authentication_rule_set(rule_set: AuthenticationRuleSet) -> bytes:
    return _canonical_model_bytes(rule_set)


APPROVED_AUTHENTICATION_RULE_SET_SHA256 = _sha256(
    serialize_authentication_rule_set(APPROVED_AUTHENTICATION_RULE_SET)
)


def authentication_failure_specs(
    attempt: AuthenticationAttempt,
    observations_by_id: dict[str, AuthenticationSourceObservation],
    rules_by_id: dict[str, AuthenticationRule],
) -> tuple[tuple[AuthenticationReasonCode, str], ...]:
    specs: list[tuple[AuthenticationReasonCode, str]] = []
    if isinstance(attempt, ExactConfirmationAttempt):
        definition = GOVERNED_CHARACTERISTIC_BY_KEY.get(
            (attempt.proposal.role, attempt.proposal.characteristic_id)
        )
        if definition is None or (
            definition.canonical_value_json != attempt.proposal.canonical_value_json
        ):
            specs.append((AuthenticationReasonCode.CHARACTERISTIC_SCHEMA_UNSUPPORTED, "proposal"))
        observation = observations_by_id.get(attempt.confirmation_evidence_id)
        if observation is None:
            specs.append(
                (
                    AuthenticationReasonCode.AUTHENTICATION_PROVENANCE_INCOMPLETE,
                    "confirmation_evidence_id",
                )
            )
        else:
            if (
                observation.observation_type is not ObservationType.USER_CONFIRMATION
                or observation.source_type is not ObservationSourceType.USER
            ):
                specs.append(
                    (
                        AuthenticationReasonCode.CONFIRMATION_TYPE_NOT_AUTHORIZED,
                        "confirmation_evidence_id",
                    )
                )
            expected_payload = (
                confirmation_payload(definition) if definition is not None else None
            )
            if (
                observation.state is not ObservationState.AVAILABLE
                or expected_payload is None
                or observation.payload_json != expected_payload
            ):
                specs.append(
                    (
                        AuthenticationReasonCode.CONFIRMATION_VALUE_MISMATCH,
                        "confirmation_evidence_id",
                    )
                )
    else:
        rule = rules_by_id.get(attempt.rule_id)
        if rule is None:
            specs.append((AuthenticationReasonCode.DERIVATION_RULE_NOT_APPROVED, "rule_id"))
        elif attempt.rule_version != rule.rule_version:
            specs.append(
                (
                    AuthenticationReasonCode.DERIVATION_RULE_VERSION_UNSUPPORTED,
                    "rule_version",
                )
            )
        for index, evidence_id in enumerate(attempt.input_evidence_ids):
            observation = observations_by_id.get(evidence_id)
            path = f"input_evidence_ids.{index}"
            if observation is None or observation.state is ObservationState.UNAVAILABLE:
                specs.append((AuthenticationReasonCode.DERIVATION_INPUT_UNAVAILABLE, path))
            elif observation.state is ObservationState.UNSUPPORTED:
                specs.append((AuthenticationReasonCode.DERIVATION_INPUT_UNSUPPORTED, path))
            elif observation.state is ObservationState.CONFLICTING:
                specs.append((AuthenticationReasonCode.DERIVATION_INPUT_CONFLICTING, path))
        if rule is not None:
            if len(attempt.input_evidence_ids) != len(rule.input_requirements):
                specs.append(
                    (
                        AuthenticationReasonCode.AUTHENTICATION_PROVENANCE_INCOMPLETE,
                        "input_evidence_ids",
                    )
                )
            for index, requirement in enumerate(rule.input_requirements):
                if index >= len(attempt.input_evidence_ids):
                    continue
                observation = observations_by_id.get(attempt.input_evidence_ids[index])
                if observation is not None and observation.state is ObservationState.AVAILABLE:
                    if (
                        observation.observation_type is not requirement.observation_type
                        or observation.source_type is not requirement.source_type
                        or observation.payload_json != requirement.payload_json
                    ):
                        specs.append(
                            (AuthenticationReasonCode.DERIVATION_INPUT_MISMATCH, f"input_evidence_ids.{index}")
                        )
            if (
                attempt.proposal.role is not rule.output.role
                or attempt.proposal.characteristic_id != rule.output.characteristic_id
                or attempt.proposal.canonical_value_json != rule.output.canonical_value_json
            ):
                specs.append((AuthenticationReasonCode.DERIVATION_OUTPUT_MISMATCH, "proposal"))
    precedence = {
        code: index for index, code in enumerate(AUTHENTICATION_REASON_PRECEDENCE)
    }
    return tuple(
        sorted(specs, key=lambda item: (precedence[item[0]], _utf8_key(item[1])))
    )


class EvidenceAuthenticationRequest(FrozenAuthenticationModel):
    schema_version: Literal["1.0"] = EVIDENCE_AUTHENTICATION_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observations: tuple[AuthenticationSourceObservation, ...] = Field(min_length=1)
    attempts: tuple[AuthenticationAttempt, ...] = Field(min_length=1)
    characteristic_value_schema_id: Literal["penny.crossing_characteristic"] = (
        CHARACTERISTIC_VALUE_SCHEMA_ID
    )
    characteristic_value_schema_version: Literal["1.0"] = (
        CHARACTERISTIC_VALUE_SCHEMA_VERSION
    )
    authentication_policy_id: Literal["ea1.authentication"] = AUTHENTICATION_POLICY_ID
    authentication_policy_version: Literal["1.0"] = AUTHENTICATION_POLICY_VERSION
    authentication_rule_set: AuthenticationRuleSet
    authentication_rule_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("request_id")
    @classmethod
    def require_exact_request_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @field_validator("attempts", mode="before")
    @classmethod
    def canonicalize_attempts(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "attempt_id")

    @model_validator(mode="after")
    def enforce_authority_correspondence(self) -> EvidenceAuthenticationRequest:
        expected_objective_digest = _sha256(
            serialize_objective_safety_artifact(self.accepted_objective)
        )
        if self.accepted_objective_sha256 != expected_objective_digest:
            raise ValueError("accepted-objective canonical digest must match exactly")
        if self.authentication_rule_set != APPROVED_AUTHENTICATION_RULE_SET:
            raise ValueError("request must use the exact approved authentication rule set")
        actual_rule_set_digest = _sha256(
            serialize_authentication_rule_set(self.authentication_rule_set)
        )
        if self.authentication_rule_set_sha256 != actual_rule_set_digest:
            raise ValueError("authentication rule-set digest must match exactly")
        evidence_ids = tuple(item.evidence_id for item in self.observations)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("authentication observation identities must be unique")
        attempt_ids = tuple(item.attempt_id for item in self.attempts)
        if len(attempt_ids) != len(set(attempt_ids)):
            raise ValueError("authentication attempt identities must be unique")
        return self


class ExactConfirmationLineage(FrozenAuthenticationModel):
    method: Literal["exact_user_confirmation"] = "exact_user_confirmation"
    confirmation_evidence_id: str = Field(min_length=1, max_length=200)

    @field_validator("confirmation_evidence_id")
    @classmethod
    def require_exact_evidence_id(cls, value: str) -> str:
        return _exact(value)


class DerivationLineage(FrozenAuthenticationModel):
    method: Literal["versioned_derivation"] = "versioned_derivation"
    rule_set_id: Literal["ea1.authentication_rules"] = AUTHENTICATION_RULE_SET_ID
    rule_set_version: Literal["1.0"] = AUTHENTICATION_RULE_SET_VERSION
    rule_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    input_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("rule_id", "rule_version")
    @classmethod
    def require_exact_rule_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("input_evidence_ids", mode="before")
    @classmethod
    def canonicalize_input_ids(cls, value: Any) -> tuple[str, ...]:
        items = tuple(value)
        for item in items:
            _exact(item)
        if len(items) != len(set(items)):
            raise ValueError("derivation lineage input IDs must be unique")
        return tuple(sorted(items, key=_utf8_key))


AuthenticationLineage = Annotated[
    ExactConfirmationLineage | DerivationLineage,
    Field(discriminator="method"),
]


class AuthenticatedStructuredCharacteristic(FrozenAuthenticationModel):
    authenticated_characteristic_id: str = Field(min_length=1, max_length=200)
    attempt_id: str = Field(min_length=1, max_length=200)
    role: CharacteristicRole
    characteristic_id: str = Field(min_length=1, max_length=200)
    characteristic_value_schema_id: Literal["penny.crossing_characteristic"] = (
        CHARACTERISTIC_VALUE_SCHEMA_ID
    )
    characteristic_value_schema_version: Literal["1.0"] = (
        CHARACTERISTIC_VALUE_SCHEMA_VERSION
    )
    canonical_value_json: str = Field(max_length=10_000)
    source_observations: tuple[AuthenticationSourceObservation, ...] = Field(min_length=1)
    authentication_method: AuthenticationMethod
    lineage: AuthenticationLineage
    authentication_policy_id: Literal["ea1.authentication"] = AUTHENTICATION_POLICY_ID
    authentication_policy_version: Literal["1.0"] = AUTHENTICATION_POLICY_VERSION

    @field_validator("authenticated_characteristic_id", "attempt_id", "characteristic_id")
    @classmethod
    def require_exact_ids(cls, value: str) -> str:
        return _exact(value)

    @field_validator("canonical_value_json")
    @classmethod
    def require_canonical_value(cls, value: str) -> str:
        return _require_canonical_json(value)

    @field_validator("source_observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @model_validator(mode="after")
    def enforce_authenticated_contract(self) -> AuthenticatedStructuredCharacteristic:
        if self.authenticated_characteristic_id != self.attempt_id:
            raise ValueError("authenticated characteristic identity must equal its attempt identity")
        definition = GOVERNED_CHARACTERISTIC_BY_KEY.get((self.role, self.characteristic_id))
        if definition is None or self.canonical_value_json != definition.canonical_value_json:
            raise ValueError("authenticated characteristic must use the governed vocabulary")
        if self.authentication_method.value != self.lineage.method:
            raise ValueError("authentication method must match lineage")
        evidence_ids = tuple(item.evidence_id for item in self.source_observations)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("authenticated source observations must be unique")
        if isinstance(self.lineage, ExactConfirmationLineage):
            if evidence_ids != (self.lineage.confirmation_evidence_id,):
                raise ValueError("confirmation lineage must identify the exact source observation")
        elif evidence_ids != self.lineage.input_evidence_ids:
            raise ValueError("derivation lineage must identify exact source observations")
        return self


class AuthenticationReason(FrozenAuthenticationModel):
    code: AuthenticationReasonCode
    field_path: str = Field(min_length=1, max_length=500)
    explanation: str

    @field_validator("field_path")
    @classmethod
    def require_exact_field_path(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_fixed_explanation(self) -> AuthenticationReason:
        if self.explanation != AUTHENTICATION_REASON_EXPLANATIONS[self.code]:
            raise ValueError("authentication reason explanation must match its fixed contract")
        return self


class WithheldAuthenticationAttempt(FrozenAuthenticationModel):
    attempt_id: str = Field(min_length=1, max_length=200)
    attempt: AuthenticationAttempt
    referenced_observations: tuple[AuthenticationSourceObservation, ...]
    reasons: tuple[AuthenticationReason, ...] = Field(min_length=1)

    @field_validator("attempt_id")
    @classmethod
    def require_exact_attempt_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("referenced_observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @field_validator("reasons")
    @classmethod
    def canonicalize_reasons(
        cls, value: tuple[AuthenticationReason, ...]
    ) -> tuple[AuthenticationReason, ...]:
        precedence = {
            code: index for index, code in enumerate(AUTHENTICATION_REASON_PRECEDENCE)
        }
        return tuple(
            sorted(
                value,
                key=lambda reason: (
                    precedence[reason.code],
                    _utf8_key(reason.field_path),
                ),
            )
        )

    @model_validator(mode="after")
    def enforce_withheld_contract(self) -> WithheldAuthenticationAttempt:
        if self.attempt_id != self.attempt.attempt_id:
            raise ValueError("withheld attempt identity must correspond exactly")
        reason_keys = tuple((item.code, item.field_path) for item in self.reasons)
        if len(reason_keys) != len(set(reason_keys)):
            raise ValueError("withholding reasons must be unique by code and field path")
        evidence_ids = tuple(item.evidence_id for item in self.referenced_observations)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("withheld referenced observations must be unique")
        return self


class AuthenticationSummary(FrozenAuthenticationModel):
    attempt_count: int = Field(ge=0, strict=True)
    authenticated_count: int = Field(ge=0, strict=True)
    withheld_count: int = Field(ge=0, strict=True)

    @model_validator(mode="after")
    def enforce_complete_count(self) -> AuthenticationSummary:
        if self.authenticated_count + self.withheld_count != self.attempt_count:
            raise ValueError("authentication summary must account for every attempt")
        return self


class AuthenticatedStructuredCharacteristicArtifactContent(FrozenAuthenticationModel):
    schema_version: Literal["1.0"] = EVIDENCE_AUTHENTICATION_SCHEMA_VERSION
    artifact_kind: Literal["authenticated_structured_characteristics"] = (
        "authenticated_structured_characteristics"
    )
    artifact_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    characteristic_value_schema_id: Literal["penny.crossing_characteristic"] = (
        CHARACTERISTIC_VALUE_SCHEMA_ID
    )
    characteristic_value_schema_version: Literal["1.0"] = (
        CHARACTERISTIC_VALUE_SCHEMA_VERSION
    )
    authentication_policy_id: Literal["ea1.authentication"] = AUTHENTICATION_POLICY_ID
    authentication_policy_version: Literal["1.0"] = AUTHENTICATION_POLICY_VERSION
    authentication_rule_set: AuthenticationRuleSet
    authentication_rule_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_observations: tuple[AuthenticationSourceObservation, ...] = Field(min_length=1)
    authentication_attempts: tuple[AuthenticationAttempt, ...] = Field(min_length=1)
    authenticated_characteristics: tuple[AuthenticatedStructuredCharacteristic, ...]
    withheld_authentication_attempts: tuple[WithheldAuthenticationAttempt, ...]
    summary: AuthenticationSummary
    crossing_inferred: Literal[False] = False
    recurring_condition_inferred: Literal[False] = False
    person_classified: Literal[False] = False
    person_diagnosed: Literal[False] = False
    particular_need_inferred: Literal[False] = False
    particular_need_confirmed: Literal[False] = False
    particular_need_modified: Literal[False] = False
    clarification_performed: Literal[False] = False
    accompaniment_inferred: Literal[False] = False
    explanation_generated: Literal[False] = False
    journey_planning_performed: Literal[False] = False
    provider_accessed: Literal[False] = False
    music_inspected: Literal[False] = False
    music_formed: Literal[False] = False
    music_scored: Literal[False] = False
    music_ranked: Literal[False] = False
    music_selected: Literal[False] = False
    music_sequenced: Literal[False] = False

    @field_validator("artifact_id", "request_id")
    @classmethod
    def require_exact_ids(cls, value: str) -> str:
        return _exact(value)

    @field_validator("source_observations", mode="before")
    @classmethod
    def canonicalize_source_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @field_validator("authentication_attempts", mode="before")
    @classmethod
    def canonicalize_attempts(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "attempt_id")

    @field_validator("authenticated_characteristics", mode="before")
    @classmethod
    def canonicalize_authenticated(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "authenticated_characteristic_id")

    @field_validator("withheld_authentication_attempts", mode="before")
    @classmethod
    def canonicalize_withheld(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "attempt_id")

    @model_validator(mode="after")
    def enforce_complete_artifact(self) -> AuthenticatedStructuredCharacteristicArtifactContent:
        if self.accepted_objective_sha256 != _sha256(
            serialize_objective_safety_artifact(self.accepted_objective)
        ):
            raise ValueError("artifact accepted-objective digest must match exactly")
        if self.authentication_rule_set != APPROVED_AUTHENTICATION_RULE_SET:
            raise ValueError("artifact must preserve the approved authentication rule set")
        if self.authentication_rule_set_sha256 != _sha256(
            serialize_authentication_rule_set(self.authentication_rule_set)
        ):
            raise ValueError("artifact authentication rule-set digest must match exactly")
        authenticated_attempt_ids = tuple(
            item.attempt_id for item in self.authenticated_characteristics
        )
        authenticated_characteristic_ids = tuple(
            item.authenticated_characteristic_id
            for item in self.authenticated_characteristics
        )
        if len(authenticated_characteristic_ids) != len(
            set(authenticated_characteristic_ids)
        ):
            raise ValueError("authenticated characteristic identities must be unique")
        withheld_attempt_ids = tuple(
            item.attempt_id for item in self.withheld_authentication_attempts
        )
        if set(authenticated_attempt_ids) & set(withheld_attempt_ids):
            raise ValueError("an authentication attempt cannot appear in both partitions")
        all_attempt_ids = authenticated_attempt_ids + withheld_attempt_ids
        if len(all_attempt_ids) != len(set(all_attempt_ids)):
            raise ValueError("authentication attempt partition identities must be unique")
        request_attempt_ids = tuple(item.attempt_id for item in self.authentication_attempts)
        if len(request_attempt_ids) != len(set(request_attempt_ids)):
            raise ValueError("artifact authentication attempt identities must be unique")
        if set(all_attempt_ids) != set(request_attempt_ids):
            raise ValueError("artifact partitions must contain every authentication attempt exactly once")
        if len(all_attempt_ids) != self.summary.attempt_count:
            raise ValueError("artifact partitions must account for every summarized attempt")
        if len(authenticated_attempt_ids) != self.summary.authenticated_count:
            raise ValueError("authenticated summary count must match partition")
        if len(withheld_attempt_ids) != self.summary.withheld_count:
            raise ValueError("withheld summary count must match partition")
        source_ids = tuple(item.evidence_id for item in self.source_observations)
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("artifact source-observation identities must be unique")
        source_by_id = {item.evidence_id: item for item in self.source_observations}
        attempts_by_id = {item.attempt_id: item for item in self.authentication_attempts}
        rules_by_id = {item.rule_id: item for item in self.authentication_rule_set.rules}
        for characteristic in self.authenticated_characteristics:
            attempt = attempts_by_id[characteristic.attempt_id]
            if authentication_failure_specs(attempt, source_by_id, rules_by_id):
                raise ValueError("authenticated partition contains an ineligible attempt")
            if attempt.proposal.role is not characteristic.role or (
                attempt.proposal.characteristic_id != characteristic.characteristic_id
                or attempt.proposal.canonical_value_json
                != characteristic.canonical_value_json
            ):
                raise ValueError("authenticated output must reproduce its exact proposal")
            if attempt.method != characteristic.authentication_method.value:
                raise ValueError("authenticated output method must match its attempt")
            for observation in characteristic.source_observations:
                if source_by_id.get(observation.evidence_id) != observation:
                    raise ValueError("authenticated lineage must reproduce artifact source evidence")
            if isinstance(attempt, ExactConfirmationAttempt):
                observation = characteristic.source_observations[0]
                definition = GOVERNED_CHARACTERISTIC_BY_KEY[
                    (characteristic.role, characteristic.characteristic_id)
                ]
                if (
                    observation.observation_type is not ObservationType.USER_CONFIRMATION
                    or observation.source_type is not ObservationSourceType.USER
                    or observation.state is not ObservationState.AVAILABLE
                    or observation.payload_json != confirmation_payload(definition)
                ):
                    raise ValueError("authenticated confirmation must reproduce exact governed evidence")
            else:
                rule = rules_by_id.get(attempt.rule_id)
                if rule is None or attempt.rule_version != rule.rule_version:
                    raise ValueError("authenticated derivation must identify an approved rule")
                if rule.output != GOVERNED_CHARACTERISTIC_BY_KEY[
                    (characteristic.role, characteristic.characteristic_id)
                ]:
                    raise ValueError("authenticated derivation output must match the approved rule")
                if len(characteristic.source_observations) != len(rule.input_requirements):
                    raise ValueError("authenticated derivation must preserve every rule input")
                for observation, requirement in zip(
                    characteristic.source_observations,
                    rule.input_requirements,
                    strict=True,
                ):
                    if (
                        observation.observation_type is not requirement.observation_type
                        or observation.source_type is not requirement.source_type
                        or observation.state is not ObservationState.AVAILABLE
                        or observation.payload_json != requirement.payload_json
                    ):
                        raise ValueError("authenticated derivation inputs must match the rule exactly")
        for withheld in self.withheld_authentication_attempts:
            if attempts_by_id[withheld.attempt_id] != withheld.attempt:
                raise ValueError("withheld partition must preserve the exact authentication attempt")
            expected_reason_keys = authentication_failure_specs(
                withheld.attempt, source_by_id, rules_by_id
            )
            actual_reason_keys = tuple(
                (reason.code, reason.field_path) for reason in withheld.reasons
            )
            if actual_reason_keys != expected_reason_keys:
                raise ValueError("withheld reasons must be complete and exact")
            for observation in withheld.referenced_observations:
                if source_by_id.get(observation.evidence_id) != observation:
                    raise ValueError("withheld lineage must reproduce artifact source evidence")
        return self


class AuthenticatedStructuredCharacteristicArtifact(FrozenAuthenticationModel):
    content: AuthenticatedStructuredCharacteristicArtifactContent
    artifact_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def verify_content_digest(self) -> AuthenticatedStructuredCharacteristicArtifact:
        if self.artifact_content_sha256 != _sha256(_canonical_model_bytes(self.content)):
            raise ValueError("artifact content digest must match canonical content bytes")
        return self

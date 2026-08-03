from __future__ import annotations

import json
import hashlib
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.evidence_authentication import (
    AuthenticatedStructuredCharacteristic,
    AuthenticatedStructuredCharacteristicArtifact,
    CharacteristicRole,
)
from playlist_narrative_engine.evidence_authentication.serialization import (
    serialize_evidence_authentication,
)
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact


CROSSING_UNDERSTANDING_SCHEMA_VERSION = "2.0"
DIRECTIONAL_TRANSITION_RULE_ID = "crossing.directional_transition"
DIRECTIONAL_TRANSITION_RULE_VERSION = "1.0"


class FrozenCrossingModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CrossingEvidenceState(StrEnum):
    SUPPORTED = "supported"
    UNAVAILABLE = "unavailable"
    CONFLICTING = "conflicting"
    UNSUPPORTED = "unsupported"
    EXPLICITLY_INAPPLICABLE = "explicitly_inapplicable"


class CrossingClaimRole(StrEnum):
    VISIBLE_EVENT = "visible_event"
    METAPHOR = "metaphor"
    ENDING = "ending"
    BEGINNING = "beginning"
    PARTICULAR_NEED = "particular_need"


class CrossingClaimBasis(StrEnum):
    USER_STATED = "user_stated"
    USER_CONFIRMED = "user_confirmed"
    VERSIONED_DERIVATION = "versioned_derivation"


class RecurringConditionOrientationBasis(StrEnum):
    USER_OBSERVATION = "user_observation"
    VERSIONED_RULE = "versioned_rule"


class CrossingUnderstandingOutcome(StrEnum):
    UNDERSTOOD = "understood"
    CLARIFICATION_REQUIRED = "clarification_required"


class CrossingClarificationReasonCode(StrEnum):
    TRANSITION_ENDING_UNAVAILABLE = "CU_TRANSITION_ENDING_UNAVAILABLE"
    TRANSITION_BEGINNING_UNAVAILABLE = "CU_TRANSITION_BEGINNING_UNAVAILABLE"
    MULTIPLE_TRANSITIONS_PLAUSIBLE = "CU_MULTIPLE_TRANSITIONS_PLAUSIBLE"


CLARIFICATION_REASON_PRECEDENCE = tuple(CrossingClarificationReasonCode)
CLARIFICATION_REASON_EXPLANATIONS = {
    CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE: (
        "What is ending or changing is unavailable."
    ),
    CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE: (
        "What is beginning or emerging is unavailable."
    ),
    CrossingClarificationReasonCode.MULTIPLE_TRANSITIONS_PLAUSIBLE: (
        "Multiple materially distinct transitions remain plausible."
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
        raise ValueError("crossing identity and provenance text must be nonblank and exact")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")


def _accepted_objective_digest(artifact: AcceptedObjectiveArtifact) -> str:
    canonical_bytes = json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


class CrossingEvidenceObservation(FrozenCrossingModel):
    evidence_id: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    payload_json: str = Field(max_length=100_000)

    @field_validator("evidence_id", "source_type", "source_reference")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("payload_json")
    @classmethod
    def require_valid_json(cls, value: str) -> str:
        try:
            json.loads(value, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("crossing evidence payload must be valid JSON") from exc
        return value


class CrossingClaim(FrozenCrossingModel):
    claim_id: str = Field(min_length=1, max_length=200)
    role: CrossingClaimRole
    state: CrossingEvidenceState
    value: str | None = Field(default=None, max_length=1_000)
    basis: CrossingClaimBasis | None = None
    observations: tuple[CrossingEvidenceObservation, ...] = ()

    @field_validator("claim_id")
    @classmethod
    def require_exact_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("value")
    @classmethod
    def require_exact_value(cls, value: str | None) -> str | None:
        return _exact(value) if value is not None else None

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @model_validator(mode="after")
    def enforce_evidence_state(self) -> CrossingClaim:
        evidence_ids = tuple(item.evidence_id for item in self.observations)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("crossing observation evidence IDs must be unique")
        if self.state is CrossingEvidenceState.SUPPORTED:
            if self.value is None or self.basis is None or not self.observations:
                raise ValueError("supported crossing claims require value, basis, and observations")
            if self.basis is CrossingClaimBasis.VERSIONED_DERIVATION:
                raise ValueError("derived values belong to transition candidates, not source claims")
            return self
        if self.value is not None or self.basis is not None:
            raise ValueError("non-supported crossing claims cannot carry a resolved value or basis")
        if self.state is CrossingEvidenceState.UNAVAILABLE and self.observations:
            raise ValueError("unavailable crossing claims cannot contain observations")
        if self.state is CrossingEvidenceState.CONFLICTING and len(self.observations) < 2:
            raise ValueError("conflicting crossing claims require at least two observations")
        if self.state in {
            CrossingEvidenceState.UNSUPPORTED,
            CrossingEvidenceState.EXPLICITLY_INAPPLICABLE,
        } and not self.observations:
            raise ValueError(f"{self.state.value} crossing claims require observations")
        return self


class TransitionDerivation(FrozenCrossingModel):
    rule_id: Literal["crossing.directional_transition"] = DIRECTIONAL_TRANSITION_RULE_ID
    rule_version: Literal["1.0"] = DIRECTIONAL_TRANSITION_RULE_VERSION
    input_authenticated_characteristic_ids: tuple[str, str]

    @field_validator("input_authenticated_characteristic_ids")
    @classmethod
    def require_exact_distinct_inputs(cls, value: tuple[str, str]) -> tuple[str, str]:
        if len(set(value)) != 2:
            raise ValueError("directional transition inputs must be distinct")
        for item in value:
            _exact(item)
        return value


class DirectionalTransitionRequest(FrozenCrossingModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    ending_authenticated_characteristic_id: str = Field(min_length=1, max_length=200)
    beginning_authenticated_characteristic_id: str = Field(min_length=1, max_length=200)

    @field_validator(
        "candidate_id",
        "ending_authenticated_characteristic_id",
        "beginning_authenticated_characteristic_id",
    )
    @classmethod
    def require_exact_id(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_distinct_characteristics(self) -> DirectionalTransitionRequest:
        if self.ending_authenticated_characteristic_id == self.beginning_authenticated_characteristic_id:
            raise ValueError("directional transition characteristics must be distinct")
        return self


class TransitionCandidate(FrozenCrossingModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    ending: AuthenticatedStructuredCharacteristic
    beginning: AuthenticatedStructuredCharacteristic
    derivation: TransitionDerivation

    @field_validator("candidate_id")
    @classmethod
    def require_exact_id(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def enforce_transition_contract(self) -> TransitionCandidate:
        if self.ending.role is not CharacteristicRole.ENDING:
            raise ValueError("transition ending must be an authenticated ending characteristic")
        if self.beginning.role is not CharacteristicRole.BEGINNING:
            raise ValueError("transition beginning must be an authenticated beginning characteristic")
        expected_inputs = (
            self.ending.authenticated_characteristic_id,
            self.beginning.authenticated_characteristic_id,
        )
        if self.derivation.input_authenticated_characteristic_ids != expected_inputs:
            raise ValueError("transition derivation inputs must match authenticated characteristics exactly")
        return self


class RecurringConditionRuleProvenance(FrozenCrossingModel):
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    input_evidence_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("rule_id", "rule_version")
    @classmethod
    def require_exact_rule_identity(cls, value: str) -> str:
        return _exact(value)

    @field_validator("input_evidence_ids", mode="before")
    @classmethod
    def canonicalize_exact_inputs(cls, value: Any) -> tuple[str, ...]:
        inputs = tuple(value)
        for item in inputs:
            _exact(item)
        if len(inputs) != len(set(inputs)):
            raise ValueError("condition rule input evidence IDs must be unique")
        return tuple(sorted(inputs, key=_utf8_key))


class RecurringConditionCandidate(FrozenCrossingModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    pattern: str = Field(min_length=1, max_length=1_000)
    orientation_basis: RecurringConditionOrientationBasis
    observations: tuple[CrossingEvidenceObservation, ...] = Field(min_length=1)
    rule_provenance: RecurringConditionRuleProvenance | None = None
    outcome: Literal["unresolved_orientation"] = "unresolved_orientation"
    applicability_to_person_established: Literal[False] = False
    person_membership_claimed: Literal[False] = False
    diagnosis_claimed: Literal[False] = False
    authoritative_for_particular_need: Literal[False] = False

    @field_validator("candidate_id", "pattern")
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("observations", mode="before")
    @classmethod
    def canonicalize_observations(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "evidence_id")

    @model_validator(mode="after")
    def enforce_orientation_only_contract(self) -> RecurringConditionCandidate:
        evidence_ids = tuple(item.evidence_id for item in self.observations)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("condition observations must have unique evidence IDs")
        if self.orientation_basis is RecurringConditionOrientationBasis.VERSIONED_RULE:
            if self.rule_provenance is None:
                raise ValueError("rule-oriented conditions require versioned rule provenance")
            if self.rule_provenance.input_evidence_ids != evidence_ids:
                raise ValueError("condition rule inputs must match observations exactly")
        elif self.rule_provenance is not None:
            raise ValueError("user-observation conditions cannot carry rule provenance")
        return self


class CrossingUnderstandingRequest(FrozenCrossingModel):
    schema_version: Literal["2.0"] = CROSSING_UNDERSTANDING_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    crossing_policy_id: str = Field(min_length=1, max_length=200)
    crossing_policy_version: str = Field(min_length=1, max_length=100)
    evidence_authentication_artifact: AuthenticatedStructuredCharacteristicArtifact
    evidence_authentication_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lived_evidence: tuple[CrossingClaim, ...]
    directional_transition_requests: tuple[DirectionalTransitionRequest, ...] = ()
    recurring_condition_candidates: tuple[RecurringConditionCandidate, ...] = ()
    particular_need: CrossingClaim | None = None

    @field_validator("request_id", "crossing_policy_id", "crossing_policy_version")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _exact(value)

    @field_validator("lived_evidence", mode="before")
    @classmethod
    def canonicalize_claims(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "claim_id")

    @field_validator("recurring_condition_candidates", mode="before")
    @classmethod
    def canonicalize_conditions(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "candidate_id")

    @field_validator("directional_transition_requests", mode="before")
    @classmethod
    def canonicalize_transitions(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "candidate_id")

    @model_validator(mode="after")
    def enforce_request_roles_and_identity(self) -> CrossingUnderstandingRequest:
        if self.accepted_objective_sha256 != _accepted_objective_digest(
            self.accepted_objective
        ):
            raise ValueError("accepted Objective Safety artifact digest must match exactly")
        if not self.lived_evidence:
            raise ValueError("crossing understanding requires lived evidence")
        if any(
            claim.role not in {CrossingClaimRole.VISIBLE_EVENT, CrossingClaimRole.METAPHOR}
            for claim in self.lived_evidence
        ):
            raise ValueError("lived evidence must use visible-event or metaphor roles")
        if self.particular_need is not None and self.particular_need.role is not CrossingClaimRole.PARTICULAR_NEED:
            raise ValueError("particular need must use the particular-need role")
        claim_ids = [claim.claim_id for claim in self.lived_evidence]
        if self.particular_need is not None:
            claim_ids.append(self.particular_need.claim_id)
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique across the request")
        if self.evidence_authentication_sha256 != hashlib.sha256(
            serialize_evidence_authentication(self.evidence_authentication_artifact)
        ).hexdigest():
            raise ValueError("Evidence Authentication artifact digest must match exactly")
        parent = self.evidence_authentication_artifact.content
        if (
            parent.accepted_objective != self.accepted_objective
            or parent.accepted_objective_sha256 != self.accepted_objective_sha256
        ):
            raise ValueError("Evidence Authentication objective lineage must correspond exactly")
        authenticated_by_id = {
            item.authenticated_characteristic_id: item
            for item in parent.authenticated_characteristics
        }
        candidate_ids = tuple(item.candidate_id for item in self.directional_transition_requests)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("transition candidate IDs must be unique")
        for transition in self.directional_transition_requests:
            ending = authenticated_by_id.get(transition.ending_authenticated_characteristic_id)
            beginning = authenticated_by_id.get(transition.beginning_authenticated_characteristic_id)
            if ending is None or beginning is None:
                raise ValueError("directional transition inputs must identify authenticated characteristics")
            if ending.role is not CharacteristicRole.ENDING or beginning.role is not CharacteristicRole.BEGINNING:
                raise ValueError("directional transition roles must correspond exactly")
        condition_ids = tuple(item.candidate_id for item in self.recurring_condition_candidates)
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("recurring-condition candidate IDs must be unique")
        return self


class CrossingClarificationReason(FrozenCrossingModel):
    code: CrossingClarificationReasonCode
    field_path: str = Field(min_length=1, max_length=500)
    explanation: str

    @field_validator("field_path")
    @classmethod
    def require_exact_field_path(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_fixed_explanation(self) -> CrossingClarificationReason:
        if self.explanation != CLARIFICATION_REASON_EXPLANATIONS[self.code]:
            raise ValueError("clarification explanation must match its fixed contract")
        return self


class CrossingUnderstandingArtifact(FrozenCrossingModel):
    schema_version: Literal["2.0"] = CROSSING_UNDERSTANDING_SCHEMA_VERSION
    artifact_kind: Literal["crossing_understanding"] = "crossing_understanding"
    artifact_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    crossing_policy_id: str = Field(min_length=1, max_length=200)
    crossing_policy_version: str = Field(min_length=1, max_length=100)
    evidence_authentication_artifact: AuthenticatedStructuredCharacteristicArtifact
    evidence_authentication_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lived_evidence: tuple[CrossingClaim, ...]
    transition_candidates: tuple[TransitionCandidate, ...]
    resolved_transition_id: str | None = Field(default=None, max_length=200)
    recurring_condition_candidates: tuple[RecurringConditionCandidate, ...]
    particular_need: CrossingClaim | None
    outcome: CrossingUnderstandingOutcome
    clarification_required: bool
    clarification_reasons: tuple[CrossingClarificationReason, ...]
    psychological_diagnosis_performed: Literal[False] = False
    person_classified: Literal[False] = False
    particular_need_inferred_from_curriculum: Literal[False] = False
    accompaniment_selected: Literal[False] = False
    soundtrack_objective_created: Literal[False] = False
    journey_planning_performed: Literal[False] = False
    candidate_formation_performed: Literal[False] = False
    music_scored: Literal[False] = False
    music_selected: Literal[False] = False
    explanation_generated: Literal[False] = False

    @field_validator(
        "artifact_id", "request_id", "crossing_policy_id", "crossing_policy_version"
    )
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        return _exact(value)

    @field_validator("resolved_transition_id")
    @classmethod
    def require_exact_resolved_id(cls, value: str | None) -> str | None:
        return _exact(value) if value is not None else None

    @field_validator("lived_evidence", mode="before")
    @classmethod
    def canonicalize_claims(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "claim_id")

    @field_validator("recurring_condition_candidates", mode="before")
    @classmethod
    def canonicalize_conditions(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "candidate_id")

    @field_validator("transition_candidates", mode="before")
    @classmethod
    def canonicalize_transitions(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "candidate_id")

    @model_validator(mode="after")
    def enforce_artifact_contract(self) -> CrossingUnderstandingArtifact:
        if self.accepted_objective_sha256 != _accepted_objective_digest(
            self.accepted_objective
        ):
            raise ValueError("artifact Objective Safety digest must match exactly")
        if not self.lived_evidence or any(
            claim.role not in {CrossingClaimRole.VISIBLE_EVENT, CrossingClaimRole.METAPHOR}
            for claim in self.lived_evidence
        ):
            raise ValueError("artifact lived evidence must use visible-event or metaphor roles")
        if self.particular_need is not None and self.particular_need.role is not CrossingClaimRole.PARTICULAR_NEED:
            raise ValueError("artifact particular need must use the particular-need role")
        claim_ids = [claim.claim_id for claim in self.lived_evidence]
        if self.particular_need is not None:
            claim_ids.append(self.particular_need.claim_id)
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("artifact claim IDs must be unique")
        if self.evidence_authentication_sha256 != hashlib.sha256(
            serialize_evidence_authentication(self.evidence_authentication_artifact)
        ).hexdigest():
            raise ValueError("artifact Evidence Authentication digest must match exactly")
        parent = self.evidence_authentication_artifact.content
        if (
            parent.accepted_objective != self.accepted_objective
            or parent.accepted_objective_sha256 != self.accepted_objective_sha256
        ):
            raise ValueError("artifact Evidence Authentication objective lineage must correspond exactly")
        authenticated_by_id = {
            item.authenticated_characteristic_id: item
            for item in parent.authenticated_characteristics
        }
        for transition in self.transition_candidates:
            for characteristic in (transition.ending, transition.beginning):
                if authenticated_by_id.get(characteristic.authenticated_characteristic_id) != characteristic:
                    raise ValueError("transition must reproduce exact authenticated parent characteristics")
        candidate_ids = tuple(item.candidate_id for item in self.transition_candidates)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("artifact transition candidate IDs must be unique")
        condition_ids = tuple(item.candidate_id for item in self.recurring_condition_candidates)
        if len(condition_ids) != len(set(condition_ids)):
            raise ValueError("artifact recurring-condition candidate IDs must be unique")
        precedence = {code: index for index, code in enumerate(CLARIFICATION_REASON_PRECEDENCE)}
        expected = tuple(
            sorted(
                self.clarification_reasons,
                key=lambda reason: (precedence[reason.code], _utf8_key(reason.field_path)),
            )
        )
        if self.clarification_reasons != expected:
            raise ValueError("clarification reasons must use fixed precedence")
        reason_keys = tuple((reason.code, reason.field_path) for reason in self.clarification_reasons)
        if len(reason_keys) != len(set(reason_keys)):
            raise ValueError("clarification reasons must be unique by code and field path")
        if not self.transition_candidates:
            expected_reason_keys = (
                (CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE, "transition.ending"),
                (CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE, "transition.beginning"),
            )
        elif len(self.transition_candidates) > 1:
            expected_reason_keys = (
                (CrossingClarificationReasonCode.MULTIPLE_TRANSITIONS_PLAUSIBLE, "transition_candidates"),
            )
        else:
            expected_reason_keys = ()
        if reason_keys != expected_reason_keys:
            raise ValueError("clarification reasons must be exactly derivable from directional transitions")
        requires_clarification = bool(self.clarification_reasons)
        if self.clarification_required is not requires_clarification:
            raise ValueError("clarification flag must match reasons")
        expected_outcome = (
            CrossingUnderstandingOutcome.CLARIFICATION_REQUIRED
            if requires_clarification
            else CrossingUnderstandingOutcome.UNDERSTOOD
        )
        if self.outcome is not expected_outcome:
            raise ValueError("crossing outcome must match clarification reasons")
        if self.resolved_transition_id is not None:
            if self.resolved_transition_id not in candidate_ids:
                raise ValueError("resolved transition must identify a retained candidate")
            if requires_clarification:
                raise ValueError("clarification-required artifacts cannot resolve a transition")
        elif not requires_clarification:
            raise ValueError("understood artifacts require a resolved transition")
        return self

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.crossing_understanding import (
    CrossingUnderstandingArtifact,
    CrossingUnderstandingOutcome,
)
from playlist_narrative_engine.crossing_understanding.serialization import serialize_crossing_understanding
from playlist_narrative_engine.evidence_authentication import (
    CHARACTERISTIC_VALUE_SCHEMA_ID,
    CHARACTERISTIC_VALUE_SCHEMA_VERSION,
    AuthenticatedStructuredCharacteristic,
    CharacteristicRole,
)
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import serialize_objective_safety_artifact


CURRICULUM_ORIENTATION_SCHEMA_VERSION = "1.0"
CURRICULUM_ID = "penny.life_transitions"
CURRICULUM_VERSION = "1.0"
ORIENTATION_POLICY_ID = "cu2.orientation"
ORIENTATION_POLICY_VERSION = "1.0"
ORIENTATION_RULE_SET_ID = "cu2.orientation_rules"
ORIENTATION_RULE_SET_VERSION = "1.0"


class FrozenOrientationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CurriculumOrientationOutcome(StrEnum):
    ORIENTED = "oriented"
    NO_ORIENTATION_SUPPORTED = "no_orientation_supported"
    CLARIFICATION_REQUIRED = "clarification_required"


class CurriculumOrientationReasonCode(StrEnum):
    PARENT_CROSSING_UNRESOLVED = "PARENT_CROSSING_UNRESOLVED"
    NO_APPROVED_RULE_MATCHED = "NO_APPROVED_ORIENTATION_RULE_MATCHED"


ORIENTATION_REASON_PRECEDENCE = tuple(CurriculumOrientationReasonCode)
ORIENTATION_REASON_EXPLANATIONS = {
    CurriculumOrientationReasonCode.PARENT_CROSSING_UNRESOLVED: (
        "The authoritative CU-1 artifact does not contain exactly one resolved crossing."
    ),
    CurriculumOrientationReasonCode.NO_APPROVED_RULE_MATCHED: (
        "No approved curriculum-orientation rule matched the exact authenticated crossing characteristics."
    ),
}


def _utf8_key(value: str) -> bytes:
    return value.encode("utf-8")


def _input_field(value: object, field_name: str) -> str:
    field_value = value.get(field_name) if isinstance(value, dict) else getattr(value, field_name, None)
    return field_value if isinstance(field_value, str) else ""


def _canonical_order(values: Any, field_name: str) -> tuple[object, ...]:
    return tuple(sorted(tuple(values), key=lambda item: _utf8_key(_input_field(item, field_name))))


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("curriculum-orientation identity text must be nonblank and exact")
    return value


def _canonical_bytes(model: BaseModel) -> bytes:
    return json.dumps(model.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class OrientationCharacteristicPredicate(FrozenOrientationModel):
    role: CharacteristicRole
    characteristic_id: str = Field(min_length=1, max_length=200)
    characteristic_value_schema_id: Literal["penny.crossing_characteristic"] = CHARACTERISTIC_VALUE_SCHEMA_ID
    characteristic_value_schema_version: Literal["1.0"] = CHARACTERISTIC_VALUE_SCHEMA_VERSION
    canonical_value_json: str = Field(min_length=1, max_length=10_000)

    @field_validator("characteristic_id")
    @classmethod
    def exact_id(cls, value: str) -> str:
        return _exact(value)

    @field_validator("canonical_value_json")
    @classmethod
    def canonical_json(cls, value: str) -> str:
        parsed = json.loads(value)
        if json.dumps(parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False) != value:
            raise ValueError("orientation predicate value must be canonical JSON")
        return value

    def matches(self, characteristic: AuthenticatedStructuredCharacteristic) -> bool:
        return (
            characteristic.role is self.role
            and characteristic.characteristic_id == self.characteristic_id
            and characteristic.characteristic_value_schema_id == self.characteristic_value_schema_id
            and characteristic.characteristic_value_schema_version == self.characteristic_value_schema_version
            and characteristic.canonical_value_json == self.canonical_value_json
        )


class OrientationRuleDefinition(FrozenOrientationModel):
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    candidate_id: str = Field(min_length=1, max_length=200)
    condition_id: str = Field(min_length=1, max_length=200)
    pattern: str = Field(min_length=1, max_length=1_000)
    ending_predicate: OrientationCharacteristicPredicate
    beginning_predicate: OrientationCharacteristicPredicate

    @field_validator("rule_id", "rule_version", "candidate_id", "condition_id", "pattern")
    @classmethod
    def exact_text(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def directional_roles(self) -> OrientationRuleDefinition:
        if self.ending_predicate.role is not CharacteristicRole.ENDING:
            raise ValueError("ending predicate must require an ending characteristic")
        if self.beginning_predicate.role is not CharacteristicRole.BEGINNING:
            raise ValueError("beginning predicate must require a beginning characteristic")
        return self


class OrientationRuleSet(FrozenOrientationModel):
    rule_set_id: Literal["cu2.orientation_rules"] = ORIENTATION_RULE_SET_ID
    rule_set_version: Literal["1.0"] = ORIENTATION_RULE_SET_VERSION
    rules: tuple[OrientationRuleDefinition, ...] = Field(min_length=1)

    @field_validator("rules", mode="before")
    @classmethod
    def canonical_rules(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "rule_id")

    @model_validator(mode="after")
    def unique_registry(self) -> OrientationRuleSet:
        dimensions = {
            "rule IDs": tuple(rule.rule_id for rule in self.rules),
            "candidate IDs": tuple(rule.candidate_id for rule in self.rules),
            "condition IDs": tuple(rule.condition_id for rule in self.rules),
            "exact predicates": tuple(
                (rule.ending_predicate.model_dump_json(), rule.beginning_predicate.model_dump_json())
                for rule in self.rules
            ),
        }
        for label, values in dimensions.items():
            if len(values) != len(set(values)):
                raise ValueError(f"orientation rule registry requires unique {label}")
        return self


def _predicate(role: CharacteristicRole, characteristic_id: str, value: str) -> OrientationCharacteristicPredicate:
    return OrientationCharacteristicPredicate(
        role=role,
        characteristic_id=characteristic_id,
        canonical_value_json=json.dumps(value, ensure_ascii=False, separators=(",", ":")),
    )


APPROVED_ORIENTATION_RULE_SET = OrientationRuleSet(rules=(
    OrientationRuleDefinition(
        rule_id="cu2.uncertainty_before_competence", rule_version="1.0",
        candidate_id="orientation.uncertainty_before_competence",
        condition_id="condition.uncertainty_before_competence", pattern="uncertainty before competence",
        ending_predicate=_predicate(CharacteristicRole.ENDING, "role.established", "established role"),
        beginning_predicate=_predicate(CharacteristicRole.BEGINNING, "role.unproven", "unproven role"),
    ),
    OrientationRuleDefinition(
        rule_id="cu2.identity_after_departure", rule_version="1.0",
        candidate_id="orientation.identity_after_departure",
        condition_id="condition.identity_after_departure", pattern="identity after departure",
        ending_predicate=_predicate(CharacteristicRole.ENDING, "identity.anchored_in_departed_role_or_relationship", "identity anchored in a departed role or relationship"),
        beginning_predicate=_predicate(CharacteristicRole.BEGINNING, "identity.not_established_after_departure", "identity not yet established after departure"),
    ),
    OrientationRuleDefinition(
        rule_id="cu2.return_without_reversal", rule_version="1.0",
        candidate_id="orientation.return_without_reversal",
        condition_id="condition.return_without_reversal", pattern="return without reversal",
        ending_predicate=_predicate(CharacteristicRole.ENDING, "context.away_from_familiar", "life away from a familiar place, practice, or relationship"),
        beginning_predicate=_predicate(CharacteristicRole.BEGINNING, "context.return_to_changed_familiar", "return to a familiar context changed by time or experience"),
    ),
))
APPROVED_ORIENTATION_RULE_SET_SHA256 = _sha256(_canonical_bytes(APPROVED_ORIENTATION_RULE_SET))
APPROVED_ORIENTATION_RULES = APPROVED_ORIENTATION_RULE_SET.rules


class CurriculumOrientationRequest(FrozenOrientationModel):
    schema_version: Literal["1.0"] = CURRICULUM_ORIENTATION_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    crossing_understanding: CrossingUnderstandingArtifact
    crossing_understanding_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    curriculum_id: Literal["penny.life_transitions"] = CURRICULUM_ID
    curriculum_version: Literal["1.0"] = CURRICULUM_VERSION
    orientation_policy_id: Literal["cu2.orientation"] = ORIENTATION_POLICY_ID
    orientation_policy_version: Literal["1.0"] = ORIENTATION_POLICY_VERSION
    orientation_rule_set: OrientationRuleSet
    orientation_rule_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("request_id")
    @classmethod
    def exact_request_id(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def authority_correspondence(self) -> CurriculumOrientationRequest:
        parent = self.crossing_understanding
        if CrossingUnderstandingArtifact.model_validate(parent.model_dump(mode="python")) != parent:
            raise ValueError("CU-1 artifact must pass complete structural revalidation")
        if OrientationRuleSet.model_validate(self.orientation_rule_set.model_dump(mode="python")) != self.orientation_rule_set:
            raise ValueError("orientation rule set must pass complete structural revalidation")
        if self.crossing_understanding_sha256 != _sha256(serialize_crossing_understanding(parent)):
            raise ValueError("CU-1 canonical digest must match exactly")
        if self.accepted_objective != parent.accepted_objective:
            raise ValueError("accepted objective must equal CU-1 authority exactly")
        if _sha256(serialize_objective_safety_artifact(self.accepted_objective)) != parent.accepted_objective_sha256:
            raise ValueError("accepted-objective lineage must match CU-1 exactly")
        if self.orientation_rule_set != APPROVED_ORIENTATION_RULE_SET:
            raise ValueError("request must use the complete approved orientation rule set")
        if self.orientation_rule_set_sha256 != _sha256(_canonical_bytes(self.orientation_rule_set)):
            raise ValueError("orientation rule-set digest must match exactly")
        return self


class OrientationTransitionEvidence(FrozenOrientationModel):
    transition_id: str = Field(min_length=1, max_length=200)
    ending: AuthenticatedStructuredCharacteristic
    beginning: AuthenticatedStructuredCharacteristic

    @field_validator("transition_id")
    @classmethod
    def exact_transition_id(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def exact_roles(self) -> OrientationTransitionEvidence:
        if self.ending.role is not CharacteristicRole.ENDING or self.beginning.role is not CharacteristicRole.BEGINNING:
            raise ValueError("orientation evidence requires exact authenticated directional roles")
        return self


class CurriculumOrientationCandidate(FrozenOrientationModel):
    candidate_id: str = Field(min_length=1, max_length=200)
    condition_id: str = Field(min_length=1, max_length=200)
    pattern: str = Field(min_length=1, max_length=1_000)
    rule_id: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    input_authenticated_characteristic_ids: tuple[str, str]
    outcome: Literal["unresolved_orientation"] = "unresolved_orientation"
    applicability_to_person_established: Literal[False] = False
    person_membership_claimed: Literal[False] = False
    diagnosis_claimed: Literal[False] = False
    authoritative_for_particular_need: Literal[False] = False
    accompaniment_inferred: Literal[False] = False

    @field_validator("candidate_id", "condition_id", "pattern", "rule_id", "rule_version")
    @classmethod
    def exact_fields(cls, value: str) -> str:
        return _exact(value)


class CurriculumOrientationReason(FrozenOrientationModel):
    code: CurriculumOrientationReasonCode
    field_path: str = Field(min_length=1, max_length=500)
    explanation: str

    @field_validator("field_path")
    @classmethod
    def exact_path(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def fixed_explanation(self) -> CurriculumOrientationReason:
        if self.explanation != ORIENTATION_REASON_EXPLANATIONS[self.code]:
            raise ValueError("orientation reason explanation must match fixed contract")
        return self


class CurriculumOrientationArtifact(FrozenOrientationModel):
    schema_version: Literal["1.0"] = CURRICULUM_ORIENTATION_SCHEMA_VERSION
    artifact_kind: Literal["curriculum_orientation"] = "curriculum_orientation"
    artifact_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    crossing_understanding: CrossingUnderstandingArtifact
    parent_crossing_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective: AcceptedObjectiveArtifact
    curriculum_id: Literal["penny.life_transitions"] = CURRICULUM_ID
    curriculum_version: Literal["1.0"] = CURRICULUM_VERSION
    orientation_policy_id: Literal["cu2.orientation"] = ORIENTATION_POLICY_ID
    orientation_policy_version: Literal["1.0"] = ORIENTATION_POLICY_VERSION
    orientation_rule_set: OrientationRuleSet
    orientation_rule_set_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transition_evidence: OrientationTransitionEvidence | None
    candidates: tuple[CurriculumOrientationCandidate, ...]
    outcome: CurriculumOrientationOutcome
    reasons: tuple[CurriculumOrientationReason, ...]
    person_classified: Literal[False] = False
    condition_applicability_established: Literal[False] = False
    particular_need_inferred: Literal[False] = False
    accompaniment_inferred: Literal[False] = False
    explanation_generated: Literal[False] = False
    journey_planning_performed: Literal[False] = False
    provider_accessed: Literal[False] = False
    music_inspected: Literal[False] = False

    @field_validator("artifact_id", "request_id")
    @classmethod
    def exact_ids(cls, value: str) -> str:
        return _exact(value)

    @field_validator("candidates", mode="before")
    @classmethod
    def canonical_candidates(cls, value: Any) -> tuple[object, ...]:
        return _canonical_order(value, "candidate_id")

    @model_validator(mode="after")
    def complete_artifact(self) -> CurriculumOrientationArtifact:
        parent = self.crossing_understanding
        if CrossingUnderstandingArtifact.model_validate(parent.model_dump(mode="python")) != parent:
            raise ValueError("artifact parent must pass complete CU-1 revalidation")
        if OrientationRuleSet.model_validate(self.orientation_rule_set.model_dump(mode="python")) != self.orientation_rule_set:
            raise ValueError("artifact rule set must pass complete structural revalidation")
        if self.parent_crossing_sha256 != _sha256(serialize_crossing_understanding(parent)):
            raise ValueError("artifact CU-1 digest must match exact parent")
        if self.accepted_objective != parent.accepted_objective:
            raise ValueError("artifact objective must equal parent authority")
        if self.orientation_rule_set != APPROVED_ORIENTATION_RULE_SET:
            raise ValueError("artifact must preserve complete approved orientation rule set")
        if self.orientation_rule_set_sha256 != _sha256(_canonical_bytes(self.orientation_rule_set)):
            raise ValueError("artifact rule-set digest must match exactly")
        resolved = tuple(item for item in parent.transition_candidates if item.candidate_id == parent.resolved_transition_id)
        expected_transition = None if len(resolved) != 1 else OrientationTransitionEvidence(
            transition_id=resolved[0].candidate_id, ending=resolved[0].ending, beginning=resolved[0].beginning
        )
        if self.transition_evidence != expected_transition:
            raise ValueError("orientation transition must reproduce exact resolved CU-1 lineage")
        matched_rules = () if expected_transition is None else tuple(
            rule for rule in self.orientation_rule_set.rules
            if rule.ending_predicate.matches(expected_transition.ending)
            and rule.beginning_predicate.matches(expected_transition.beginning)
        )
        expected_candidates = tuple(CurriculumOrientationCandidate(
            candidate_id=rule.candidate_id, condition_id=rule.condition_id, pattern=rule.pattern,
            rule_id=rule.rule_id, rule_version=rule.rule_version,
            input_authenticated_characteristic_ids=(
                expected_transition.ending.authenticated_characteristic_id,
                expected_transition.beginning.authenticated_characteristic_id,
            ),
        ) for rule in matched_rules)
        if self.candidates != expected_candidates:
            raise ValueError("orientation candidates must be exactly derived from authenticated lineage")
        if expected_transition is None:
            expected_outcome = CurriculumOrientationOutcome.CLARIFICATION_REQUIRED
            expected_reason = CurriculumOrientationReasonCode.PARENT_CROSSING_UNRESOLVED
        elif expected_candidates:
            expected_outcome = CurriculumOrientationOutcome.ORIENTED
            expected_reason = None
        else:
            expected_outcome = CurriculumOrientationOutcome.NO_ORIENTATION_SUPPORTED
            expected_reason = CurriculumOrientationReasonCode.NO_APPROVED_RULE_MATCHED
        if self.outcome is not expected_outcome:
            raise ValueError("orientation outcome must be deterministically derived")
        expected_reasons = () if expected_reason is None else (CurriculumOrientationReason(
            code=expected_reason,
            field_path="crossing_understanding.resolved_transition_id" if expected_transition is None else "transition_evidence",
            explanation=ORIENTATION_REASON_EXPLANATIONS[expected_reason],
        ),)
        if self.reasons != expected_reasons:
            raise ValueError("orientation reasons must be complete and exact")
        return self


def serialize_orientation_rule_set(rule_set: OrientationRuleSet) -> bytes:
    return _canonical_bytes(rule_set)

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from playlist_narrative_engine.research_store.study_schemas import (
    StudyAnalysisCalculationPlanInput,
    StudyExecutionInputKind,
    StudyOutcomeCalculationPlanInput,
    StudyProtocolInput,
)


STATUSES = frozenset({"PASS", "PARTIAL", "FAIL", "UNKNOWN"})
ORDINARY_STATUSES = frozenset({"PASS", "PARTIAL", "FAIL"})


@dataclass(frozen=True)
class DecimalExecutionContract:
    precision: int
    rounding: str
    notation: str
    strip_trailing_zeroes: bool
    canonical_zero: str
    allow_exponent_notation: bool
    allow_leading_plus: bool
    require_leading_zero_below_one: bool


@dataclass(frozen=True)
class CalculatorExecutionEnvelope:
    execution_state: str
    derivability_state: str | None
    calculation_state: str | None
    reason_code: str | None = None

    def validate(self) -> None:
        legal = {
            ("AVAILABLE", "DERIVABLE", "CALCULATED"),
            ("AVAILABLE", "DERIVABLE", "MISSING"),
            ("AVAILABLE", "DERIVABLE", "NOT_CALCULABLE"),
            ("AVAILABLE", "NOT_DERIVABLE", None),
            ("UNAVAILABLE", None, None),
        }
        if (self.execution_state, self.derivability_state, self.calculation_state) not in legal:
            raise ValueError("contradictory calculator execution envelope")
        if self.execution_state == "UNAVAILABLE" and self.reason_code != "CALCULATOR_IMPLEMENTATION_UNAVAILABLE":
            raise ValueError("unavailable calculator requires the stable unavailable reason code")


DECIMAL_V1_CONTRACT = DecimalExecutionContract(
    precision=34,
    rounding="ROUND_HALF_EVEN",
    notation="PLAIN_BASE_10",
    strip_trailing_zeroes=True,
    canonical_zero="0",
    allow_exponent_notation=False,
    allow_leading_plus=False,
    require_leading_zero_below_one=True,
)


DISPOSITION_REASON_CODES = {
    ("PENDING", "MISSING"): "PENDING_REGISTERED_RUN",
    ("MAESTRO_REFUSAL_RECORDED", "MISSING"): "REFUSAL_OUTCOME_MISSING",
    ("MAESTRO_REFUSAL_RECORDED", "NOT_CALCULABLE"): "REFUSAL_OUTCOME_NOT_CALCULABLE",
    ("MAESTRO_FAILURE_RECORDED", "MISSING"): "GENERATION_FAILURE_OUTCOME_MISSING",
    ("MAESTRO_FAILURE_RECORDED", "NOT_CALCULABLE"): "GENERATION_FAILURE_OUTCOME_NOT_CALCULABLE",
}


def applicable_bound_constraint_keys(plan, planned_run) -> tuple[str, ...]:
    """Return calculator-v1 contributors for one run without interpreting keys."""
    applicable = set(planned_run.applicable_constraint_keys)
    return tuple(
        binding.constraint_key
        for binding in sorted(plan.constraint_bindings, key=lambda item: item.ordinal)
        if binding.constraint_key in applicable
    )


@dataclass(frozen=True)
class ParameterSpecification:
    value_type: str
    minimum_count: int
    maximum_count: int | None
    allowed_text_values: frozenset[str] | None = None


@dataclass(frozen=True)
class OutcomeCalculatorSpecification:
    calculator_key: str
    calculator_version: str
    input_kind: str
    output_value_type: str
    required_binding_roles: Mapping[str, tuple[int, int | None]]
    supported_subject_kinds: frozenset[str]
    parameters: Mapping[str, ParameterSpecification]


@dataclass(frozen=True)
class AnalysisCalculatorSpecification:
    calculator_key: str
    calculator_version: str
    population_scope: str
    output_shape_key: str
    output_shape_version: str
    required_dimensions: frozenset[tuple[str, str]]
    required_condition_roles: frozenset[str]
    parameters: Mapping[str, ParameterSpecification]


RATE_PARAMETERS = {
    "numerator_status": ParameterSpecification("TEXT", 1, None, STATUSES),
    "denominator_status": ParameterSpecification("TEXT", 1, None, STATUSES),
    "unknown_policy": ParameterSpecification(
        "TEXT", 1, 1, frozenset({"EXCLUDE", "NOT_CALCULABLE"})
    ),
    "missing_input_policy": ParameterSpecification(
        "TEXT", 1, 1, frozenset({"NOT_DERIVABLE", "NOT_CALCULABLE"})
    ),
}


OUTCOME_CALCULATORS = (
    OutcomeCalculatorSpecification(
        "outcome.constraint_status_rate", "1", "CONSTRAINT_RESULTS", "DECIMAL",
        {"CONTRIBUTOR": (1, None)}, frozenset(), RATE_PARAMETERS,
    ),
    OutcomeCalculatorSpecification(
        "outcome.subject_status_rate", "1", "STRUCTURED_SUBJECT_RESULTS", "DECIMAL",
        {"CONTRIBUTOR": (1, None)},
        frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), RATE_PARAMETERS,
    ),
)


ANALYSIS_CALCULATORS = (
    AnalysisCalculatorSpecification(
        "analysis.paired_difference", "1", "ALL_REGISTERED_PLANNED_RUNS",
        "PAIRED_DIFFERENCE_SUMMARY", "1",
        frozenset({("MATCH", "BLOCK"), ("MATCH", "REPLICATE")}),
        frozenset({"LEFT", "RIGHT"}),
        {
            "difference_direction": ParameterSpecification(
                "TEXT", 1, 1, frozenset({"RIGHT_MINUS_LEFT", "LEFT_MINUS_RIGHT"})
            ),
            "pair_completeness": ParameterSpecification(
                "TEXT", 1, 1, frozenset({"REQUIRED"})
            ),
            "missing_policy": ParameterSpecification(
                "TEXT", 1, 1, frozenset({"NOT_CALCULABLE"})
            ),
        },
    ),
)


def _validate_parameters(parameters, specifications, label: str) -> None:
    by_key: dict[str, list[object]] = {}
    for parameter in parameters:
        by_key.setdefault(parameter.parameter_key, []).append(parameter)
    if set(by_key) != set(specifications):
        raise ValueError(f"{label} parameters do not match the calculator specification")
    for key, specification in specifications.items():
        values = sorted(by_key[key], key=lambda item: item.ordinal)
        if len(values) < specification.minimum_count or (
            specification.maximum_count is not None and len(values) > specification.maximum_count
        ):
            raise ValueError(f"{label} parameter {key} has invalid cardinality")
        if [item.ordinal for item in values] != list(range(1, len(values) + 1)):
            raise ValueError(f"{label} parameter {key} ordinals must be contiguous from 1")
        for item in values:
            if item.value_type.value != specification.value_type:
                raise ValueError(f"{label} parameter {key} requires {specification.value_type}")
            if (
                specification.allowed_text_values is not None
                and item.text_value not in specification.allowed_text_values
            ):
                raise ValueError(f"{label} parameter {key} has an unsupported value")


class OutcomeCalculatorRegistry:
    def __init__(self, specifications: Iterable[OutcomeCalculatorSpecification] = ()) -> None:
        self._specifications = {
            (item.calculator_key, item.calculator_version): item for item in specifications
        }

    def validate(self, plan: StudyOutcomeCalculationPlanInput) -> None:
        identity = (plan.calculator_key, plan.calculator_version)
        if identity not in self._specifications:
            raise ValueError(f"unsupported outcome calculator identity: {identity[0]}/{identity[1]}")
        specification = self._specifications[identity]
        if plan.input_kind.value != specification.input_kind:
            raise ValueError("outcome calculator input kind is incompatible")
        if plan.output_value_type.value != specification.output_value_type:
            raise ValueError("outcome calculator output type is incompatible")
        if plan.vocabulary_terms:
            raise ValueError("outcome calculator does not support plan-local vocabulary")
        roles: dict[str, int] = {}
        for binding in plan.constraint_bindings:
            roles[binding.binding_role] = roles.get(binding.binding_role, 0) + 1
        if set(roles) != set(specification.required_binding_roles):
            raise ValueError("outcome calculator binding roles are incompatible")
        for role, (minimum, maximum) in specification.required_binding_roles.items():
            if roles[role] < minimum or (maximum is not None and roles[role] > maximum):
                raise ValueError(f"outcome calculator binding role {role} has invalid cardinality")
        subject_kinds = frozenset(item.value for item in plan.subject_kinds)
        if plan.input_kind == StudyExecutionInputKind.STRUCTURED_SUBJECT_RESULTS:
            if not subject_kinds or not subject_kinds <= specification.supported_subject_kinds:
                raise ValueError("outcome calculator subject kinds are incompatible")
        elif subject_kinds:
            raise ValueError("subject kinds are valid only for structured-subject input")
        _validate_parameters(plan.parameters, specification.parameters, "outcome calculator")
        if plan.calculator_key in {
            "outcome.constraint_status_rate", "outcome.subject_status_rate"
        }:
            status_sets = {
                key: [item.text_value for item in plan.parameters if item.parameter_key == key]
                for key in ("numerator_status", "denominator_status")
            }
            for key, values in status_sets.items():
                if len(values) != len(set(values)):
                    raise ValueError(f"outcome calculator {key} values must be unique")
                if "UNKNOWN" in values:
                    raise ValueError("UNKNOWN is governed only by unknown_policy")
            numerator = set(status_sets["numerator_status"])
            denominator = set(status_sets["denominator_status"])
            if not numerator <= denominator:
                raise ValueError("numerator_status must be a subset of denominator_status")
            if not ORDINARY_STATUSES <= denominator:
                raise ValueError("denominator_status must include PASS, PARTIAL, and FAIL")


class AnalysisCalculatorRegistry:
    def __init__(self, specifications: Iterable[AnalysisCalculatorSpecification] = ()) -> None:
        self._specifications = {
            (item.calculator_key, item.calculator_version): item for item in specifications
        }

    def validate(self, plan: StudyAnalysisCalculationPlanInput) -> None:
        identity = (plan.calculator_key, plan.calculator_version)
        if identity not in self._specifications:
            raise ValueError(f"unsupported analysis calculator identity: {identity[0]}/{identity[1]}")
        specification = self._specifications[identity]
        if plan.population_scope.value != specification.population_scope:
            raise ValueError("analysis population scope is incompatible")
        if (
            plan.output_shape_key != specification.output_shape_key
            or plan.output_shape_version != specification.output_shape_version
        ):
            raise ValueError("analysis output shape is incompatible")
        dimensions = frozenset(
            (item.dimension_role.value, item.dimension_key.value) for item in plan.dimensions
        )
        if dimensions != specification.required_dimensions:
            raise ValueError("analysis dimensions are incompatible")
        condition_roles = frozenset(item.comparison_role.value for item in plan.condition_bindings)
        if condition_roles != specification.required_condition_roles:
            raise ValueError("analysis condition bindings are incompatible")
        _validate_parameters(plan.parameters, specification.parameters, "analysis calculator")


class StudyExecutionRegistry:
    def __init__(
        self,
        outcomes: OutcomeCalculatorRegistry,
        analyses: AnalysisCalculatorRegistry,
    ) -> None:
        self.outcomes = outcomes
        self.analyses = analyses

    def validate_protocol(self, protocol: StudyProtocolInput) -> None:
        contract = protocol.execution_contract
        if contract is None:
            return
        constraints = {item.constraint_key: item for item in protocol.constraint_definitions}
        for plan in contract.outcome_calculation_plans:
            self.outcomes.validate(plan)
            if plan.input_kind == StudyExecutionInputKind.STRUCTURED_SUBJECT_RESULTS:
                authorized = {item.value for item in plan.subject_kinds}
                for binding in plan.constraint_bindings:
                    structured = constraints[binding.constraint_key].structured_evaluation_plan
                    if structured is None:
                        raise ValueError("structured-subject outcome binds an aggregate-only constraint")
                    if structured.subject_kind.value not in authorized:
                        raise ValueError("outcome subject-kind authorization excludes a bound constraint plan")
        for plan in contract.analysis_calculation_plans:
            self.analyses.validate(plan)
            if (
                plan.calculator_key == "analysis.paired_difference"
                and plan.calculator_version == "1"
            ):
                bound_conditions = {item.condition_key for item in plan.condition_bindings}
                registered_conditions = {item.condition_key for item in protocol.conditions}
                if bound_conditions != registered_conditions:
                    raise ValueError(
                        "paired_difference/1 LEFT and RIGHT must cover every registered condition"
                    )


DEFAULT_OUTCOME_CALCULATOR_REGISTRY = OutcomeCalculatorRegistry(OUTCOME_CALCULATORS)
DEFAULT_ANALYSIS_CALCULATOR_REGISTRY = AnalysisCalculatorRegistry(ANALYSIS_CALCULATORS)
DEFAULT_STUDY_EXECUTION_REGISTRY = StudyExecutionRegistry(
    DEFAULT_OUTCOME_CALCULATOR_REGISTRY, DEFAULT_ANALYSIS_CALCULATOR_REGISTRY
)

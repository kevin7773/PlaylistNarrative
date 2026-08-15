from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import Field, model_validator

from playlist_narrative_engine.research_store.schemas import (
    ProvenanceType,
    StrictModel,
)


class StudyConditionRole(StrEnum):
    CONTROL = "CONTROL"
    TREATMENT = "TREATMENT"


class StudyOutcomeRole(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    EXPLORATORY = "EXPLORATORY"


class StructuredEvaluationSubjectKind(StrEnum):
    RUN = "RUN"
    EXPERIMENT_PLACEMENT = "EXPERIMENT_PLACEMENT"
    PLACEMENT_FIELD = "PLACEMENT_FIELD"


class StructuredEvaluationField(StrEnum):
    DISPLAY_TITLE = "display_title"
    DISPLAY_ARTIST = "display_artist"
    EXPLICIT_FLAG = "explicit_flag"
    VERSION_OR_REMASTER_TEXT = "version_or_remaster_text"


class StructuredMeasurementAuthority(StrEnum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    STRUCTURAL_DERIVATION = "STRUCTURAL_DERIVATION"
    EXTERNAL_FACT_VERIFICATION = "EXTERNAL_FACT_VERIFICATION"
    HUMAN_ASSESSMENT = "HUMAN_ASSESSMENT"


class StructuredUnavailablePolicy(StrEnum):
    MUST_HAVE_VALUE = "MUST_HAVE_VALUE"
    MAY_BE_UNAVAILABLE = "MAY_BE_UNAVAILABLE"


class StructuredValueType(StrEnum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    TEXT = "TEXT"
    DATE = "DATE"
    VOCABULARY_TERM = "VOCABULARY_TERM"


class StudyExecutionInputKind(StrEnum):
    CONSTRAINT_RESULTS = "CONSTRAINT_RESULTS"
    STRUCTURED_SUBJECT_RESULTS = "STRUCTURED_SUBJECT_RESULTS"
    STRUCTURED_MEASUREMENTS = "STRUCTURED_MEASUREMENTS"
    REALIZATION_DISPOSITION = "REALIZATION_DISPOSITION"


class StudyCalculationValueType(StrEnum):
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    VOCABULARY_TERM = "VOCABULARY_TERM"
    DISPOSITION = "DISPOSITION"


class StudySubjectInterpretation(StrEnum):
    FIELD_PREDICATE = "FIELD_PREDICATE"
    PLACEMENT_EVENT = "PLACEMENT_EVENT"


class StudyAnalysisPopulationScope(StrEnum):
    ALL_REGISTERED_PLANNED_RUNS = "ALL_REGISTERED_PLANNED_RUNS"


class StudyAnalysisDimensionRole(StrEnum):
    GROUP = "GROUP"
    MATCH = "MATCH"


class StudyAnalysisDimensionKey(StrEnum):
    CONDITION = "CONDITION"
    BLOCK = "BLOCK"
    REPLICATE = "REPLICATE"


class StudyAnalysisConditionRole(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class StudyOutcomePopulationState(StrEnum):
    EXPERIMENT_RECORDED = "EXPERIMENT_RECORDED"
    MAESTRO_REFUSAL_RECORDED = "MAESTRO_REFUSAL_RECORDED"
    MAESTRO_FAILURE_RECORDED = "MAESTRO_FAILURE_RECORDED"
    PENDING = "PENDING"


class StudyOutcomeDispositionTreatment(StrEnum):
    CALCULATE = "CALCULATE"
    MISSING = "MISSING"
    NOT_CALCULABLE = "NOT_CALCULABLE"


class EvaluatorReferenceInput(StrictModel):
    evaluator_key: str = Field(min_length=1)
    evaluator_version: str = Field(min_length=1)


class StudyConstraintMeasurementDefinitionInput(StrictModel):
    measurement_key: str = Field(min_length=1)
    authority: StructuredMeasurementAuthority
    value_type: StructuredValueType
    unit_key: str | None = None
    vocabulary_key: str | None = None
    required: bool = True
    evidence_required: bool = True
    derivation_key: str | None = None
    derivation_version: str | None = None
    unavailable_policy: StructuredUnavailablePolicy | None = None

    @model_validator(mode="after")
    def validate_vocabulary_value(self) -> StudyConstraintMeasurementDefinitionInput:
        if self.value_type == StructuredValueType.VOCABULARY_TERM and not self.vocabulary_key:
            raise ValueError("VOCABULARY_TERM measurements require vocabulary_key")
        if self.value_type != StructuredValueType.VOCABULARY_TERM and self.vocabulary_key is not None:
            raise ValueError("vocabulary_key is valid only for VOCABULARY_TERM measurements")
        if (self.derivation_key is None) != (self.derivation_version is None):
            raise ValueError("structural derivation key and version must be supplied together")
        return self


class StudyConstraintEvaluationParameterInput(StrictModel):
    parameter_key: str = Field(min_length=1)
    value_type: StructuredValueType
    boolean_value: bool | None = None
    integer_value: int | None = None
    decimal_value: Decimal | None = None
    text_value: str | None = None
    date_value: date | None = None
    vocabulary_key: str | None = None
    vocabulary_term_key: str | None = None

    @model_validator(mode="after")
    def require_exact_typed_value(self) -> StudyConstraintEvaluationParameterInput:
        populated = {
            StructuredValueType.BOOLEAN: self.boolean_value,
            StructuredValueType.INTEGER: self.integer_value,
            StructuredValueType.DECIMAL: self.decimal_value,
            StructuredValueType.TEXT: self.text_value,
            StructuredValueType.DATE: self.date_value,
        }
        ordinary_values = [value for value in populated.values() if value is not None]
        vocabulary_supplied = self.vocabulary_key is not None or self.vocabulary_term_key is not None
        if self.value_type == StructuredValueType.VOCABULARY_TERM:
            if ordinary_values or not self.vocabulary_key or not self.vocabulary_term_key:
                raise ValueError("VOCABULARY_TERM parameter requires exactly vocabulary_key and vocabulary_term_key")
        elif vocabulary_supplied or populated[self.value_type] is None or len(ordinary_values) != 1:
            raise ValueError("parameter must populate exactly the column selected by value_type")
        return self


class StudyConstraintEvaluationVocabularyTermInput(StrictModel):
    vocabulary_key: str = Field(min_length=1)
    term_key: str = Field(min_length=1)
    term_definition: str = Field(min_length=1)


class StudyCalculationParameterInput(StudyConstraintEvaluationParameterInput):
    ordinal: int = Field(gt=0)


class StudyCalculationVocabularyTermInput(StudyConstraintEvaluationVocabularyTermInput):
    pass


class StudyOutcomeConstraintBindingInput(StrictModel):
    constraint_key: str = Field(min_length=1)
    binding_role: str = Field(min_length=1)
    ordinal: int = Field(gt=0)


class StudyOutcomeDispositionPolicyInput(StrictModel):
    population_state: StudyOutcomePopulationState
    treatment: StudyOutcomeDispositionTreatment


class StudyOutcomeCalculationPlanInput(StrictModel):
    outcome_key: str = Field(min_length=1)
    calculator_key: str = Field(min_length=1)
    calculator_version: str = Field(min_length=1)
    input_kind: StudyExecutionInputKind
    output_value_type: StudyCalculationValueType
    output_vocabulary_key: str | None = None
    subject_interpretation: StudySubjectInterpretation | None = None
    constraint_bindings: list[StudyOutcomeConstraintBindingInput] = Field(default_factory=list)
    subject_kinds: list[StructuredEvaluationSubjectKind] = Field(default_factory=list)
    parameters: list[StudyCalculationParameterInput] = Field(default_factory=list)
    vocabulary_terms: list[StudyCalculationVocabularyTermInput] = Field(default_factory=list)
    disposition_policies: list[StudyOutcomeDispositionPolicyInput] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_plan_shape(self) -> StudyOutcomeCalculationPlanInput:
        if self.output_value_type == StudyCalculationValueType.VOCABULARY_TERM:
            if not self.output_vocabulary_key:
                raise ValueError("VOCABULARY_TERM output requires output_vocabulary_key")
        elif self.output_vocabulary_key is not None:
            raise ValueError("output_vocabulary_key is valid only for VOCABULARY_TERM output")
        if len(self.subject_kinds) != len(set(self.subject_kinds)):
            raise ValueError("outcome subject kinds must be unique")
        binding_ordinals = [item.ordinal for item in self.constraint_bindings]
        if len(binding_ordinals) != len(set(binding_ordinals)):
            raise ValueError("outcome constraint-binding ordinals must be unique")
        if sorted(binding_ordinals) != list(range(1, len(binding_ordinals) + 1)):
            raise ValueError("outcome constraint-binding ordinals must be contiguous from 1")
        binding_identity = [
            (item.binding_role, item.constraint_key) for item in self.constraint_bindings
        ]
        if len(binding_identity) != len(set(binding_identity)):
            raise ValueError("outcome constraint bindings must be unique")
        parameter_identity = [(item.parameter_key, item.ordinal) for item in self.parameters]
        if len(parameter_identity) != len(set(parameter_identity)):
            raise ValueError("outcome parameter key/ordinal identities must be unique")
        terms = [(item.vocabulary_key, item.term_key) for item in self.vocabulary_terms]
        if len(terms) != len(set(terms)):
            raise ValueError("outcome vocabulary terms must be unique")
        declared = {item.vocabulary_key for item in self.vocabulary_terms}
        referenced = {
            item.vocabulary_key for item in self.parameters
            if item.value_type == StructuredValueType.VOCABULARY_TERM
        }
        if self.output_vocabulary_key is not None:
            referenced.add(self.output_vocabulary_key)
        if not referenced <= declared:
            raise ValueError("referenced outcome vocabularies must be defined by the plan")
        if StructuredEvaluationSubjectKind.PLACEMENT_FIELD in self.subject_kinds:
            if self.subject_interpretation is None:
                raise ValueError("PLACEMENT_FIELD outcome requires explicit subject_interpretation")
        elif self.subject_interpretation is not None:
            raise ValueError("subject_interpretation is valid only when PLACEMENT_FIELD is authorized")
        states = [item.population_state for item in self.disposition_policies]
        if len(states) != len(set(states)):
            raise ValueError("outcome disposition population states must be unique")
        if set(states) != set(StudyOutcomePopulationState):
            raise ValueError("outcome disposition policy must cover every population state")
        treatments = {item.population_state: item.treatment for item in self.disposition_policies}
        if treatments[StudyOutcomePopulationState.EXPERIMENT_RECORDED] != StudyOutcomeDispositionTreatment.CALCULATE:
            raise ValueError("EXPERIMENT_RECORDED disposition must use CALCULATE")
        if treatments[StudyOutcomePopulationState.PENDING] != StudyOutcomeDispositionTreatment.MISSING:
            raise ValueError("PENDING disposition must use MISSING")
        for state in (
            StudyOutcomePopulationState.MAESTRO_REFUSAL_RECORDED,
            StudyOutcomePopulationState.MAESTRO_FAILURE_RECORDED,
        ):
            if treatments[state] not in {
                StudyOutcomeDispositionTreatment.MISSING,
                StudyOutcomeDispositionTreatment.NOT_CALCULABLE,
            }:
                raise ValueError(f"{state.value} disposition has an unsupported treatment")
        return self


class StudyAnalysisDimensionInput(StrictModel):
    dimension_role: StudyAnalysisDimensionRole
    dimension_key: StudyAnalysisDimensionKey
    ordinal: int = Field(gt=0)


class StudyAnalysisConditionBindingInput(StrictModel):
    comparison_role: StudyAnalysisConditionRole
    condition_key: str = Field(min_length=1)


class StudyAnalysisCalculationPlanInput(StrictModel):
    analysis_key: str = Field(min_length=1)
    calculator_key: str = Field(min_length=1)
    calculator_version: str = Field(min_length=1)
    population_scope: StudyAnalysisPopulationScope
    output_shape_key: str = Field(min_length=1)
    output_shape_version: str = Field(min_length=1)
    dimensions: list[StudyAnalysisDimensionInput] = Field(default_factory=list)
    condition_bindings: list[StudyAnalysisConditionBindingInput] = Field(default_factory=list)
    parameters: list[StudyCalculationParameterInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan_shape(self) -> StudyAnalysisCalculationPlanInput:
        dimension_ordinals = [item.ordinal for item in self.dimensions]
        if len(dimension_ordinals) != len(set(dimension_ordinals)):
            raise ValueError("analysis dimension ordinals must be unique")
        if sorted(dimension_ordinals) != list(range(1, len(dimension_ordinals) + 1)):
            raise ValueError("analysis dimension ordinals must be contiguous from 1")
        dimension_identity = [(item.dimension_role, item.dimension_key) for item in self.dimensions]
        if len(dimension_identity) != len(set(dimension_identity)):
            raise ValueError("analysis dimensions must be unique")
        roles = [item.comparison_role for item in self.condition_bindings]
        if len(roles) != len(set(roles)):
            raise ValueError("analysis condition comparison roles must be unique")
        if len({item.condition_key for item in self.condition_bindings}) != len(self.condition_bindings):
            raise ValueError("analysis LEFT and RIGHT conditions must be distinct")
        parameter_identity = [(item.parameter_key, item.ordinal) for item in self.parameters]
        if len(parameter_identity) != len(set(parameter_identity)):
            raise ValueError("analysis parameter key/ordinal identities must be unique")
        return self


class StudyExecutionContractInput(StrictModel):
    contract_version: str = Field(min_length=1)
    outcome_calculation_plans: list[StudyOutcomeCalculationPlanInput] = Field(min_length=1)
    analysis_calculation_plans: list[StudyAnalysisCalculationPlanInput] = Field(min_length=1)


class StudyConstraintEvaluationPlanInput(StrictModel):
    instrumentation_version: str = Field(min_length=1)
    subject_kind: StructuredEvaluationSubjectKind
    subject_field: StructuredEvaluationField | None = None
    subject_selector: EvaluatorReferenceInput
    subject_evaluator: EvaluatorReferenceInput
    aggregate_evaluator: EvaluatorReferenceInput
    require_complete_subject_set: bool = True
    allow_partial_subject_status: bool = False
    measurement_definitions: list[StudyConstraintMeasurementDefinitionInput] = Field(min_length=1)
    parameters: list[StudyConstraintEvaluationParameterInput] = Field(default_factory=list)
    vocabulary_terms: list[StudyConstraintEvaluationVocabularyTermInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan_shape(self) -> StudyConstraintEvaluationPlanInput:
        if self.subject_kind == StructuredEvaluationSubjectKind.PLACEMENT_FIELD:
            if self.subject_field is None:
                raise ValueError("PLACEMENT_FIELD requires subject_field")
        elif self.subject_field is not None:
            raise ValueError("subject_field is valid only for PLACEMENT_FIELD")
        measurement_keys = [item.measurement_key for item in self.measurement_definitions]
        if len(measurement_keys) != len(set(measurement_keys)):
            raise ValueError("measurement keys must be unique within an evaluation plan")
        parameter_keys = [item.parameter_key for item in self.parameters]
        if len(parameter_keys) != len(set(parameter_keys)):
            raise ValueError("parameter keys must be unique within an evaluation plan")
        terms = [(item.vocabulary_key, item.term_key) for item in self.vocabulary_terms]
        if len(terms) != len(set(terms)):
            raise ValueError("vocabulary terms must be unique within an evaluation plan")
        declared_vocabularies = {item.vocabulary_key for item in self.vocabulary_terms}
        referenced_vocabularies = {
            item.vocabulary_key for item in self.measurement_definitions
            if item.vocabulary_key is not None
        } | {
            item.vocabulary_key for item in self.parameters
            if item.value_type == StructuredValueType.VOCABULARY_TERM
        }
        if not referenced_vocabularies <= declared_vocabularies:
            raise ValueError("referenced evaluation vocabularies must be defined by the plan")
        return self


class StudyRunDisposition(StrEnum):
    EXPERIMENT_RECORDED = "EXPERIMENT_RECORDED"
    MAESTRO_REFUSAL_RECORDED = "MAESTRO_REFUSAL_RECORDED"
    MAESTRO_FAILURE_RECORDED = "MAESTRO_FAILURE_RECORDED"


class StudyConditionInput(StrictModel):
    condition_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    role: StudyConditionRole
    exact_factor_definition: str = Field(min_length=1)


class StudyBlockInput(StrictModel):
    block_key: str = Field(min_length=1)
    label: str = Field(min_length=1)
    block_definition: str = Field(min_length=1)


class StudyConstraintDefinitionInput(StrictModel):
    constraint_key: str = Field(min_length=1)
    constraint_type: str = Field(min_length=1)
    constraint_text: str = Field(min_length=1)
    is_hard_constraint: bool = True
    evaluation_rule: str = Field(min_length=1)
    permitted_result_provenance: ProvenanceType
    unknown_handling: str = Field(min_length=1)
    structured_evaluation_plan: StudyConstraintEvaluationPlanInput | None = None

    @model_validator(mode="after")
    def require_derived_aggregate_provenance(self) -> StudyConstraintDefinitionInput:
        if (
            self.structured_evaluation_plan is not None
            and self.permitted_result_provenance != ProvenanceType.DERIVED_QUERY_RESULT
        ):
            raise ValueError(
                "structured evaluation requires DERIVED_QUERY_RESULT aggregate provenance"
            )
        return self


class StudyOutcomeDefinitionInput(StrictModel):
    outcome_key: str = Field(min_length=1)
    role: StudyOutcomeRole
    unit_of_analysis: str = Field(min_length=1)
    outcome_definition: str = Field(min_length=1)
    computation_rule: str = Field(min_length=1)
    missing_data_rule: str = Field(min_length=1)
    refusal_handling: str = Field(min_length=1)
    operational_failure_handling: str = Field(min_length=1)


class StudyAnalysisDefinitionInput(StrictModel):
    analysis_key: str = Field(min_length=1)
    outcome_key: str = Field(min_length=1)
    analysis_population: str = Field(min_length=1)
    comparison_definition: str = Field(min_length=1)
    aggregation_rule: str = Field(min_length=1)
    exclusion_rule: str = Field(min_length=1)
    reporting_rule: str = Field(min_length=1)


class StudyPlannedRunInput(StrictModel):
    run_key: str = Field(min_length=1)
    condition_key: str = Field(min_length=1)
    block_key: str = Field(min_length=1)
    replicate_number: int = Field(gt=0)
    randomized_ordinal: int = Field(gt=0)
    planned_prompt_text: str = Field(min_length=1)
    planned_source_system: str | None = None
    applicable_constraint_keys: list[str] = Field(min_length=1)
    replacement_for_run_key: str | None = None


class StudyProtocolInput(StrictModel):
    version_number: int = Field(gt=0)
    amendment_reason: str | None = None
    objective: str = Field(min_length=1)
    primary_hypothesis: str = Field(min_length=1)
    null_hypothesis: str = Field(min_length=1)
    design_summary: str = Field(min_length=1)
    planned_sample_size: int = Field(gt=0)
    randomization_method: str = Field(min_length=1)
    randomization_seed: str = Field(min_length=1)
    operational_failure_policy: str = Field(min_length=1)
    operational_failure_consumes_run: bool = False
    refusal_policy: str = Field(min_length=1)
    missing_result_policy: str = Field(min_length=1)
    conditions: list[StudyConditionInput] = Field(min_length=1)
    blocks: list[StudyBlockInput] = Field(min_length=1)
    constraint_definitions: list[StudyConstraintDefinitionInput] = Field(min_length=1)
    outcome_definitions: list[StudyOutcomeDefinitionInput] = Field(min_length=1)
    analysis_definitions: list[StudyAnalysisDefinitionInput] = Field(min_length=1)
    planned_runs: list[StudyPlannedRunInput] = Field(min_length=1)
    execution_contract: StudyExecutionContractInput | None = None

    @model_validator(mode="after")
    def validate_complete_protocol(self) -> StudyProtocolInput:
        def unique(values: list[str], label: str) -> set[str]:
            result = set(values)
            if len(result) != len(values):
                raise ValueError(f"{label} must be unique")
            return result

        conditions = unique([item.condition_key for item in self.conditions], "condition keys")
        blocks = unique([item.block_key for item in self.blocks], "block keys")
        constraints = unique(
            [item.constraint_key for item in self.constraint_definitions],
            "constraint keys",
        )
        outcomes = unique([item.outcome_key for item in self.outcome_definitions], "outcome keys")
        unique([item.analysis_key for item in self.analysis_definitions], "analysis keys")
        runs = unique([item.run_key for item in self.planned_runs], "run keys")

        if self.planned_sample_size != len(self.planned_runs):
            raise ValueError("planned_sample_size must equal planned run count")
        ordinals = sorted(item.randomized_ordinal for item in self.planned_runs)
        if ordinals != list(range(1, len(self.planned_runs) + 1)):
            raise ValueError("randomized ordinals must be contiguous from 1")
        replicate_keys = [
            (item.block_key, item.condition_key, item.replicate_number)
            for item in self.planned_runs
        ]
        if len(replicate_keys) != len(set(replicate_keys)):
            raise ValueError("block/condition/replicate identities must be unique")
        for run in self.planned_runs:
            if run.condition_key not in conditions or run.block_key not in blocks:
                raise ValueError("every planned run must reference its protocol condition and block")
            if len(run.applicable_constraint_keys) != len(set(run.applicable_constraint_keys)):
                raise ValueError("planned-run constraint applicability must not contain duplicates")
            if not set(run.applicable_constraint_keys) <= constraints:
                raise ValueError("planned runs may reference only protocol constraint definitions")
            if run.replacement_for_run_key is not None:
                if run.replacement_for_run_key not in runs:
                    raise ValueError("replacement run must reference a run in the same protocol")
                if run.replacement_for_run_key == run.run_key:
                    raise ValueError("a planned run cannot replace itself")
        if any(item.outcome_key not in outcomes for item in self.analysis_definitions):
            raise ValueError("analysis definitions may reference only protocol outcomes")
        primary = {item.outcome_key for item in self.outcome_definitions if item.role == StudyOutcomeRole.PRIMARY}
        analyzed = {item.outcome_key for item in self.analysis_definitions}
        if not primary or not primary <= analyzed:
            raise ValueError("every protocol requires an analysis for every primary outcome")
        if self.execution_contract is not None:
            outcome_plans = unique(
                [item.outcome_key for item in self.execution_contract.outcome_calculation_plans],
                "outcome calculation-plan keys",
            )
            analysis_plans = unique(
                [item.analysis_key for item in self.execution_contract.analysis_calculation_plans],
                "analysis calculation-plan keys",
            )
            analysis_keys = {item.analysis_key for item in self.analysis_definitions}
            if outcome_plans != outcomes:
                raise ValueError("execution contract requires exactly one plan for every outcome")
            if analysis_plans != analysis_keys:
                raise ValueError("execution contract requires exactly one plan for every analysis")
            for plan in self.execution_contract.outcome_calculation_plans:
                if any(item.constraint_key not in constraints for item in plan.constraint_bindings):
                    raise ValueError("outcome plans may bind only same-protocol constraints")
            for plan in self.execution_contract.analysis_calculation_plans:
                if any(item.condition_key not in conditions for item in plan.condition_bindings):
                    raise ValueError("analysis plans may bind only same-protocol conditions")
        return self


class StudyRegistrationInput(StrictModel):
    study_key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    protocol: StudyProtocolInput

    @model_validator(mode="after")
    def require_initial_version(self) -> StudyRegistrationInput:
        if self.protocol.version_number != 1:
            raise ValueError("initial study registration must use protocol version 1")
        if self.protocol.amendment_reason is not None:
            raise ValueError("initial study registration cannot declare an amendment reason")
        return self


class StudyProtocolAmendmentInput(StrictModel):
    predecessor_version: int = Field(gt=0)
    protocol: StudyProtocolInput

    @model_validator(mode="after")
    def validate_succession(self) -> StudyProtocolAmendmentInput:
        if self.protocol.version_number != self.predecessor_version + 1:
            raise ValueError("amendment version must equal predecessor version plus one")
        if not self.protocol.amendment_reason:
            raise ValueError("amendment_reason is required")
        return self


class StudyOperationalAttemptInput(StrictModel):
    failure_code: str = Field(min_length=1)
    notes: str = Field(min_length=1)


class StructuredEvaluationEvidenceRole(StrEnum):
    SUBJECT_IDENTITY = "SUBJECT_IDENTITY"
    OBSERVED_VALUE = "OBSERVED_VALUE"
    EXTERNAL_FACT = "EXTERNAL_FACT"
    CORRESPONDENCE = "CORRESPONDENCE"
    OPERATOR_JUDGMENT = "OPERATOR_JUDGMENT"


class StructuredMeasurementEvidenceInput(StrictModel):
    source_key: str = Field(min_length=1)
    evidence_link_id: int | None = Field(default=None, gt=0)
    evidence_link_field: str | None = None
    evidence_role: StructuredEvaluationEvidenceRole
    provenance_type: ProvenanceType
    support_status: str = Field(pattern="^(FULL|PARTIAL)$")
    field_or_segment_reference: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_one_link_locator(self) -> StructuredMeasurementEvidenceInput:
        if self.evidence_link_id is not None and self.evidence_link_field is not None:
            raise ValueError("evidence may use an existing link id or a draft field locator, not both")
        return self


class StructuredMeasurementInput(StrictModel):
    measurement_key: str = Field(min_length=1)
    authority_kind: StructuredMeasurementAuthority
    value_type: str = Field(pattern="^(BOOLEAN|INTEGER|DECIMAL|TEXT|DATE|VOCABULARY_TERM|UNAVAILABLE)$")
    boolean_value: bool | None = None
    integer_value: int | None = None
    decimal_value: Decimal | None = None
    text_value: str | None = None
    date_value: date | None = None
    vocabulary_term_key: str | None = None
    unavailable_reason: str | None = None
    recorded_by: str = Field(min_length=1)
    notes: str | None = None
    evidence: list[StructuredMeasurementEvidenceInput] = Field(default_factory=list)


class StructuredEvaluationSubjectInput(StrictModel):
    subject_kind: StructuredEvaluationSubjectKind
    enumeration_ordinal: int = Field(gt=0)
    track_observed_ordinal: int | None = Field(default=None, gt=0)
    governed_field: StructuredEvaluationField | None = None
    measurements: list[StructuredMeasurementInput]

    @model_validator(mode="after")
    def validate_subject_locator(self) -> StructuredEvaluationSubjectInput:
        if self.subject_kind == StructuredEvaluationSubjectKind.RUN:
            if self.track_observed_ordinal is not None or self.governed_field is not None:
                raise ValueError("RUN subject has no placement locator or governed field")
        elif self.subject_kind == StructuredEvaluationSubjectKind.EXPERIMENT_PLACEMENT:
            if self.track_observed_ordinal is None or self.governed_field is not None:
                raise ValueError("EXPERIMENT_PLACEMENT requires only track_observed_ordinal")
        elif self.track_observed_ordinal is None or self.governed_field is None:
            raise ValueError("PLACEMENT_FIELD requires track_observed_ordinal and governed_field")
        keys = [item.measurement_key for item in self.measurements]
        if len(keys) != len(set(keys)):
            raise ValueError("structured subject measurements must be unique")
        return self


class StructuredConstraintEvaluationInput(StrictModel):
    study_constraint_definition_id: int = Field(gt=0)
    subjects: list[StructuredEvaluationSubjectInput]
    asserted_aggregate_status: str | None = Field(
        default=None, pattern="^(PASS|PARTIAL|FAIL|UNKNOWN)$"
    )


class StructuredStudyEvaluationInput(StrictModel):
    constraints: list[StructuredConstraintEvaluationInput]

    @model_validator(mode="after")
    def unique_constraint_definitions(self) -> StructuredStudyEvaluationInput:
        identifiers = [item.study_constraint_definition_id for item in self.constraints]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("structured constraint evaluations must be unique")
        return self

from __future__ import annotations

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

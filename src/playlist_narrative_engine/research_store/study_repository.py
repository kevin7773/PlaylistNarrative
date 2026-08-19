from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from playlist_narrative_engine.research_store.models import (
    Constraint,
    ConstraintResult,
    ConstraintEvaluationMeasurement,
    ConstraintEvaluationMeasurementEvidence,
    ConstraintEvaluationSubject,
    ConstraintSubjectResult,
    EvidenceLink,
    EvidenceSource,
    ExperimentTrack,
    GenerationFailure,
    Study,
    StudyAnalysisDefinition,
    StudyAnalysisCalculationParameter,
    StudyAnalysisCalculationPlan,
    StudyAnalysisConditionBinding,
    StudyAnalysisDimension,
    StudyBlock,
    StudyCondition,
    StudyConstraintDefinition,
    StudyConstraintEvaluationParameter,
    StudyConstraintEvaluationPlan,
    StudyConstraintEvaluationVocabularyTerm,
    StudyConstraintMeasurementDefinition,
    StudyOutcomeDefinition,
    StudyOutcomeCalculationParameter,
    StudyOutcomeCalculationPlan,
    StudyOutcomeDispositionPolicy,
    StudyOutcomeCalculationVocabularyTerm,
    StudyOutcomeConstraintBinding,
    StudyOutcomeSubjectKind,
    StudyPlannedRun,
    StudyPlannedRunConstraint,
    StudyProtocolVersion,
    StudyExecutionContract,
    StudyRunAttempt,
    StudyRunRealization,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput,
    GenerationFailureInput,
)
from playlist_narrative_engine.research_store.study_protocol import (
    protocol_registration_hash,
)
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
    StudyEvaluatorRegistry,
)
from playlist_narrative_engine.research_store.study_execution_registry import (
    DEFAULT_STUDY_EXECUTION_REGISTRY,
    StudyExecutionRegistry,
)
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyProtocolAmendmentInput,
    StudyProtocolInput,
    StudyRegistrationInput,
    StudyRunDisposition,
    StructuredStudyEvaluationInput,
)
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    evaluate_structured_constraint,
)


class StudyRepository:
    """Persistence boundary for prospective study registration and execution."""

    def __init__(
        self,
        session: Session,
        evaluator_registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
        execution_registry: StudyExecutionRegistry = DEFAULT_STUDY_EXECUTION_REGISTRY,
    ) -> None:
        self.session = session
        self._research = ResearchRepository(session)
        self._evaluator_registry = evaluator_registry
        self._execution_registry = execution_registry

    def register_study(self, draft: StudyRegistrationInput) -> dict[str, object]:
        self._evaluator_registry.validate_protocol(draft.protocol)
        self._execution_registry.validate_protocol(draft.protocol)
        with self.session.begin():
            if self.session.scalar(select(Study.id).where(Study.study_key == draft.study_key)):
                raise ValueError(f"study_key already exists: {draft.study_key}")
            study = Study(study_key=draft.study_key, title=draft.title)
            self.session.add(study)
            self.session.flush()
            protocol = self._insert_protocol(
                study, draft.protocol, predecessor=None,
                registration_hash=protocol_registration_hash(
                    draft.study_key, draft.title, draft.protocol
                ),
            )
            study_id = study.id
            version = protocol.version_number
            result = self.get_study(study_id)
            if result is None:
                raise RuntimeError("registered study could not be read back")
            result["registered_protocol_version"] = version
            result["registered_protocol"] = self._protocol_dict(study, protocol)
            return result

    def register_protocol_amendment(
        self, study_id: int, draft: StudyProtocolAmendmentInput
    ) -> dict[str, object]:
        self._evaluator_registry.validate_protocol(draft.protocol)
        self._execution_registry.validate_protocol(draft.protocol)
        with self.session.begin():
            study = self.session.get(Study, study_id)
            if study is None:
                raise ValueError(f"study not found: {study_id}")
            predecessor = self.session.scalar(
                select(StudyProtocolVersion).where(
                    StudyProtocolVersion.study_id == study.id,
                    StudyProtocolVersion.version_number == draft.predecessor_version,
                )
            )
            if predecessor is None or predecessor.registered_at is None:
                raise ValueError("amendment predecessor must be a registered version of the same study")
            existing = self.session.scalar(
                select(StudyProtocolVersion.id).where(
                    StudyProtocolVersion.study_id == study.id,
                    StudyProtocolVersion.version_number == draft.protocol.version_number,
                )
            )
            if existing is not None:
                raise ValueError("protocol version already exists")
            protocol = self._insert_protocol(
                study, draft.protocol, predecessor=predecessor,
                registration_hash=protocol_registration_hash(
                    study.study_key, study.title, draft.protocol
                ),
            )
            version = protocol.version_number
            result = self.get_protocol_version(study_id, version)
            if result is None:
                raise RuntimeError("registered amendment could not be read back")
            return result

    def _insert_protocol(
        self,
        study: Study,
        draft: StudyProtocolInput,
        *,
        predecessor: StudyProtocolVersion | None,
        registration_hash: str,
    ) -> StudyProtocolVersion:
        protocol = StudyProtocolVersion(
            study_id=study.id,
            version_number=draft.version_number,
            predecessor_version_id=None if predecessor is None else predecessor.id,
            registered_at=None,
            registration_hash=None,
            amendment_reason=draft.amendment_reason,
            objective=draft.objective,
            primary_hypothesis=draft.primary_hypothesis,
            null_hypothesis=draft.null_hypothesis,
            design_summary=draft.design_summary,
            planned_sample_size=draft.planned_sample_size,
            randomization_method=draft.randomization_method,
            randomization_seed=draft.randomization_seed,
            operational_failure_policy=draft.operational_failure_policy,
            operational_failure_consumes_run=draft.operational_failure_consumes_run,
            refusal_policy=draft.refusal_policy,
            missing_result_policy=draft.missing_result_policy,
        )
        self.session.add(protocol)
        self.session.flush()

        conditions: dict[str, StudyCondition] = {}
        for item in draft.conditions:
            value = StudyCondition(
                protocol_version_id=protocol.id,
                condition_key=item.condition_key,
                label=item.label,
                role=item.role.value,
                exact_factor_definition=item.exact_factor_definition,
            )
            self.session.add(value)
            conditions[item.condition_key] = value
        blocks: dict[str, StudyBlock] = {}
        for item in draft.blocks:
            value = StudyBlock(
                protocol_version_id=protocol.id,
                block_key=item.block_key,
                label=item.label,
                block_definition=item.block_definition,
            )
            self.session.add(value)
            blocks[item.block_key] = value
        constraint_definitions: dict[str, StudyConstraintDefinition] = {}
        for item in draft.constraint_definitions:
            value = StudyConstraintDefinition(
                protocol_version_id=protocol.id,
                constraint_key=item.constraint_key,
                constraint_type=item.constraint_type,
                constraint_text=item.constraint_text,
                is_hard_constraint=item.is_hard_constraint,
                evaluation_rule=item.evaluation_rule,
                permitted_result_provenance=item.permitted_result_provenance.value,
                unknown_handling=item.unknown_handling,
            )
            self.session.add(value)
            constraint_definitions[item.constraint_key] = value
        self.session.flush()
        for item in draft.constraint_definitions:
            plan_input = item.structured_evaluation_plan
            if plan_input is None:
                continue
            definition = constraint_definitions[item.constraint_key]
            plan = StudyConstraintEvaluationPlan(
                constraint_definition_id=definition.id,
                instrumentation_version=plan_input.instrumentation_version,
                subject_kind=plan_input.subject_kind.value,
                subject_field=None if plan_input.subject_field is None else plan_input.subject_field.value,
                subject_selector_key=plan_input.subject_selector.evaluator_key,
                subject_selector_version=plan_input.subject_selector.evaluator_version,
                subject_evaluator_key=plan_input.subject_evaluator.evaluator_key,
                subject_evaluator_version=plan_input.subject_evaluator.evaluator_version,
                aggregate_evaluator_key=plan_input.aggregate_evaluator.evaluator_key,
                aggregate_evaluator_version=plan_input.aggregate_evaluator.evaluator_version,
                require_complete_subject_set=plan_input.require_complete_subject_set,
                allow_partial_subject_status=plan_input.allow_partial_subject_status,
            )
            self.session.add(plan)
            self.session.flush()
            for measurement in plan_input.measurement_definitions:
                self.session.add(StudyConstraintMeasurementDefinition(
                    evaluation_plan_id=plan.id,
                    measurement_key=measurement.measurement_key,
                    authority=measurement.authority.value,
                    value_type=measurement.value_type.value,
                    unit_key=measurement.unit_key,
                    vocabulary_key=measurement.vocabulary_key,
                    required=measurement.required,
                    evidence_required=measurement.evidence_required,
                    derivation_key=measurement.derivation_key,
                    derivation_version=measurement.derivation_version,
                    unavailable_policy=None if measurement.unavailable_policy is None else measurement.unavailable_policy.value,
                ))
            for parameter in plan_input.parameters:
                self.session.add(StudyConstraintEvaluationParameter(
                    evaluation_plan_id=plan.id,
                    parameter_key=parameter.parameter_key,
                    value_type=parameter.value_type.value,
                    boolean_value=parameter.boolean_value,
                    integer_value=parameter.integer_value,
                    decimal_value=None if parameter.decimal_value is None else str(parameter.decimal_value),
                    text_value=parameter.text_value,
                    date_value=parameter.date_value,
                    vocabulary_key=parameter.vocabulary_key,
                    vocabulary_term_key=parameter.vocabulary_term_key,
                ))
            for term in plan_input.vocabulary_terms:
                self.session.add(StudyConstraintEvaluationVocabularyTerm(
                    evaluation_plan_id=plan.id,
                    vocabulary_key=term.vocabulary_key,
                    term_key=term.term_key,
                    term_definition=term.term_definition,
                ))
        outcomes: dict[str, StudyOutcomeDefinition] = {}
        for item in draft.outcome_definitions:
            value = StudyOutcomeDefinition(
                protocol_version_id=protocol.id,
                outcome_key=item.outcome_key,
                role=item.role.value,
                unit_of_analysis=item.unit_of_analysis,
                outcome_definition=item.outcome_definition,
                computation_rule=item.computation_rule,
                missing_data_rule=item.missing_data_rule,
                refusal_handling=item.refusal_handling,
                operational_failure_handling=item.operational_failure_handling,
            )
            self.session.add(value)
            outcomes[item.outcome_key] = value
        self.session.flush()
        analyses: dict[str, StudyAnalysisDefinition] = {}
        for item in draft.analysis_definitions:
            value = StudyAnalysisDefinition(
                protocol_version_id=protocol.id,
                outcome_definition_id=outcomes[item.outcome_key].id,
                analysis_key=item.analysis_key,
                analysis_population=item.analysis_population,
                comparison_definition=item.comparison_definition,
                aggregation_rule=item.aggregation_rule,
                exclusion_rule=item.exclusion_rule,
                reporting_rule=item.reporting_rule,
            )
            self.session.add(value)
            analyses[item.analysis_key] = value
        self.session.flush()

        contract_input = draft.execution_contract
        if contract_input is not None:
            contract = StudyExecutionContract(
                protocol_version_id=protocol.id,
                contract_version=contract_input.contract_version,
            )
            self.session.add(contract)
            self.session.flush()
            for plan_input in contract_input.outcome_calculation_plans:
                plan = StudyOutcomeCalculationPlan(
                    execution_contract_id=contract.id,
                    outcome_definition_id=outcomes[plan_input.outcome_key].id,
                    calculator_key=plan_input.calculator_key,
                    calculator_version=plan_input.calculator_version,
                    input_kind=plan_input.input_kind.value,
                    output_value_type=plan_input.output_value_type.value,
                    output_vocabulary_key=plan_input.output_vocabulary_key,
                    subject_interpretation=(
                        None if plan_input.subject_interpretation is None
                        else plan_input.subject_interpretation.value
                    ),
                )
                self.session.add(plan)
                self.session.flush()
                for policy in plan_input.disposition_policies:
                    self.session.add(StudyOutcomeDispositionPolicy(
                        calculation_plan_id=plan.id,
                        population_state=policy.population_state.value,
                        treatment=policy.treatment.value,
                    ))
                for binding in plan_input.constraint_bindings:
                    self.session.add(StudyOutcomeConstraintBinding(
                        calculation_plan_id=plan.id,
                        constraint_definition_id=constraint_definitions[binding.constraint_key].id,
                        binding_role=binding.binding_role,
                        ordinal=binding.ordinal,
                    ))
                for subject_kind in plan_input.subject_kinds:
                    self.session.add(StudyOutcomeSubjectKind(
                        calculation_plan_id=plan.id, subject_kind=subject_kind.value
                    ))
                for parameter in plan_input.parameters:
                    self.session.add(StudyOutcomeCalculationParameter(
                        calculation_plan_id=plan.id,
                        **self._calculation_parameter_values(parameter),
                    ))
                for term in plan_input.vocabulary_terms:
                    self.session.add(StudyOutcomeCalculationVocabularyTerm(
                        calculation_plan_id=plan.id,
                        vocabulary_key=term.vocabulary_key,
                        term_key=term.term_key,
                        term_definition=term.term_definition,
                    ))
            for plan_input in contract_input.analysis_calculation_plans:
                plan = StudyAnalysisCalculationPlan(
                    execution_contract_id=contract.id,
                    analysis_definition_id=analyses[plan_input.analysis_key].id,
                    calculator_key=plan_input.calculator_key,
                    calculator_version=plan_input.calculator_version,
                    population_scope=plan_input.population_scope.value,
                    output_shape_key=plan_input.output_shape_key,
                    output_shape_version=plan_input.output_shape_version,
                )
                self.session.add(plan)
                self.session.flush()
                for dimension in plan_input.dimensions:
                    self.session.add(StudyAnalysisDimension(
                        calculation_plan_id=plan.id,
                        dimension_role=dimension.dimension_role.value,
                        dimension_key=dimension.dimension_key.value,
                        ordinal=dimension.ordinal,
                    ))
                for binding in plan_input.condition_bindings:
                    self.session.add(StudyAnalysisConditionBinding(
                        calculation_plan_id=plan.id,
                        condition_id=conditions[binding.condition_key].id,
                        comparison_role=binding.comparison_role.value,
                    ))
                for parameter in plan_input.parameters:
                    self.session.add(StudyAnalysisCalculationParameter(
                        calculation_plan_id=plan.id,
                        **self._calculation_parameter_values(parameter),
                    ))
            self.session.flush()

        runs: dict[str, StudyPlannedRun] = {}
        for item in draft.planned_runs:
            value = StudyPlannedRun(
                protocol_version_id=protocol.id,
                condition_id=conditions[item.condition_key].id,
                block_id=blocks[item.block_key].id,
                run_key=item.run_key,
                replicate_number=item.replicate_number,
                randomized_ordinal=item.randomized_ordinal,
                planned_prompt_text=item.planned_prompt_text,
                planned_source_system=item.planned_source_system,
                replacement_for_run_id=None,
            )
            self.session.add(value)
            runs[item.run_key] = value
        self.session.flush()
        for item in draft.planned_runs:
            run = runs[item.run_key]
            if item.replacement_for_run_key is not None:
                run.replacement_for_run_id = runs[item.replacement_for_run_key].id
            for key in item.applicable_constraint_keys:
                self.session.add(StudyPlannedRunConstraint(
                    planned_run_id=run.id,
                    constraint_definition_id=constraint_definitions[key].id,
                ))
        self.session.flush()
        self.session.execute(
            update(StudyProtocolVersion)
            .where(StudyProtocolVersion.id == protocol.id)
            .values(
                registered_at=func.current_timestamp(),
                registration_hash=registration_hash,
            )
        )
        self.session.flush()
        self.session.expire(protocol)
        if protocol.registered_at is None:
            raise RuntimeError("database did not assign protocol registration time")
        return protocol

    @staticmethod
    def _calculation_parameter_values(parameter) -> dict[str, object]:
        return {
            "parameter_key": parameter.parameter_key,
            "ordinal": parameter.ordinal,
            "value_type": parameter.value_type.value,
            "boolean_value": parameter.boolean_value,
            "integer_value": parameter.integer_value,
            "decimal_value": None if parameter.decimal_value is None else str(parameter.decimal_value),
            "text_value": parameter.text_value,
            "date_value": parameter.date_value,
            "vocabulary_key": parameter.vocabulary_key,
            "vocabulary_term_key": parameter.vocabulary_term_key,
        }

    def record_operational_attempt(
        self, planned_run_id: int, draft: StudyOperationalAttemptInput
    ) -> dict[str, object]:
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            attempt_number = (
                self.session.scalar(
                    select(func.max(StudyRunAttempt.attempt_number)).where(
                        StudyRunAttempt.planned_run_id == run.id
                    )
                ) or 0
            ) + 1
            attempt = StudyRunAttempt(
                planned_run_id=run.id,
                attempt_number=attempt_number,
                attempt_type="OPERATIONAL_FAILURE",
                consumes_planned_run=self.session.get(
                    StudyProtocolVersion, run.protocol_version_id
                ).operational_failure_consumes_run,
                failure_code=draft.failure_code,
                notes=draft.notes,
            )
            self.session.add(attempt)
            self.session.flush()
            return self._attempt_dict(attempt)

    def realize_experiment(
        self, planned_run_id: int, draft: ExperimentInput
    ) -> dict[str, object]:
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            if any(self._definition_plan(item.id) is not None for item in self._run_definitions(run.id)):
                raise ValueError(
                    "planned run contains STRUCTURED_REQUIRED constraints; "
                    "use structured realization"
                )
            self._validate_experiment_against_run(run, draft)
            experiment_id = self._research.insert_experiment(draft)
            realization = StudyRunRealization(
                planned_run_id=run.id,
                disposition=StudyRunDisposition.EXPERIMENT_RECORDED.value,
                experiment_id=experiment_id,
                generation_failure_id=None,
            )
            self.session.add(realization)
            self.session.flush()
            return self._realization_dict(realization)

    def realize_structured_experiment(
        self,
        planned_run_id: int,
        draft: ExperimentInput,
        structured: StructuredStudyEvaluationInput,
    ) -> dict[str, object]:
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            definitions = self._run_definitions(run.id)
            structured_definitions = {
                item.id: item for item in definitions if self._definition_plan(item.id) is not None
            }
            if not structured_definitions:
                raise ValueError("planned run has no STRUCTURED_REQUIRED constraints")
            submitted = {
                item.study_constraint_definition_id: item for item in structured.constraints
            }
            if set(submitted) != set(structured_definitions):
                raise ValueError(
                    "structured evaluation input must cover exactly the STRUCTURED_REQUIRED constraints"
                )
            self._validate_experiment_against_run(run, draft)
            for item in draft.constraints:
                if item.study_constraint_definition_id in structured_definitions and item.result is not None:
                    raise ValueError(
                        "STRUCTURED_REQUIRED aggregate result may not be supplied in ExperimentInput"
                    )
            experiment_id = self._research.insert_experiment(draft)
            experiment = self._research.get_experiment(experiment_id)
            constraints = {
                item.study_constraint_definition_id: item
                for item in self.session.scalars(
                    select(Constraint).where(Constraint.experiment_id == experiment_id)
                )
            }
            tracks = {
                item.observed_ordinal: item for item in self.session.scalars(
                    select(ExperimentTrack).where(ExperimentTrack.experiment_id == experiment_id)
                )
            }
            sources = {
                item.source_key: item for item in self.session.scalars(
                    select(EvidenceSource).where(EvidenceSource.experiment_id == experiment_id)
                )
            }
            for definition_id, definition in structured_definitions.items():
                constraint = constraints[definition_id]
                plan = self._constraint_definition_dict(definition)["structured_evaluation_plan"]
                payload = submitted[definition_id]
                expected_subjects = self._enumerated_subjects(plan, experiment, constraint.id)
                self._validate_submitted_subjects(payload, expected_subjects, tracks)
                self._validate_direct_field_measurements(payload, expected_subjects, tracks, plan)
                flattened = self._flatten_measurements(payload, expected_subjects, tracks)
                calculated = evaluate_structured_constraint(
                    plan, experiment, constraint.id, flattened,
                    supplied_aggregate_status=payload.asserted_aggregate_status,
                    registry=self._evaluator_registry,
                )
                if not calculated["complete"]:
                    raise ValueError(
                        f"structured evaluation is incomplete: {calculated['issues']}"
                    )
                persisted_subjects = self._persist_structured_evaluation(
                    constraint, plan, calculated, payload, tracks, sources
                )
                if len(persisted_subjects) != len(expected_subjects):
                    raise RuntimeError("structured subject persistence is incomplete")
                aggregate = calculated["aggregate_constraint_result"]
                self.session.add(ConstraintResult(
                    experiment_id=experiment_id,
                    constraint_id=constraint.id,
                    status=aggregate["status"],
                    evidence=aggregate["evidence"],
                    provenance_type=aggregate["provenance_type"],
                    recorded_by=aggregate["recorded_by"],
                    provenance_notes=aggregate["provenance_notes"],
                ))
            realization = StudyRunRealization(
                planned_run_id=run.id,
                disposition=StudyRunDisposition.EXPERIMENT_RECORDED.value,
                experiment_id=experiment_id,
                generation_failure_id=None,
            )
            self.session.add(realization)
            self.session.flush()
            return self._realization_dict(realization)

    def _enumerated_subjects(self, plan, experiment, constraint_id):
        from playlist_narrative_engine.research_store.study_structured_evaluation import (
            enumerate_evaluation_subjects,
        )
        return enumerate_evaluation_subjects(
            plan, experiment, constraint_id, self._evaluator_registry
        )

    @staticmethod
    def _validate_submitted_subjects(payload, expected, tracks) -> None:
        expected_by_ordinal = {item["enumeration_ordinal"]: item for item in expected}
        if len(payload.subjects) != len(expected) or {
            item.enumeration_ordinal for item in payload.subjects
        } != set(expected_by_ordinal):
            raise ValueError("submitted structured subjects do not match exact enumeration")
        observed_by_track = {item.id: ordinal for ordinal, item in tracks.items()}
        for item in payload.subjects:
            subject = expected_by_ordinal[item.enumeration_ordinal]
            expected_observed = (
                None if subject["experiment_track_id"] is None
                else observed_by_track[subject["experiment_track_id"]]
            )
            if (
                item.subject_kind.value != subject["subject_kind"]
                or item.track_observed_ordinal != expected_observed
                or (None if item.governed_field is None else item.governed_field.value)
                != subject["governed_field"]
            ):
                raise ValueError("submitted structured subject differs from frozen enumeration")

    @staticmethod
    def _flatten_measurements(payload, expected, tracks):
        expected_by_ordinal = {item["enumeration_ordinal"]: item for item in expected}
        rows = []
        for subject in payload.subjects:
            expected_subject = expected_by_ordinal[subject.enumeration_ordinal]
            for measurement in subject.measurements:
                row = measurement.model_dump(mode="python")
                row["subject_key"] = expected_subject["subject_key"]
                row["authority_kind"] = measurement.authority_kind.value
                row["evidence"] = [item.model_dump(mode="python") for item in measurement.evidence]
                rows.append(row)
        return rows

    @staticmethod
    def _validate_direct_field_measurements(payload, expected, tracks, plan) -> None:
        expected_by_ordinal = {item["enumeration_ordinal"]: item for item in expected}
        definitions = {item["measurement_key"]: item for item in plan["measurement_definitions"]}
        fields = {
            "display_title": "display_title", "display_artist": "display_artist",
            "explicit_flag": "explicit_flag",
            "version_or_remaster_text": "version_or_remaster_text",
        }
        value_columns = {
            "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
            "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
        }
        for subject in payload.subjects:
            frozen = expected_by_ordinal[subject.enumeration_ordinal]
            governed_field = frozen["governed_field"]
            if governed_field is None:
                continue
            track = next(item for item in tracks.values() if item.id == frozen["experiment_track_id"])
            governed_value = getattr(track, fields[governed_field])
            for measurement in subject.measurements:
                definition = definitions[measurement.measurement_key]
                if definition["authority"] != "DIRECT_OBSERVATION" or measurement.value_type == "UNAVAILABLE":
                    continue
                supplied = getattr(measurement, value_columns[definition["value_type"]])
                if supplied != governed_value:
                    raise ValueError("direct-observation measurement contradicts the governed placement field")

    def _persist_structured_evaluation(
        self, constraint, plan, calculated, payload, tracks, sources
    ):
        definitions = {
            item.measurement_key: item for item in self.session.scalars(
                select(StudyConstraintMeasurementDefinition).where(
                    StudyConstraintMeasurementDefinition.evaluation_plan_id == plan["id"]
                )
            )
        }
        input_subjects = {item.enumeration_ordinal: item for item in payload.subjects}
        result_by_key = {
            item["subject"]["subject_key"]: item for item in calculated["subject_results"]
        }
        persisted = []
        for expected in calculated["subjects"]:
            subject_input = input_subjects[expected["enumeration_ordinal"]]
            subject = ConstraintEvaluationSubject(
                experiment_id=constraint.experiment_id,
                constraint_id=constraint.id,
                subject_kind=expected["subject_kind"],
                experiment_track_id=expected["experiment_track_id"],
                governed_field=expected["governed_field"],
                enumeration_ordinal=expected["enumeration_ordinal"],
            )
            self.session.add(subject)
            self.session.flush()
            calculated_measurements = {
                item["measurement_key"]: item for item in calculated["measurements"]
                if item["subject_key"] == expected["subject_key"]
            }
            for definition in definitions.values():
                if definition.authority != "STRUCTURAL_DERIVATION":
                    continue
                derived = calculated_measurements[definition.measurement_key]
                self.session.add(ConstraintEvaluationMeasurement(
                    subject_id=subject.id,
                    measurement_definition_id=definition.id,
                    authority_kind="STRUCTURAL_DERIVATION",
                    value_type=derived["value_type"],
                    boolean_value=derived.get("boolean_value"),
                    integer_value=derived.get("integer_value"),
                    decimal_value=None if derived.get("decimal_value") is None else str(derived["decimal_value"]),
                    text_value=derived.get("text_value"),
                    date_value=derived.get("date_value"),
                    vocabulary_term_key=derived.get("vocabulary_term_key"),
                    unavailable_reason=None,
                    recorded_by=derived["recorded_by"],
                    notes=None,
                ))
            for measurement_input in subject_input.measurements:
                definition = definitions[measurement_input.measurement_key]
                measurement = ConstraintEvaluationMeasurement(
                    subject_id=subject.id,
                    measurement_definition_id=definition.id,
                    authority_kind=measurement_input.authority_kind.value,
                    value_type=measurement_input.value_type,
                    boolean_value=measurement_input.boolean_value,
                    integer_value=measurement_input.integer_value,
                    decimal_value=(None if measurement_input.decimal_value is None else str(measurement_input.decimal_value)),
                    text_value=measurement_input.text_value,
                    date_value=measurement_input.date_value,
                    vocabulary_term_key=measurement_input.vocabulary_term_key,
                    unavailable_reason=measurement_input.unavailable_reason,
                    recorded_by=measurement_input.recorded_by,
                    notes=measurement_input.notes,
                )
                self.session.add(measurement)
                self.session.flush()
                for evidence_input in measurement_input.evidence:
                    source = sources.get(evidence_input.source_key)
                    if source is None:
                        raise ValueError(f"structured measurement source is not Experiment-owned: {evidence_input.source_key}")
                    link = self._resolve_measurement_link(
                        evidence_input, source.id, expected
                    )
                    self.session.add(ConstraintEvaluationMeasurementEvidence(
                        measurement_id=measurement.id,
                        evidence_source_id=source.id,
                        evidence_link_id=None if link is None else link.id,
                        evidence_role=evidence_input.evidence_role.value,
                        provenance_type=evidence_input.provenance_type.value,
                        support_status=evidence_input.support_status,
                        field_or_segment_reference=evidence_input.field_or_segment_reference,
                        notes=evidence_input.notes,
                    ))
            result = result_by_key.get(expected["subject_key"])
            if result is not None:
                self.session.add(ConstraintSubjectResult(
                    subject_id=subject.id,
                    status=result["status"],
                    evaluator_key=result["evaluator_key"],
                    evaluator_version=result["evaluator_version"],
                    reason_code=result["reason_code"],
                ))
            persisted.append(subject)
        self.session.flush()
        return persisted

    def _resolve_measurement_link(self, item, source_id, subject):
        if item.evidence_link_id is not None:
            link = self.session.get(EvidenceLink, item.evidence_link_id)
            if link is None:
                raise ValueError("structured measurement EvidenceLink does not exist")
            if link.evidence_source_id != source_id:
                raise ValueError("structured measurement EvidenceLink is not owned by the selected Experiment source")
            if subject["experiment_track_id"] is None:
                if link.experiment_id != subject["experiment_id"]:
                    raise ValueError("structured measurement EvidenceLink belongs to another Experiment")
            elif link.experiment_track_id != subject["experiment_track_id"]:
                raise ValueError("structured measurement EvidenceLink belongs to another evaluation subject")
            return link
        if item.evidence_link_field is None:
            return None
        statement = select(EvidenceLink).where(
            EvidenceLink.evidence_source_id == source_id,
            EvidenceLink.field_name == item.evidence_link_field,
        )
        if subject["experiment_track_id"] is None:
            statement = statement.where(EvidenceLink.experiment_id == subject["experiment_id"])
        else:
            statement = statement.where(
                EvidenceLink.experiment_track_id == subject["experiment_track_id"]
            )
        matches = list(self.session.scalars(statement))
        if len(matches) != 1:
            raise ValueError("structured measurement field evidence must resolve exactly one EvidenceLink")
        return matches[0]

    def realize_generation_failure(
        self,
        planned_run_id: int,
        draft: GenerationFailureInput,
        disposition: StudyRunDisposition,
    ) -> dict[str, object]:
        if disposition not in {
            StudyRunDisposition.MAESTRO_REFUSAL_RECORDED,
            StudyRunDisposition.MAESTRO_FAILURE_RECORDED,
        }:
            raise ValueError("generation-failure realization requires a Maestro failure disposition")
        with self.session.begin():
            run = self._registered_open_run(planned_run_id)
            if draft.prompt != run.planned_prompt_text:
                raise ValueError("generation-failure prompt must exactly match the planned prompt")
            if run.planned_source_system is not None and draft.source_system != run.planned_source_system:
                raise ValueError("generation-failure source system must match the planned source system")
            failure_id = self._research.record_generation_failure(draft)
            realization = StudyRunRealization(
                planned_run_id=run.id,
                disposition=disposition.value,
                experiment_id=None,
                generation_failure_id=failure_id,
            )
            self.session.add(realization)
            self.session.flush()
            return self._realization_dict(realization)

    def _registered_open_run(self, planned_run_id: int) -> StudyPlannedRun:
        run = self.session.get(StudyPlannedRun, planned_run_id)
        if run is None:
            raise ValueError(f"planned run not found: {planned_run_id}")
        protocol = self.session.get(StudyProtocolVersion, run.protocol_version_id)
        if protocol is None or protocol.registered_at is None:
            raise ValueError("planned run must belong to a registered protocol")
        realized = self.session.scalar(
            select(StudyRunRealization.id).where(StudyRunRealization.planned_run_id == run.id)
        )
        if realized is not None:
            raise ValueError("planned run already has a terminal scientific realization")
        consumed = self.session.scalar(
            select(StudyRunAttempt.id).where(
                StudyRunAttempt.planned_run_id == run.id,
                StudyRunAttempt.consumes_planned_run.is_(True),
            )
        )
        if consumed is not None:
            raise ValueError("planned run was consumed by protocol-authorized operational failure")
        return run

    def _validate_experiment_against_run(
        self, run: StudyPlannedRun, draft: ExperimentInput
    ) -> None:
        if draft.prompt != run.planned_prompt_text:
            raise ValueError("experiment prompt must exactly match the planned prompt")
        if run.planned_source_system is not None and draft.source_system != run.planned_source_system:
            raise ValueError("experiment source system must match the planned source system")
        definitions = list(self.session.scalars(
            select(StudyConstraintDefinition)
            .join(
                StudyPlannedRunConstraint,
                StudyPlannedRunConstraint.constraint_definition_id == StudyConstraintDefinition.id,
            )
            .where(StudyPlannedRunConstraint.planned_run_id == run.id)
            .order_by(StudyConstraintDefinition.id)
        ))
        supplied = {item.study_constraint_definition_id: item for item in draft.constraints}
        expected_ids = {item.id for item in definitions}
        if None in supplied or set(supplied) != expected_ids or len(supplied) != len(draft.constraints):
            raise ValueError("experiment must materialize exactly the planned run constraints")
        for definition in definitions:
            item = supplied[definition.id]
            if (
                item.constraint_type != definition.constraint_type
                or item.constraint_text != definition.constraint_text
                or item.is_hard_constraint != definition.is_hard_constraint
            ):
                raise ValueError("experiment constraint snapshot must exactly match its frozen definition")
            if item.result is not None and item.result.provenance_type.value != definition.permitted_result_provenance:
                raise ValueError("constraint result provenance is not permitted by its frozen definition")

    def _run_definitions(self, planned_run_id: int) -> list[StudyConstraintDefinition]:
        return list(self.session.scalars(
            select(StudyConstraintDefinition)
            .join(
                StudyPlannedRunConstraint,
                StudyPlannedRunConstraint.constraint_definition_id
                == StudyConstraintDefinition.id,
            )
            .where(StudyPlannedRunConstraint.planned_run_id == planned_run_id)
            .order_by(StudyConstraintDefinition.id)
        ))

    def _definition_plan(self, definition_id: int) -> StudyConstraintEvaluationPlan | None:
        return self.session.scalar(select(StudyConstraintEvaluationPlan).where(
            StudyConstraintEvaluationPlan.constraint_definition_id == definition_id
        ))

    def get_study(self, study_id_or_key: int | str) -> dict[str, object] | None:
        study = self._resolve_study(study_id_or_key)
        if study is None:
            return None
        versions = list(self.session.scalars(
            select(StudyProtocolVersion)
            .where(StudyProtocolVersion.study_id == study.id)
            .order_by(StudyProtocolVersion.version_number)
        ))
        current = versions[-1] if versions else None
        counts = {
            "planned_run_count": 0,
            "realized_run_count": 0,
            "operational_attempt_count": 0,
            "remaining_executable_run_count": 0,
        }
        if current is not None:
            runs = list(self.session.scalars(select(StudyPlannedRun).where(
                StudyPlannedRun.protocol_version_id == current.id
            )))
            run_ids = [item.id for item in runs]
            realized_ids = set(self.session.scalars(select(StudyRunRealization.planned_run_id).where(
                StudyRunRealization.planned_run_id.in_(run_ids or [-1])
            )))
            attempts = list(self.session.scalars(select(StudyRunAttempt).where(
                StudyRunAttempt.planned_run_id.in_(run_ids or [-1])
            )))
            consumed_ids = {item.planned_run_id for item in attempts if item.consumes_planned_run}
            counts = {
                "planned_run_count": len(runs),
                "realized_run_count": len(realized_ids),
                "operational_attempt_count": len(attempts),
                "remaining_executable_run_count": len(run_ids) - len(realized_ids | consumed_ids),
            }
        return {
            "id": study.id,
            "study_key": study.study_key,
            "title": study.title,
            "created_at": study.created_at.isoformat(),
            "protocol_versions": [self._protocol_summary(item) for item in versions],
            **counts,
        }

    def get_protocol_version(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        study = self._resolve_study(study_id_or_key)
        if study is None:
            return None
        protocol = self.session.scalar(select(StudyProtocolVersion).where(
            StudyProtocolVersion.study_id == study.id,
            StudyProtocolVersion.version_number == version,
        ))
        if protocol is None:
            return None
        return self._protocol_dict(study, protocol)

    def classify_study_execution(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        protocol = self.get_protocol_version(study_id_or_key, version)
        if protocol is None:
            return None
        return {
            "study_id": protocol["study_id"],
            "protocol_version_id": protocol["id"],
            "protocol_version": protocol["version_number"],
            "execution_classification": protocol["execution_classification"],
            "execution_contract_present": protocol["execution_contract"] is not None,
        }

    def get_planned_run_evaluation_context(
        self, planned_run_id: int
    ) -> dict[str, object] | None:
        """Return frozen protocol context for a prospective worksheet without writing."""
        run = self.session.get(StudyPlannedRun, planned_run_id)
        if run is None:
            return None
        protocol = self.session.get(StudyProtocolVersion, run.protocol_version_id)
        study = self.session.get(Study, protocol.study_id)
        projection = self._protocol_dict(study, protocol)
        run_projection = next(item for item in projection["planned_runs"] if item["id"] == run.id)
        applicable = set(run_projection["applicable_constraint_keys"])
        return {
            "study_id": study.id,
            "study_key": study.study_key,
            "protocol_version_id": protocol.id,
            "protocol_version": protocol.version_number,
            "registration_hash": protocol.registration_hash,
            "run": run_projection,
            "constraint_definitions": [
                item for item in projection["constraint_definitions"]
                if item["constraint_key"] in applicable
            ],
        }

    def list_studies(self) -> list[dict[str, object]]:
        return [self.get_study(item.id) for item in self.session.scalars(select(Study).order_by(Study.study_key))]

    def classify_evaluation_instrumentation(self, constraint_id: int) -> dict[str, object] | None:
        constraint = self.session.get(Constraint, constraint_id)
        if constraint is None:
            return None
        plan = None
        if constraint.study_constraint_definition_id is not None:
            plan = self.session.scalar(select(StudyConstraintEvaluationPlan).where(
                StudyConstraintEvaluationPlan.constraint_definition_id
                == constraint.study_constraint_definition_id
            ))
        subject_count = self.session.scalar(
            select(func.count()).select_from(ConstraintEvaluationSubject).where(
                ConstraintEvaluationSubject.constraint_id == constraint_id
            )
        ) or 0
        return {
            "constraint_id": constraint.id,
            "experiment_id": constraint.experiment_id,
            "study_constraint_definition_id": constraint.study_constraint_definition_id,
            "instrumentation_classification": (
                "LEGACY_AGGREGATE_ONLY" if plan is None else "STRUCTURED_DERIVABLE"
            ),
            "evaluation_plan_id": None if plan is None else plan.id,
            "structured_subject_count": subject_count,
        }

    def get_structured_constraint_context(self, constraint_id: int) -> dict[str, object] | None:
        constraint = self.session.get(Constraint, constraint_id)
        if constraint is None:
            return None
        classification = self.classify_evaluation_instrumentation(constraint_id)
        experiment = self._research.get_experiment(constraint.experiment_id)
        if classification["evaluation_plan_id"] is None:
            return {**classification, "experiment": experiment, "plan": None}
        definition = self.session.get(
            StudyConstraintDefinition, constraint.study_constraint_definition_id
        )
        definition_projection = self._constraint_definition_dict(definition)
        return {
            **classification,
            "experiment": experiment,
            "plan": definition_projection["structured_evaluation_plan"],
        }

    def get_structured_constraint_evaluation(
        self, constraint_id: int
    ) -> dict[str, object] | None:
        classification = self.classify_evaluation_instrumentation(constraint_id)
        if classification is None:
            return None
        subjects = list(self.session.scalars(
            select(ConstraintEvaluationSubject)
            .where(ConstraintEvaluationSubject.constraint_id == constraint_id)
            .order_by(ConstraintEvaluationSubject.enumeration_ordinal, ConstraintEvaluationSubject.id)
        ))
        subject_rows: list[dict[str, object]] = []
        for subject in subjects:
            measurements = list(self.session.scalars(
                select(ConstraintEvaluationMeasurement)
                .where(ConstraintEvaluationMeasurement.subject_id == subject.id)
                .order_by(ConstraintEvaluationMeasurement.measurement_definition_id)
            ))
            result = self.session.scalar(select(ConstraintSubjectResult).where(
                ConstraintSubjectResult.subject_id == subject.id
            ))
            subject_rows.append({
                "id": subject.id,
                "experiment_id": subject.experiment_id,
                "constraint_id": subject.constraint_id,
                "subject_kind": subject.subject_kind,
                "experiment_track_id": subject.experiment_track_id,
                "governed_field": subject.governed_field,
                "enumeration_ordinal": subject.enumeration_ordinal,
                "measurements": [self._measurement_dict(item) for item in measurements],
                "result": None if result is None else {
                    "id": result.id,
                    "status": result.status,
                    "evaluator_key": result.evaluator_key,
                    "evaluator_version": result.evaluator_version,
                    "evaluated_at": result.evaluated_at.isoformat(),
                    "reason_code": result.reason_code,
                },
            })
        return {**classification, "subjects": subject_rows}

    def get_evaluation_provenance(self, constraint_id: int) -> dict[str, object] | None:
        evaluation = self.get_structured_constraint_evaluation(constraint_id)
        if evaluation is None:
            return None
        evidence_rows: list[dict[str, object]] = []
        for subject in evaluation["subjects"]:
            for measurement in subject["measurements"]:
                evidence_rows.extend(measurement["evidence"])
        return {
            "constraint_id": constraint_id,
            "experiment_id": evaluation["experiment_id"],
            "instrumentation_classification": evaluation["instrumentation_classification"],
            "evidence": evidence_rows,
        }

    def _measurement_dict(self, item: ConstraintEvaluationMeasurement) -> dict[str, object]:
        definition = self.session.get(
            StudyConstraintMeasurementDefinition, item.measurement_definition_id
        )
        evidence = list(self.session.scalars(
            select(ConstraintEvaluationMeasurementEvidence)
            .where(ConstraintEvaluationMeasurementEvidence.measurement_id == item.id)
            .order_by(ConstraintEvaluationMeasurementEvidence.id)
        ))
        return {
            "id": item.id,
            "measurement_definition_id": item.measurement_definition_id,
            "measurement_key": None if definition is None else definition.measurement_key,
            "authority_kind": item.authority_kind,
            "value_type": item.value_type,
            "boolean_value": item.boolean_value,
            "integer_value": item.integer_value,
            "decimal_value": item.decimal_value,
            "text_value": item.text_value,
            "date_value": None if item.date_value is None else item.date_value.isoformat(),
            "vocabulary_term_key": item.vocabulary_term_key,
            "unavailable_reason": item.unavailable_reason,
            "recorded_by": item.recorded_by,
            "created_at": item.created_at.isoformat(),
            "notes": item.notes,
            "evidence": [self._measurement_evidence_dict(row) for row in evidence],
        }

    def _measurement_evidence_dict(
        self, item: ConstraintEvaluationMeasurementEvidence
    ) -> dict[str, object]:
        source = self.session.get(EvidenceSource, item.evidence_source_id)
        link = self.session.get(EvidenceLink, item.evidence_link_id) if item.evidence_link_id else None
        return {
            "id": item.id,
            "measurement_id": item.measurement_id,
            "evidence_source_id": item.evidence_source_id,
            "source_key": None if source is None else source.source_key,
            "source_type": None if source is None else source.source_type,
            "source_reference": None if source is None else source.source_reference,
            "evidence_link_id": item.evidence_link_id,
            "evidence_link_field": None if link is None else link.field_name,
            "evidence_role": item.evidence_role,
            "provenance_type": item.provenance_type,
            "support_status": item.support_status,
            "field_or_segment_reference": item.field_or_segment_reference,
            "notes": item.notes,
        }

    def _resolve_study(self, value: int | str) -> Study | None:
        if isinstance(value, int):
            return self.session.get(Study, value)
        return self.session.scalar(select(Study).where(Study.study_key == value))

    def _protocol_dict(self, study: Study, protocol: StudyProtocolVersion) -> dict[str, object]:
        conditions = list(self.session.scalars(select(StudyCondition).where(StudyCondition.protocol_version_id == protocol.id).order_by(StudyCondition.id)))
        blocks = list(self.session.scalars(select(StudyBlock).where(StudyBlock.protocol_version_id == protocol.id).order_by(StudyBlock.id)))
        constraints = list(self.session.scalars(select(StudyConstraintDefinition).where(StudyConstraintDefinition.protocol_version_id == protocol.id).order_by(StudyConstraintDefinition.id)))
        outcomes = list(self.session.scalars(select(StudyOutcomeDefinition).where(StudyOutcomeDefinition.protocol_version_id == protocol.id).order_by(StudyOutcomeDefinition.id)))
        analyses = list(self.session.scalars(select(StudyAnalysisDefinition).where(StudyAnalysisDefinition.protocol_version_id == protocol.id).order_by(StudyAnalysisDefinition.id)))
        runs = list(self.session.scalars(select(StudyPlannedRun).where(StudyPlannedRun.protocol_version_id == protocol.id).order_by(StudyPlannedRun.randomized_ordinal)))
        condition_by_id = {item.id: item.condition_key for item in conditions}
        block_by_id = {item.id: item.block_key for item in blocks}
        outcome_by_id = {item.id: item.outcome_key for item in outcomes}
        return {
            "study_id": study.id,
            "study_key": study.study_key,
            "title": study.title,
            **self._protocol_summary(protocol),
            "objective": protocol.objective,
            "primary_hypothesis": protocol.primary_hypothesis,
            "null_hypothesis": protocol.null_hypothesis,
            "design_summary": protocol.design_summary,
            "planned_sample_size": protocol.planned_sample_size,
            "randomization_method": protocol.randomization_method,
            "randomization_seed": protocol.randomization_seed,
            "operational_failure_policy": protocol.operational_failure_policy,
            "operational_failure_consumes_run": protocol.operational_failure_consumes_run,
            "refusal_policy": protocol.refusal_policy,
            "missing_result_policy": protocol.missing_result_policy,
            "conditions": [{"id": x.id, "condition_key": x.condition_key, "label": x.label, "role": x.role, "exact_factor_definition": x.exact_factor_definition} for x in conditions],
            "blocks": [{"id": x.id, "block_key": x.block_key, "label": x.label, "block_definition": x.block_definition} for x in blocks],
            "constraint_definitions": [self._constraint_definition_dict(x) for x in constraints],
            "outcome_definitions": [{"id": x.id, "outcome_key": x.outcome_key, "role": x.role, "unit_of_analysis": x.unit_of_analysis, "outcome_definition": x.outcome_definition, "computation_rule": x.computation_rule, "missing_data_rule": x.missing_data_rule, "refusal_handling": x.refusal_handling, "operational_failure_handling": x.operational_failure_handling} for x in outcomes],
            "analysis_definitions": [{"id": x.id, "analysis_key": x.analysis_key, "outcome_key": outcome_by_id[x.outcome_definition_id], "analysis_population": x.analysis_population, "comparison_definition": x.comparison_definition, "aggregation_rule": x.aggregation_rule, "exclusion_rule": x.exclusion_rule, "reporting_rule": x.reporting_rule} for x in analyses],
            "planned_runs": [self._run_dict(x, condition_by_id, block_by_id) for x in runs],
            "execution_classification": (
                "LEGACY_EXECUTION"
                if self.session.scalar(select(StudyExecutionContract.id).where(
                    StudyExecutionContract.protocol_version_id == protocol.id
                )) is None
                else "CALCULATOR_GOVERNED_EXECUTION"
            ),
            "execution_contract": self._execution_contract_dict(
                protocol.id, constraints, outcomes, analyses, conditions
            ),
        }

    def _execution_contract_dict(
        self,
        protocol_version_id: int,
        constraints: list[StudyConstraintDefinition],
        outcomes: list[StudyOutcomeDefinition],
        analyses: list[StudyAnalysisDefinition],
        conditions: list[StudyCondition],
    ) -> dict[str, object] | None:
        contract = self.session.scalar(select(StudyExecutionContract).where(
            StudyExecutionContract.protocol_version_id == protocol_version_id
        ))
        if contract is None:
            return None
        constraint_keys = {item.id: item.constraint_key for item in constraints}
        outcome_keys = {item.id: item.outcome_key for item in outcomes}
        analysis_keys = {item.id: item.analysis_key for item in analyses}
        condition_keys = {item.id: item.condition_key for item in conditions}
        outcome_plans = list(self.session.scalars(
            select(StudyOutcomeCalculationPlan)
            .where(StudyOutcomeCalculationPlan.execution_contract_id == contract.id)
            .order_by(StudyOutcomeCalculationPlan.id)
        ))
        outcome_rows = []
        for plan in outcome_plans:
            bindings = list(self.session.scalars(
                select(StudyOutcomeConstraintBinding)
                .where(StudyOutcomeConstraintBinding.calculation_plan_id == plan.id)
                .order_by(StudyOutcomeConstraintBinding.ordinal)
            ))
            subject_kinds = list(self.session.scalars(
                select(StudyOutcomeSubjectKind)
                .where(StudyOutcomeSubjectKind.calculation_plan_id == plan.id)
                .order_by(StudyOutcomeSubjectKind.subject_kind)
            ))
            parameters = list(self.session.scalars(
                select(StudyOutcomeCalculationParameter)
                .where(StudyOutcomeCalculationParameter.calculation_plan_id == plan.id)
                .order_by(StudyOutcomeCalculationParameter.parameter_key, StudyOutcomeCalculationParameter.ordinal)
            ))
            terms = list(self.session.scalars(
                select(StudyOutcomeCalculationVocabularyTerm)
                .where(StudyOutcomeCalculationVocabularyTerm.calculation_plan_id == plan.id)
                .order_by(StudyOutcomeCalculationVocabularyTerm.vocabulary_key, StudyOutcomeCalculationVocabularyTerm.term_key)
            ))
            disposition_policies = list(self.session.scalars(
                select(StudyOutcomeDispositionPolicy)
                .where(StudyOutcomeDispositionPolicy.calculation_plan_id == plan.id)
                .order_by(StudyOutcomeDispositionPolicy.population_state)
            ))
            outcome_rows.append({
                "id": plan.id,
                "outcome_key": outcome_keys[plan.outcome_definition_id],
                "calculator_key": plan.calculator_key,
                "calculator_version": plan.calculator_version,
                "input_kind": plan.input_kind,
                "output_value_type": plan.output_value_type,
                "output_vocabulary_key": plan.output_vocabulary_key,
                "subject_interpretation": plan.subject_interpretation,
                "constraint_bindings": [{
                    "id": item.id,
                    "constraint_key": constraint_keys[item.constraint_definition_id],
                    "binding_role": item.binding_role,
                    "ordinal": item.ordinal,
                } for item in bindings],
                "subject_kinds": [item.subject_kind for item in subject_kinds],
                "parameters": [self._calculation_parameter_dict(item) for item in parameters],
                "vocabulary_terms": [{
                    "vocabulary_key": item.vocabulary_key,
                    "term_key": item.term_key,
                    "term_definition": item.term_definition,
                } for item in terms],
                "disposition_policies": [{
                    "id": item.id,
                    "population_state": item.population_state,
                    "treatment": item.treatment,
                } for item in disposition_policies],
            })
        analysis_plans = list(self.session.scalars(
            select(StudyAnalysisCalculationPlan)
            .where(StudyAnalysisCalculationPlan.execution_contract_id == contract.id)
            .order_by(StudyAnalysisCalculationPlan.id)
        ))
        analysis_rows = []
        for plan in analysis_plans:
            dimensions = list(self.session.scalars(
                select(StudyAnalysisDimension)
                .where(StudyAnalysisDimension.calculation_plan_id == plan.id)
                .order_by(StudyAnalysisDimension.ordinal)
            ))
            bindings = list(self.session.scalars(
                select(StudyAnalysisConditionBinding)
                .where(StudyAnalysisConditionBinding.calculation_plan_id == plan.id)
                .order_by(StudyAnalysisConditionBinding.comparison_role)
            ))
            parameters = list(self.session.scalars(
                select(StudyAnalysisCalculationParameter)
                .where(StudyAnalysisCalculationParameter.calculation_plan_id == plan.id)
                .order_by(StudyAnalysisCalculationParameter.parameter_key, StudyAnalysisCalculationParameter.ordinal)
            ))
            analysis_rows.append({
                "id": plan.id,
                "analysis_key": analysis_keys[plan.analysis_definition_id],
                "calculator_key": plan.calculator_key,
                "calculator_version": plan.calculator_version,
                "population_scope": plan.population_scope,
                "output_shape_key": plan.output_shape_key,
                "output_shape_version": plan.output_shape_version,
                "dimensions": [{
                    "dimension_role": item.dimension_role,
                    "dimension_key": item.dimension_key,
                    "ordinal": item.ordinal,
                } for item in dimensions],
                "condition_bindings": [{
                    "comparison_role": item.comparison_role,
                    "condition_key": condition_keys[item.condition_id],
                } for item in bindings],
                "parameters": [self._calculation_parameter_dict(item) for item in parameters],
            })
        return {
            "id": contract.id,
            "contract_version": contract.contract_version,
            "outcome_calculation_plans": sorted(outcome_rows, key=lambda item: item["outcome_key"]),
            "analysis_calculation_plans": sorted(analysis_rows, key=lambda item: item["analysis_key"]),
        }

    @staticmethod
    def _calculation_parameter_dict(item) -> dict[str, object]:
        return {
            "parameter_key": item.parameter_key,
            "ordinal": item.ordinal,
            "value_type": item.value_type,
            "boolean_value": item.boolean_value,
            "integer_value": item.integer_value,
            "decimal_value": item.decimal_value,
            "text_value": item.text_value,
            "date_value": None if item.date_value is None else item.date_value.isoformat(),
            "vocabulary_key": item.vocabulary_key,
            "vocabulary_term_key": item.vocabulary_term_key,
        }

    def _constraint_definition_dict(
        self, definition: StudyConstraintDefinition
    ) -> dict[str, object]:
        result = {
            "id": definition.id,
            "constraint_key": definition.constraint_key,
            "constraint_type": definition.constraint_type,
            "constraint_text": definition.constraint_text,
            "is_hard_constraint": definition.is_hard_constraint,
            "evaluation_rule": definition.evaluation_rule,
            "permitted_result_provenance": definition.permitted_result_provenance,
            "unknown_handling": definition.unknown_handling,
        }
        plan = self.session.scalar(select(StudyConstraintEvaluationPlan).where(
            StudyConstraintEvaluationPlan.constraint_definition_id == definition.id
        ))
        if plan is None:
            return result
        measurements = list(self.session.scalars(
            select(StudyConstraintMeasurementDefinition)
            .where(StudyConstraintMeasurementDefinition.evaluation_plan_id == plan.id)
            .order_by(StudyConstraintMeasurementDefinition.id)
        ))
        parameters = list(self.session.scalars(
            select(StudyConstraintEvaluationParameter)
            .where(StudyConstraintEvaluationParameter.evaluation_plan_id == plan.id)
            .order_by(StudyConstraintEvaluationParameter.id)
        ))
        terms = list(self.session.scalars(
            select(StudyConstraintEvaluationVocabularyTerm)
            .where(StudyConstraintEvaluationVocabularyTerm.evaluation_plan_id == plan.id)
            .order_by(StudyConstraintEvaluationVocabularyTerm.id)
        ))
        result["structured_evaluation_plan"] = {
            "id": plan.id,
            "instrumentation_version": plan.instrumentation_version,
            "subject_kind": plan.subject_kind,
            "subject_field": plan.subject_field,
            "subject_selector": {
                "evaluator_key": plan.subject_selector_key,
                "evaluator_version": plan.subject_selector_version,
            },
            "subject_evaluator": {
                "evaluator_key": plan.subject_evaluator_key,
                "evaluator_version": plan.subject_evaluator_version,
            },
            "aggregate_evaluator": {
                "evaluator_key": plan.aggregate_evaluator_key,
                "evaluator_version": plan.aggregate_evaluator_version,
            },
            "require_complete_subject_set": plan.require_complete_subject_set,
            "allow_partial_subject_status": plan.allow_partial_subject_status,
            "measurement_definitions": [{
                "id": item.id,
                "measurement_key": item.measurement_key,
                "authority": item.authority,
                "value_type": item.value_type,
                "unit_key": item.unit_key,
                "vocabulary_key": item.vocabulary_key,
                "required": item.required,
                "evidence_required": item.evidence_required,
                "derivation_key": item.derivation_key,
                "derivation_version": item.derivation_version,
                "unavailable_policy": item.unavailable_policy,
            } for item in measurements],
            "parameters": [{
                "id": item.id,
                "parameter_key": item.parameter_key,
                "value_type": item.value_type,
                "boolean_value": item.boolean_value,
                "integer_value": item.integer_value,
                "decimal_value": item.decimal_value,
                "text_value": item.text_value,
                "date_value": None if item.date_value is None else item.date_value.isoformat(),
                "vocabulary_key": item.vocabulary_key,
                "vocabulary_term_key": item.vocabulary_term_key,
            } for item in parameters],
            "vocabulary_terms": [{
                "id": item.id,
                "vocabulary_key": item.vocabulary_key,
                "term_key": item.term_key,
                "term_definition": item.term_definition,
            } for item in terms],
        }
        return result

    def _run_dict(self, run, condition_by_id, block_by_id):
        applicable = list(self.session.scalars(select(StudyConstraintDefinition.constraint_key).join(StudyPlannedRunConstraint, StudyPlannedRunConstraint.constraint_definition_id == StudyConstraintDefinition.id).where(StudyPlannedRunConstraint.planned_run_id == run.id).order_by(StudyConstraintDefinition.id)))
        attempts = list(self.session.scalars(select(StudyRunAttempt).where(StudyRunAttempt.planned_run_id == run.id).order_by(StudyRunAttempt.attempt_number)))
        realization = self.session.scalar(select(StudyRunRealization).where(StudyRunRealization.planned_run_id == run.id))
        replacement = self.session.get(StudyPlannedRun, run.replacement_for_run_id) if run.replacement_for_run_id else None
        return {"id": run.id, "run_key": run.run_key, "condition_key": condition_by_id[run.condition_id], "block_key": block_by_id[run.block_id], "replicate_number": run.replicate_number, "randomized_ordinal": run.randomized_ordinal, "planned_prompt_text": run.planned_prompt_text, "planned_source_system": run.planned_source_system, "replacement_for_run_key": None if replacement is None else replacement.run_key, "applicable_constraint_keys": applicable, "attempts": [self._attempt_dict(x) for x in attempts], "realization": None if realization is None else self._realization_dict(realization)}

    @staticmethod
    def _protocol_summary(item):
        return {"id": item.id, "version_number": item.version_number, "predecessor_version_id": item.predecessor_version_id, "registered_at": None if item.registered_at is None else item.registered_at.isoformat(), "registration_hash": item.registration_hash, "amendment_reason": item.amendment_reason}

    @staticmethod
    def _attempt_dict(item):
        return {"id": item.id, "planned_run_id": item.planned_run_id, "attempt_number": item.attempt_number, "attempted_at": item.attempted_at.isoformat(), "attempt_type": item.attempt_type, "consumes_planned_run": item.consumes_planned_run, "failure_code": item.failure_code, "notes": item.notes}

    @staticmethod
    def _realization_dict(item):
        return {"id": item.id, "planned_run_id": item.planned_run_id, "disposition": item.disposition, "experiment_id": item.experiment_id, "generation_failure_id": item.generation_failure_id, "realized_at": item.realized_at.isoformat()}

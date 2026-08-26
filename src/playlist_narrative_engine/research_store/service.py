from __future__ import annotations

import hashlib
import itertools
import statistics
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Iterator, Literal, TypeVar

from pydantic import ValidationError

from playlist_narrative_engine.research_store.database import (
    make_research_engine,
    make_research_session_factory,
)
from playlist_narrative_engine.research_store.migrations import migrate_research_database
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.study_repository import StudyRepository
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
    StudyEvaluatorRegistry,
)
from playlist_narrative_engine.research_store.study_execution_registry import (
    DEFAULT_STUDY_EXECUTION_REGISTRY,
    StudyExecutionRegistry,
)
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    calculate_aggregate_constraint_result as calculate_structured_aggregate,
    calculate_subject_results as calculate_structured_subjects,
    enumerate_evaluation_subjects as enumerate_structured_subjects,
    evaluate_structured_constraint,
    validate_structured_measurements as validate_measurements,
)
from playlist_narrative_engine.research_store.study_evaluation import (
    evaluate_calculator_governed_study,
    evaluate_registered_study,
)
from playlist_narrative_engine.research_store.study_exploration import explore_study
from playlist_narrative_engine.research_store.study_closeout import (
    build_study_closeout,
    current_repository_revision,
)
from playlist_narrative_engine.research_store.study_calculators import (
    DEFAULT_STUDY_CALCULATOR_EXECUTOR,
    StudyCalculatorExecutor,
    calculate_paired_difference,
    calculate_status_rate,
    unavailable_projection,
)
from playlist_narrative_engine.research_store.schemas import (
    EvidenceSourceInput,
    ExperimentInput,
    GenerationFailureInput,
    PersistedPlaylistArtifactInput,
)
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyProtocolAmendmentInput,
    StudyRegistrationInput,
    StudyRunDisposition,
    StructuredStudyEvaluationInput,
)


ValidatedValue = TypeVar("ValidatedValue")
QueryValue = TypeVar("QueryValue")
RecordKind = Literal["experiment", "persisted_artifact"]


@dataclass(frozen=True)
class ValidationIssue:
    location: tuple[str | int, ...]
    message: str
    issue_type: str


@dataclass(frozen=True)
class ValidationResult(Generic[ValidatedValue]):
    value: ValidatedValue | None
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return self.value is not None and not self.issues


@dataclass(frozen=True)
class EvidenceVerificationIssue:
    source_key: str
    local_path: str
    issue_type: Literal["file_not_found", "checksum_mismatch"]
    message: str


@dataclass(frozen=True)
class EvidenceVerificationResult:
    issues: tuple[EvidenceVerificationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class IngestedRecord:
    kind: RecordKind
    record_id: int
    record: dict[str, object]


class ResearchStoreService:
    """Orchestrate existing research-store operations without adding semantics."""

    def __init__(
        self,
        repository: ResearchRepository,
        *,
        evaluator_registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
        execution_registry: StudyExecutionRegistry = DEFAULT_STUDY_EXECUTION_REGISTRY,
        calculator_executor: StudyCalculatorExecutor = DEFAULT_STUDY_CALCULATOR_EXECUTOR,
    ) -> None:
        self._repository = repository
        self._evaluator_registry = evaluator_registry
        self._calculator_executor = calculator_executor
        self._studies = StudyRepository(
            repository.session, evaluator_registry, execution_registry
        )

    @staticmethod
    def validate_experiment(proposal: object) -> ValidationResult[ExperimentInput]:
        return _validate(ExperimentInput, proposal)

    @staticmethod
    def validate_persisted_artifact(
        proposal: object,
    ) -> ValidationResult[PersistedPlaylistArtifactInput]:
        return _validate(PersistedPlaylistArtifactInput, proposal)

    @staticmethod
    def validate_study_protocol(
        proposal: object,
    ) -> ValidationResult[StudyRegistrationInput]:
        return _validate(StudyRegistrationInput, proposal)

    @staticmethod
    def validate_study_protocol_amendment(
        proposal: object,
    ) -> ValidationResult[StudyProtocolAmendmentInput]:
        return _validate(StudyProtocolAmendmentInput, proposal)

    def register_study(self, proposal: StudyRegistrationInput) -> dict[str, object]:
        _require_type(proposal, StudyRegistrationInput)
        return self._studies.register_study(proposal)

    def register_protocol_amendment(
        self, study_id: int, proposal: StudyProtocolAmendmentInput
    ) -> dict[str, object]:
        _require_type(proposal, StudyProtocolAmendmentInput)
        return self._studies.register_protocol_amendment(study_id, proposal)

    def get_study(self, study_id_or_key: int | str) -> dict[str, object] | None:
        return self._read_projection(self._studies.get_study, study_id_or_key)

    def get_protocol_version(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        return self._read_query(
            self._studies.get_protocol_version, study_id_or_key, version
        )

    def classify_study_execution(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        return self._read_query(
            self._studies.classify_study_execution, study_id_or_key, version
        )

    def get_calculator_availability(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        protocol = self.get_protocol_version(study_id_or_key, version)
        if protocol is None:
            return None
        contract = protocol["execution_contract"]
        if contract is None:
            return {
                "study_id": protocol["study_id"], "protocol_version_id": protocol["id"],
                "execution_classification": "LEGACY_EXECUTION", "outcomes": [], "analyses": [],
            }
        return {
            "study_id": protocol["study_id"], "protocol_version_id": protocol["id"],
            "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
            "outcomes": [{
                "registered_outcome_plan_id": plan["id"],
                "calculator_key": plan["calculator_key"],
                "calculator_version": plan["calculator_version"],
                "execution_state": "AVAILABLE" if self._calculator_executor.outcome_available(plan) else "UNAVAILABLE",
            } for plan in contract["outcome_calculation_plans"]],
            "analyses": [{
                "registered_analysis_plan_id": plan["id"],
                "calculator_key": plan["calculator_key"],
                "calculator_version": plan["calculator_version"],
                "execution_state": "AVAILABLE" if self._calculator_executor.analysis_available(plan) else "UNAVAILABLE",
            } for plan in contract["analysis_calculation_plans"]],
        }

    def calculate_registered_outcome(
        self, study_id_or_key: int | str, version: int,
        planned_run_id: int, outcome_plan_id: int,
        *, _protocol: dict[str, object] | None = None,
        _experiment_cache: dict[int, dict[str, object] | None] | None = None,
        _structured_cache: dict[int, dict[str, object] | None] | None = None,
    ) -> dict[str, object]:
        protocol = _protocol or self.get_protocol_version(study_id_or_key, version)
        if protocol is None:
            raise ValueError("registered protocol not found")
        contract = protocol["execution_contract"]
        if contract is None:
            raise ValueError("LEGACY_EXECUTION protocol has no registered calculator contract")
        plan = next((item for item in contract["outcome_calculation_plans"] if item["id"] == outcome_plan_id), None)
        run = next((item for item in protocol["planned_runs"] if item["id"] == planned_run_id), None)
        if plan is None or run is None:
            raise ValueError("outcome plan and planned run must belong to the registered protocol version")
        if not self._calculator_executor.outcome_available(plan):
            return unavailable_projection(plan["calculator_key"], plan["calculator_version"])
        realization = run["realization"]
        population_state = "PENDING" if realization is None else realization["disposition"]
        context = {
            "protocol_version_id": protocol["id"], "registration_hash": protocol["registration_hash"],
            "planned_run_id": run["id"], "population_state": population_state,
            "realization": realization,
        }
        if population_state != "EXPERIMENT_RECORDED":
            projection = calculate_status_rate(plan, context, [], [])
            if plan["calculator_key"] == "outcome.subject_status_rate":
                projection.update(
                    authorized_subject_kinds=plan["subject_kinds"],
                    subject_interpretation=plan["subject_interpretation"],
                    subject_result_ids=[], subject_identities=[],
                    contributing_constraint_definition_ids=[],
                )
            return projection
        experiment_id = int(realization["experiment_id"])
        if _experiment_cache is None:
            experiment = self.get_experiment(experiment_id)
        else:
            if experiment_id not in _experiment_cache:
                _experiment_cache[experiment_id] = self.get_experiment(experiment_id)
            experiment = _experiment_cache[experiment_id]
        bound = {item["constraint_key"] for item in plan["constraint_bindings"]}
        expected_keys = bound.intersection(run["applicable_constraint_keys"])
        definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
        constraints = {
            item["study_constraint_definition_id"]: item for item in experiment["constraints"]
            if item["study_constraint_definition_id"] is not None
        }
        inputs: list[dict[str, object]] = []
        missing: list[dict[str, object]] = []
        incompatible: str | None = None
        for key in sorted(expected_keys, key=lambda value: next(
            item["ordinal"] for item in plan["constraint_bindings"] if item["constraint_key"] == value
        )):
            definition = definitions[key]
            constraint = constraints.get(definition["id"])
            missing_row = {
                "constraint_definition_id": definition["id"], "constraint_key": key,
                "sort_key": [definition["id"]],
            }
            if constraint is None:
                missing.append(missing_row)
                continue
            if plan["calculator_key"] == "outcome.constraint_status_rate":
                if constraint["result"] is None:
                    missing.append({**missing_row, "constraint_id": constraint["id"]})
                else:
                    inputs.append({
                        "constraint_definition_id": definition["id"], "constraint_id": constraint["id"],
                        "experiment_id": experiment["id"], "status": constraint["result"]["status"],
                        "provenance_type": constraint["result"]["provenance_type"],
                        "source_reason_code": constraint["result"].get("provenance_notes"),
                        "sort_key": [definition["id"], constraint["id"]],
                    })
                continue
            structured_plan = definition.get("structured_evaluation_plan")
            if structured_plan is None or structured_plan["subject_kind"] not in plan["subject_kinds"]:
                incompatible = f"constraint definition {definition['id']} is incompatible with the registered subject population"
                continue
            constraint_id = int(constraint["id"])
            if _structured_cache is None:
                evaluation = self.get_structured_constraint_evaluation(constraint_id)
            else:
                if constraint_id not in _structured_cache:
                    _structured_cache[constraint_id] = self.get_structured_constraint_evaluation(constraint_id)
                evaluation = _structured_cache[constraint_id]
            if evaluation is None or evaluation["instrumentation_classification"] != "STRUCTURED_DERIVABLE":
                incompatible = f"constraint {constraint['id']} lacks registered structured instrumentation"
                continue
            for subject in evaluation["subjects"]:
                if subject["subject_kind"] not in plan["subject_kinds"]:
                    incompatible = f"subject {subject['id']} has an unauthorized subject kind"
                    continue
                result = subject["result"]
                if result is None:
                    missing.append({
                        **missing_row, "constraint_id": constraint["id"], "subject_id": subject["id"],
                        "sort_key": [definition["id"], subject["enumeration_ordinal"], subject["id"]],
                    })
                    continue
                registered_evaluator = structured_plan["subject_evaluator"]
                if (result["evaluator_key"], result["evaluator_version"]) != (
                    registered_evaluator["evaluator_key"], registered_evaluator["evaluator_version"]
                ):
                    incompatible = f"subject result {result['id']} evaluator differs from the registered plan"
                    continue
                inputs.append({
                    "constraint_definition_id": definition["id"], "constraint_id": constraint["id"],
                    "experiment_id": experiment["id"], "subject_id": subject["id"],
                    "subject_kind": subject["subject_kind"], "experiment_track_id": subject["experiment_track_id"],
                    "governed_field": subject["governed_field"], "subject_result_id": result["id"],
                    "status": result["status"], "measurements": subject["measurements"],
                    "sort_key": [definition["id"], subject["enumeration_ordinal"], subject["id"]],
                })
        projection = calculate_status_rate(plan, context, inputs, missing, incompatible_reason=incompatible)
        projection["source_reason_codes"] = sorted({
            str(item["source_reason_code"]) for item in inputs
            if item.get("source_reason_code")
        })
        if plan["calculator_key"] == "outcome.subject_status_rate":
            projection.update(
                authorized_subject_kinds=plan["subject_kinds"],
                subject_interpretation=plan["subject_interpretation"],
                subject_result_ids=sorted(item["subject_result_id"] for item in inputs),
                subject_identities=[{
                    "subject_id": item["subject_id"], "subject_kind": item["subject_kind"],
                    "experiment_track_id": item["experiment_track_id"], "governed_field": item["governed_field"],
                } for item in sorted(inputs, key=lambda row: tuple(row["sort_key"]))],
                contributing_constraint_definition_ids=sorted({
                    item["constraint_definition_id"] for item in projection["contributing_inputs"]
                }),
            )
        return projection

    def calculate_registered_run_outcomes(
        self, study_id_or_key: int | str, version: int, planned_run_id: int
    ) -> list[dict[str, object]]:
        protocol = self.get_protocol_version(study_id_or_key, version)
        if protocol is None or protocol["execution_contract"] is None:
            raise ValueError("registered calculator execution is unavailable for this protocol")
        return [
            self.calculate_registered_outcome(study_id_or_key, version, planned_run_id, plan["id"])
            for plan in protocol["execution_contract"]["outcome_calculation_plans"]
        ]

    def calculate_registered_analysis(
        self, study_id_or_key: int | str, version: int, analysis_plan_id: int,
        *, _protocol: dict[str, object] | None = None,
        _outcome_cache: dict[tuple[int, int], dict[str, object]] | None = None,
        _experiment_cache: dict[int, dict[str, object] | None] | None = None,
        _structured_cache: dict[int, dict[str, object] | None] | None = None,
    ) -> dict[str, object]:
        protocol = _protocol or self.get_protocol_version(study_id_or_key, version)
        if protocol is None or protocol["execution_contract"] is None:
            raise ValueError("LEGACY_EXECUTION protocol has no registered calculator contract")
        contract = protocol["execution_contract"]
        plan = next((item for item in contract["analysis_calculation_plans"] if item["id"] == analysis_plan_id), None)
        if plan is None:
            raise ValueError("analysis plan must belong to the registered protocol version")
        analysis = next(item for item in protocol["analysis_definitions"] if item["analysis_key"] == plan["analysis_key"])
        outcome_plan = next(item for item in contract["outcome_calculation_plans"] if item["outcome_key"] == analysis["outcome_key"])
        run_outcomes = {}
        for run in protocol["planned_runs"]:
            cache_key = (int(run["id"]), int(outcome_plan["id"]))
            if _outcome_cache is not None and cache_key in _outcome_cache:
                run_outcomes[run["id"]] = _outcome_cache[cache_key]
                continue
            calculated = self.calculate_registered_outcome(
                study_id_or_key, version, run["id"], outcome_plan["id"],
                _protocol=protocol,
                _experiment_cache=_experiment_cache,
                _structured_cache=_structured_cache,
            )
            run_outcomes[run["id"]] = calculated
            if _outcome_cache is not None:
                _outcome_cache[cache_key] = calculated
        return calculate_paired_difference(
            {**plan, "outcome_key": analysis["outcome_key"]}, protocol, run_outcomes,
            available=self._calculator_executor.analysis_available(plan),
        )

    def list_studies(self) -> list[dict[str, object]]:
        return self._read_query(self._studies.list_studies)

    def classify_evaluation_instrumentation(
        self, constraint_id: int
    ) -> dict[str, object] | None:
        return self._read_query(
            self._studies.classify_evaluation_instrumentation, constraint_id
        )

    def get_structured_constraint_evaluation(
        self, constraint_id: int
    ) -> dict[str, object] | None:
        return self._read_query(
            self._studies.get_structured_constraint_evaluation, constraint_id
        )

    def get_evaluation_provenance(
        self, constraint_id: int
    ) -> dict[str, object] | None:
        return self._read_query(self._studies.get_evaluation_provenance, constraint_id)

    def enumerate_evaluation_subjects(self, constraint_id: int) -> list[dict[str, object]]:
        context = self._structured_context(constraint_id)
        return enumerate_structured_subjects(
            context["plan"], context["experiment"], constraint_id,
            self._evaluator_registry,
        )

    def validate_structured_measurements(
        self, constraint_id: int, measurements: list[dict[str, object]]
    ) -> dict[str, object]:
        context = self._structured_context(constraint_id)
        subjects = enumerate_structured_subjects(
            context["plan"], context["experiment"], constraint_id,
            self._evaluator_registry,
        )
        return validate_measurements(context["plan"], subjects, measurements, context["experiment"])

    def calculate_subject_results(
        self, constraint_id: int, measurements: list[dict[str, object]]
    ) -> list[dict[str, object]]:
        context = self._structured_context(constraint_id)
        subjects = enumerate_structured_subjects(
            context["plan"], context["experiment"], constraint_id,
            self._evaluator_registry,
        )
        validation = validate_measurements(context["plan"], subjects, measurements, context["experiment"])
        if not validation["valid"]:
            raise ValueError(f"structured measurements are incomplete or invalid: {validation['issues']}")
        return calculate_structured_subjects(
            context["plan"], subjects, validation["measurements"], self._evaluator_registry
        )

    def calculate_aggregate_constraint_result(
        self, constraint_id: int, subject_results: list[dict[str, object]],
        *, supplied_aggregate_status: str | None = None,
    ) -> dict[str, object]:
        context = self._structured_context(constraint_id)
        return calculate_structured_aggregate(
            context["plan"], subject_results,
            supplied_aggregate_status=supplied_aggregate_status,
            registry=self._evaluator_registry,
        )

    def validate_structured_evaluation_completeness(
        self, constraint_id: int, measurements: list[dict[str, object]],
        *, supplied_aggregate_status: str | None = None,
    ) -> dict[str, object]:
        context = self._structured_context(constraint_id)
        return evaluate_structured_constraint(
            context["plan"], context["experiment"], constraint_id, measurements,
            supplied_aggregate_status=supplied_aggregate_status,
            registry=self._evaluator_registry,
        )

    def _structured_context(self, constraint_id: int) -> dict[str, object]:
        context = self._read_query(
            self._studies.get_structured_constraint_context, constraint_id
        )
        if context is None:
            raise ValueError(f"constraint not found: {constraint_id}")
        if context["plan"] is None:
            raise ValueError("constraint is LEGACY_AGGREGATE_ONLY")
        return context

    def evaluate_study(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        protocol = self.get_protocol_version(study_id_or_key, version)
        if protocol is None:
            return None
        classification = self.classify_study_execution(study_id_or_key, version)
        if classification is None:
            return None
        execution_classification = classification["execution_classification"]
        if execution_classification == "LEGACY_EXECUTION":
            evaluation = evaluate_registered_study(protocol, self.get_experiment)
            evaluation["execution_classification"] = "LEGACY_EXECUTION"
            return evaluation
        if execution_classification == "CALCULATOR_GOVERNED_EXECUTION":
            outcome_cache: dict[tuple[int, int], dict[str, object]] = {}
            experiment_cache: dict[int, dict[str, object] | None] = {}
            structured_cache: dict[int, dict[str, object] | None] = {}

            def calculate_outcome(planned_run_id: int, outcome_plan_id: int):
                cache_key = (planned_run_id, outcome_plan_id)
                if cache_key not in outcome_cache:
                    outcome_cache[cache_key] = self.calculate_registered_outcome(
                        study_id_or_key, version, planned_run_id, outcome_plan_id,
                        _protocol=protocol,
                        _experiment_cache=experiment_cache,
                        _structured_cache=structured_cache,
                    )
                return outcome_cache[cache_key]

            def read_experiment(experiment_id: int):
                if experiment_id not in experiment_cache:
                    experiment_cache[experiment_id] = self.get_experiment(experiment_id)
                return experiment_cache[experiment_id]

            return evaluate_calculator_governed_study(
                protocol,
                read_experiment,
                calculate_outcome,
                lambda analysis_plan_id: self.calculate_registered_analysis(
                    study_id_or_key, version, analysis_plan_id,
                    _protocol=protocol,
                    _outcome_cache=outcome_cache,
                    _experiment_cache=experiment_cache,
                    _structured_cache=structured_cache,
                ),
            )
        raise ValueError(
            f"unsupported study execution classification: {execution_classification}"
        )

    def explore_study(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        evaluation = self.evaluate_study(study_id_or_key, version)
        if evaluation is None or not evaluation["completion"]["realized_runs"]:
            return None
        return explore_study(
            evaluation, self.get_experiment, self.get_structured_constraint_evaluation,
            self.get_protocol_version(study_id_or_key, version),
        )

    def closeout_study(
        self, study_id_or_key: int | str, version: int, *, generated_at: str | None = None
    ) -> dict[str, object] | None:
        protocol = self.get_protocol_version(study_id_or_key, version)
        evaluation = self.evaluate_study(study_id_or_key, version)
        if protocol is None or evaluation is None:
            return None
        exploration = self.explore_study(study_id_or_key, version)
        return build_study_closeout(
            protocol, evaluation, exploration, self.get_experiment,
            generated_at=generated_at,
            repository_revision=current_repository_revision(),
        )

    def record_study_operational_attempt(
        self, planned_run_id: int, proposal: StudyOperationalAttemptInput
    ) -> dict[str, object]:
        _require_type(proposal, StudyOperationalAttemptInput)
        return self._studies.record_operational_attempt(planned_run_id, proposal)

    def ingest_planned_experiment(
        self, planned_run_id: int, proposal: ExperimentInput
    ) -> dict[str, object]:
        _require_type(proposal, ExperimentInput)
        return self._studies.realize_experiment(planned_run_id, proposal)

    def realize_structured_study_experiment(
        self,
        planned_run_id: int,
        experiment_input: ExperimentInput,
        structured_evaluation_input: StructuredStudyEvaluationInput,
    ) -> dict[str, object]:
        _require_type(experiment_input, ExperimentInput)
        _require_type(structured_evaluation_input, StructuredStudyEvaluationInput)
        return self._studies.realize_structured_experiment(
            planned_run_id, experiment_input, structured_evaluation_input
        )

    def prepare_structured_evaluation_worksheet(
        self, planned_run_id: int, experiment_input: ExperimentInput
    ) -> dict[str, object]:
        """Enumerate frozen subjects against an unpersisted Experiment draft."""
        _require_type(experiment_input, ExperimentInput)
        context = self._read_query(
            self._studies.get_planned_run_evaluation_context, planned_run_id
        )
        if context is None:
            raise ValueError(f"planned run not found: {planned_run_id}")
        experiment = self._structured_draft_projection(experiment_input)
        constraints = []
        for definition in context["constraint_definitions"]:
            plan = definition.get("structured_evaluation_plan")
            if plan is None:
                continue
            subjects = enumerate_structured_subjects(
                plan, experiment, definition["id"], self._evaluator_registry
            )
            prepared = validate_measurements(plan, subjects, [], experiment)
            unique_target = (
                plan["aggregate_evaluator"]["evaluator_key"] == "aggregate.unique_selected_subject"
                and plan["aggregate_evaluator"]["evaluator_version"] == "1"
            )
            selection_state = (
                "TARGET_ABSENT" if unique_target and not subjects else
                "TARGET_AMBIGUOUS" if unique_target and len(subjects) > 1 else
                "TARGET_FOUND" if unique_target else "ORDINARY_SUBJECT_SET"
            )
            constraints.append({
                "definition": definition,
                "subjects": [self._worksheet_subject(item, experiment) for item in subjects],
                "selection_state": selection_state,
                "derived_measurements": [
                    row for row in prepared["measurements"]
                    if row["authority_kind"] == "STRUCTURAL_DERIVATION"
                ],
            })
        return {**context, "constraints": constraints}

    def preview_structured_study_evaluation(
        self, planned_run_id: int, experiment_input: ExperimentInput,
        structured_input: StructuredStudyEvaluationInput,
    ) -> dict[str, object]:
        """Calculate a disposable P7C preview; no governed rows are created."""
        worksheet = self.prepare_structured_evaluation_worksheet(
            planned_run_id, experiment_input
        )
        experiment = self._structured_draft_projection(experiment_input)
        submitted = {
            item.study_constraint_definition_id: item for item in structured_input.constraints
        }
        results = []
        for item in worksheet["constraints"]:
            definition = item["definition"]
            payload = submitted.get(definition["id"])
            if payload is None:
                results.append({"study_constraint_definition_id": definition["id"], "complete": False,
                                "issues": [{"code": "STRUCTURED_INPUT_MISSING", "message": "structured constraint input is absent"}],
                                "subjects": item["subjects"], "subject_results": [], "aggregate_constraint_result": None})
                continue
            expected = enumerate_structured_subjects(
                definition["structured_evaluation_plan"], experiment, definition["id"],
                self._evaluator_registry,
            )
            expected_by_ordinal = {row["enumeration_ordinal"]: row for row in expected}
            issues = []
            measurements = []
            if len(payload.subjects) != len(expected):
                issues.append({"code": "SUBJECT_SET_MISMATCH", "message": "submitted subjects differ from frozen enumeration"})
            for subject in payload.subjects:
                frozen = expected_by_ordinal.get(subject.enumeration_ordinal)
                expected_track_ordinal = frozen["experiment_track_id"] if frozen is not None else None
                if (frozen is None or subject.subject_kind.value != frozen["subject_kind"]
                        or subject.track_observed_ordinal != expected_track_ordinal
                        or (None if subject.governed_field is None else subject.governed_field.value) != frozen["governed_field"]):
                    issues.append({"code": "SUBJECT_SET_MISMATCH", "message": "submitted subject differs from frozen enumeration"})
                    continue
                for measurement in subject.measurements:
                    row = measurement.model_dump(mode="python")
                    row["subject_key"] = frozen["subject_key"]
                    row["authority_kind"] = measurement.authority_kind.value
                    row["evidence"] = [e.model_dump(mode="python") for e in measurement.evidence]
                    measurements.append(row)
                    issues.extend(self._validate_draft_measurement_evidence(
                        experiment_input, subject.track_observed_ordinal, measurement
                    ))
                    issues.extend(self._validate_draft_direct_field_value(
                        experiment_input, subject, measurement,
                        definition["structured_evaluation_plan"],
                    ))
            if issues:
                calculated = {"complete": False, "issues": issues, "subjects": item["subjects"], "subject_results": [], "aggregate_constraint_result": None}
            else:
                calculated = evaluate_structured_constraint(
                    definition["structured_evaluation_plan"], experiment, definition["id"], measurements,
                    supplied_aggregate_status=payload.asserted_aggregate_status,
                    registry=self._evaluator_registry,
                )
                calculated["subjects"] = item["subjects"]
            results.append({"study_constraint_definition_id": definition["id"], **calculated})
        expected_ids = {row["definition"]["id"] for row in worksheet["constraints"]}
        complete = bool(expected_ids) and set(submitted) == expected_ids and all(row["complete"] for row in results)
        return {"complete": complete, "constraints": results}

    @staticmethod
    def _validate_draft_measurement_evidence(experiment, track_ordinal, measurement):
        issues = []
        source_keys = {item.source_key for item in experiment.evidence_sources}
        for evidence in measurement.evidence:
            if evidence.source_key not in source_keys:
                issues.append({"code": "CROSS_EXPERIMENT_EVIDENCE", "message": f"measurement source is not owned by this Experiment: {evidence.source_key}"})
                continue
            if evidence.evidence_link_id is not None:
                issues.append({"code": "DRAFT_EVIDENCE_LINK_ID_INVALID", "message": "unpersisted Experiment drafts must use exact field locators, not EvidenceLink IDs"})
                continue
            if evidence.evidence_link_field is None:
                continue
            links = experiment.evidence if track_ordinal is None else experiment.tracks[track_ordinal - 1].evidence
            matches = [item for item in links if item.source_key == evidence.source_key and item.field_name == evidence.evidence_link_field]
            if len(matches) != 1:
                issues.append({"code": "EVIDENCE_LINK_NOT_EXACT", "message": "measurement evidence must resolve to exactly one draft field link"})
        return issues

    @staticmethod
    def _validate_draft_direct_field_value(experiment, subject, measurement, plan):
        if measurement.authority_kind.value != "DIRECT_OBSERVATION" or subject.governed_field is None or measurement.value_type == "UNAVAILABLE":
            return []
        definition = next(item for item in plan["measurement_definitions"] if item["measurement_key"] == measurement.measurement_key)
        fields = {
            "display_title": "title", "display_artist": "artist",
            "explicit_flag": "explicit_flag", "version_or_remaster_text": "version_or_remaster_text",
        }
        value_columns = {
            "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
            "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
        }
        track = experiment.tracks[subject.track_observed_ordinal - 1]
        governed = getattr(track, fields[subject.governed_field.value])
        supplied = getattr(measurement, value_columns[definition["value_type"]])
        if supplied != governed:
            return [{"code": "DIRECT_VALUE_CONTRADICTS_FIELD", "message": "direct-observation value differs from the governed placement field"}]
        return []

    def get_structured_run_evaluation(
        self, planned_run_id: int
    ) -> dict[str, object] | None:
        context = self._read_query(
            self._studies.get_planned_run_evaluation_context, planned_run_id
        )
        if context is None or context["run"].get("realization") is None:
            return None
        experiment_id = context["run"]["realization"].get("experiment_id")
        if experiment_id is None:
            return {**context, "experiment": None, "constraints": []}
        experiment = self.get_experiment(int(experiment_id))
        rows = []
        for constraint in experiment.get("constraints", []):
            if constraint.get("study_constraint_definition_id") is None:
                continue
            definition = next((item for item in context["constraint_definitions"] if item["id"] == constraint["study_constraint_definition_id"]), None)
            if definition is None or definition.get("structured_evaluation_plan") is None:
                continue
            rows.append({"definition": definition, "aggregate": constraint.get("result"),
                         "structured": self.get_structured_constraint_evaluation(constraint["id"])})
        return {**context, "experiment": experiment, "constraints": rows}

    @staticmethod
    def _structured_draft_projection(draft: ExperimentInput) -> dict[str, object]:
        projection = draft.model_dump(mode="json")
        projection["id"] = 0
        projection["tracks"] = [
            {**track, "id": ordinal, "observed_ordinal": ordinal}
            for ordinal, track in enumerate(projection.get("tracks", []), start=1)
        ]
        return projection

    @staticmethod
    def _worksheet_subject(subject: dict[str, object], experiment: dict[str, object]) -> dict[str, object]:
        track = next((row for row in experiment["tracks"] if row["id"] == subject["experiment_track_id"]), None)
        return {**subject, "track_observed_ordinal": None if track is None else track["observed_ordinal"],
                "displayed_context": None if track is None else {
                    "title": track.get("title"), "artist": track.get("artist"),
                    "version_or_remaster_text": track.get("version_or_remaster_text"),
                    "explicit_flag": track.get("explicit_flag"),
                }}

    def record_planned_generation_failure(
        self,
        planned_run_id: int,
        proposal: GenerationFailureInput,
        disposition: StudyRunDisposition,
    ) -> dict[str, object]:
        _require_type(proposal, GenerationFailureInput)
        return self._studies.realize_generation_failure(
            planned_run_id, proposal, disposition
        )

    @staticmethod
    def verify_experiment_evidence(
        proposal: ExperimentInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    @staticmethod
    def verify_persisted_artifact_evidence(
        proposal: PersistedPlaylistArtifactInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    def ingest_experiment(self, proposal: ExperimentInput) -> IngestedRecord:
        _require_type(proposal, ExperimentInput)
        record_id = self._repository.insert_experiment(proposal)
        record = self._read_experiment(record_id)
        if record is None:
            raise RuntimeError("inserted experiment could not be read back")
        return IngestedRecord("experiment", record_id, record)

    def ingest_persisted_artifact(
        self, proposal: PersistedPlaylistArtifactInput
    ) -> IngestedRecord:
        _require_type(proposal, PersistedPlaylistArtifactInput)
        record_id = self._repository.insert_persisted_artifact(proposal)
        record = self._read_persisted_artifact(record_id)
        if record is None:
            raise RuntimeError("inserted persisted artifact could not be read back")
        return IngestedRecord("persisted_artifact", record_id, record)

    def get_experiment(self, record_id: int) -> dict[str, object] | None:
        return self._read_experiment(record_id)

    def get_persisted_artifact(self, record_id: int) -> dict[str, object] | None:
        return self._read_persisted_artifact(record_id)

    def query_experiments(
        self, *, assessment: str | None = None,
        assessment_outcome: str | None = None,
        constraint_status: str | None = None,
        saved: bool | None = None,
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.query_experiments,
            assessment=assessment,
            assessment_outcome=assessment_outcome,
            constraint_status=constraint_status,
            saved=saved,
        )

    def recurring_tracks(self, limit: int = 20) -> list[dict[str, object]]:
        return self._read_query(self._repository.recurring_tracks, limit)

    def recurring_artists(self, limit: int = 20) -> list[dict[str, object]]:
        return self._read_query(self._repository.recurring_artists, limit)

    def track_occurrences(
        self, canonical_track_id: int
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.track_occurrences, canonical_track_id
        )

    def artist_occurrences(
        self, canonical_artist: str
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.artist_occurrences, canonical_artist
        )

    def track_profile(
        self, canonical_track_id: int
    ) -> dict[str, object] | None:
        occurrences = self.track_occurrences(canonical_track_id)
        if not occurrences:
            return None
        summary = _position_summary(occurrences)
        first = occurrences[0]
        return {
            "canonical_track_id": canonical_track_id,
            "canonical_title": first["canonical_title"],
            "canonical_artist": first["canonical_artist"],
            "experiment_count": len({item["experiment_id"] for item in occurrences}),
            "appearance_count": len(occurrences),
            **summary,
            "occurrences": occurrences,
        }

    def artist_profile(
        self, canonical_artist: str
    ) -> dict[str, object] | None:
        occurrences = self.artist_occurrences(canonical_artist)
        if not occurrences:
            return None
        summary = _position_summary(occurrences, position_key="positions")
        return {
            "canonical_artist": canonical_artist,
            "experiment_count": len({item["experiment_id"] for item in occurrences}),
            "appearance_count": len(occurrences),
            **summary,
            "occurrences": occurrences,
        }

    def recurring_track_profiles(self, limit: int = 20) -> list[dict[str, object]]:
        profiles: list[dict[str, object]] = []
        for item in self.recurring_tracks(limit):
            profile = self.track_profile(int(item["id"]))
            if profile is not None:
                profiles.append(profile)
        return profiles

    def recurring_artist_profiles(self, limit: int = 20) -> list[dict[str, object]]:
        profiles: list[dict[str, object]] = []
        for item in self.recurring_artists(limit):
            profile = self.artist_profile(str(item["canonical_artist"]))
            if profile is not None:
                profiles.append(profile)
        return profiles

    def compare_experiments(
        self, experiment_id_a: int, experiment_id_b: int
    ) -> dict[str, object] | None:
        experiment_a = self.get_experiment(experiment_id_a)
        experiment_b = self.get_experiment(experiment_id_b)
        if experiment_a is None or experiment_b is None:
            return None
        tracks_a = {
            int(item["track_id"])
            for item in experiment_a["tracks"]
            if item["track_id"] is not None
        }
        tracks_b = {
            int(item["track_id"])
            for item in experiment_b["tracks"]
            if item["track_id"] is not None
        }
        artists_a = {
            str(item["canonical_artist"])
            for item in experiment_a["tracks"]
            if item["track_id"] is not None
        }
        artists_b = {
            str(item["canonical_artist"])
            for item in experiment_b["tracks"]
            if item["track_id"] is not None
        }
        shared_tracks = sorted(tracks_a & tracks_b)
        shared_artists = sorted(artists_a & artists_b)
        return {
            "experiment_id_a": experiment_id_a,
            "experiment_id_b": experiment_id_b,
            "generated_title_a": experiment_a["generated_title"],
            "generated_title_b": experiment_b["generated_title"],
            "track_count_a": len(experiment_a["tracks"]),
            "track_count_b": len(experiment_b["tracks"]),
            "shared_canonical_track_ids": shared_tracks,
            "shared_canonical_track_count": len(shared_tracks),
            "track_overlap_ratio_a": _ratio(len(shared_tracks), len(tracks_a)),
            "track_overlap_ratio_b": _ratio(len(shared_tracks), len(tracks_b)),
            "shared_canonical_artists": shared_artists,
            "shared_canonical_artist_count": len(shared_artists),
            "artist_overlap_ratio_a": _ratio(len(shared_artists), len(artists_a)),
            "artist_overlap_ratio_b": _ratio(len(shared_artists), len(artists_b)),
        }

    def track_cooccurrences(
        self, canonical_track_id: int, limit: int = 20
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        track_sets, track_appearances, catalog = _track_corpus(experiments)
        source_experiments = track_sets.get(canonical_track_id, set())
        results: list[dict[str, object]] = []
        for candidate_id, candidate_experiments in track_sets.items():
            if candidate_id == canonical_track_id:
                continue
            shared = sorted(source_experiments & candidate_experiments)
            if not shared:
                continue
            candidate = catalog[candidate_id]
            results.append({
                "canonical_track_id": candidate_id,
                "canonical_title": candidate["canonical_title"],
                "canonical_artist": candidate["canonical_artist"],
                "experiment_count_together": len(shared),
                "appearance_count_together": sum(
                    track_appearances[(experiment_id, candidate_id)]
                    for experiment_id in shared
                ),
                "source_track_experiment_count": len(source_experiments),
                "candidate_track_experiment_count": len(candidate_experiments),
                "shared_experiment_ids": shared,
                "shared_experiment_count": len(shared),
                "source_support_ratio": _ratio(len(shared), len(source_experiments)),
                "candidate_support_ratio": _ratio(len(shared), len(candidate_experiments)),
            })
        return sorted(
            results,
            key=lambda item: (-int(item["shared_experiment_count"]), int(item["canonical_track_id"])),
        )[:limit]

    def artist_cooccurrences(
        self, canonical_artist: str, limit: int = 20
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        artist_sets = _artist_experiment_sets(experiments)
        source_experiments = artist_sets.get(canonical_artist, set())
        results: list[dict[str, object]] = []
        for candidate, candidate_experiments in artist_sets.items():
            if candidate == canonical_artist:
                continue
            shared = sorted(source_experiments & candidate_experiments)
            if not shared:
                continue
            results.append({
                "canonical_artist": candidate,
                "experiment_count_together": len(shared),
                "source_artist_experiment_count": len(source_experiments),
                "candidate_artist_experiment_count": len(candidate_experiments),
                "shared_experiment_ids": shared,
                "shared_experiment_count": len(shared),
                "source_support_ratio": _ratio(len(shared), len(source_experiments)),
                "candidate_support_ratio": _ratio(len(shared), len(candidate_experiments)),
            })
        return sorted(
            results,
            key=lambda item: (-int(item["shared_experiment_count"]), str(item["canonical_artist"])),
        )[:limit]

    def track_pair_occurrences(
        self, canonical_track_id_a: int, canonical_track_id_b: int
    ) -> list[dict[str, object]]:
        if canonical_track_id_a == canonical_track_id_b:
            return []
        results: list[dict[str, object]] = []
        for experiment in self._all_experiments():
            placements_a = [
                item for item in experiment["tracks"]
                if item["track_id"] == canonical_track_id_a
            ]
            placements_b = [
                item for item in experiment["tracks"]
                if item["track_id"] == canonical_track_id_b
            ]
            if not placements_a or not placements_b:
                continue
            length = _experiment_tracklist_length(experiment)
            position_a = _single_position(placements_a)
            position_b = _single_position(placements_b)
            normalized_a = _normalized_position(position_a, length)
            normalized_b = _normalized_position(position_b, length)
            results.append({
                "experiment_id": experiment["id"],
                "generated_title": experiment["generated_title"],
                "prompt_title": experiment["prompt_title"],
                "tracklist_length": length,
                "track_a_absolute_position": position_a,
                "track_b_absolute_position": position_b,
                "track_a_absolute_positions": _known_positions(placements_a),
                "track_b_absolute_positions": _known_positions(placements_b),
                "absolute_position_distance": (
                    abs(position_a - position_b)
                    if position_a is not None and position_b is not None else None
                ),
                "track_a_normalized_position": normalized_a,
                "track_b_normalized_position": normalized_b,
                "normalized_distance": (
                    abs(normalized_a - normalized_b)
                    if normalized_a is not None and normalized_b is not None else None
                ),
            })
        return results

    def artist_pair_occurrences(
        self, canonical_artist_a: str, canonical_artist_b: str
    ) -> list[dict[str, object]]:
        if canonical_artist_a == canonical_artist_b:
            return []
        results: list[dict[str, object]] = []
        for experiment in self._all_experiments():
            placements_a = _artist_placements(experiment, canonical_artist_a)
            placements_b = _artist_placements(experiment, canonical_artist_b)
            if not placements_a or not placements_b:
                continue
            results.append({
                "experiment_id": experiment["id"],
                "generated_title": experiment["generated_title"],
                "prompt_title": experiment["prompt_title"],
                "tracklist_length": _experiment_tracklist_length(experiment),
                "artist_a_placements": placements_a,
                "artist_b_placements": placements_b,
            })
        return results

    def recurring_track_pairs(
        self, limit: int = 20, minimum_shared_experiments: int = 2
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        track_sets, _appearances, catalog = _track_corpus(experiments)
        results: list[dict[str, object]] = []
        for track_a, track_b in itertools.combinations(sorted(track_sets), 2):
            shared = sorted(track_sets[track_a] & track_sets[track_b])
            if len(shared) < minimum_shared_experiments:
                continue
            item_a = catalog[track_a]
            item_b = catalog[track_b]
            results.append({
                "track_a_canonical_id": track_a,
                "track_a_canonical_title": item_a["canonical_title"],
                "track_a_canonical_artist": item_a["canonical_artist"],
                "track_b_canonical_id": track_b,
                "track_b_canonical_title": item_b["canonical_title"],
                "track_b_canonical_artist": item_b["canonical_artist"],
                "shared_experiment_count": len(shared),
                "shared_experiment_ids": shared,
                "track_a_experiment_count": len(track_sets[track_a]),
                "track_b_experiment_count": len(track_sets[track_b]),
                "track_a_support_ratio": _ratio(len(shared), len(track_sets[track_a])),
                "track_b_support_ratio": _ratio(len(shared), len(track_sets[track_b])),
            })
        return sorted(results, key=lambda item: (
            -int(item["shared_experiment_count"]),
            int(item["track_a_canonical_id"]),
            int(item["track_b_canonical_id"]),
        ))[:limit]

    def recurring_artist_pairs(
        self, limit: int = 20, minimum_shared_experiments: int = 2
    ) -> list[dict[str, object]]:
        artist_sets = _artist_experiment_sets(self._all_experiments())
        results: list[dict[str, object]] = []
        for artist_a, artist_b in itertools.combinations(sorted(artist_sets), 2):
            shared = sorted(artist_sets[artist_a] & artist_sets[artist_b])
            if len(shared) < minimum_shared_experiments:
                continue
            results.append({
                "artist_a": artist_a,
                "artist_b": artist_b,
                "shared_experiment_count": len(shared),
                "shared_experiment_ids": shared,
                "artist_a_experiment_count": len(artist_sets[artist_a]),
                "artist_b_experiment_count": len(artist_sets[artist_b]),
                "artist_a_support_ratio": _ratio(len(shared), len(artist_sets[artist_a])),
                "artist_b_support_ratio": _ratio(len(shared), len(artist_sets[artist_b])),
            })
        return sorted(results, key=lambda item: (
            -int(item["shared_experiment_count"]),
            str(item["artist_a"]),
            str(item["artist_b"]),
        ))[:limit]

    def _all_experiments(self) -> list[dict[str, object]]:
        record_ids = self._read_query(self._repository.list_experiment_ids)
        return [
            experiment
            for record_id in record_ids
            if (experiment := self.get_experiment(int(record_id))) is not None
        ]

    def _read_experiment(self, record_id: int) -> dict[str, object] | None:
        return self._read_projection(self._repository.get_experiment, record_id)

    def _read_persisted_artifact(self, record_id: int) -> dict[str, object] | None:
        return self._read_projection(self._repository.get_persisted_artifact, record_id)

    def _read_projection(
        self,
        reader: Callable[[int], dict[str, object] | None],
        record_id: int,
    ) -> dict[str, object] | None:
        session = self._repository.session
        transaction_already_active = session.in_transaction()
        try:
            return reader(record_id)
        finally:
            if not transaction_already_active and session.in_transaction():
                session.rollback()

    def _read_query(
        self,
        reader: Callable[..., QueryValue],
        *args: Any,
        **kwargs: Any,
    ) -> QueryValue:
        session = self._repository.session
        transaction_already_active = session.in_transaction()
        try:
            return reader(*args, **kwargs)
        finally:
            if not transaction_already_active and session.in_transaction():
                session.rollback()


def initialize_research_store(database_url: str | None = None) -> int:
    """Prepare the isolated research store without exposing its persistence objects."""
    return migrate_research_database(make_research_engine(database_url))


@contextmanager
def open_research_store_service(
    database_url: str | None = None,
) -> Iterator[ResearchStoreService]:
    """Open one service scope while keeping repository and session wiring private."""
    engine = make_research_engine(database_url)
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        yield ResearchStoreService(ResearchRepository(session))


def _validate(model_type: type[ValidatedValue], proposal: object) -> ValidationResult[ValidatedValue]:
    try:
        value = model_type.model_validate(proposal)  # type: ignore[attr-defined]
    except ValidationError as exc:
        issues = tuple(
            ValidationIssue(
                location=tuple(item["loc"]),
                message=item["msg"],
                issue_type=item["type"],
            )
            for item in exc.errors()
        )
        return ValidationResult(value=None, issues=issues)
    return ValidationResult(value=value)


def _verify_sources(sources: list[EvidenceSourceInput]) -> EvidenceVerificationResult:
    issues: list[EvidenceVerificationIssue] = []
    for source in sources:
        if source.local_path is None:
            continue
        path = Path(source.local_path)
        if not path.is_file():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="file_not_found",
                message=f"local evidence file not found: {path}",
            ))
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != source.sha256.lower():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="checksum_mismatch",
                message=f"evidence checksum mismatch: {path}",
            ))
    return EvidenceVerificationResult(tuple(issues))


def _require_type(value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"ingestion requires a validated {expected.__name__}")


def _position_summary(
    occurrences: list[dict[str, object]], *, position_key: str = "absolute_positions"
) -> dict[str, object]:
    positions = [
        int(item["absolute_position"])
        for item in occurrences
        if item["absolute_position"] is not None
    ]
    quartiles = [0, 0, 0, 0]
    for item in occurrences:
        position = item["absolute_position"]
        length = item["tracklist_length"]
        if position is None or length is None or int(length) <= 0:
            continue
        quartile = min(4, ((int(position) - 1) * 4 // int(length)) + 1)
        quartiles[quartile - 1] += 1
    return {
        position_key: positions,
        "minimum_position": min(positions) if positions else None,
        "maximum_position": max(positions) if positions else None,
        "mean_position": statistics.fmean(positions) if positions else None,
        "median_position": statistics.median(positions) if positions else None,
        "position_standard_deviation": statistics.pstdev(positions) if positions else None,
        "first_quartile_count": quartiles[0],
        "second_quartile_count": quartiles[1],
        "third_quartile_count": quartiles[2],
        "fourth_quartile_count": quartiles[3],
        "unknown_position_count": len(occurrences) - len(positions),
    }


def _ratio(shared_count: int, total_count: int) -> float:
    return shared_count / total_count if total_count else 0.0


def _track_corpus(
    experiments: list[dict[str, object]],
) -> tuple[
    dict[int, set[int]],
    dict[tuple[int, int], int],
    dict[int, dict[str, object]],
]:
    experiment_sets: dict[int, set[int]] = {}
    appearances: dict[tuple[int, int], int] = {}
    catalog: dict[int, dict[str, object]] = {}
    for experiment in experiments:
        experiment_id = int(experiment["id"])
        for placement in experiment["tracks"]:
            track_id = placement["track_id"]
            if track_id is None:
                continue
            canonical_track_id = int(track_id)
            experiment_sets.setdefault(canonical_track_id, set()).add(experiment_id)
            key = (experiment_id, canonical_track_id)
            appearances[key] = appearances.get(key, 0) + 1
            catalog[canonical_track_id] = {
                "canonical_title": placement["canonical_title"],
                "canonical_artist": placement["canonical_artist"],
            }
    return experiment_sets, appearances, catalog


def _artist_experiment_sets(
    experiments: list[dict[str, object]],
) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for experiment in experiments:
        experiment_id = int(experiment["id"])
        for placement in experiment["tracks"]:
            if placement["track_id"] is None:
                continue
            artist = str(placement["canonical_artist"])
            result.setdefault(artist, set()).add(experiment_id)
    return result


def _experiment_tracklist_length(experiment: dict[str, object]) -> int:
    generated = experiment["generated_track_count"]
    return int(generated) if generated is not None else len(experiment["tracks"])


def _known_positions(placements: list[dict[str, object]]) -> list[int]:
    return [
        int(item["absolute_position"])
        for item in placements
        if item["absolute_position"] is not None
    ]


def _single_position(placements: list[dict[str, object]]) -> int | None:
    positions = _known_positions(placements)
    return positions[0] if len(placements) == 1 and len(positions) == 1 else None


def _normalized_position(position: int | None, tracklist_length: int) -> float | None:
    if position is None or tracklist_length <= 0:
        return None
    return position / tracklist_length


def _artist_placements(
    experiment: dict[str, object], canonical_artist: str
) -> list[dict[str, object]]:
    return [
        {
            "canonical_track_id": item["track_id"],
            "canonical_title": item["canonical_title"],
            "canonical_artist": item["canonical_artist"],
            "display_title": item["title"],
            "display_artist": item["artist"],
            "observed_ordinal": item["observed_ordinal"],
            "absolute_position": item["absolute_position"],
        }
        for item in experiment["tracks"]
        if item["track_id"] is not None
        and item["canonical_artist"] == canonical_artist
    ]

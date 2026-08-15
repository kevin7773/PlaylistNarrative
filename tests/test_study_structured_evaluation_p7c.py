from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest
from sqlalchemy import func, select

from playlist_narrative_engine.research_store.models import (
    Constraint,
    ConstraintEvaluationSubject,
    ConstraintEvaluationMeasurement,
    ConstraintEvaluationMeasurementEvidence,
    ConstraintSubjectResult,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
    EvaluatorIdentity,
    EvaluatorRole,
    ExecutableEvaluator,
    StudyEvaluatorRegistry,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    calculate_aggregate_constraint_result,
    calculate_subject_results,
    enumerate_evaluation_subjects,
    evaluate_structured_constraint,
    validate_structured_measurements,
)
from test_study_structured_evaluation_p7a import _document


def _reference(key: str) -> dict[str, str]:
    return {"evaluator_key": key, "evaluator_version": "1"}


def _plan(
    *, kind: str, field: str | None, subject_evaluator: str,
    value_type: str, authority: str = "DIRECT_OBSERVATION",
    parameters: list[dict[str, object]], aggregate: str = "aggregate.single_subject",
    evidence_required: bool = False, allow_partial: bool = False,
) -> dict[str, object]:
    return {
        "instrumentation_version": "1", "subject_kind": kind,
        "subject_field": field,
        "subject_selector": _reference("selector.run" if kind == "RUN" else "selector.all_placements"),
        "subject_evaluator": _reference(subject_evaluator),
        "aggregate_evaluator": _reference(aggregate),
        "require_complete_subject_set": True,
        "allow_partial_subject_status": allow_partial,
        "measurement_definitions": [{
            "id": 10, "measurement_key": "observed", "authority": authority,
            "value_type": value_type, "unit_key": None,
            "vocabulary_key": "terms" if value_type == "VOCABULARY_TERM" else None,
            "required": True, "evidence_required": evidence_required,
            "unavailable_policy": "MAY_BE_UNAVAILABLE",
            **({"derivation_key": "structural.placement_count", "derivation_version": "1"} if authority == "STRUCTURAL_DERIVATION" else {}),
        }],
        "parameters": parameters,
        "vocabulary_terms": (
            [{"vocabulary_key": "terms", "term_key": "allowed", "term_definition": "Allowed."},
             {"vocabulary_key": "terms", "term_key": "blocked", "term_definition": "Blocked."}]
            if value_type == "VOCABULARY_TERM" else []
        ),
    }


def _experiment(titles: list[str] = ()) -> dict[str, object]:
    return {
        "id": 7,
        "tracks": [
            {"id": 100 + index, "observed_ordinal": index, "display_title": title,
             "display_artist": f"Artist {index}", "explicit_flag": None}
            for index, title in enumerate(titles, start=1)
        ],
    }


def _measurement(subject_key: str, value_type: str, *, value=None, unavailable=False):
    row = {
        "id": 1, "subject_key": subject_key, "measurement_key": "observed",
        "authority_kind": "DIRECT_OBSERVATION",
        "value_type": "UNAVAILABLE" if unavailable else value_type,
        "boolean_value": None, "integer_value": None, "decimal_value": None,
        "text_value": None, "date_value": None, "vocabulary_term_key": None,
        "unavailable_reason": "not established" if unavailable else None,
        "evidence": [],
    }
    if not unavailable:
        column = {
            "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "TEXT": "text_value",
            "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
        }[value_type]
        row[column] = value
    return row


def _evaluate(plan, experiment, measurements):
    return evaluate_structured_constraint(plan, experiment, 42, measurements)


@pytest.mark.parametrize("value,expected", [(10, "PASS"), (9, "FAIL")])
def test_run_cardinality_is_deterministic_without_placement_subjects(value, expected) -> None:
    plan = _plan(
        kind="RUN", field=None, subject_evaluator="subject.integer_equals",
        value_type="INTEGER", authority="STRUCTURAL_DERIVATION",
        parameters=[{"parameter_key": "expected", "value_type": "INTEGER", "integer_value": 10}],
    )
    result = _evaluate(plan, _experiment([f"Track {index}" for index in range(value)]), [])
    assert [item["subject_kind"] for item in result["subjects"]] == ["RUN"]
    assert result["aggregate_constraint_result"]["status"] == expected


def test_unavailable_run_measurement_remains_unknown() -> None:
    plan = _plan(kind="RUN", field=None, subject_evaluator="subject.integer_equals", value_type="INTEGER", authority="DIRECT_OBSERVATION", parameters=[{"parameter_key": "expected", "value_type": "INTEGER", "integer_value": 10}])
    measurement = _measurement("RUN", "INTEGER", unavailable=True)
    assert _evaluate(plan, _experiment(), [measurement])["aggregate_constraint_result"]["status"] == "UNKNOWN"


def test_exact_standalone_lexical_token_examples() -> None:
    titles = ["Night Moves", "Nightbird", "One of These Nights", "Last Nite"]
    plan = _plan(
        kind="PLACEMENT_FIELD", field="display_title",
        subject_evaluator="subject.lexical_standalone_token", value_type="TEXT",
        parameters=[
            {"parameter_key": "token", "value_type": "TEXT", "text_value": "night"},
            {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": False},
            {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
            {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
            {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
        ], aggregate="aggregate.all_subjects_required",
    )
    subjects = enumerate_evaluation_subjects(plan, _experiment(titles), 42)
    measurements = [_measurement(subject["subject_key"], "TEXT", value=title) for subject, title in zip(subjects, titles)]
    result = _evaluate(plan, _experiment(titles), list(reversed(measurements)))
    assert [row["status"] for row in result["subject_results"]] == ["PASS", "FAIL", "FAIL", "FAIL"]
    assert result["aggregate_constraint_result"]["status"] == "PARTIAL"


@pytest.mark.parametrize("value,expected", [(False, "PASS"), (True, "FAIL")])
def test_displayed_boolean_expectation(value, expected) -> None:
    plan = _plan(kind="PLACEMENT_FIELD", field="explicit_flag", subject_evaluator="subject.boolean_equals", value_type="BOOLEAN", parameters=[{"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False}])
    subject = enumerate_evaluation_subjects(plan, _experiment(["Track"]), 42)[0]
    assert _evaluate(plan, _experiment(["Track"]), [_measurement(subject["subject_key"], "BOOLEAN", value=value)])["subject_results"][0]["status"] == expected


@pytest.mark.parametrize("value,expected", [(date(2020, 6, 1), "PASS"), (date(2021, 1, 1), "FAIL")])
def test_generic_inclusive_date_window(value, expected) -> None:
    plan = _plan(kind="EXPERIMENT_PLACEMENT", field=None, subject_evaluator="subject.date_inclusive_window", value_type="DATE", authority="EXTERNAL_FACT_VERIFICATION", parameters=[
        {"parameter_key": "start_date", "value_type": "DATE", "date_value": "2020-01-01"},
        {"parameter_key": "end_date", "value_type": "DATE", "date_value": "2020-12-31"},
    ])
    subject = enumerate_evaluation_subjects(plan, _experiment(["Track"]), 42)[0]
    measurement = _measurement(subject["subject_key"], "DATE", value=value)
    measurement["authority_kind"] = "EXTERNAL_FACT_VERIFICATION"
    assert _evaluate(plan, _experiment(["Track"]), [measurement])["subject_results"][0]["status"] == expected


def test_mixed_aggregate_mapping_and_contradiction_are_exact() -> None:
    plan = _plan(kind="PLACEMENT_FIELD", field="display_title", subject_evaluator="subject.boolean_equals", value_type="BOOLEAN", parameters=[
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": True},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ], aggregate="aggregate.all_subjects_required")
    subject_results = [{"status": "PASS"}, {"status": "FAIL"}]
    assert calculate_aggregate_constraint_result(plan, subject_results)["status"] == "PARTIAL"
    with pytest.raises(ValueError, match="contradicts"):
        calculate_aggregate_constraint_result(plan, subject_results, supplied_aggregate_status="PASS")


def test_completeness_reports_missing_evidence_and_measurements() -> None:
    plan = _plan(kind="PLACEMENT_FIELD", field="display_title", subject_evaluator="subject.boolean_equals", value_type="BOOLEAN", parameters=[{"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": True}], evidence_required=True)
    experiment = _experiment(["A", "B"])
    subject = enumerate_evaluation_subjects(plan, experiment, 42)[0]
    result = _evaluate(plan, experiment, [_measurement(subject["subject_key"], "BOOLEAN", value=True)])
    assert not result["complete"]
    assert {item["code"] for item in result["issues"]} == {"EVIDENCE_REQUIRED", "REQUIRED_MEASUREMENT_MISSING"}


def test_insertion_order_and_nonsemantic_measurement_ids_do_not_change_results() -> None:
    plan = _plan(kind="PLACEMENT_FIELD", field="explicit_flag", subject_evaluator="subject.boolean_equals", value_type="BOOLEAN", parameters=[
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ], aggregate="aggregate.all_subjects_required")
    experiment = _experiment(["A", "B"])
    subjects = enumerate_evaluation_subjects(plan, experiment, 42)
    left = [_measurement(subjects[0]["subject_key"], "BOOLEAN", value=False), _measurement(subjects[1]["subject_key"], "BOOLEAN", value=True)]
    right = deepcopy(list(reversed(left)))
    right[0]["id"], right[1]["id"] = 999, 888
    a, b = _evaluate(plan, experiment, left), _evaluate(plan, experiment, right)
    assert [(x["status"], x["reason_code"]) for x in a["subject_results"]] == [(x["status"], x["reason_code"]) for x in b["subject_results"]]
    assert a["aggregate_constraint_result"] == b["aggregate_constraint_result"]


def test_service_pipeline_is_read_only_and_legacy_constraints_are_not_evaluated(research_session) -> None:
    document = _document(structured=True)
    document["study_key"] = "P7C-RUN"
    definition = document["protocol"]["constraint_definitions"][0]
    definition["structured_evaluation_plan"] = {
        "instrumentation_version": "1", "subject_kind": "RUN",
        "subject_selector": _reference("selector.run"),
        "subject_evaluator": _reference("subject.integer_equals"),
        "aggregate_evaluator": _reference("aggregate.single_subject"),
        "require_complete_subject_set": True, "allow_partial_subject_status": False,
        "measurement_definitions": [{"measurement_key": "observed", "authority": "STRUCTURAL_DERIVATION", "value_type": "INTEGER", "required": True, "evidence_required": False, "derivation_key": "structural.placement_count", "derivation_version": "1", "unavailable_policy": "MUST_HAVE_VALUE"}],
        "parameters": [{"parameter_key": "expected", "value_type": "INTEGER", "integer_value": 10}],
    }
    service = ResearchStoreService(ResearchRepository(research_session))
    study = service.register_study(StudyRegistrationInput.model_validate(document))
    protocol = service.get_protocol_version(study["id"], 1)
    frozen = protocol["constraint_definitions"][0]
    experiment_id = service.ingest_experiment(ExperimentInput.model_validate({
        "source_system": "Maestro Beta", "tracks": [
            {"position": index, "title": f"Track {index}", "artist": f"Artist {index}"}
            for index in range(1, 11)
        ], "constraints": [{
            "study_constraint_definition_id": frozen["id"], "constraint_type": frozen["constraint_type"],
            "constraint_text": frozen["constraint_text"], "is_hard_constraint": True,
        }],
    })).record_id
    constraint = research_session.scalar(select(Constraint).where(Constraint.experiment_id == experiment_id))
    before = [research_session.scalar(select(func.count()).select_from(model)) for model in (ConstraintEvaluationSubject, ConstraintEvaluationMeasurement, ConstraintEvaluationMeasurementEvidence, ConstraintSubjectResult)]
    result = service.validate_structured_evaluation_completeness(constraint.id, [])
    after = [research_session.scalar(select(func.count()).select_from(model)) for model in (ConstraintEvaluationSubject, ConstraintEvaluationMeasurement, ConstraintEvaluationMeasurementEvidence, ConstraintSubjectResult)]
    assert result["aggregate_constraint_result"]["status"] == "PASS"
    assert before == after == [0, 0, 0, 0]
    research_session.rollback()
    legacy_document = _document(structured=False); legacy_document["study_key"] = "P7C-LEGACY"
    legacy = service.register_study(StudyRegistrationInput.model_validate(legacy_document))
    legacy_protocol = service.get_protocol_version(legacy["id"], 1)
    assert "structured_evaluation_plan" not in legacy_protocol["constraint_definitions"][0]


def test_evaluator_version_is_registration_bound() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        DEFAULT_STUDY_EVALUATOR_REGISTRY.executable(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.boolean_equals", "2"))


def test_per_subject_partial_is_rejected_unless_plan_explicitly_allows_it() -> None:
    identity = EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.fixture_partial", "1")
    registry = StudyEvaluatorRegistry(executables=[ExecutableEvaluator(
        identity, frozenset({"RUN"}), ("BOOLEAN",), {},
        lambda *_: ("PARTIAL", "FIXTURE_PARTIAL"),
    )])
    plan = _plan(kind="RUN", field=None, subject_evaluator="subject.fixture_partial", value_type="BOOLEAN", parameters=[])
    subjects = enumerate_evaluation_subjects(plan, _experiment(), 42)
    measurements = [_measurement("RUN", "BOOLEAN", value=True)]
    validation = validate_structured_measurements(plan, subjects, measurements)
    with pytest.raises(ValueError, match="prohibits"):
        calculate_subject_results(plan, subjects, validation["measurements"], registry)
    plan["allow_partial_subject_status"] = True
    assert calculate_subject_results(plan, subjects, validation["measurements"], registry)[0]["status"] == "PARTIAL"


def test_generic_vocabulary_equality_preserves_unknown() -> None:
    plan = _plan(
        kind="RUN", field=None, subject_evaluator="subject.vocabulary_allowed",
        value_type="VOCABULARY_TERM",
        parameters=[{
            "parameter_key": "allowed_term", "value_type": "VOCABULARY_TERM",
            "vocabulary_key": "terms", "vocabulary_term_key": "allowed",
        }],
    )
    assert _evaluate(plan, _experiment(), [_measurement("RUN", "VOCABULARY_TERM", value="allowed")])["subject_results"][0]["status"] == "PASS"
    assert _evaluate(plan, _experiment(), [_measurement("RUN", "VOCABULARY_TERM", unavailable=True)])["subject_results"][0]["status"] == "UNKNOWN"

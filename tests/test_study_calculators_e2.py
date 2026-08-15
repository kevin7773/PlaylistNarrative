from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import text

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_calculators import (
    StudyCalculatorExecutor,
    calculate_paired_difference,
    calculate_status_rate,
    canonical_decimal,
    decimal_difference,
    decimal_mean,
    decimal_ratio,
    unavailable_projection,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from test_study_execution_contract_e1 import (
    _analysis_plan, _disposition_policies, _future_document, _service,
)


def _plan(*, numerator=("PASS",), unknown="EXCLUDE", missing="NOT_DERIVABLE"):
    parameters = [
        *[{"parameter_key": "numerator_status", "ordinal": i, "text_value": value} for i, value in enumerate(numerator, 1)],
        *[{"parameter_key": "denominator_status", "ordinal": i, "text_value": value} for i, value in enumerate(("PASS", "PARTIAL", "FAIL"), 1)],
        {"parameter_key": "unknown_policy", "ordinal": 1, "text_value": unknown},
        {"parameter_key": "missing_input_policy", "ordinal": 1, "text_value": missing},
    ]
    return {"id": 10, "calculator_key": "outcome.constraint_status_rate", "calculator_version": "1", "parameters": parameters, "disposition_policies": [
        {"population_state": "EXPERIMENT_RECORDED", "treatment": "CALCULATE"},
        {"population_state": "PENDING", "treatment": "MISSING"},
        {"population_state": "MAESTRO_REFUSAL_RECORDED", "treatment": "MISSING"},
        {"population_state": "MAESTRO_FAILURE_RECORDED", "treatment": "NOT_CALCULABLE"},
    ]}


def _context(state="EXPERIMENT_RECORDED"):
    return {"protocol_version_id": 3, "registration_hash": "a" * 64, "planned_run_id": 4, "population_state": state, "realization": None}


def _inputs(*statuses):
    return [{"id": i, "status": status, "sort_key": [i]} for i, status in enumerate(statuses, 1)]


@pytest.mark.parametrize("statuses,numerator,expected", [
    (("PASS", "PASS"), ("PASS",), (2, 2, "1")),
    (("FAIL", "FAIL"), ("PASS",), (0, 2, "0")),
    (("PASS", "FAIL"), ("PASS",), (1, 2, "0.5")),
    (("PARTIAL", "FAIL"), ("PARTIAL",), (1, 2, "0.5")),
    (("PARTIAL", "FAIL"), ("PASS",), (0, 2, "0")),
])
def test_status_rate_frozen_status_semantics(statuses, numerator, expected):
    result = calculate_status_rate(_plan(numerator=numerator), _context(), _inputs(*statuses), [])
    assert (result["numerator_count"], result["denominator_count"], result["decimal_value"]) == expected
    assert result["calculation_state"] == "CALCULATED"


def test_unknown_policies_and_missing_policies():
    excluded = calculate_status_rate(_plan(), _context(), _inputs("PASS", "UNKNOWN"), [])
    assert excluded["decimal_value"] == "1" and excluded["unknown_count"] == excluded["excluded_count"] == 1
    assert excluded["excluded_inputs"][0]["exclusion_reason"] == "UNKNOWN_EXCLUDED_BY_REGISTERED_POLICY"
    unknown = calculate_status_rate(_plan(unknown="NOT_CALCULABLE"), _context(), _inputs("PASS", "UNKNOWN"), [])
    assert unknown["calculation_state"] == "NOT_CALCULABLE" and unknown["reason_code"] == "APPLICABLE_UNKNOWN"
    missing = [{"id": 9, "sort_key": [9]}]
    not_derived = calculate_status_rate(_plan(missing="NOT_DERIVABLE"), _context(), [], missing)
    assert not_derived["derivability_state"] == "NOT_DERIVABLE" and not_derived["reason_code"] == "REQUIRED_INPUT_NOT_GOVERNED"
    not_calculable = calculate_status_rate(_plan(missing="NOT_CALCULABLE"), _context(), [], missing)
    assert not_calculable["calculation_state"] == "NOT_CALCULABLE" and not_calculable["reason_code"] == "EXPECTED_INPUT_MISSING"


def test_zero_denominator_incompatible_and_unavailable():
    zero = calculate_status_rate(_plan(), _context(), [], [])
    assert zero["reason_code"] == "ZERO_DENOMINATOR" and zero["decimal_value"] is None
    incompatible = calculate_status_rate(_plan(), _context(), [], [], incompatible_reason="wrong evaluator")
    assert incompatible["derivability_state"] == "NOT_DERIVABLE"
    assert incompatible["reason_code"] == "INCOMPATIBLE_INSTRUMENTATION"
    unavailable = unavailable_projection("outcome.constraint_status_rate", "1")
    assert unavailable["execution_state"] == "UNAVAILABLE" and unavailable["derivability_state"] is None


@pytest.mark.parametrize("state,calculation,reason", [
    ("PENDING", "MISSING", "PENDING_REGISTERED_RUN"),
    ("MAESTRO_REFUSAL_RECORDED", "MISSING", "REFUSAL_OUTCOME_MISSING"),
    ("MAESTRO_FAILURE_RECORDED", "NOT_CALCULABLE", "GENERATION_FAILURE_OUTCOME_NOT_CALCULABLE"),
])
def test_disposition_policy_is_consumed_exactly(state, calculation, reason):
    result = calculate_status_rate(_plan(), _context(state), [], [])
    assert result["calculation_state"] == calculation and result["reason_code"] == reason


def test_alternate_refusal_and_failure_policies_are_honored():
    plan = _plan()
    next(item for item in plan["disposition_policies"] if item["population_state"] == "MAESTRO_REFUSAL_RECORDED")["treatment"] = "NOT_CALCULABLE"
    next(item for item in plan["disposition_policies"] if item["population_state"] == "MAESTRO_FAILURE_RECORDED")["treatment"] = "MISSING"
    refusal = calculate_status_rate(plan, _context("MAESTRO_REFUSAL_RECORDED"), [], [])
    failure = calculate_status_rate(plan, _context("MAESTRO_FAILURE_RECORDED"), [], [])
    assert refusal["reason_code"] == "REFUSAL_OUTCOME_NOT_CALCULABLE"
    assert failure["reason_code"] == "GENERATION_FAILURE_OUTCOME_MISSING"


def test_decimal_contract_is_deterministic_and_float_free():
    assert decimal_ratio(1, 3) == "0.3333333333333333333333333333333333"
    assert canonical_decimal(__import__("decimal").Decimal("0.5000")) == "0.5"
    assert decimal_difference("0.1", "0.3", "RIGHT_MINUS_LEFT") == "0.2"
    assert decimal_difference("0.1", "0.3", "LEFT_MINUS_RIGHT") == "-0.2"
    assert decimal_mean(["0.1", "0.2"]) == "0.15"


def test_rate_input_order_is_incidental():
    inputs = _inputs("PASS", "FAIL", "PARTIAL")
    assert calculate_status_rate(_plan(), _context(), inputs, []) == calculate_status_rate(
        _plan(), _context(), list(reversed(inputs)), []
    )


def _outcome(run_id, value=None, state="CALCULATED", derivability="DERIVABLE"):
    return {"execution_state": "AVAILABLE", "derivability_state": derivability,
            "calculation_state": state if derivability == "DERIVABLE" else None,
            "decimal_value": value, "planned_run_id": run_id}


def _paired_protocol():
    return {"id": 3, "registration_hash": "b" * 64, "planned_runs": [
        {"id": 1, "condition_key": "a", "block_key": "b1", "replicate_number": 1, "realization": {"id": 11}},
        {"id": 2, "condition_key": "z", "block_key": "b1", "replicate_number": 1, "realization": {"id": 12}},
        {"id": 3, "condition_key": "a", "block_key": "b2", "replicate_number": 1, "realization": {"id": 13}},
        {"id": 4, "condition_key": "z", "block_key": "b2", "replicate_number": 1, "realization": {"id": 14}},
    ]}


def _paired_plan(direction="RIGHT_MINUS_LEFT"):
    return {"id": 8, "analysis_key": "opaque", "outcome_key": "opaque-outcome",
            "calculator_key": "analysis.paired_difference", "calculator_version": "1",
            "dimensions": [{"dimension_role": "MATCH", "dimension_key": "BLOCK", "ordinal": 1}, {"dimension_role": "MATCH", "dimension_key": "REPLICATE", "ordinal": 2}],
            "condition_bindings": [{"comparison_role": "LEFT", "condition_key": "a"}, {"comparison_role": "RIGHT", "condition_key": "z"}],
            "parameters": [{"parameter_key": "difference_direction", "ordinal": 1, "text_value": direction}, {"parameter_key": "pair_completeness", "ordinal": 1, "text_value": "REQUIRED"}, {"parameter_key": "missing_policy", "ordinal": 1, "text_value": "NOT_CALCULABLE"}]}


def test_paired_difference_exact_mean_direction_counts_and_order():
    outcomes = {1: _outcome(1, "0.8"), 2: _outcome(2, "0.5"), 3: _outcome(3, "0.2"), 4: _outcome(4, "0.4")}
    result = calculate_paired_difference(_paired_plan(), _paired_protocol(), outcomes)
    assert [pair["difference"] for pair in result["pairs"]] == ["-0.3", "0.2"]
    assert result["mean_difference"] == "-0.05"
    assert (result["negative_difference_count"], result["zero_difference_count"], result["positive_difference_count"]) == (1, 0, 1)
    reversed_result = calculate_paired_difference(_paired_plan("LEFT_MINUS_RIGHT"), _paired_protocol(), outcomes)
    assert [pair["difference"] for pair in reversed_result["pairs"]] == ["0.3", "-0.2"]


@pytest.mark.parametrize("member,reason", [
    (_outcome(2, None, derivability="NOT_DERIVABLE"), "MEMBER_NOT_DERIVABLE"),
    (_outcome(2, None, state="MISSING"), "MEMBER_MISSING"),
    (_outcome(2, None, state="NOT_CALCULABLE"), "MEMBER_NOT_CALCULABLE"),
    (_outcome(2, None, state="CALCULATED"), "MEMBER_OUTPUT_TYPE_MISMATCH"),
])
def test_paired_member_non_numeric_states(member, reason):
    protocol = _paired_protocol(); protocol["planned_runs"] = protocol["planned_runs"][:2]
    result = calculate_paired_difference(_paired_plan(), protocol, {1: _outcome(1, "1"), 2: member})
    assert result["calculation_state"] == "NOT_CALCULABLE"
    assert result["pairs"][0]["reason_code"] == reason


def test_paired_missing_duplicate_zero_pairs_and_unavailable():
    protocol = _paired_protocol(); protocol["planned_runs"] = protocol["planned_runs"][:1]
    missing = calculate_paired_difference(_paired_plan(), protocol, {1: _outcome(1, "1")})
    assert missing["pairs"][0]["reason_code"] == "PAIR_RIGHT_MISSING"
    right_only_protocol = _paired_protocol(); right_only_protocol["planned_runs"] = right_only_protocol["planned_runs"][1:2]
    left_missing = calculate_paired_difference(_paired_plan(), right_only_protocol, {2: _outcome(2, "1")})
    assert left_missing["pairs"][0]["reason_code"] == "PAIR_LEFT_MISSING"
    neither_protocol = {"id": 3, "registration_hash": "b" * 64, "planned_runs": [
        {"id": 7, "condition_key": "outside", "block_key": "b1", "replicate_number": 1, "realization": None}
    ]}
    both_missing = calculate_paired_difference(_paired_plan(), neither_protocol, {7: _outcome(7, "1")})
    assert both_missing["pairs"][0]["reason_code"] == "PAIR_BOTH_SIDES_MISSING"
    duplicate_protocol = _paired_protocol(); duplicate_protocol["planned_runs"] = duplicate_protocol["planned_runs"][:2]
    duplicate_protocol["planned_runs"].append({**duplicate_protocol["planned_runs"][0], "id": 9})
    duplicate = calculate_paired_difference(_paired_plan(), duplicate_protocol, {1: _outcome(1, "1"), 2: _outcome(2, "1"), 9: _outcome(9, "1")})
    assert duplicate["pairs"][0]["reason_code"] == "PAIR_LEFT_DUPLICATE"
    empty = calculate_paired_difference(_paired_plan(), {"id": 3, "registration_hash": "b" * 64, "planned_runs": []}, {})
    assert empty["reason_code"] == "ZERO_VALID_PAIRS"
    unavailable = calculate_paired_difference(_paired_plan(), protocol, {}, available=False)
    assert unavailable["execution_state"] == "UNAVAILABLE"


def test_service_pending_execution_is_governed_id_read_only(research_session):
    service = _service(research_session)
    registered = service.register_study(StudyRegistrationInput.model_validate(_future_document()))
    protocol = registered["registered_protocol"]
    run_id = protocol["planned_runs"][0]["id"]
    plan_id = protocol["execution_contract"]["outcome_calculation_plans"][0]["id"]
    before = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    result = service.calculate_registered_outcome(registered["id"], 1, run_id, plan_id)
    after = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    assert result["reason_code"] == "PENDING_REGISTERED_RUN"
    assert before == after
    availability = service.get_calculator_availability(registered["id"], 1)
    assert availability["execution_classification"] == "CALCULATOR_GOVERNED_EXECUTION"
    analysis_id = protocol["execution_contract"]["analysis_calculation_plans"][0]["id"]
    analysis = service.calculate_registered_analysis(registered["id"], 1, analysis_id)
    assert analysis["calculation_state"] == "NOT_CALCULABLE"
    assert analysis["pairs"][0]["reason_code"] == "MEMBER_MISSING"


def test_service_reports_implementation_unavailable_without_scientific_state(research_session):
    from playlist_narrative_engine.research_store.repository import ResearchRepository
    base = _service(research_session)
    registered = base.register_study(StudyRegistrationInput.model_validate(_future_document()))
    service = ResearchStoreService(
        ResearchRepository(research_session),
        evaluator_registry=base._evaluator_registry,
        calculator_executor=StudyCalculatorExecutor(outcome_calculators=set(), analysis_calculators=set()),
    )
    protocol = service.get_protocol_version(registered["id"], 1)
    result = service.calculate_registered_outcome(
        registered["id"], 1, protocol["planned_runs"][0]["id"],
        protocol["execution_contract"]["outcome_calculation_plans"][0]["id"],
    )
    assert result == unavailable_projection("outcome.constraint_status_rate", "1")


def test_legacy_protocol_is_not_routed_through_e2(research_session):
    from test_study_structured_evaluation_p7a import _document
    service = _service(research_session)
    registered = service.register_study(StudyRegistrationInput.model_validate(_document(structured=False)))
    assert service.get_calculator_availability(registered["id"], 1)["execution_classification"] == "LEGACY_EXECUTION"
    with pytest.raises(ValueError, match="LEGACY_EXECUTION"):
        service.calculate_registered_outcome(registered["id"], 1, 1, 1)


def test_registered_outcome_replays_identically_after_reopen(tmp_path):
    from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
    from playlist_narrative_engine.research_store.migrations import migrate_research_database
    from test_study_structured_evaluation_p7a import _registry
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'e2-replay.db').as_posix()}")
    migrate_research_database(engine)
    factory = make_research_session_factory(engine)
    with factory() as session:
        service = ResearchStoreService(ResearchRepository(session), evaluator_registry=_registry())
        registered = service.register_study(StudyRegistrationInput.model_validate(_future_document()))
        protocol = registered["registered_protocol"]
        identity = (registered["id"], protocol["planned_runs"][0]["id"], protocol["execution_contract"]["outcome_calculation_plans"][0]["id"])
        first = service.calculate_registered_outcome(identity[0], 1, identity[1], identity[2])
    engine.dispose()
    reopened = make_research_engine(f"sqlite:///{(tmp_path / 'e2-replay.db').as_posix()}")
    with make_research_session_factory(reopened)() as session:
        service = ResearchStoreService(ResearchRepository(session), evaluator_registry=_registry())
        second = service.calculate_registered_outcome(identity[0], 1, identity[1], identity[2])
    reopened.dispose()
    assert first == second


def _structured_execution_study():
    from test_study_structured_evaluation_p7d import _study
    document = _study().model_dump(mode="json")
    protocol = document["protocol"]
    protocol["conditions"].append({
        "condition_key": "treatment", "label": "Treatment", "role": "TREATMENT",
        "exact_factor_definition": "One opaque treatment factor.",
    })
    protocol["planned_sample_size"] = 2
    second = deepcopy(protocol["planned_runs"][0])
    second.update(run_key="run-2", condition_key="treatment", randomized_ordinal=2)
    protocol["planned_runs"].append(second)
    protocol["outcome_definitions"].append({
        "outcome_key": "subject-rate", "role": "SECONDARY",
        "unit_of_analysis": "structured subject result", "outcome_definition": "Registered subject-result rate.",
        "computation_rule": "Registered calculator only.", "missing_data_rule": "Registered missing policy.",
        "refusal_handling": "Registered disposition policy.", "operational_failure_handling": "Pending remains pending.",
    })
    protocol["analysis_definitions"].append({
        "analysis_key": "subject-paired", "outcome_key": "subject-rate",
        "analysis_population": "All registered planned runs.", "comparison_definition": "Registered relational pairing.",
        "aggregation_rule": "Registered paired calculator.", "exclusion_rule": "No exclusion.",
        "reporting_rule": "Descriptive only.",
    })
    rate_parameters = [
        {"parameter_key": "numerator_status", "ordinal": 1, "value_type": "TEXT", "text_value": "PASS"},
        *[{"parameter_key": "denominator_status", "ordinal": ordinal, "value_type": "TEXT", "text_value": status}
          for ordinal, status in enumerate(("PASS", "PARTIAL", "FAIL"), start=1)],
        {"parameter_key": "unknown_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_CALCULABLE"},
        {"parameter_key": "missing_input_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_DERIVABLE"},
    ]
    protocol["execution_contract"] = {
        "contract_version": "1",
        "outcome_calculation_plans": [
            {"outcome_key": "primary", "calculator_key": "outcome.constraint_status_rate", "calculator_version": "1",
             "input_kind": "CONSTRAINT_RESULTS", "output_value_type": "DECIMAL",
             "constraint_bindings": [{"constraint_key": "structured", "binding_role": "CONTRIBUTOR", "ordinal": 1}],
             "parameters": deepcopy(rate_parameters), "disposition_policies": _disposition_policies()},
            {"outcome_key": "subject-rate", "calculator_key": "outcome.subject_status_rate", "calculator_version": "1",
             "input_kind": "STRUCTURED_SUBJECT_RESULTS", "output_value_type": "DECIMAL",
             "constraint_bindings": [{"constraint_key": "structured", "binding_role": "CONTRIBUTOR", "ordinal": 1}],
             "subject_kinds": ["RUN"], "parameters": deepcopy(rate_parameters), "disposition_policies": _disposition_policies()},
        ],
        "analysis_calculation_plans": [_analysis_plan("primary"), _analysis_plan("subject-paired")],
    }
    return StudyRegistrationInput.model_validate(document)


def test_service_executes_governed_constraint_subject_and_paired_calculators(research_session):
    from test_study_structured_evaluation_p7d import _experiment, _run_payload
    service = ResearchStoreService(ResearchRepository(research_session))
    registered = service.register_study(_structured_execution_study())
    protocol = registered["registered_protocol"]
    definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
    for run in protocol["planned_runs"]:
        experiment = _experiment(protocol, definitions)
        if run["id"] != protocol["planned_runs"][0]["id"]:
            changed = experiment.model_dump(mode="json")
            changed["prompt"] = run["planned_prompt_text"]
            from playlist_narrative_engine.research_store.schemas import ExperimentInput
            experiment = ExperimentInput.model_validate(changed)
        service.realize_structured_study_experiment(
            run["id"], experiment, _run_payload(definitions["structured"]["id"])
        )
    refreshed = service.get_protocol_version(registered["id"], 1)
    plans = {item["outcome_key"]: item for item in refreshed["execution_contract"]["outcome_calculation_plans"]}
    first_run = refreshed["planned_runs"][0]
    before = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    aggregate = service.calculate_registered_outcome(registered["id"], 1, first_run["id"], plans["primary"]["id"])
    subject = service.calculate_registered_outcome(registered["id"], 1, first_run["id"], plans["subject-rate"]["id"])
    assert aggregate["decimal_value"] == "1"
    assert subject["decimal_value"] == "1"
    assert len(subject["subject_result_ids"]) == 1
    assert subject["contributing_inputs"][0]["measurements"][0]["authority_kind"] == "STRUCTURAL_DERIVATION"
    analyses = {item["analysis_key"]: item for item in refreshed["execution_contract"]["analysis_calculation_plans"]}
    paired = service.calculate_registered_analysis(registered["id"], 1, analyses["primary"]["id"])
    assert paired["calculation_state"] == "CALCULATED"
    assert paired["mean_difference"] == "0"
    after = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    assert before == after

from __future__ import annotations

from copy import deepcopy

from sqlalchemy import text

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_calculators import (
    StudyCalculatorExecutor,
)
from playlist_narrative_engine.research_store.study_evaluation import (
    evaluate_calculator_governed_study,
    evaluate_registered_study,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from test_study_calculators_e2 import _structured_execution_study
from test_study_execution_contract_e1 import _future_document, _service
from test_study_structured_evaluation_p7a import _document
from test_study_structured_evaluation_p7d import _experiment, _run_payload


def test_legacy_dispatch_never_invokes_calculator_path(research_session, monkeypatch):
    service = _service(research_session)
    registered = service.register_study(
        StudyRegistrationInput.model_validate(_document(structured=False))
    )
    monkeypatch.setattr(
        service,
        "calculate_registered_outcome",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("E2 invoked")),
    )
    result = service.evaluate_study(registered["id"], 1)
    assert result["execution_classification"] == "LEGACY_EXECUTION"
    protocol = service.get_protocol_version(registered["id"], 1)
    direct = evaluate_registered_study(protocol, service.get_experiment)
    normalized = deepcopy(result)
    normalized.pop("execution_classification")
    assert normalized == direct


def test_calculator_dispatch_never_invokes_legacy_path(research_session, monkeypatch):
    import playlist_narrative_engine.research_store.service as service_module

    service = _service(research_session)
    registered = service.register_study(
        StudyRegistrationInput.model_validate(_future_document())
    )
    monkeypatch.setattr(
        service_module,
        "evaluate_registered_study",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("legacy invoked")),
    )
    result = service.evaluate_study(registered["id"], 1)
    assert result["execution_classification"] == "CALCULATOR_GOVERNED_EXECUTION"
    assert all(
        outcome["strategy"] == "REGISTERED_CALCULATOR"
        for run in result["runs"]
        for outcome in run["outcomes"]
    )


def test_unavailable_calculator_is_preserved_without_fallback(research_session):
    base = _service(research_session)
    registered = base.register_study(
        StudyRegistrationInput.model_validate(_future_document())
    )
    service = ResearchStoreService(
        ResearchRepository(research_session),
        evaluator_registry=base._evaluator_registry,
        calculator_executor=StudyCalculatorExecutor(
            outcome_calculators=set(), analysis_calculators=set()
        ),
    )
    result = service.evaluate_study(registered["id"], 1)
    outcome = result["runs"][0]["outcomes"][0]
    analysis = result["analyses"][0]
    assert outcome["status"] == outcome["execution_state"] == "UNAVAILABLE"
    assert outcome["reason_code"] == "CALCULATOR_IMPLEMENTATION_UNAVAILABLE"
    assert analysis["status"] == analysis["execution_state"] == "UNAVAILABLE"
    assert analysis["reason_code"] == "CALCULATOR_IMPLEMENTATION_UNAVAILABLE"


def test_all_noncalculated_e2_states_remain_distinct_in_p3_adapter():
    protocol = _future_document()["protocol"]
    protocol.update(
        study_id=1,
        study_key="FUTURE",
        id=2,
        registration_hash="a" * 64,
        version_number=1,
    )
    for index, run in enumerate(protocol["planned_runs"], start=1):
        run.update(id=index, attempts=[], realization=None)
    for index, definition in enumerate(protocol["constraint_definitions"], start=1):
        definition["id"] = index
    for index, definition in enumerate(protocol["outcome_definitions"], start=1):
        definition["id"] = index
    for index, definition in enumerate(protocol["analysis_definitions"], start=1):
        definition["id"] = index
    contract = protocol["execution_contract"]
    for index, plan in enumerate(contract["outcome_calculation_plans"], start=1):
        plan["id"] = index
    for index, plan in enumerate(contract["analysis_calculation_plans"], start=1):
        plan["id"] = index
    states = {
        1: {"execution_state": "AVAILABLE", "derivability_state": "NOT_DERIVABLE", "calculation_state": None, "reason_code": "REQUIRED_INPUT_NOT_GOVERNED"},
        2: {"execution_state": "AVAILABLE", "derivability_state": "DERIVABLE", "calculation_state": "MISSING", "reason_code": "PENDING_REGISTERED_RUN"},
    }
    result = evaluate_calculator_governed_study(
        protocol,
        lambda _: None,
        lambda _, plan_id: states[plan_id],
        lambda _: {"execution_state": "AVAILABLE", "derivability_state": "DERIVABLE", "calculation_state": "NOT_CALCULABLE", "reason_code": "MEMBER_MISSING"},
    )
    assert [item["status"] for item in result["runs"][0]["outcomes"]] == [
        "NOT_DERIVABLE",
        "MISSING",
    ]
    assert result["analyses"][0]["status"] == "NOT_CALCULABLE"


def _realized_calculator_study(service):
    registered = service.register_study(_structured_execution_study())
    protocol = registered["registered_protocol"]
    definitions = {
        item["constraint_key"]: item for item in protocol["constraint_definitions"]
    }
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
    return registered["id"]


def test_future_evaluation_equals_direct_e2_and_retains_provenance(research_session):
    service = ResearchStoreService(ResearchRepository(research_session))
    study_id = _realized_calculator_study(service)
    protocol = service.get_protocol_version(study_id, 1)
    before = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    evaluation = service.evaluate_study(study_id, 1)
    after = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    assert before == after
    plans = {
        item["outcome_key"]: item
        for item in protocol["execution_contract"]["outcome_calculation_plans"]
    }
    first_run = protocol["planned_runs"][0]
    direct = service.calculate_registered_outcome(
        study_id, 1, first_run["id"], plans["subject-rate"]["id"]
    )
    projected = next(
        item
        for item in evaluation["runs"][0]["outcomes"]
        if item["outcome_key"] == "subject-rate"
    )
    assert projected["calculator_projection"] == direct
    assert direct["subject_result_ids"]
    measurement = direct["contributing_inputs"][0]["measurements"][0]
    assert measurement["authority_kind"] == "STRUCTURAL_DERIVATION"
    assert measurement["id"]
    analysis_plan = protocol["execution_contract"]["analysis_calculation_plans"][0]
    direct_analysis = service.calculate_registered_analysis(
        study_id, 1, analysis_plan["id"]
    )
    projected_analysis = next(
        item
        for item in evaluation["analyses"]
        if item["analysis_key"] == analysis_plan["analysis_key"]
    )
    assert projected_analysis["calculator_projection"] == direct_analysis


def test_future_matching_legacy_prose_and_keys_cannot_trigger_legacy(research_session):
    document = _future_document()
    document["protocol"]["outcome_definitions"][0].update(
        outcome_key="hard_constraint_compliance",
        outcome_definition="Proportion of the run's two applicable hard constraints completely satisfied.",
        computation_rule="Score PASS=1 and PARTIAL/FAIL=0, then divide by 2.",
    )
    document["protocol"]["execution_contract"]["outcome_calculation_plans"][0][
        "outcome_key"
    ] = "hard_constraint_compliance"
    document["protocol"]["analysis_definitions"][0]["outcome_key"] = "hard_constraint_compliance"
    proposal = StudyRegistrationInput.model_validate(document)
    service = _service(research_session)
    registered = service.register_study(proposal)
    evaluation = service.evaluate_study(registered["id"], 1)
    first = evaluation["runs"][0]["outcomes"][0]
    assert first["strategy"] == "REGISTERED_CALCULATOR"
    assert first["reason_code"] == "PENDING_REGISTERED_RUN"


def test_calculator_evaluation_is_identical_after_database_reopen(tmp_path):
    from playlist_narrative_engine.research_store.database import (
        make_research_engine,
        make_research_session_factory,
    )
    from playlist_narrative_engine.research_store.migrations import migrate_research_database

    path = tmp_path / "e3-reopen.db"
    engine = make_research_engine(f"sqlite:///{path.as_posix()}")
    migrate_research_database(engine)
    factory = make_research_session_factory(engine)
    with factory() as session:
        service = ResearchStoreService(ResearchRepository(session))
        study_id = _realized_calculator_study(service)
        first = service.evaluate_study(study_id, 1)
    engine.dispose()
    reopened = make_research_engine(f"sqlite:///{path.as_posix()}")
    with make_research_session_factory(reopened)() as session:
        second = ResearchStoreService(ResearchRepository(session)).evaluate_study(
            study_id, 1
        )
    reopened.dispose()
    assert first == second

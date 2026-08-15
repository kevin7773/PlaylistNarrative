from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from sqlalchemy import text

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_schemas import (
    StructuredStudyEvaluationInput,
    StudyRegistrationInput,
)
from test_study_execution_contract_e1 import _analysis_plan, _disposition_policies
from test_study_structured_evaluation_p7d import _experiment, _study


def _parameters():
    return [
        {"parameter_key": "numerator_status", "ordinal": 1, "value_type": "TEXT", "text_value": "PASS"},
        *[
            {"parameter_key": "denominator_status", "ordinal": ordinal, "value_type": "TEXT", "text_value": status}
            for ordinal, status in enumerate(("PASS", "PARTIAL", "FAIL"), start=1)
        ],
        {"parameter_key": "unknown_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_CALCULABLE"},
        {"parameter_key": "missing_input_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_DERIVABLE"},
    ]


def _p7f_study():
    params = [
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    document = _study(
        "PLACEMENT_FIELD", "explicit_flag", "subject.boolean_equals", "BOOLEAN",
        evidence_required=True, aggregate="aggregate.all_subjects_required",
        parameters=params, legacy=True,
    ).model_dump(mode="json")
    document["study_key"] = "P7F-SYNTHETIC"
    protocol = document["protocol"]
    protocol["conditions"].append({
        "condition_key": "treatment", "label": "Treatment", "role": "TREATMENT",
        "exact_factor_definition": "One opaque registered treatment factor.",
    })
    protocol["planned_sample_size"] = 2
    second = deepcopy(protocol["planned_runs"][0])
    second.update(run_key="run-2", condition_key="treatment", randomized_ordinal=2)
    protocol["planned_runs"].append(second)
    protocol["outcome_definitions"].append({
        "outcome_key": "subject-rate", "role": "SECONDARY",
        "unit_of_analysis": "registered structured subject",
        "outcome_definition": "Registered structured subject-result rate.",
        "computation_rule": "Registered calculator only.",
        "missing_data_rule": "Registered missing policy.",
        "refusal_handling": "Registered disposition policy.",
        "operational_failure_handling": "Pending remains pending.",
    })
    protocol["analysis_definitions"].append({
        "analysis_key": "subject-paired", "outcome_key": "subject-rate",
        "analysis_population": "All registered planned runs.",
        "comparison_definition": "Registered relational pairing.",
        "aggregation_rule": "Registered paired calculator.",
        "exclusion_rule": "Registered missing policy.",
        "reporting_rule": "Descriptive only.",
    })
    protocol["execution_contract"] = {
        "contract_version": "1",
        "outcome_calculation_plans": [
            {
                "outcome_key": "primary", "calculator_key": "outcome.constraint_status_rate",
                "calculator_version": "1", "input_kind": "CONSTRAINT_RESULTS",
                "output_value_type": "DECIMAL",
                "constraint_bindings": [{"constraint_key": "structured", "binding_role": "CONTRIBUTOR", "ordinal": 1}],
                "parameters": deepcopy(_parameters()), "disposition_policies": _disposition_policies(),
            },
            {
                "outcome_key": "subject-rate", "calculator_key": "outcome.subject_status_rate",
                "calculator_version": "1", "input_kind": "STRUCTURED_SUBJECT_RESULTS",
                "output_value_type": "DECIMAL", "subject_interpretation": "FIELD_PREDICATE",
                "constraint_bindings": [{"constraint_key": "structured", "binding_role": "CONTRIBUTOR", "ordinal": 1}],
                "subject_kinds": ["PLACEMENT_FIELD"], "parameters": deepcopy(_parameters()),
                "disposition_policies": _disposition_policies(),
            },
        ],
        "analysis_calculation_plans": [_analysis_plan("primary"), _analysis_plan("subject-paired")],
    }
    return StudyRegistrationInput.model_validate(document)


def _payload(definition_id):
    subjects = []
    for ordinal, value in enumerate((False, True), start=1):
        subjects.append({
            "subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": ordinal,
            "track_observed_ordinal": ordinal, "governed_field": "explicit_flag",
            "measurements": [{
                "measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION",
                "value_type": "BOOLEAN", "boolean_value": value, "recorded_by": "fixture",
                "evidence": [{
                    "source_key": "screen", "evidence_link_field": "explicit_flag",
                    "evidence_role": "OBSERVED_VALUE", "provenance_type": "DIRECT_OBSERVATION",
                    "support_status": "FULL",
                }],
            }],
        })
    return StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definition_id, "subjects": subjects,
    }]})


def _realize(service):
    registered = service.register_study(_p7f_study())
    protocol = registered["registered_protocol"]
    definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
    for run in protocol["planned_runs"]:
        experiment = _experiment(
            protocol, definitions, count=2, explicit=[False, True], evidence=True, legacy=True
        )
        raw = experiment.model_dump(mode="json")
        raw["prompt"] = run["planned_prompt_text"]
        experiment = ExperimentInput.model_validate(raw)
        service.realize_structured_study_experiment(
            run["id"], experiment, _payload(definitions["structured"]["id"])
        )
    return registered["id"]


def test_p7f_consumes_e2_and_persisted_p7_without_writes(research_session):
    service = ResearchStoreService(ResearchRepository(research_session))
    study_id = _realize(service)
    protocol = service.get_protocol_version(study_id, 1)
    before = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    evaluation = service.evaluate_study(study_id, 1)
    exploration = service.explore_study(study_id, 1)
    closeout = service.closeout_study(study_id, 1, generated_at="fixed")
    after = research_session.execute(text("SELECT total_changes()" )).scalar_one()
    assert before == after
    assert evaluation["execution_classification"] == "CALCULATOR_GOVERNED_EXECUTION"
    first_run = protocol["planned_runs"][0]
    plans = {item["outcome_key"]: item for item in protocol["execution_contract"]["outcome_calculation_plans"]}
    direct = service.calculate_registered_outcome(
        study_id, 1, first_run["id"], plans["subject-rate"]["id"]
    )
    projected = next(item for item in evaluation["runs"][0]["outcomes"] if item["outcome_key"] == "subject-rate")
    assert projected["calculator_projection"] == direct
    structured = exploration["structured_evaluation"]
    assert structured["status"] == "EXPLORATORY — NOT PREREGISTERED"
    assert structured["available_population"] == {
        "LEGACY_AGGREGATE_ONLY": 2, "STRUCTURED_DERIVABLE": 2
    }
    assert structured["status_counts_by_subject_kind"] == [{
        "subject_kind": "PLACEMENT_FIELD", "status_counts": {"FAIL": 2, "PASS": 2}
    }]
    assert all(item["experiment_track_id"] is not None for item in structured["contributors"])
    assert all(item["measurement_ids"] and item["evidence"] for item in structured["contributors"])
    assert not any("violation_rate" in key for key in structured)
    consumed = closeout["structured_consumption"]
    assert consumed["execution_contract_version"] == "1"
    assert consumed["structured_subject_count"] == 4
    assert consumed["subject_result_count"] == 4
    assert consumed["measurement_count"] == 4
    assert consumed["measurement_evidence_count"] == 4
    assert closeout["reproducibility_manifest"]["subject_result_ids"] == consumed["subject_result_ids"]
    assert closeout["registered_results"] == evaluation


def test_p7f_replay_is_deterministic_after_reopen(tmp_path):
    from playlist_narrative_engine.research_store.database import (
        make_research_engine, make_research_session_factory,
    )
    from playlist_narrative_engine.research_store.migrations import migrate_research_database

    path = tmp_path / "p7f.db"
    engine = make_research_engine(f"sqlite:///{path.as_posix()}")
    migrate_research_database(engine)
    with make_research_session_factory(engine)() as session:
        service = ResearchStoreService(ResearchRepository(session))
        study_id = _realize(service)
        first = (
            service.evaluate_study(study_id, 1),
            service.explore_study(study_id, 1),
            service.closeout_study(study_id, 1, generated_at="fixed"),
        )
    engine.dispose()
    reopened = make_research_engine(f"sqlite:///{path.as_posix()}")
    with make_research_session_factory(reopened)() as session:
        service = ResearchStoreService(ResearchRepository(session))
        second = (
            service.evaluate_study(study_id, 1),
            service.explore_study(study_id, 1),
            service.closeout_study(study_id, 1, generated_at="fixed"),
        )
    reopened.dispose()
    assert first == second


def test_sections_06_to_08_render_structured_consumption_without_write_controls():
    script = Path(
        "src/playlist_narrative_engine/maestro_workbench/static/studies.js"
    ).read_text(encoding="utf-8")
    assert "renderCalculatorEvaluation" in script
    assert "execution_state" in script and "derivability_state" in script
    assert "ratio_numerator" in script and "ratio_denominator" in script
    assert "renderStructuredExploration" in script
    assert "EXPLORATORY — NOT PREREGISTERED" in script
    assert "structuredCloseoutMarkup" in script
    assert "subject_result_ids" in script and "structured_evidence_link_ids" in script
    structured_renderers = script[script.index("function calculatorState"):]
    assert "override result" not in structured_renderers.lower()
    assert "recalculate" not in structured_renderers.lower()

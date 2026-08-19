from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.models import (
    StudyAnalysisCalculationPlan,
    StudyExecutionContract,
    StudyOutcomeCalculationPlan,
)
from playlist_narrative_engine.research_store.database import (
    make_research_engine,
    make_research_session_factory,
)
from playlist_narrative_engine.research_store.migrations import (
    get_schema_version,
    migrate_research_database,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_protocol import (
    canonical_protocol_bytes,
    protocol_registration_hash,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from test_study_structured_evaluation_p7a import _document, _registry


def _rate_parameters() -> list[dict[str, object]]:
    return [
        {"parameter_key": "numerator_status", "ordinal": 1, "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "denominator_status", "ordinal": 1, "value_type": "TEXT", "text_value": "PASS"},
        {"parameter_key": "denominator_status", "ordinal": 2, "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "denominator_status", "ordinal": 3, "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_CALCULABLE"},
        {"parameter_key": "missing_input_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_DERIVABLE"},
    ]


def _disposition_policies() -> list[dict[str, str]]:
    return [
        {"population_state": "EXPERIMENT_RECORDED", "treatment": "CALCULATE"},
        {"population_state": "MAESTRO_REFUSAL_RECORDED", "treatment": "MISSING"},
        {"population_state": "MAESTRO_FAILURE_RECORDED", "treatment": "NOT_CALCULABLE"},
        {"population_state": "PENDING", "treatment": "MISSING"},
    ]


def _analysis_plan(key: str) -> dict[str, object]:
    return {
        "analysis_key": key,
        "calculator_key": "analysis.paired_difference",
        "calculator_version": "1",
        "population_scope": "ALL_REGISTERED_PLANNED_RUNS",
        "output_shape_key": "PAIRED_DIFFERENCE_SUMMARY",
        "output_shape_version": "1",
        "dimensions": [
            {"dimension_role": "MATCH", "dimension_key": "BLOCK", "ordinal": 1},
            {"dimension_role": "MATCH", "dimension_key": "REPLICATE", "ordinal": 2},
        ],
        "condition_bindings": [
            {"comparison_role": "LEFT", "condition_key": "control"},
            {"comparison_role": "RIGHT", "condition_key": "treatment"},
        ],
        "parameters": [
            {"parameter_key": "difference_direction", "ordinal": 1, "value_type": "TEXT", "text_value": "RIGHT_MINUS_LEFT"},
            {"parameter_key": "pair_completeness", "ordinal": 1, "value_type": "TEXT", "text_value": "REQUIRED"},
            {"parameter_key": "missing_policy", "ordinal": 1, "value_type": "TEXT", "text_value": "NOT_CALCULABLE"},
        ],
    }


def _future_document() -> dict[str, object]:
    document = _document(structured=True)
    protocol = document["protocol"]
    protocol["conditions"].append({
        "condition_key": "treatment", "label": "Treatment", "role": "TREATMENT",
        "exact_factor_definition": "One frozen treatment factor.",
    })
    protocol["planned_sample_size"] = 2
    protocol["planned_runs"].append({
        "run_key": "run-2", "condition_key": "treatment", "block_key": "block-1",
        "replicate_number": 1, "randomized_ordinal": 2,
        "planned_prompt_text": "Return one governed treatment output.",
        "planned_source_system": "Maestro Beta",
        "applicable_constraint_keys": ["generic-constraint"],
    })
    protocol["outcome_definitions"].append({
        "outcome_key": "subject-rate", "role": "SECONDARY",
        "unit_of_analysis": "registered subject result",
        "outcome_definition": "Registered subject-result event rate.",
        "computation_rule": "Governed by the registered calculator declaration.",
        "missing_data_rule": "Use the registered missing-input policy.",
        "refusal_handling": "Report separately.",
        "operational_failure_handling": "Exclude according to registration.",
    })
    protocol["analysis_definitions"].append({
        "analysis_key": "subject-paired", "outcome_key": "subject-rate",
        "analysis_population": "All registered planned runs.",
        "comparison_definition": "Registered relational condition pairing.",
        "aggregation_rule": "Governed by the registered calculator declaration.",
        "exclusion_rule": "Use the registered missing policy.",
        "reporting_rule": "Descriptive only.",
    })
    protocol["execution_contract"] = {
        "contract_version": "1",
        "outcome_calculation_plans": [
            {
                "outcome_key": "primary",
                "calculator_key": "outcome.constraint_status_rate",
                "calculator_version": "1",
                "input_kind": "CONSTRAINT_RESULTS",
                "output_value_type": "DECIMAL",
                "constraint_bindings": [{
                    "constraint_key": "generic-constraint", "binding_role": "CONTRIBUTOR", "ordinal": 1,
                }],
                "parameters": _rate_parameters(),
                "disposition_policies": _disposition_policies(),
            },
            {
                "outcome_key": "subject-rate",
                "calculator_key": "outcome.subject_status_rate",
                "calculator_version": "1",
                "input_kind": "STRUCTURED_SUBJECT_RESULTS",
                "output_value_type": "DECIMAL",
                "subject_interpretation": "FIELD_PREDICATE",
                "constraint_bindings": [{
                    "constraint_key": "generic-constraint", "binding_role": "CONTRIBUTOR", "ordinal": 1,
                }],
                "subject_kinds": ["PLACEMENT_FIELD"],
                "parameters": _rate_parameters(),
                "disposition_policies": _disposition_policies(),
            },
        ],
        "analysis_calculation_plans": [
            _analysis_plan("primary"), _analysis_plan("subject-paired"),
        ],
    }
    return document


def _service(research_session) -> ResearchStoreService:
    return ResearchStoreService(
        ResearchRepository(research_session), evaluator_registry=_registry()
    )


def _change_constraint_binding(document: dict[str, object]) -> None:
    protocol = document["protocol"]
    alternate = deepcopy(protocol["constraint_definitions"][0])
    alternate["constraint_key"] = "alternate-constraint"
    protocol["constraint_definitions"].append(alternate)
    protocol["execution_contract"]["outcome_calculation_plans"][0]["constraint_bindings"][0][
        "constraint_key"
    ] = "alternate-constraint"


def test_legacy_protocol_has_no_contract_and_keeps_exact_canonical_shape(research_session):
    proposal = StudyRegistrationInput.model_validate(_document(structured=False))
    assert b"execution_contract" not in canonical_protocol_bytes(
        proposal.study_key, proposal.title, proposal.protocol
    )
    registered = _service(research_session).register_study(proposal)
    protocol = registered["registered_protocol"]
    assert protocol["execution_classification"] == "LEGACY_EXECUTION"
    assert protocol["execution_contract"] is None


def test_future_contract_registers_and_reads_all_normalized_declarations(research_session):
    proposal = StudyRegistrationInput.model_validate(_future_document())
    registered = _service(research_session).register_study(proposal)
    protocol = registered["registered_protocol"]
    assert protocol["execution_classification"] == "CALCULATOR_GOVERNED_EXECUTION"
    contract = protocol["execution_contract"]
    assert contract["contract_version"] == "1"
    assert [item["outcome_key"] for item in contract["outcome_calculation_plans"]] == ["primary", "subject-rate"]
    subject = contract["outcome_calculation_plans"][1]
    assert subject["subject_kinds"] == ["PLACEMENT_FIELD"]
    assert subject["subject_interpretation"] == "FIELD_PREDICATE"
    assert [item["text_value"] for item in subject["parameters"] if item["parameter_key"] == "denominator_status"] == ["PASS", "PARTIAL", "FAIL"]
    analysis = contract["analysis_calculation_plans"][0]
    assert analysis["condition_bindings"] == [
        {"comparison_role": "LEFT", "condition_key": "control"},
        {"comparison_role": "RIGHT", "condition_key": "treatment"},
    ]
    assert [(item["dimension_role"], item["dimension_key"]) for item in analysis["dimensions"]] == [
        ("MATCH", "BLOCK"), ("MATCH", "REPLICATE")
    ]
    assert _service(research_session).classify_study_execution(registered["id"], 1)["execution_contract_present"]


@pytest.mark.parametrize("field,mutate", [
    ("contract version", lambda d: d["protocol"]["execution_contract"].update(contract_version="2")),
    ("outcome calculator key", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(calculator_key="outcome.other")),
    ("outcome calculator version", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(calculator_version="2")),
    ("input kind", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(input_kind="STRUCTURED_MEASUREMENTS")),
    ("output type", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(output_value_type="INTEGER")),
    ("constraint binding", _change_constraint_binding),
    ("binding role", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0]["constraint_bindings"][0].update(binding_role="OTHER")),
    ("subject kind", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][1].update(subject_kinds=["EXPERIMENT_PLACEMENT"], subject_interpretation=None)),
    ("parameter value", lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0]["parameters"][0].update(text_value="PARTIAL")),
    ("repeated order", lambda d: [item.update(ordinal=4-item["ordinal"]) for item in d["protocol"]["execution_contract"]["outcome_calculation_plans"][0]["parameters"] if item["parameter_key"] == "denominator_status"]),
    ("analysis calculator", lambda d: d["protocol"]["execution_contract"]["analysis_calculation_plans"][0].update(calculator_version="2")),
    ("dimension", lambda d: d["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["dimensions"][0].update(dimension_key="CONDITION")),
    ("condition direction", lambda d: [item.update(comparison_role="RIGHT" if item["comparison_role"] == "LEFT" else "LEFT") for item in d["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["condition_bindings"]]),
    ("output shape", lambda d: d["protocol"]["execution_contract"]["analysis_calculation_plans"][0].update(output_shape_version="2")),
])
def test_every_future_execution_declaration_is_hash_visible(field, mutate):
    baseline = _future_document()
    changed = deepcopy(baseline)
    mutate(changed)
    left = StudyRegistrationInput.model_validate(baseline)
    right = StudyRegistrationInput.model_validate(changed)
    assert protocol_registration_hash(left.study_key, left.title, left.protocol) != protocol_registration_hash(
        right.study_key, right.title, right.protocol
    ), field


@pytest.mark.parametrize("mutation,match", [
    (lambda d: d["protocol"]["execution_contract"].update(outcome_calculation_plans=d["protocol"]["execution_contract"]["outcome_calculation_plans"][:1]), "every outcome"),
    (lambda d: d["protocol"]["execution_contract"].update(analysis_calculation_plans=d["protocol"]["execution_contract"]["analysis_calculation_plans"][:1]), "every analysis"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(calculator_version="9"), "unsupported outcome calculator"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(input_kind="REALIZATION_DISPOSITION"), "input kind"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0]["constraint_bindings"][0].update(constraint_key="foreign"), "same-protocol constraints"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][1].update(subject_kinds=["RUN"], subject_interpretation=None), "excludes a bound constraint"),
    (lambda d: d["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["condition_bindings"][0].update(condition_key="foreign"), "same-protocol conditions"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0]["parameters"][2].update(ordinal=1), "key/ordinal identities"),
    (lambda d: d["protocol"]["execution_contract"]["outcome_calculation_plans"][0].update(vocabulary_terms=[{"vocabulary_key": "unused", "term_key": "x", "term_definition": "Unused term."}]), "does not support plan-local vocabulary"),
    (lambda d: d["protocol"]["execution_contract"]["analysis_calculation_plans"][0].update(population_scope="OTHER"), "population_scope"),
])
def test_invalid_execution_contract_is_rejected_before_write(research_session, mutation, match):
    document = _future_document()
    mutation(document)
    with pytest.raises(ValueError, match=match):
        proposal = StudyRegistrationInput.model_validate(document)
        _service(research_session).register_study(proposal)
    assert research_session.scalar(select(func.count()).select_from(StudyExecutionContract)) == 0


def test_registered_execution_contract_is_immutable(research_session):
    registered = _service(research_session).register_study(
        StudyRegistrationInput.model_validate(_future_document())
    )
    contract_id = registered["registered_protocol"]["execution_contract"]["id"]
    with pytest.raises(IntegrityError, match="registered execution contract is immutable"):
        research_session.execute(
            text("UPDATE study_execution_contracts SET contract_version='2' WHERE id=:id"),
            {"id": contract_id},
        )
        research_session.commit()
    research_session.rollback()

    protected_tables = {
        "study_execution_contracts",
        "study_outcome_calculation_plans",
        "study_outcome_constraint_bindings",
        "study_outcome_subject_kinds",
        "study_outcome_calculation_parameters",
        "study_outcome_calculation_vocabulary_terms",
        "study_analysis_calculation_plans",
        "study_analysis_dimensions",
        "study_analysis_condition_bindings",
        "study_analysis_calculation_parameters",
    }
    triggers = set(research_session.execute(text(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    )).scalars())
    for table in protected_tables:
        assert f"{table}_no_insert_after_registration" in triggers
        assert f"{table}_no_update_after_registration" in triggers
        assert f"{table}_no_delete_after_registration" in triggers


def test_schema_v8_has_only_protocol_time_execution_tables_and_no_legacy_rows(research_session):
    names = set(inspect(research_session.bind).get_table_names())
    expected = {
        "study_execution_contracts", "study_outcome_calculation_plans",
        "study_outcome_disposition_policies",
        "study_outcome_constraint_bindings", "study_outcome_subject_kinds",
        "study_outcome_calculation_parameters", "study_outcome_calculation_vocabulary_terms",
        "study_analysis_calculation_plans", "study_analysis_dimensions",
        "study_analysis_condition_bindings", "study_analysis_calculation_parameters",
    }
    assert expected <= names
    assert not {"study_outcome_results", "study_analysis_results"} & names
    for name in expected:
        assert research_session.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar_one() == 0


def test_v6_to_v7_migration_is_additive_and_creates_no_legacy_contract(tmp_path):
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'representative-v6.db').as_posix()}")
    assert migrate_research_database(engine) == 9
    factory = make_research_session_factory(engine)
    with factory() as session:
        service = _service(session)
        registered = service.register_study(
            StudyRegistrationInput.model_validate(_document(structured=False))
        )
        stored_hash = registered["registered_protocol"]["registration_hash"]
    e1_tables = [
        "study_outcome_disposition_policies",
        "study_analysis_calculation_parameters",
        "study_analysis_condition_bindings",
        "study_analysis_dimensions",
        "study_analysis_calculation_plans",
        "study_outcome_calculation_vocabulary_terms",
        "study_outcome_calculation_parameters",
        "study_outcome_subject_kinds",
        "study_outcome_constraint_bindings",
        "study_outcome_calculation_plans",
        "study_execution_contracts",
    ]
    with engine.begin() as connection:
        for table in e1_tables:
            connection.exec_driver_sql(f"DROP TABLE {table}")
            connection.execute(text("DELETE FROM schema_version WHERE version IN (7, 8, 9)"))
        connection.execute(text(
            "INSERT INTO schema_version(version, applied_at) VALUES (6, CURRENT_TIMESTAMP)"
        ))
    assert get_schema_version(engine) == 6
    assert migrate_research_database(engine) == 9
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT COUNT(*) FROM studies")) == 1
        assert connection.scalar(text("SELECT registration_hash FROM study_protocol_versions")) == stored_hash
        assert all(connection.scalar(text(f"SELECT COUNT(*) FROM {table}")) == 0 for table in e1_tables)


def test_canonical_order_is_mechanical_but_repeated_parameter_ordinals_are_governed():
    first = _future_document()
    reordered = deepcopy(first)
    contract = reordered["protocol"]["execution_contract"]
    contract["outcome_calculation_plans"].reverse()
    contract["analysis_calculation_plans"].reverse()
    contract["outcome_calculation_plans"][0]["parameters"].reverse()
    contract["analysis_calculation_plans"][0]["dimensions"].reverse()
    left = StudyRegistrationInput.model_validate(first)
    right = StudyRegistrationInput.model_validate(reordered)
    assert canonical_protocol_bytes(left.study_key, left.title, left.protocol) == canonical_protocol_bytes(
        right.study_key, right.title, right.protocol
    )

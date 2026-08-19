from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.database import (
    make_research_engine,
    make_research_session_factory,
)
from playlist_narrative_engine.research_store.migrations import (
    get_schema_version,
    migrate_research_database,
)
from playlist_narrative_engine.research_store.models import StudyOutcomeDispositionPolicy
from playlist_narrative_engine.research_store.study_execution_registry import (
    CalculatorExecutionEnvelope,
    DECIMAL_V1_CONTRACT,
    DISPOSITION_REASON_CODES,
)
from playlist_narrative_engine.research_store.study_protocol import protocol_registration_hash
from playlist_narrative_engine.research_store.study_schemas import (
    StudyRegistrationInput,
    StudyRunDisposition,
)
from test_study_execution_contract_e1 import _future_document, _service


def _plan(document: dict, ordinal: int = 0) -> dict:
    return document["protocol"]["execution_contract"]["outcome_calculation_plans"][ordinal]


def _parameter(plan: dict, key: str) -> list[dict]:
    return [item for item in plan["parameters"] if item["parameter_key"] == key]


def _remove_denominator_status(plan: dict, status: str) -> None:
    plan["parameters"] = [
        item for item in plan["parameters"]
        if not (item["parameter_key"] == "denominator_status" and item["text_value"] == status)
    ]
    for ordinal, item in enumerate(_parameter(plan, "denominator_status"), start=1):
        item["ordinal"] = ordinal


def test_disposition_policy_registers_reads_back_and_changes_hash(research_session):
    document = _future_document()
    proposal = StudyRegistrationInput.model_validate(document)
    baseline_hash = protocol_registration_hash(document["study_key"], document["title"], proposal.protocol)
    registered = _service(research_session).register_study(proposal)
    policies = registered["registered_protocol"]["execution_contract"]["outcome_calculation_plans"][0]["disposition_policies"]
    assert policies == sorted(policies, key=lambda item: item["population_state"])
    assert {item["population_state"] for item in policies} == {
        "EXPERIMENT_RECORDED", "MAESTRO_REFUSAL_RECORDED",
        "MAESTRO_FAILURE_RECORDED", "PENDING",
    }

    changed = deepcopy(document)
    next(item for item in _plan(changed)["disposition_policies"] if item["population_state"] == "MAESTRO_REFUSAL_RECORDED")["treatment"] = "NOT_CALCULABLE"
    changed_proposal = StudyRegistrationInput.model_validate(changed)
    assert protocol_registration_hash(changed["study_key"], changed["title"], changed_proposal.protocol) != baseline_hash

    failure_changed = deepcopy(document)
    next(
        item for item in _plan(failure_changed)["disposition_policies"]
        if item["population_state"] == "MAESTRO_FAILURE_RECORDED"
    )["treatment"] = "MISSING"
    failure_proposal = StudyRegistrationInput.model_validate(failure_changed)
    assert protocol_registration_hash(
        failure_changed["study_key"], failure_changed["title"], failure_proposal.protocol
    ) != baseline_hash


@pytest.mark.parametrize("mutation,match", [
    (lambda p: p["disposition_policies"].pop(), "at least 4 items"),
    (lambda p: p["disposition_policies"].append(deepcopy(p["disposition_policies"][0])), "at most 4 items"),
    (lambda p: p["disposition_policies"][0].update(population_state="OTHER"), "population_state"),
    (lambda p: p["disposition_policies"][0].update(treatment="OTHER"), "treatment"),
    (lambda p: next(item for item in p["disposition_policies"] if item["population_state"] == "PENDING").update(treatment="NOT_CALCULABLE"), "PENDING disposition must use MISSING"),
    (lambda p: next(item for item in p["disposition_policies"] if item["population_state"] == "EXPERIMENT_RECORDED").update(treatment="MISSING"), "EXPERIMENT_RECORDED disposition must use CALCULATE"),
])
def test_disposition_policy_requires_closed_complete_semantics(mutation, match):
    document = _future_document()
    mutation(_plan(document))
    with pytest.raises(ValueError, match=match):
        StudyRegistrationInput.model_validate(document)


@pytest.mark.parametrize("mutation,match", [
    (lambda p: _parameter(p, "numerator_status")[0].update(text_value="UNKNOWN"), "UNKNOWN is governed only"),
    (lambda p: _parameter(p, "denominator_status")[0].update(text_value="UNKNOWN"), "UNKNOWN is governed only"),
    (lambda p: _remove_denominator_status(p, "FAIL"), "subset"),
    (lambda p: _remove_denominator_status(p, "PARTIAL"), "include PASS, PARTIAL, and FAIL"),
])
def test_rate_status_set_invariants_are_registration_conformance(mutation, match):
    document = _future_document()
    mutation(_plan(document))
    proposal = StudyRegistrationInput.model_validate(document)
    with pytest.raises(ValueError, match=match):
        from playlist_narrative_engine.research_store.study_execution_registry import DEFAULT_STUDY_EXECUTION_REGISTRY
        DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(proposal.protocol)


def test_duplicate_rate_status_is_rejected():
    document = _future_document()
    _plan(document)["parameters"].append(deepcopy(_parameter(_plan(document), "numerator_status")[0]))
    with pytest.raises(ValueError, match="identities must be unique"):
        StudyRegistrationInput.model_validate(document)


@pytest.mark.parametrize("key,value", [
    ("pair_completeness", "EXCLUDE_INCOMPLETE"),
    ("missing_policy", "EXCLUDE"),
])
def test_paired_v1_rejects_exclusion_semantics(key, value):
    document = _future_document()
    parameter = next(item for item in document["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["parameters"] if item["parameter_key"] == key)
    parameter["text_value"] = value
    proposal = StudyRegistrationInput.model_validate(document)
    from playlist_narrative_engine.research_store.study_execution_registry import DEFAULT_STUDY_EXECUTION_REGISTRY
    with pytest.raises(ValueError, match="unsupported value"):
        DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(proposal.protocol)


def test_decimal_contract_and_execution_envelope_are_registry_only():
    assert DECIMAL_V1_CONTRACT.precision == 34
    assert DECIMAL_V1_CONTRACT.rounding == "ROUND_HALF_EVEN"
    assert DECIMAL_V1_CONTRACT.notation == "PLAIN_BASE_10"
    assert not DECIMAL_V1_CONTRACT.allow_exponent_notation
    assert not DECIMAL_V1_CONTRACT.allow_leading_plus
    assert DECIMAL_V1_CONTRACT.require_leading_zero_below_one
    assert DISPOSITION_REASON_CODES[("PENDING", "MISSING")] == "PENDING_REGISTERED_RUN"
    CalculatorExecutionEnvelope("UNAVAILABLE", None, None, "CALCULATOR_IMPLEMENTATION_UNAVAILABLE").validate()
    CalculatorExecutionEnvelope("AVAILABLE", "NOT_DERIVABLE", None).validate()
    with pytest.raises(ValueError, match="contradictory"):
        CalculatorExecutionEnvelope("UNAVAILABLE", "NOT_DERIVABLE", None).validate()


def test_operational_attempt_is_not_a_scientific_disposition():
    assert {item.value for item in StudyRunDisposition} == {
        "EXPERIMENT_RECORDED",
        "MAESTRO_REFUSAL_RECORDED",
        "MAESTRO_FAILURE_RECORDED",
    }
    assert "OPERATIONAL_FAILURE" not in {state for state, _ in DISPOSITION_REASON_CODES}


def test_registered_disposition_policy_is_immutable(research_session):
    registered = _service(research_session).register_study(StudyRegistrationInput.model_validate(_future_document()))
    policy_id = registered["registered_protocol"]["execution_contract"]["outcome_calculation_plans"][0]["disposition_policies"][0]["id"]
    with pytest.raises(IntegrityError, match="registered execution contract is immutable"):
        research_session.execute(text("UPDATE study_outcome_disposition_policies SET treatment='MISSING' WHERE id=:id"), {"id": policy_id})
        research_session.commit()
    research_session.rollback()


def test_v7_to_v8_migration_is_additive_and_creates_no_policy_rows(tmp_path):
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'v7.db').as_posix()}")
    assert migrate_research_database(engine) == 9
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE study_outcome_disposition_policies")
        connection.execute(text("DELETE FROM schema_version WHERE version=9"))
        connection.execute(text(
            "INSERT INTO schema_version(version, applied_at) VALUES (7, CURRENT_TIMESTAMP)"
        ))
    assert get_schema_version(engine) == 7
    assert migrate_research_database(engine) == 9
    assert "study_outcome_disposition_policies" in inspect(engine).get_table_names()
    factory = make_research_session_factory(engine)
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(StudyOutcomeDispositionPolicy)) == 0
    engine.dispose()

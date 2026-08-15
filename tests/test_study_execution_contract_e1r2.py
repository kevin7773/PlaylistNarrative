from __future__ import annotations

from copy import deepcopy

import pytest

from playlist_narrative_engine.research_store.study_execution_registry import (
    DEFAULT_STUDY_EXECUTION_REGISTRY,
    applicable_bound_constraint_keys,
)
from playlist_narrative_engine.research_store.study_protocol import protocol_registration_hash
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from test_study_execution_contract_e1 import _future_document


def _proposal(document: dict) -> StudyRegistrationInput:
    return StudyRegistrationInput.model_validate(document)


def test_bound_constraint_population_is_intersection_in_binding_order():
    proposal = _proposal(_future_document())
    plan = proposal.protocol.execution_contract.outcome_calculation_plans[0]
    run = proposal.protocol.planned_runs[0]
    assert applicable_bound_constraint_keys(plan, run) == ("generic-constraint",)

    non_applicable = run.model_copy(update={"applicable_constraint_keys": ["alternate"]})
    assert applicable_bound_constraint_keys(plan, non_applicable) == ()

    applicable_unbound = run.model_copy(
        update={"applicable_constraint_keys": ["generic-constraint", "alternate"]}
    )
    assert applicable_bound_constraint_keys(plan, applicable_unbound) == ("generic-constraint",)


def test_applicability_order_does_not_change_population():
    proposal = _proposal(_future_document())
    plan = proposal.protocol.execution_contract.outcome_calculation_plans[0]
    run = proposal.protocol.planned_runs[0].model_copy(
        update={"applicable_constraint_keys": ["unbound", "generic-constraint"]}
    )
    reversed_run = run.model_copy(update={"applicable_constraint_keys": list(reversed(run.applicable_constraint_keys))})
    assert applicable_bound_constraint_keys(plan, run) == applicable_bound_constraint_keys(plan, reversed_run)


def test_exact_two_condition_left_right_coverage_registers():
    proposal = _proposal(_future_document())
    DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(proposal.protocol)
    bound = {
        item.condition_key
        for plan in proposal.protocol.execution_contract.analysis_calculation_plans
        for item in plan.condition_bindings
    }
    assert bound == {item.condition_key for item in proposal.protocol.conditions}
    assert all(run.condition_key in bound for run in proposal.protocol.planned_runs)


def test_third_condition_is_rejected_without_exclusion_or_narrowing():
    document = _future_document()
    document["protocol"]["conditions"].append({
        "condition_key": "third",
        "label": "Third",
        "role": "TREATMENT",
        "exact_factor_definition": "A third registered condition.",
    })
    proposal = _proposal(document)
    with pytest.raises(ValueError, match="cover every registered condition"):
        DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(proposal.protocol)


def test_duplicate_left_or_right_is_rejected():
    document = _future_document()
    bindings = document["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["condition_bindings"]
    bindings.append(deepcopy(bindings[0]))
    with pytest.raises(ValueError, match="comparison roles must be unique"):
        _proposal(document)


def test_same_condition_on_both_sides_is_rejected():
    document = _future_document()
    bindings = document["protocol"]["execution_contract"]["analysis_calculation_plans"][0]["condition_bindings"]
    bindings[1]["condition_key"] = bindings[0]["condition_key"]
    with pytest.raises(ValueError, match="conditions must be distinct"):
        _proposal(document)


def test_condition_names_are_not_interpreted_and_registry_rule_is_not_hash_visible():
    document = _future_document()
    renamed = deepcopy(document)
    mapping = {"control": "alpha", "treatment": "omega"}
    for condition in renamed["protocol"]["conditions"]:
        condition["condition_key"] = mapping[condition["condition_key"]]
        condition["label"] = "Opaque condition"
    for run in renamed["protocol"]["planned_runs"]:
        run["condition_key"] = mapping[run["condition_key"]]
    for plan in renamed["protocol"]["execution_contract"]["analysis_calculation_plans"]:
        for binding in plan["condition_bindings"]:
            binding["condition_key"] = mapping[binding["condition_key"]]
    proposal = _proposal(renamed)
    DEFAULT_STUDY_EXECUTION_REGISTRY.validate_protocol(proposal.protocol)

    baseline = _proposal(document)
    first = protocol_registration_hash(baseline.study_key, baseline.title, baseline.protocol)
    second = protocol_registration_hash(baseline.study_key, baseline.title, baseline.protocol)
    assert first == second

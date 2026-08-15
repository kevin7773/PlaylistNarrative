from __future__ import annotations

from copy import deepcopy

import pytest

from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
)
from playlist_narrative_engine.research_store.study_protocol import protocol_registration_hash
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    evaluate_structured_constraint,
)
from test_study_structured_evaluation_p7a import _document


def _future_document():
    document = _document(structured=False)
    document["study_key"] = "P7-REFINEMENT"
    definition = document["protocol"]["constraint_definitions"][0]
    definition["permitted_result_provenance"] = "DERIVED_QUERY_RESULT"
    definition["structured_evaluation_plan"] = {
        "instrumentation_version": "1", "subject_kind": "RUN",
        "subject_selector": {"evaluator_key": "selector.run", "evaluator_version": "1"},
        "subject_evaluator": {"evaluator_key": "subject.integer_equals", "evaluator_version": "1"},
        "aggregate_evaluator": {"evaluator_key": "aggregate.single_subject", "evaluator_version": "1"},
        "require_complete_subject_set": True, "allow_partial_subject_status": False,
        "measurement_definitions": [{
            "measurement_key": "observed", "authority": "STRUCTURAL_DERIVATION",
            "value_type": "INTEGER", "required": True, "evidence_required": False,
            "derivation_key": "structural.placement_count", "derivation_version": "1",
            "unavailable_policy": "MUST_HAVE_VALUE",
        }],
        "parameters": [{"parameter_key": "expected", "value_type": "INTEGER", "integer_value": 2}],
    }
    return document


def _proposal(document=None):
    return StudyRegistrationInput.model_validate(document or _future_document())


def test_placement_count_is_derived_deterministically_and_cannot_be_overridden():
    plan = _proposal().protocol.constraint_definitions[0].structured_evaluation_plan.model_dump(mode="json")
    experiment = {"id": 1, "tracks": [{"id": 1, "observed_ordinal": 1}, {"id": 2, "observed_ordinal": 2}]}
    first = evaluate_structured_constraint(plan, experiment, 10, [])
    second = evaluate_structured_constraint(plan, deepcopy(experiment), 10, [])
    assert first == second
    assert first["measurements"][0]["integer_value"] == 2
    assert first["aggregate_constraint_result"]["status"] == "PASS"
    supplied = [{"subject_key": "RUN", "measurement_key": "observed", "authority_kind": "STRUCTURAL_DERIVATION", "value_type": "INTEGER", "integer_value": 99, "recorded_by": "operator", "evidence": []}]
    refused = evaluate_structured_constraint(plan, experiment, 10, supplied)
    assert not refused["complete"]
    assert "DERIVED_VALUE_SUPPLIED" in {item["code"] for item in refused["issues"]}


@pytest.mark.parametrize("mutation,match", [
    (("derivation_key", "structural.unsupported"), "unsupported structural derivation"),
    (("derivation_version", "999"), "unsupported structural derivation"),
    (("value_type", "TEXT"), "measurement definitions|output type"),
])
def test_registration_rejects_invalid_derivation_identity_or_type(mutation, match):
    document = _future_document()
    document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]["measurement_definitions"][0][mutation[0]] = mutation[1]
    proposal = _proposal(document)
    with pytest.raises(ValueError, match=match):
        DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(proposal.protocol)


def test_wrong_subject_and_required_parameter_are_rejected():
    wrong_subject = _future_document()
    plan = wrong_subject["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]
    plan.update(subject_kind="EXPERIMENT_PLACEMENT", subject_selector={"evaluator_key": "selector.all_placements", "evaluator_version": "1"})
    with pytest.raises(ValueError, match="subject kind"):
        DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(_proposal(wrong_subject).protocol)

    required = _future_document()
    measurement = required["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]["measurement_definitions"][0]
    measurement.update(derivation_key="structural.distinct_field_value_count")
    with pytest.raises(ValueError, match="requires parameter governed_field"):
        DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(_proposal(required).protocol)


def test_unavailable_policy_is_machine_enforced_independently_of_unknown_aggregation():
    document = _future_document()
    plan = document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]
    measurement = plan["measurement_definitions"][0]
    measurement.update(authority="DIRECT_OBSERVATION", derivation_key=None, derivation_version=None)
    proposal = _proposal(document)
    frozen = proposal.protocol.constraint_definitions[0].structured_evaluation_plan.model_dump(mode="json")
    unavailable = [{"subject_key": "RUN", "measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION", "value_type": "UNAVAILABLE", "unavailable_reason": "not established", "recorded_by": "operator", "evidence": []}]
    experiment = {"id": 1, "tracks": []}
    refused = evaluate_structured_constraint(frozen, experiment, 1, unavailable)
    assert "UNAVAILABLE_PROHIBITED" in {item["code"] for item in refused["issues"]}
    measurement["unavailable_policy"] = "MAY_BE_UNAVAILABLE"
    allowed = _proposal(document).protocol.constraint_definitions[0].structured_evaluation_plan.model_dump(mode="json")
    result = evaluate_structured_constraint(allowed, experiment, 1, unavailable)
    assert result["complete"] and result["aggregate_constraint_result"]["status"] == "UNKNOWN"
    unavailable[0]["unavailable_reason"] = None
    assert not evaluate_structured_constraint(allowed, experiment, 1, unavailable)["complete"]


def test_future_hash_changes_for_each_new_governed_declaration():
    base = _proposal()
    original = protocol_registration_hash(base.study_key, base.title, base.protocol)
    for path, value in (
        (("derivation_key",), "structural.distinct_field_value_count"),
        (("derivation_version",), "2"),
        (("unavailable_policy",), "MAY_BE_UNAVAILABLE"),
    ):
        changed = _future_document()
        changed["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]["measurement_definitions"][0][path[0]] = value
        candidate = _proposal(changed)
        assert protocol_registration_hash(candidate.study_key, candidate.title, candidate.protocol) != original
    changed_parameter = _future_document()
    changed_parameter["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]["parameters"][0]["integer_value"] = 3
    candidate = _proposal(changed_parameter)
    assert protocol_registration_hash(candidate.study_key, candidate.title, candidate.protocol) != original

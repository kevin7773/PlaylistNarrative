from __future__ import annotations

from copy import deepcopy

import pytest

from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from playlist_narrative_engine.research_store.study_structured_evaluation import (
    evaluate_structured_constraint,
)
from playlist_narrative_engine.research_store.study_vocabulary import (
    STANDALONE_MEMBER_MATCH_CONTRACT_ID,
    STANDALONE_MEMBER_MATCH_CONTRACT_SHA256,
    STANDALONE_MEMBER_MATCH_CONTRACT_VERSION,
    canonical_finite_vocabulary_bytes,
    finite_vocabulary_sha256,
    verify_finite_vocabulary_plan,
    FINITE_VOCABULARY_SCHEMA_VERSION,
)
from test_study_structured_evaluation_p7a import _document


def _text_parameter(key: str, value: str) -> dict[str, object]:
    return {"parameter_key": key, "value_type": "TEXT", "text_value": value}


def _plan(*, terms=("Red", "Blue"), case_sensitive=False) -> dict[str, object]:
    vocabulary_terms = [
        {"vocabulary_key": "registered-colors", "term_key": f"term-{index}", "term_definition": term}
        for index, term in enumerate(terms, start=1)
    ]
    digest = finite_vocabulary_sha256(
        vocabulary_id="fixture.colors",
        vocabulary_version="1.0",
        vocabulary_key="registered-colors",
        terms=vocabulary_terms,
    )
    return {
        "instrumentation_version": "1",
        "subject_kind": "PLACEMENT_FIELD",
        "subject_field": "display_title",
        "subject_selector": {"evaluator_key": "selector.all_placements", "evaluator_version": "1"},
        "subject_evaluator": {"evaluator_key": "subject.lexical_any_vocabulary_member", "evaluator_version": "1"},
        "aggregate_evaluator": {"evaluator_key": "aggregate.all_subjects_required", "evaluator_version": "1"},
        "require_complete_subject_set": True,
        "allow_partial_subject_status": False,
        "measurement_definitions": [{
            "measurement_key": "observed-title", "authority": "DIRECT_OBSERVATION",
            "value_type": "TEXT", "required": True, "evidence_required": False,
            "unavailable_policy": "MAY_BE_UNAVAILABLE",
        }],
        "parameters": [
            _text_parameter("vocabulary_key", "registered-colors"),
            _text_parameter("vocabulary_schema_version", FINITE_VOCABULARY_SCHEMA_VERSION),
            _text_parameter("vocabulary_id", "fixture.colors"),
            _text_parameter("vocabulary_version", "1.0"),
            _text_parameter("vocabulary_sha256", digest),
            _text_parameter("matching_contract_id", STANDALONE_MEMBER_MATCH_CONTRACT_ID),
            _text_parameter("matching_contract_version", STANDALONE_MEMBER_MATCH_CONTRACT_VERSION),
            _text_parameter("matching_contract_sha256", STANDALONE_MEMBER_MATCH_CONTRACT_SHA256),
            {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": case_sensitive},
            _text_parameter("mixed_status", "FAIL"),
            _text_parameter("all_fail_status", "FAIL"),
            _text_parameter("unknown_status", "UNKNOWN"),
        ],
        "vocabulary_terms": vocabulary_terms,
    }


def _experiment(titles: tuple[str, ...]) -> dict[str, object]:
    return {
        "id": 7,
        "tracks": [
            {"id": 100 + index, "observed_ordinal": index, "display_title": title,
             "display_artist": "Red" if index == 1 else "Artist"}
            for index, title in enumerate(titles, start=1)
        ],
    }


def _measurements(titles: tuple[str | None, ...]) -> list[dict[str, object]]:
    rows = []
    for index, title in enumerate(titles, start=1):
        rows.append({
            "subject_key": f"FIELD:{100 + index}:display_title",
            "measurement_key": "observed-title", "authority_kind": "DIRECT_OBSERVATION",
            "value_type": "UNAVAILABLE" if title is None else "TEXT",
            "boolean_value": None, "integer_value": None, "decimal_value": None,
            "text_value": title, "date_value": None, "vocabulary_term_key": None,
            "unavailable_reason": "title not established" if title is None else None,
            "evidence": [],
        })
    return rows


def _evaluate(titles: tuple[str, ...], observed: tuple[str | None, ...] | None = None):
    return evaluate_structured_constraint(
        _plan(), _experiment(titles), 42, _measurements(observed or titles)
    )


def test_any_registered_standalone_member_passes_and_multiple_matches_are_deterministic() -> None:
    result = _evaluate(("Red Morning", "Blue Red Sky"))
    assert [item["status"] for item in result["subject_results"]] == ["PASS", "PASS"]
    assert result["aggregate_constraint_result"]["status"] == "PASS"
    assert result["subject_results"][1]["reason_code"] == "STANDALONE_VOCABULARY_MEMBER_PRESENT"


def test_wrong_field_match_remains_fail_and_one_failure_fails_universal_aggregate() -> None:
    result = _evaluate(("Plain Song", "Blue Moon"))
    assert result["subjects"][0]["governed_field"] == "display_title"
    assert result["subject_results"][0]["status"] == "FAIL"  # Artist "Red" is irrelevant.
    assert result["subject_results"][1]["status"] == "PASS"
    assert result["aggregate_constraint_result"]["status"] == "FAIL"


def test_unavailable_governed_field_is_unknown_not_pass() -> None:
    result = _evaluate(("Red Morning",), (None,))
    assert result["subject_results"][0]["status"] == "UNKNOWN"
    assert result["aggregate_constraint_result"]["status"] == "UNKNOWN"


def test_vocabulary_canonicalization_is_order_independent_and_mutation_changes_digest() -> None:
    plan = _plan()
    terms = plan["vocabulary_terms"]
    arguments = {
        "vocabulary_id": "fixture.colors", "vocabulary_version": "1.0",
        "vocabulary_key": "registered-colors",
    }
    assert canonical_finite_vocabulary_bytes(terms=terms, **arguments) == canonical_finite_vocabulary_bytes(terms=reversed(terms), **arguments)
    changed = deepcopy(terms)
    changed[0]["term_definition"] = "Green"
    assert finite_vocabulary_sha256(terms=terms, **arguments) != finite_vocabulary_sha256(terms=changed, **arguments)


@pytest.mark.parametrize("parameter", ["vocabulary_sha256", "matching_contract_sha256", "matching_contract_version"])
def test_vocabulary_or_matching_contract_substitution_is_rejected(parameter: str) -> None:
    plan = _plan()
    values = {
        item["parameter_key"]: item.get("boolean_value", item.get("text_value"))
        for item in plan["parameters"]
    }
    values[parameter] = "0" * 64 if parameter.endswith("sha256") else "substituted"
    with pytest.raises(ValueError):
        verify_finite_vocabulary_plan(plan, values)


def test_registered_protocol_accepts_verified_generic_vocabulary_plan() -> None:
    document = _document(structured=True)
    document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"] = _plan()
    protocol = StudyRegistrationInput.model_validate(document).protocol
    DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(protocol)


def test_protocol_validation_rejects_mutated_vocabulary_under_stale_digest() -> None:
    document = _document(structured=True)
    plan = _plan()
    plan["vocabulary_terms"][0]["term_definition"] = "Green"
    document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"] = plan
    protocol = StudyRegistrationInput.model_validate(document).protocol
    with pytest.raises(ValueError, match="digest"):
        DEFAULT_STUDY_EVALUATOR_REGISTRY.validate_protocol(protocol)


def test_favorable_semantic_assessment_can_coexist_with_hard_constraint_failure() -> None:
    experiment = ExperimentInput.model_validate({
        "assessment_outcome": "PASS",
        "tracklist_completeness": "PARTIAL",
        "tracks": [{"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1,
                    "title": "Plain Song", "artist": "Artist"}],
        "constraints": [{
            "constraint_type": "field_predicate", "constraint_text": "Registered field predicate.",
            "is_hard_constraint": True,
            "result": {"status": "FAIL", "provenance_type": "DERIVED_QUERY_RESULT"},
        }],
    })
    assert experiment.assessment_outcome.value == "PASS"
    assert experiment.constraints[0].result.status.value == "FAIL"

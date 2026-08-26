from __future__ import annotations

from copy import deepcopy

from playlist_narrative_engine.research_store.animal_vocabulary import (
    ANIMAL_VOCABULARY_TERMS,
    animal_vocabulary_parameters,
)
from playlist_narrative_engine.research_store.study_exploration import explore_study


def _constraint(identifier, key, kind, status, *, hard=True):
    return {
        "definition_id": identifier, "constraint_key": key,
        "constraint_type": kind, "constraint_text": key,
        "is_hard_constraint": hard, "evaluation_rule": "Frozen.",
        "unknown_handling": "UNKNOWN remains missing.",
        "constraint_result_id": identifier * 100,
        "status": status, "evidence": "Structured result already recorded.",
        "provenance_type": "DIRECT_OBSERVATION", "provenance_notes": None,
    }


def _run(identifier, condition, replicate, exact, rule, metadata):
    constraints = [
        _constraint(10 + identifier, "ten_tracks", "exact_cardinality", exact),
        _constraint(20 + identifier, "different_rule", "synthetic_rule", rule),
        _constraint(30 + identifier, "metadata_notice", "metadata_requirement_acknowledgment", metadata, hard=False),
    ]
    divergence = int(metadata == "PASS" and rule in {"PARTIAL", "FAIL"})
    return {
        "planned_run_id": identifier, "run_key": f"run-{identifier}",
        "randomized_ordinal": identifier, "condition_key": condition,
        "block_key": "different-block", "replicate_number": replicate,
        "attempts": [], "realization": {"id": identifier, "disposition": "EXPERIMENT_RECORDED"},
        "experiment_id": 1000 + identifier, "generation_failure_id": None,
        "constraints": constraints,
        "outcomes": [{"outcome_key": "divergence", "strategy": "METADATA_CONSTRUCTION_DIVERGENCE",
                      "status": "CALCULATED", "value": divergence,
                      "source_constraint_result_ids": [constraints[1]["constraint_result_id"], constraints[2]["constraint_result_id"]]}],
    }


def _evaluation():
    return {
        "study_id": 88, "study_key": "OTHER-STUDY", "protocol_version_id": 17,
        "protocol_version": 3, "registration_hash": "c" * 64,
        "summary": {"registered_condition_roles": {"BASELINE": "CONTROL", "STORY": "TREATMENT"}},
        "runs": [
            _run(1, "BASELINE", 1, "PASS", "PASS", "PASS"),
            _run(2, "STORY", 1, "FAIL", "PARTIAL", "PASS"),
            _run(3, "BASELINE", 2, "UNKNOWN", "PASS", "PARTIAL"),
            _run(4, "STORY", 2, "PARTIAL", "FAIL", "FAIL"),
        ],
    }


def test_exploration_preserves_statuses_roles_and_governed_contributors():
    evaluation = _evaluation(); original = deepcopy(evaluation)
    experiments = {1001: {"generated_track_count": 10}, 1002: {"generated_track_count": 8},
                   1003: {"generated_track_count": None}, 1004: {"generated_track_count": 11}}
    result = explore_study(evaluation, experiments.get)
    exact = next(item for item in result["constraint_matrix"] if item["constraint_key"] == "ten_tracks")
    assert exact["conditions"]["BASELINE"]["PASS"] == 1
    assert exact["conditions"]["BASELINE"]["UNKNOWN"] == 1
    assert exact["conditions"]["STORY"]["FAIL"] == 1
    assert exact["conditions"]["STORY"]["PARTIAL"] == 1
    assert exact["descriptive_binary_difference"]["control_condition_key"] == "BASELINE"
    assert exact["descriptive_binary_difference"]["treatment_condition_key"] == "STORY"
    assert all(item["run_key"] and item["constraint_result_id"] for item in exact["contributors"])
    assert result["track_level_analysis"]["status"] == "NOT_DERIVABLE"
    assert result["provenance"]["free_text_parsing"] == "none"
    assert evaluation == original


def test_exact_count_and_replicate_diagnostics_use_structured_values_only():
    evaluation = _evaluation()
    experiments = {1001: {"generated_track_count": 10}, 1002: {"generated_track_count": 8},
                   1003: {"generated_track_count": None}, 1004: {"generated_track_count": 11}}
    result = explore_study(evaluation, experiments.get)
    diagnostics = result["exact_count_diagnostics"]
    assert diagnostics["by_condition"]["BASELINE"]["UNKNOWN"] == 1
    assert [item["generated_track_count"] for item in diagnostics["contributors"]] == [10, 8, None, 11]
    assert len(diagnostics["matched_pairs"]) == 2
    assert {item["replicate_number"] for item in result["constraint_by_replicate"]} == {1, 2}
    assert all("evidence" not in item for item in diagnostics["contributors"])


def test_metadata_cross_view_is_descriptive_and_generic():
    result = explore_study(_evaluation(), lambda identifier: {"generated_track_count": 10})
    assert result["study_id"] == 88 and result["study_key"] == "OTHER-STUDY"
    assert any(cell["metadata_status"] == "PASS" and cell["hard_compliance_status"] == "FAIL"
               for cell in result["metadata_cross_view"]["cells"])
    assert all(cell["contributors"] for cell in result["metadata_cross_view"]["cells"])
    assert result["synopsis"]["label"] == "EXPLORATORY DESCRIPTIVE SUMMARY — NOT A REGISTERED STUDY CONCLUSION"


def test_finite_vocabulary_failure_modes_preserve_field_scope_and_ambiguity():
    plan = {
        "subject_kind": "PLACEMENT_FIELD",
        "subject_evaluator": {
            "evaluator_key": "subject.lexical_any_vocabulary_member",
            "evaluator_version": "1",
        },
        "parameters": list(animal_vocabulary_parameters()),
        "vocabulary_terms": list(ANIMAL_VOCABULARY_TERMS),
    }
    protocol = {
        "constraint_definitions": [{
            "id": 19, "constraint_key": "animal-title",
            "structured_evaluation_plan": plan,
        }],
    }
    constraints = [{
        "definition_id": 19, "constraint_id": 301,
        "constraint_result_id": 401, "constraint_key": "animal-title",
    }]
    evaluation = {
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "study_id": 5, "study_key": "FIELD-SCOPE", "protocol_version_id": 7,
        "protocol_version": 1, "registration_hash": "a" * 64,
        "runs": [{
            "planned_run_id": 1, "run_key": "left-r01", "condition_key": "condition-a",
            "block_key": "b01", "replicate_number": 1, "experiment_id": 201,
            "constraints": constraints,
        }],
    }
    experiment = {"tracks": [
        {"id": 1, "title": "Blackbird", "artist": "The Beatles"},
        {"id": 2, "title": "Hotel California", "artist": "Eagles"},
        {"id": 3, "title": "Black Math", "artist": "The White Stripes"},
        {"id": 4, "title": "Obscured", "artist": "A-Ha"},
    ]}
    statuses = ("PASS", "FAIL", "FAIL", "UNKNOWN")
    structured = {
        "instrumentation_classification": "STRUCTURED_DERIVABLE",
        "subjects": [{
            "id": 100 + index, "subject_kind": "PLACEMENT_FIELD",
            "experiment_track_id": index, "governed_field": "display_title",
            "enumeration_ordinal": index,
            "measurements": [{"id": 200 + index, "evidence": []}],
            "result": {"id": 300 + index, "status": status},
        } for index, status in enumerate(statuses, 1)],
    }
    original_evaluation = deepcopy(evaluation)
    result = explore_study(
        evaluation, lambda _: experiment, lambda _: structured, protocol
    )["finite_vocabulary_field_failure_analysis"]

    combined = next(item for item in result["summaries"] if item["population"] == "COMBINED")
    assert combined["counts"] == {
        "LITERAL_TITLE_PASS": 1,
        "ARTIST_FIELD_SUBSTITUTION": 1,
        "SEMANTIC_ASSOCIATIVE_RELATION": None,
        "UNCLASSIFIED_NONMATCH": 1,
        "UNKNOWN_UNAVAILABLE": 1,
    }
    by_title = {item["title"]: item for item in result["classifications"]}
    assert by_title["Hotel California"]["failure_mode"] == "ARTIST_FIELD_SUBSTITUTION"
    assert by_title["Black Math"]["failure_mode"] == "UNCLASSIFIED_NONMATCH"
    assert by_title["Obscured"]["failure_mode"] == "UNKNOWN_UNAVAILABLE"
    assert result["classification_authority"]["semantic_associative_relation"].startswith("NOT_DERIVABLE")
    assert evaluation == original_evaluation


def test_calculator_exploration_without_protocol_does_not_guess_vocabulary_authority():
    evaluation = {
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "study_id": 1, "study_key": "NO-PROTOCOL", "protocol_version_id": 1,
        "protocol_version": 1, "registration_hash": "b" * 64, "runs": [],
    }
    result = explore_study(evaluation, lambda _: None, lambda _: None)
    assert result["finite_vocabulary_field_failure_analysis"]["status"] == "NOT_DERIVABLE"

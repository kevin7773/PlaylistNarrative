from __future__ import annotations

from copy import deepcopy

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

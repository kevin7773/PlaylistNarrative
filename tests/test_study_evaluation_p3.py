from __future__ import annotations

from copy import deepcopy

from playlist_narrative_engine.research_store.study_evaluation import (
    evaluate_registered_study,
)


def _definition(identifier, key, constraint_type, *, hard=True):
    return {"id": identifier, "constraint_key": key, "constraint_type": constraint_type,
            "constraint_text": key, "is_hard_constraint": hard,
            "evaluation_rule": "Frozen.", "permitted_result_provenance": "DIRECT_OBSERVATION",
            "unknown_handling": "UNKNOWN is not imputed."}


def _outcome(identifier, key, definition, computation, *, role="SECONDARY"):
    return {"id": identifier, "outcome_key": key, "role": role,
            "unit_of_analysis": "one planned run", "outcome_definition": definition,
            "computation_rule": computation, "missing_data_rule": "UNKNOWN remains missing.",
            "refusal_handling": "Separate.", "operational_failure_handling": "Exclude."}


def _analysis(identifier, key, outcome, comparison, aggregation="Report raw values."):
    return {"id": identifier, "analysis_key": key, "outcome_key": outcome,
            "analysis_population": "Matched registered runs with calculable values.",
            "comparison_definition": comparison, "aggregation_rule": aggregation,
            "exclusion_rule": "Report missing values and do not impute.",
            "reporting_rule": "Descriptive only."}


def _protocol():
    outcomes = [
        _outcome(1, "primary", "Proportion of the run’s two applicable hard constraints completely satisfied.", "Score PASS=1 and PARTIAL/FAIL=0, then divide by 2.", role="PRIMARY"),
        _outcome(2, "track-rate", "Proportion of evaluated observed tracks that violate the block constraint.", "Divide failing evaluated observed tracks by evaluated observed tracks."),
        _outcome(3, "violated", "Number of the run’s two applicable hard constraints with a PARTIAL or FAIL result.", "Count PARTIAL or FAIL."),
        _outcome(4, "count", "Whether the output satisfies the common exactly-10-tracks constraint.", "Return 1 for exact_count_10 PASS, otherwise 0."),
        _outcome(5, "disposition", "Terminal Maestro disposition using StudyRunDisposition.", "Use governed StudyRunDisposition."),
        _outcome(6, "ack", "Whether metadata explicitly and unambiguously acknowledges the requirement.", "Use the metadata constraint result."),
        _outcome(7, "divergence", "Whether metadata acknowledges the requirement while track construction does not.", "Return 1 for divergence."),
    ]
    analyses = [
        _analysis(1, "paired-primary", "primary", "For each block and replicate calculate NARRATIVE minus CONTROL."),
        _analysis(2, "track-comparison", "track-rate", "For each block and replicate calculate NARRATIVE minus CONTROL."),
        _analysis(3, "count-comparison", "count", "For each block and replicate calculate NARRATIVE minus CONTROL."),
        _analysis(4, "disposition-summary", "disposition", "Compare terminal dispositions.", "Report counts and proportions."),
        _analysis(5, "divergence-summary", "divergence", "Compare by condition and block.", "Report counts and proportions."),
        _analysis(6, "replicate-consistency", "primary", "Compare the replicate-1 and replicate-2 NARRATIVE-minus-CONTROL differences.", "Report both replicate differences."),
    ]
    runs = []
    ordinal = 1
    experiment_id = 100
    for replicate in (1, 2):
        for condition in ("C", "T"):
            runs.append({"id": ordinal, "run_key": f"b1-{condition}-{replicate}",
                         "condition_key": condition, "block_key": "b1",
                         "replicate_number": replicate, "randomized_ordinal": ordinal,
                         "applicable_constraint_keys": ["exact_count_10", "block", "metadata"],
                         "attempts": [], "realization": {"id": ordinal,
                         "planned_run_id": ordinal, "disposition": "EXPERIMENT_RECORDED",
                         "experiment_id": experiment_id, "generation_failure_id": None,
                         "realized_at": "2026-01-01T00:00:00"}})
            ordinal += 1; experiment_id += 1
    return {"study_id": 42, "study_key": "GENERIC", "title": "Generic",
            "id": 9, "version_number": 2, "registration_hash": "a" * 64,
            "conditions": [{"condition_key": "C", "role": "CONTROL"},
                           {"condition_key": "T", "role": "TREATMENT"}],
            "constraint_definitions": [_definition(1, "exact_count_10", "exact_cardinality"),
                                       _definition(2, "block", "lexical_title"),
                                       _definition(3, "metadata", "metadata_requirement_acknowledgment", hard=False)],
            "outcome_definitions": outcomes, "analysis_definitions": analyses,
            "planned_runs": runs}


def _experiment(experiment_id, exact="PASS", block="PASS", metadata="PASS"):
    statuses = [(1, "exact_cardinality", exact, True), (2, "lexical_title", block, True),
                (3, "metadata_requirement_acknowledgment", metadata, False)]
    return {"id": experiment_id, "constraints": [
        {"id": experiment_id * 10 + definition_id,
         "study_constraint_definition_id": definition_id,
         "constraint_type": constraint_type, "constraint_text": constraint_type,
         "is_hard_constraint": hard,
         "result": {"status": status, "evidence": f"Evidence for {status}",
                    "provenance_type": "DIRECT_OBSERVATION", "provenance_notes": None}}
        for definition_id, constraint_type, status, hard in statuses]}


def _experiments(protocol):
    values = {}
    for run in protocol["planned_runs"]:
        treatment = run["condition_key"] == "T"
        values[run["realization"]["experiment_id"]] = _experiment(
            run["realization"]["experiment_id"], block="PARTIAL" if treatment else "PASS"
        )
    return values


def test_completed_study_derives_registered_results_without_mutation():
    protocol = _protocol(); original = deepcopy(protocol); experiments = _experiments(protocol)
    result = evaluate_registered_study(protocol, experiments.get)
    assert result["completion"] == {
        "planned_runs": 4, "realized_runs": 4, "pending_runs": 0,
        "executable_runs": 0, "refusal_count": 0, "generation_failure_count": 0,
        "operational_attempt_count": 0, "collection_complete": True,
        "primary_analysis_fully_calculable": True,
    }
    assert result["study_id"] == 42 and result["protocol_version_id"] == 9
    assert result["registration_hash"] == "a" * 64
    assert protocol == original
    primary = next(item for item in result["analyses"] if item["analysis_key"] == "paired-primary")
    assert [item["difference"] for item in primary["raw_results"]] == [-0.5, -0.5]
    replicate = next(item for item in result["analyses"] if item["analysis_key"] == "replicate-consistency")
    assert replicate["raw_results"][0]["classification"] == "CONCORDANT_NEGATIVE"
    track = next(item for item in result["analyses"] if item["analysis_key"] == "track-comparison")
    assert track["status"] == "NOT_DERIVABLE"


def test_unknown_is_missing_and_pair_exclusion_is_explicit():
    protocol = _protocol(); experiments = _experiments(protocol)
    first_treatment = next(run for run in protocol["planned_runs"] if run["condition_key"] == "T")
    experiments[first_treatment["realization"]["experiment_id"]] = _experiment(
        first_treatment["realization"]["experiment_id"], block="UNKNOWN"
    )
    result = evaluate_registered_study(protocol, experiments.get)
    run = next(item for item in result["runs"] if item["run_key"] == first_treatment["run_key"])
    primary = next(item for item in run["outcomes"] if item["outcome_key"] == "primary")
    assert primary["status"] == "MISSING" and primary["value"] is None
    analysis = next(item for item in result["analyses"] if item["analysis_key"] == "paired-primary")
    assert len(analysis["raw_results"]) == 1 and len(analysis["exclusions"]) == 1
    assert first_treatment["run_key"] in analysis["exclusions"][0]["treatment_run_key"]


def test_refusal_and_pending_runs_never_receive_compliance_scores():
    protocol = _protocol(); experiments = _experiments(protocol)
    refusal, pending = protocol["planned_runs"][:2]
    refusal["realization"] = {"id": 77, "planned_run_id": refusal["id"],
                              "disposition": "MAESTRO_REFUSAL_RECORDED",
                              "experiment_id": None, "generation_failure_id": 88,
                              "realized_at": "2026-01-01T00:00:00"}
    pending["realization"] = None
    result = evaluate_registered_study(protocol, experiments.get)
    assert not result["completion"]["collection_complete"]
    assert result["completion"]["refusal_count"] == 1
    for run_key in (refusal["run_key"], pending["run_key"]):
        run = next(item for item in result["runs"] if item["run_key"] == run_key)
        primary = next(item for item in run["outcomes"] if item["outcome_key"] == "primary")
        assert primary["status"] == "MISSING" and primary["value"] is None


def test_pairing_uses_registered_roles_block_and_replicate_not_ids():
    protocol = _protocol(); protocol["study_id"] = 9876
    protocol["conditions"] = [{"condition_key": "BASE", "role": "CONTROL"},
                              {"condition_key": "STORY", "role": "TREATMENT"}]
    for run in protocol["planned_runs"]:
        run["condition_key"] = "BASE" if run["condition_key"] == "C" else "STORY"
    experiments = _experiments(protocol)
    result = evaluate_registered_study(protocol, experiments.get)
    analysis = next(item for item in result["analyses"] if item["analysis_key"] == "paired-primary")
    assert len(analysis["raw_results"]) == 2
    assert all(item["block_key"] == "b1" for item in analysis["raw_results"])


def test_protocol_versions_are_evaluated_as_independent_projections():
    first = _protocol(); second = deepcopy(first)
    second["id"] = 10; second["version_number"] = 3; second["registration_hash"] = "b" * 64
    second["planned_runs"] = second["planned_runs"][:2]
    first_result = evaluate_registered_study(first, _experiments(first).get)
    second_result = evaluate_registered_study(second, _experiments(second).get)
    assert first_result["protocol_version_id"] == 9 and len(first_result["runs"]) == 4
    assert second_result["protocol_version_id"] == 10 and len(second_result["runs"]) == 2
    assert second_result["registration_hash"] == "b" * 64

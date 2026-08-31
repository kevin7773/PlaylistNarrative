from __future__ import annotations

from copy import deepcopy

from playlist_narrative_engine.research_store.study_closeout import (
    build_study_closeout,
    closeout_json_bytes,
    closeout_markdown,
)


def _inputs(*, complete=True):
    protocol = {
        "study_id": 707, "study_key": "GENERIC-CLOSEOUT", "title": "Generic closeout",
        "id": 33, "version_number": 4, "registration_hash": "d" * 64,
        "registered_at": "2026-01-01T00:00:00", "objective": "Compare frozen conditions.",
        "primary_hypothesis": "Treatment difference is negative.",
        "null_hypothesis": "Treatment difference is zero.",
        "conditions": [{"condition_key": "BASE", "role": "CONTROL"}, {"condition_key": "STORY", "role": "TREATMENT"}],
        "blocks": [{"block_key": "Z9", "label": "Other block"}],
        "constraint_definitions": [{"constraint_key": "other_constraint", "constraint_type": "other", "constraint_text": "Frozen other constraint."}],
        "outcome_definitions": [{"outcome_key": "primary", "role": "PRIMARY"}],
        "analysis_definitions": [{"analysis_key": "paired", "outcome_key": "primary", "reporting_rule": "Descriptive only."}],
        "planned_runs": [{"id": 1, "run_key": "base", "condition_key": "BASE", "block_key": "Z9", "replicate_number": 1, "randomized_ordinal": 1}],
    }
    realization = {"id": 1, "disposition": "EXPERIMENT_RECORDED"} if complete else None
    analysis = {"analysis_key": "paired", "outcome_key": "primary", "status": "CALCULATED" if complete else "MISSING", "reason": None,
                "aggregate": {"pair_count": 1, "mean_difference": -0.25, "negative": 1, "zero": 0, "positive": 0} if complete else None,
                "exclusions": [], "raw_results": [], "registered_definition": {"reporting_rule": "Descriptive only."}}
    evaluation = {
        "projection_type": "DERIVED_READ_ONLY_STUDY_EVALUATION", "study_id": 707,
        "study_key": "GENERIC-CLOSEOUT", "protocol_version_id": 33, "protocol_version": 4,
        "registration_hash": "d" * 64,
        "completion": {"planned_runs": 1, "realized_runs": 1 if complete else 0,
                       "pending_runs": 0 if complete else 1, "executable_runs": 0 if complete else 1,
                       "refusal_count": 0, "generation_failure_count": 0,
                       "operational_attempt_count": 0, "collection_complete": complete,
                       "primary_analysis_fully_calculable": complete},
        "runs": [{"planned_run_id": 1, "run_key": "base", "realization": realization,
                  "experiment_id": 901 if complete else None, "generation_failure_id": None,
                  "constraints": [{"constraint_result_id": 801, "status": "PASS"}] if complete else [],
                  "outcomes": []}],
        "analyses": [analysis],
        "summary": {"primary_outcome_key": "primary", "primary_by_condition": [{"condition_key": "BASE", "calculable_runs": 1, "mean": 1.0}],
                    "primary_paired_analysis": analysis, "primary_block_comparison": [],
                    "replicate_consistency": None, "constraint_result_counts": {"PASS": 1} if complete else {},
                    "metadata_acknowledgment_counts": {}, "metadata_divergence_counts": {}},
    }
    exploration = None if not complete else {
        "projection_type": "EXPLORATORY_READ_ONLY_STUDY_ANALYSIS",
        "synopsis": {"label": "EXPLORATORY DESCRIPTIVE SUMMARY — NOT A REGISTERED STUDY CONCLUSION",
                     "constraint_type_count": 1, "constraint_keys_with_fail": [], "constraint_keys_with_partial": []},
        "track_level_analysis": {"status": "NOT_DERIVABLE", "reason": "No governed per-track results."},
        "exact_count_diagnostics": {"by_condition": {}},
        "constraint_result_concentration": {"totals": {"PASS": 1}},
        "metadata_cross_view": {"cells": []},
        "constraint_matrix": [{"constraint_key": "other_constraint", "constraint_type": "other", "conditions": {"BASE": {"PASS": 1}}}],
    }
    experiments = {901: {"evidence_sources": [{"id": 71, "source_key": "source_1", "source_type": "SCREENSHOT", "source_reference": "Explicit reference", "original_filename": "one.png", "sha256": "a" * 64}]}}
    return protocol, evaluation, exploration, experiments


def test_closeout_is_deterministic_except_declared_generation_time_and_preserves_inputs():
    protocol, evaluation, exploration, experiments = _inputs()
    originals = deepcopy((protocol, evaluation, exploration, experiments))
    first = build_study_closeout(protocol, evaluation, exploration, experiments.get, generated_at="2026-01-01T01:00:00+00:00", repository_revision="abc123")
    second = build_study_closeout(protocol, evaluation, exploration, experiments.get, generated_at="2026-01-02T01:00:00+00:00", repository_revision="abc123")
    assert first["deterministic_payload_sha256"] == second["deterministic_payload_sha256"]
    assert first["report_generation"]["generated_at"] != second["report_generation"]["generated_at"]
    assert first["registered_results"] is evaluation
    assert first["exploratory_not_preregistered"] is exploration
    assert (protocol, evaluation, exploration, experiments) == originals
    assert first["reproducibility_manifest"]["experiment_ids"] == [901]
    assert first["reproducibility_manifest"]["constraint_result_ids"] == [801]
    assert first["reproducibility_manifest"]["source_identifiers"][0]["source_key"] == "source_1"


def test_closeout_preserves_registered_exploratory_and_not_derivable_boundaries():
    protocol, evaluation, exploration, experiments = _inputs()
    report = build_study_closeout(protocol, evaluation, exploration, experiments.get, generated_at="fixed", repository_revision=None)
    assert report["collection_status"] == "STUDY COMPLETE — REGISTERED ANALYSIS AVAILABLE"
    assert report["scientific_conclusion_boundary"]["registered_direction"] == "NEGATIVE"
    assert report["follow_up_readiness"]["unresolved_not_derivable_questions"] == ["track_level_exploratory_analysis"]
    markdown = closeout_markdown(report)
    assert "## REGISTERED RESULTS" in markdown
    assert "## EXPLORATORY — NOT PREREGISTERED" in markdown
    assert "NOT_DERIVABLE" in markdown
    assert "no significance, causal, or general-population claim" in markdown
    assert closeout_json_bytes(report).endswith(b"\n")


def test_incomplete_study_cannot_be_labeled_complete():
    protocol, evaluation, exploration, experiments = _inputs(complete=False)
    report = build_study_closeout(protocol, evaluation, exploration, experiments.get, generated_at="fixed")
    assert report["collection_status"] == "COLLECTION INCOMPLETE"
    assert report["reproducibility_manifest"]["unresolved_planned_run_keys"] == ["base"]
    assert not report["follow_up_readiness"]["registered_findings_available"]
    assert not report["follow_up_readiness"]["exploratory_findings_available"]


def test_calculator_closeout_markdown_renders_authoritative_pairs_and_distinct_populations():
    protocol, evaluation, exploration, experiments = _inputs()
    report = build_study_closeout(
        protocol, evaluation, exploration, experiments.get,
        generated_at="fixed", repository_revision="abc123",
    )
    primary_pairs = [
        {
            "dimensions": [
                {"dimension_key": "BLOCK", "value": "b01"},
                {"dimension_key": "REPLICATE", "value": 1},
            ],
            "left_decimal": "0.4", "right_decimal": "0.5",
            "difference": "0.1", "pair_state": "CALCULATED", "reason_code": None,
        },
        {
            "dimensions": [
                {"dimension_key": "BLOCK", "value": "b01"},
                {"dimension_key": "REPLICATE", "value": 2},
            ],
            "left_decimal": "0.6", "right_decimal": None,
            "difference": None, "pair_state": "NOT_CALCULABLE",
            "reason_code": "RIGHT_MEMBER_MISSING",
        },
    ]
    secondary_pairs = [{
        "dimensions": [
            {"dimension_key": "BLOCK", "value": "b01"},
            {"dimension_key": "REPLICATE", "value": 1},
        ],
        "left_decimal": "0", "right_decimal": "0", "difference": "0",
        "pair_state": "CALCULATED", "reason_code": None,
    }]
    report["registered_results"]["execution_classification"] = "CALCULATOR_GOVERNED_EXECUTION"
    report["registered_results"]["analyses"] = [
        {
            "analysis_key": "paired-placement-compliance-difference",
            "outcome_key": "placement-compliance-rate", "status": "CALCULATED",
            "reason": None,
            "calculator_key": "analysis.paired_difference", "raw_results": primary_pairs,
            "exclusions": [{"dimensions": primary_pairs[1]["dimensions"],
                            "reason_code": "RIGHT_MEMBER_MISSING"}],
            "aggregate": {
                "mean_difference": "0.1", "valid_numeric_pair_count": 1,
                "negative_difference_count": 0, "zero_difference_count": 0,
                "positive_difference_count": 1,
            },
        },
        {
            "analysis_key": "paired-playlist-pass-difference",
            "outcome_key": "playlist-universal-pass-rate", "status": "CALCULATED",
            "reason": None,
            "calculator_key": "analysis.paired_difference", "raw_results": secondary_pairs,
            "exclusions": [],
            "aggregate": {
                "mean_difference": "0", "valid_numeric_pair_count": 1,
                "negative_difference_count": 0, "zero_difference_count": 1,
                "positive_difference_count": 0,
            },
        },
    ]
    report["realized"]["constraint_result_status_totals"] = {"FAIL": 3, "PASS": 1}
    report["exploratory_not_preregistered"] = {
        "projection_type": "EXPLORATORY_READ_ONLY_STUDY_ANALYSIS",
        "synopsis": {"label": "EXPLORATORY"},
        "track_level_analysis": {"status": "CALCULATED", "reason": "Governed subjects available."},
        "structured_evaluation": {
            "contributors": [{"id": item} for item in range(7)],
            "available_population": {"STRUCTURED_DERIVABLE": 4},
            "status_counts_by_constraint": [],
        },
    }
    before_json = closeout_json_bytes(report)
    before_sha = report["deterministic_payload_sha256"]

    markdown = closeout_markdown(report)

    assert "`paired-placement-compliance-difference`" in markdown
    assert "`paired-playlist-pass-difference`" in markdown
    assert "Block b01; replicate 1; LEFT 0.4; RIGHT 0.5; difference 0.1; state CALCULATED" in markdown
    assert "Block b01; replicate 2; LEFT 0.6; RIGHT None; difference None; state NOT_CALCULABLE; exclusion reason RIGHT_MEMBER_MISSING" in markdown
    assert "Block b01; replicate 1; LEFT 0; RIGHT 0; difference 0; state CALCULATED" in markdown
    assert "Direction counts (negative / zero / positive): 0 / 0 / 1" in markdown
    assert "Excluded pairs: 1" in markdown
    assert "No separately registered replicate-consistency classification exists; none was inferred." in markdown
    assert "Persisted structured subjects: 7" in markdown
    assert 'Structured constraint instances: 4 ({"STRUCTURED_DERIVABLE": 4})' in markdown
    assert 'Aggregate ConstraintResults: 4 ({"FAIL": 3, "PASS": 1})' in markdown
    assert "replicate consistency:" not in markdown.lower()
    assert closeout_json_bytes(report) == before_json
    assert report["deterministic_payload_sha256"] == before_sha

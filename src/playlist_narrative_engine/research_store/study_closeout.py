from __future__ import annotations

import hashlib
import json
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path


ExperimentReader = Callable[[int], dict[str, object] | None]
REPORT_VERSION = "1.0"


def current_repository_revision() -> str | None:
    root = Path(__file__).resolve().parents[3]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True,
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def build_study_closeout(
    protocol: dict[str, object],
    evaluation: dict[str, object],
    exploration: dict[str, object] | None,
    experiment_reader: ExperimentReader,
    *,
    generated_at: str | None = None,
    repository_revision: str | None = None,
) -> dict[str, object]:
    generated_at = generated_at or datetime.now(timezone.utc).isoformat()
    experiments = []
    source_identifiers = []
    experiment_ids = sorted({
        run["experiment_id"] for run in evaluation["runs"]
        if run["experiment_id"] is not None
    })
    for experiment_id in experiment_ids:
        experiment = experiment_reader(int(experiment_id))
        if experiment is None:
            continue
        sources = [
            {key: source.get(key) for key in (
                "id", "source_key", "source_type", "source_reference",
                "original_filename", "sha256",
            )}
            for source in experiment.get("evidence_sources", [])
        ]
        source_identifiers.extend(
            {"experiment_id": experiment_id, **source} for source in sources
        )
        experiments.append({"experiment_id": experiment_id, "evidence_sources": sources})

    constraint_result_ids = sorted({
        constraint["constraint_result_id"]
        for run in evaluation["runs"] for constraint in run["constraints"]
        if constraint["constraint_result_id"] is not None
    })
    unresolved_runs = [
        run["run_key"] for run in evaluation["runs"] if run["realization"] is None
    ]
    calculator_governed = evaluation.get("execution_classification") == "CALCULATOR_GOVERNED_EXECUTION"
    not_derivable = [
        item["analysis_key"] for item in evaluation["analyses"]
        if item["status"] == "NOT_DERIVABLE"
    ]
    unresolved_calculator_results = []
    if calculator_governed:
        for run in evaluation["runs"]:
            for outcome in run["outcomes"]:
                if outcome["status"] != "CALCULATED":
                    unresolved_calculator_results.append({
                        "kind": "OUTCOME", "planned_run_id": run["planned_run_id"],
                        "run_key": run["run_key"], "key": outcome["outcome_key"],
                        "execution_state": outcome["execution_state"],
                        "derivability_state": outcome["derivability_state"],
                        "calculation_state": outcome["calculation_state"],
                        "reason_code": outcome["reason_code"],
                    })
        for analysis in evaluation["analyses"]:
            if analysis["status"] != "CALCULATED":
                unresolved_calculator_results.append({
                    "kind": "ANALYSIS", "planned_run_id": None, "run_key": None,
                    "key": analysis["analysis_key"],
                    "execution_state": analysis["execution_state"],
                    "derivability_state": analysis["derivability_state"],
                    "calculation_state": analysis["calculation_state"],
                    "reason_code": analysis["reason_code"],
                })
    primary = evaluation["summary"]["primary_paired_analysis"]
    mean_difference = None if primary is None or primary["aggregate"] is None else primary["aggregate"].get("mean_difference")
    if calculator_governed:
        direction = "NOT_CALCULABLE" if mean_difference is None else "REGISTERED_CALCULATOR_RESULT_REPORTED"
    else:
        direction = (
            "NOT_CALCULABLE" if mean_difference is None else
            "NEGATIVE" if mean_difference < 0 else
            "POSITIVE" if mean_difference > 0 else "ZERO"
        )
    structured_manifest = _structured_manifest(exploration)
    conclusion = {
        "type": "DETERMINISTIC_REGISTERED_RESULT_BOUNDARY",
        "registered_direction": direction,
        "primary_outcome_key": evaluation["summary"]["primary_outcome_key"],
        "condition_values": evaluation["summary"]["primary_by_condition"],
        "paired_aggregate": None if primary is None else primary["aggregate"],
        "replicate_classifications": None if evaluation["summary"]["replicate_consistency"] is None else evaluation["summary"]["replicate_consistency"]["raw_results"],
        "registered_analyses_not_derivable": not_derivable,
        "exploratory_observations": None if exploration is None else {
            "status": "EXPLORATORY — NOT PREREGISTERED",
            "synopsis": exploration["synopsis"],
        },
        "language_boundary": "Descriptive registered values only; no significance, causal, or general-population claim is made.",
    }
    deterministic = {
        "report_type": "DERIVED_READ_ONLY_STUDY_CLOSEOUT",
        "report_version": REPORT_VERSION,
        "collection_status": "STUDY COMPLETE — REGISTERED ANALYSIS AVAILABLE" if evaluation["completion"]["collection_complete"] else "COLLECTION INCOMPLETE",
        "registered": {
            "study_id": protocol["study_id"],
            "study_key": protocol["study_key"],
            "title": protocol["title"],
            "protocol_version_id": protocol["id"],
            "protocol_version": protocol["version_number"],
            "registration_hash": protocol["registration_hash"],
            "registered_at": protocol["registered_at"],
            "objective": protocol["objective"],
            "primary_hypothesis": protocol["primary_hypothesis"],
            "null_hypothesis": protocol["null_hypothesis"],
            "conditions": protocol["conditions"],
            "blocks": protocol["blocks"],
            "constraint_definitions": protocol["constraint_definitions"],
            "outcome_definitions": protocol["outcome_definitions"],
            "analysis_definitions": protocol["analysis_definitions"],
            "planned_runs": protocol["planned_runs"],
            **({
                "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
                "execution_contract": protocol["execution_contract"],
            } if calculator_governed else {}),
        },
        "realized": {
            "completion": evaluation["completion"],
            "experiment_ids": experiment_ids,
            "generation_failure_ids": sorted({
                run["generation_failure_id"] for run in evaluation["runs"]
                if run["generation_failure_id"] is not None
            }),
            "constraint_result_status_totals": evaluation["summary"]["constraint_result_counts"],
            "experiments_and_sources": experiments,
            "source_identifiers": source_identifiers,
        },
        "registered_results": evaluation,
        "exploratory_not_preregistered": exploration,
        **({"structured_consumption": {
            "available": bool(structured_manifest["subject_result_ids"]),
            "execution_classification": evaluation.get("execution_classification", "LEGACY_EXECUTION"),
            "execution_contract_version": None if protocol.get("execution_contract") is None else protocol["execution_contract"]["contract_version"],
            "outcome_calculators": [] if protocol.get("execution_contract") is None else [
                _outcome_plan_manifest(item)
                for item in protocol["execution_contract"]["outcome_calculation_plans"]
            ],
            "analysis_calculators": [] if protocol.get("execution_contract") is None else [
                _analysis_plan_manifest(item)
                for item in protocol["execution_contract"]["analysis_calculation_plans"]
            ],
            "constraint_instrumentation": [
                _constraint_instrumentation_manifest(item)
                for item in protocol["constraint_definitions"]
            ],
            "unresolved_registered_results": unresolved_calculator_results,
            **structured_manifest,
        }} if calculator_governed else {}),
        "scientific_conclusion_boundary": conclusion,
        "follow_up_readiness": {
            "predecessor_study": {
                "study_id": protocol["study_id"],
                "study_key": protocol["study_key"],
                "protocol_version_id": protocol["id"],
                "protocol_version": protocol["version_number"],
                "registration_hash": protocol["registration_hash"],
            },
            "registered_findings_available": bool(evaluation["completion"]["primary_analysis_fully_calculable"]),
            "exploratory_findings_available": exploration is not None,
            "unresolved_not_derivable_questions": not_derivable + ([] if exploration is None or exploration["track_level_analysis"]["status"] != "NOT_DERIVABLE" else ["track_level_exploratory_analysis"]),
            "automatic_follow_up_created": False,
        },
        "reproducibility_manifest": {
            "study_id": protocol["study_id"],
            "protocol_version_id": protocol["id"],
            "protocol_version": protocol["version_number"],
            "registration_hash": protocol["registration_hash"],
            "evaluation_projection_type": evaluation["projection_type"],
            "exploration_projection_type": None if exploration is None else exploration["projection_type"],
            "experiment_ids": experiment_ids,
            "constraint_result_ids": constraint_result_ids,
            **({
                "subject_result_ids": structured_manifest["subject_result_ids"],
                "measurement_ids": structured_manifest["measurement_ids"],
                "measurement_evidence_ids": structured_manifest["measurement_evidence_ids"],
                "structured_evidence_source_ids": structured_manifest["evidence_source_ids"],
                "structured_evidence_link_ids": structured_manifest["evidence_link_ids"],
            } if calculator_governed else {}),
            "source_identifiers": source_identifiers,
            "unresolved_planned_run_keys": unresolved_runs,
            "repository_revision": repository_revision,
        },
    }
    deterministic_bytes = json.dumps(
        deterministic, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        **deterministic,
        "report_generation": {
            "generated_at": generated_at,
            "timestamp_semantics": "Report generation time only; not Study registration or realization time.",
            "volatile_fields": ["report_generation.generated_at"],
        },
        "deterministic_payload_sha256": hashlib.sha256(deterministic_bytes).hexdigest(),
    }


def _outcome_plan_manifest(plan):
    return {
        "plan_id": plan["id"], "outcome_key": plan["outcome_key"],
        "calculator_key": plan["calculator_key"],
        "calculator_version": plan["calculator_version"],
        "input_kind": plan["input_kind"], "output_value_type": plan["output_value_type"],
        "disposition_policies": plan["disposition_policies"],
    }


def _analysis_plan_manifest(plan):
    return {
        "plan_id": plan["id"], "analysis_key": plan["analysis_key"],
        "calculator_key": plan["calculator_key"],
        "calculator_version": plan["calculator_version"],
        "population_scope": plan["population_scope"],
        "matching_dimensions": plan["dimensions"],
        "condition_bindings": plan["condition_bindings"],
    }


def _constraint_instrumentation_manifest(definition):
    plan = definition.get("structured_evaluation_plan")
    if plan is None:
        return {
            "constraint_definition_id": definition["id"],
            "constraint_key": definition["constraint_key"],
            "instrumentation_classification": "LEGACY_AGGREGATE_ONLY",
        }
    return {
        "constraint_definition_id": definition["id"],
        "constraint_key": definition["constraint_key"],
        "instrumentation_classification": "STRUCTURED_DERIVABLE",
        "plan_id": plan["id"], "subject_kind": plan["subject_kind"],
        "subject_selector": plan["subject_selector"],
        "subject_evaluator": plan["subject_evaluator"],
        "aggregate_evaluator": plan["aggregate_evaluator"],
        "measurement_definitions": plan["measurement_definitions"],
    }


def _structured_manifest(exploration):
    empty = {
        "structured_subject_count": 0, "subject_result_count": 0,
        "measurement_count": 0, "measurement_evidence_count": 0,
        "subject_result_ids": [], "measurement_ids": [],
        "measurement_evidence_ids": [], "evidence_source_ids": [],
        "evidence_link_ids": [],
    }
    if exploration is None or "structured_evaluation" not in exploration:
        return empty
    contributors = exploration["structured_evaluation"]["contributors"]
    subject_result_ids = sorted({
        item["subject_result_id"] for item in contributors
        if item["subject_result_id"] is not None
    })
    measurement_ids = sorted({
        identifier for item in contributors for identifier in item["measurement_ids"]
    })
    evidence_rows = [
        evidence for item in contributors for evidence in item["evidence"]
    ]
    return {
        "structured_subject_count": len(contributors),
        "subject_result_count": len(subject_result_ids),
        "measurement_count": len(measurement_ids),
        "measurement_evidence_count": len({item["id"] for item in evidence_rows}),
        "subject_result_ids": subject_result_ids,
        "measurement_ids": measurement_ids,
        "measurement_evidence_ids": sorted({item["id"] for item in evidence_rows}),
        "evidence_source_ids": sorted({item["evidence_source_id"] for item in evidence_rows}),
        "evidence_link_ids": sorted({
            item["evidence_link_id"] for item in evidence_rows
            if item["evidence_link_id"] is not None
        }),
    }


def closeout_json_bytes(closeout: dict[str, object]) -> bytes:
    return (json.dumps(closeout, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def closeout_markdown(closeout: dict[str, object]) -> str:
    registered = closeout["registered"]
    realized = closeout["realized"]
    evaluation = closeout["registered_results"]
    exploration = closeout["exploratory_not_preregistered"]
    conclusion = closeout["scientific_conclusion_boundary"]
    manifest = closeout["reproducibility_manifest"]
    primary = evaluation["summary"]["primary_paired_analysis"]
    lines = [
        f"# Study Closeout — {registered['study_key']}", "",
        f"**{closeout['collection_status']}**", "",
        "> This report is a derived read-only projection, not a new scientific record.", "",
        "## REGISTERED", "",
        f"- Study: {registered['study_id']} — {registered['title']}",
        f"- Protocol version: {registered['protocol_version']} (ID {registered['protocol_version_id']})",
        f"- Registration hash: `{registered['registration_hash']}`",
        f"- Objective: {registered['objective']}",
        f"- Primary hypothesis: {registered['primary_hypothesis']}",
        f"- Conditions: {', '.join(item['condition_key'] for item in registered['conditions'])}",
        f"- Blocks: {', '.join(item['block_key'] for item in registered['blocks'])}",
        f"- Planned runs: {len(registered['planned_runs'])}", "",
        "### Frozen randomized run order", "",
    ]
    lines.extend(
        f"{item['randomized_ordinal']}. `{item['run_key']}` — {item['condition_key']} / {item['block_key']} / replicate {item['replicate_number']}"
        for item in sorted(registered["planned_runs"], key=lambda item: item["randomized_ordinal"])
    )
    lines.extend(["", "### Frozen constraints", ""])
    lines.extend(
        f"- `{item['constraint_key']}` ({item['constraint_type']}): {item['constraint_text']}"
        for item in registered["constraint_definitions"]
    )
    lines.extend(["", "### Registered analyses and reporting rules", ""])
    lines.extend(
        f"- `{item['analysis_key']}` → `{item['outcome_key']}`: {item['reporting_rule']}"
        for item in registered["analysis_definitions"]
    )
    lines.extend(["", "## REALIZED", "",
        f"- Planned / realized: {realized['completion']['planned_runs']} / {realized['completion']['realized_runs']}",
        f"- Refusals: {realized['completion']['refusal_count']}",
        f"- Generation failures: {realized['completion']['generation_failure_count']}",
        f"- Operational attempts: {realized['completion']['operational_attempt_count']}",
        f"- Experiments: {', '.join(str(item) for item in realized['experiment_ids']) or 'none'}",
        f"- ConstraintResult totals: {json.dumps(realized['constraint_result_status_totals'], sort_keys=True)}", "",
        f"- Evidence sources represented: {len(realized['source_identifiers'])}", "",
        "## REGISTERED RESULTS", "",
    ])
    for item in evaluation["summary"]["primary_by_condition"]:
        lines.append(f"- {item['condition_key']}: {item['mean']} across {item['calculable_runs']} calculable runs")
    lines.extend([
        f"- Paired difference: {None if primary is None or primary['aggregate'] is None else primary['aggregate']['mean_difference']}",
        f"- Direction: {conclusion['registered_direction']}",
        f"- Exclusions: {0 if primary is None else len(primary['exclusions'])}", "",
        "### Registered analyses", "",
    ])
    lines.extend(
        f"- `{item['analysis_key']}` — **{item['status']}**" + (f": {item['reason']}" if item["reason"] else "")
        for item in evaluation["analyses"]
    )
    lines.extend(["", "### Block and replicate summaries", ""])
    lines.extend(
        f"- {item['block_key']}: paired differences {item['paired_differences']}; mean {item['mean_difference']}"
        for item in evaluation["summary"]["primary_block_comparison"]
    )
    replicate = evaluation["summary"]["replicate_consistency"]
    if replicate is not None:
        lines.extend(
            f"- {item['block_key']}: {item['classification']} ({item['replicate_differences']})"
            for item in replicate["raw_results"]
        )
    lines.extend(["", "### Metadata registered summaries", "",
        f"- Acknowledgment counts: {json.dumps(evaluation['summary']['metadata_acknowledgment_counts'], sort_keys=True)}",
        f"- Construction-divergence counts: {json.dumps(evaluation['summary']['metadata_divergence_counts'], sort_keys=True)}",
    ])
    lines.extend(["", "## EXPLORATORY — NOT PREREGISTERED", ""])
    if exploration is None:
        lines.append("No exploratory projection is available.")
    elif "structured_evaluation" in exploration:
        structured = exploration["structured_evaluation"]
        lines.extend([
            "**EXPLORATORY DESCRIPTIVE SUMMARY — NOT A REGISTERED STUDY CONCLUSION**", "",
            f"- Structured subjects inspected: {len(structured['contributors'])}",
            f"- Instrumentation population: {json.dumps(structured['available_population'], sort_keys=True)}",
            f"- Track-level boundary: {exploration['track_level_analysis']['status']} — {exploration['track_level_analysis']['reason']}",
            "", "### Structured constraint summaries", "",
        ])
        lines.extend(
            f"- `{item['constraint_key']}`: {json.dumps(item['status_counts'], sort_keys=True)}"
            for item in structured["status_counts_by_constraint"]
        )
    else:
        synopsis = exploration["synopsis"]
        lines.extend([
            f"**{synopsis['label']}**", "",
            f"- Constraint types inspected: {synopsis['constraint_type_count']}",
            f"- Constraints with FAIL: {', '.join(synopsis['constraint_keys_with_fail']) or 'none'}",
            f"- Constraints with PARTIAL: {', '.join(synopsis['constraint_keys_with_partial']) or 'none'}",
            f"- Track-level analysis: {exploration['track_level_analysis']['status']} — {exploration['track_level_analysis']['reason']}",
            f"- Exact-count diagnostics: {json.dumps(exploration['exact_count_diagnostics']['by_condition'], sort_keys=True)}",
            f"- Constraint-result concentration: {json.dumps(exploration['constraint_result_concentration']['totals'], sort_keys=True)}",
            f"- Metadata cross-view cells: {len(exploration['metadata_cross_view']['cells'])}",
            "", "### Constraint-type summaries", "",
        ])
        lines.extend(
            f"- `{item['constraint_key']}` ({item['constraint_type']}): {json.dumps(item['conditions'], sort_keys=True)}"
            for item in exploration["constraint_matrix"]
        )
    lines.extend(["", "## Scientific conclusion boundary", "",
        f"- Registered directional result: {conclusion['registered_direction']}",
        f"- Analyses not derivable: {', '.join(conclusion['registered_analyses_not_derivable']) or 'none'}",
        f"- {conclusion['language_boundary']}", "",
        "## Reproducibility manifest", "",
        f"- Evaluation projection: `{manifest['evaluation_projection_type']}`",
        f"- Exploration projection: `{manifest['exploration_projection_type']}`",
        f"- Repository revision: `{manifest['repository_revision'] or 'unavailable'}`",
        f"- Deterministic payload SHA-256: `{closeout['deterministic_payload_sha256']}`",
        f"- Report generated at: {closeout['report_generation']['generated_at']}",
        f"- Timestamp meaning: {closeout['report_generation']['timestamp_semantics']}", "",
        "Complete protocol, results, provenance identifiers, and exploratory structures are retained in the JSON research bundle.",
    ])
    return "\n".join(lines) + "\n"

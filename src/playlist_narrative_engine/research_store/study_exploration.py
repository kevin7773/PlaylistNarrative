from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable


ExperimentReader = Callable[[int], dict[str, object] | None]
StructuredEvaluationReader = Callable[[int], dict[str, object] | None]
RESULT_STATUSES = ("PASS", "PARTIAL", "FAIL", "UNKNOWN", "MISSING")


def _is_exact_count(constraint) -> bool:
    return constraint["constraint_type"] in {"exact_cardinality", "exact_count"}


def explore_study(
    evaluation: dict[str, object], experiment_reader: ExperimentReader,
    structured_evaluation_reader: StructuredEvaluationReader | None = None,
) -> dict[str, object]:
    """Build a disposable post-hoc projection from structured governed fields."""
    if evaluation.get("execution_classification") == "CALCULATOR_GOVERNED_EXECUTION":
        if structured_evaluation_reader is None:
            raise ValueError("calculator-governed exploration requires persisted structured-evaluation reads")
        return _explore_calculator_governed(evaluation, structured_evaluation_reader)
    runs = list(evaluation["runs"])
    condition_roles = dict(evaluation["summary"]["registered_condition_roles"])
    matrix = _constraint_matrix(runs, condition_roles)
    replicates = _constraint_replicates(runs)
    exact_count = _exact_count_diagnostics(runs, experiment_reader)
    concentration = _constraint_concentration(matrix)
    metadata = _metadata_cross_view(runs)
    synopsis = _synopsis(matrix, replicates, exact_count)
    return {
        "projection_type": "EXPLORATORY_READ_ONLY_STUDY_ANALYSIS",
        "status": "EXPLORATORY — NOT PREREGISTERED",
        "study_id": evaluation["study_id"],
        "study_key": evaluation["study_key"],
        "protocol_version_id": evaluation["protocol_version_id"],
        "protocol_version": evaluation["protocol_version"],
        "registration_hash": evaluation["registration_hash"],
        "registered_condition_roles": condition_roles,
        "constraint_matrix": matrix,
        "constraint_by_replicate": replicates,
        "exact_count_diagnostics": exact_count,
        "constraint_result_concentration": concentration,
        "metadata_cross_view": metadata,
        "track_level_analysis": {
            "status": "NOT_DERIVABLE",
            "reason": "Track-level exploratory analysis is unavailable because governed per-track constraint results were not captured for this Study.",
        },
        "synopsis": synopsis,
        "provenance": {
            "study_id": evaluation["study_id"],
            "protocol_version_id": evaluation["protocol_version_id"],
            "registration_hash": evaluation["registration_hash"],
            "source": "frozen P3 projection and structured governed Experiment fields",
            "persistence": "none; this exploratory projection is disposable and read-only",
            "free_text_parsing": "none",
        },
    }


def _explore_calculator_governed(evaluation, structured_evaluation_reader):
    status_by_constraint = defaultdict(Counter)
    status_by_subject_kind = defaultdict(Counter)
    status_by_population = defaultdict(Counter)
    ordinal_distributions = defaultdict(Counter)
    contributors = []
    instrumentation = Counter()
    seen_constraints = set()
    for run in evaluation["runs"]:
        for constraint in run["constraints"]:
            constraint_id = constraint.get("constraint_id")
            if constraint_id is None:
                instrumentation["MISSING_CONSTRAINT"] += 1
                continue
            if constraint_id in seen_constraints:
                continue
            seen_constraints.add(constraint_id)
            structured = structured_evaluation_reader(int(constraint_id))
            if structured is None or structured["instrumentation_classification"] != "STRUCTURED_DERIVABLE":
                instrumentation["LEGACY_AGGREGATE_ONLY"] += 1
                continue
            instrumentation["STRUCTURED_DERIVABLE"] += 1
            for subject in structured["subjects"]:
                result = subject["result"]
                status = "MISSING" if result is None else result["status"]
                subject_kind = subject["subject_kind"]
                status_by_constraint[constraint["constraint_key"]][status] += 1
                status_by_subject_kind[subject_kind][status] += 1
                population_key = (
                    run["condition_key"], run["block_key"], run["replicate_number"]
                )
                status_by_population[population_key][status] += 1
                ordinal_distributions[subject_kind][subject["enumeration_ordinal"]] += 1
                measurement_ids = [item["id"] for item in subject["measurements"]]
                evidence = [
                    evidence_item
                    for measurement in subject["measurements"]
                    for evidence_item in measurement["evidence"]
                ]
                contributors.append({
                    "planned_run_id": run["planned_run_id"],
                    "run_key": run["run_key"],
                    "condition_key": run["condition_key"],
                    "block_key": run["block_key"],
                    "replicate_number": run["replicate_number"],
                    "experiment_id": run["experiment_id"],
                    "constraint_id": constraint_id,
                    "constraint_result_id": constraint["constraint_result_id"],
                    "constraint_key": constraint["constraint_key"],
                    "subject_id": subject["id"],
                    "subject_kind": subject_kind,
                    "enumeration_ordinal": subject["enumeration_ordinal"],
                    "experiment_track_id": subject["experiment_track_id"],
                    "governed_field": subject["governed_field"],
                    "subject_result_id": None if result is None else result["id"],
                    "recorded_status": status,
                    "measurement_ids": measurement_ids,
                    "evidence": evidence,
                })
    structured = {
        "status": "EXPLORATORY — NOT PREREGISTERED",
        "available_population": dict(sorted(instrumentation.items())),
        "status_counts_by_constraint": [
            {"constraint_key": key, "status_counts": dict(sorted(counts.items()))}
            for key, counts in sorted(status_by_constraint.items())
        ],
        "status_counts_by_subject_kind": [
            {"subject_kind": key, "status_counts": dict(sorted(counts.items()))}
            for key, counts in sorted(status_by_subject_kind.items())
        ],
        "status_counts_by_condition_block_replicate": [
            {"condition_key": key[0], "block_key": key[1], "replicate_number": key[2],
             "status_counts": dict(sorted(counts.items()))}
            for key, counts in sorted(status_by_population.items())
        ],
        "subject_result_distribution_by_enumeration_ordinal": [
            {"subject_kind": kind, "ordinals": [
                {"enumeration_ordinal": ordinal, "subject_count": count}
                for ordinal, count in sorted(counts.items())
            ]}
            for kind, counts in sorted(ordinal_distributions.items())
        ],
        "contributors": sorted(
            contributors,
            key=lambda item: (
                item["constraint_key"], item["condition_key"], item["block_key"],
                item["replicate_number"], item["enumeration_ordinal"], item["subject_id"],
            ),
        ),
        "non_claims": [
            "No exploratory violation rate is calculated.",
            "FIELD_PREDICATE results are not promoted to whole-track results.",
            "Evaluation ordinal is not interpreted as playlist absolute position.",
            "RUN subjects are not represented as track-level observations.",
        ],
    }
    return {
        "projection_type": "EXPLORATORY_READ_ONLY_STUDY_ANALYSIS",
        "status": "EXPLORATORY — NOT PREREGISTERED",
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "study_id": evaluation["study_id"],
        "study_key": evaluation["study_key"],
        "protocol_version_id": evaluation["protocol_version_id"],
        "protocol_version": evaluation["protocol_version"],
        "registration_hash": evaluation["registration_hash"],
        "structured_evaluation": structured,
        "track_level_analysis": {
            "status": "AVAILABLE_ONLY_AS_REGISTERED_SUBJECTS",
            "reason": "Only persisted P7 subject results are shown; no composite track result is inferred.",
        },
        "synopsis": {
            "label": "EXPLORATORY DESCRIPTIVE SUMMARY — NOT A REGISTERED STUDY CONCLUSION",
            "structured_constraint_count": instrumentation["STRUCTURED_DERIVABLE"],
            "aggregate_only_constraint_count": instrumentation["LEGACY_AGGREGATE_ONLY"],
            "structured_subject_count": len(contributors),
        },
        "provenance": {
            "study_id": evaluation["study_id"],
            "protocol_version_id": evaluation["protocol_version_id"],
            "registration_hash": evaluation["registration_hash"],
            "source": "persisted P7 subjects, measurements, subject results, and measurement evidence",
            "persistence": "none; this exploratory projection is disposable and read-only",
            "free_text_parsing": "none",
        },
    }


def _empty_counts() -> dict[str, int]:
    return {status: 0 for status in RESULT_STATUSES}


def _run_reference(run, constraint) -> dict[str, object]:
    return {
        "planned_run_id": run["planned_run_id"],
        "run_key": run["run_key"],
        "condition_key": run["condition_key"],
        "block_key": run["block_key"],
        "replicate_number": run["replicate_number"],
        "experiment_id": run["experiment_id"],
        "constraint_result_id": constraint["constraint_result_id"],
        "recorded_status": constraint["status"] or "MISSING",
    }


def _constraint_matrix(runs, condition_roles) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for run in runs:
        for constraint in run["constraints"]:
            key = constraint["constraint_key"]
            item = grouped.setdefault(key, {
                "constraint_key": key,
                "constraint_type": constraint["constraint_type"],
                "block_keys": set(),
                "conditions": {},
                "contributors": [],
            })
            item["block_keys"].add(run["block_key"])
            counts = item["conditions"].setdefault(run["condition_key"], _empty_counts())
            counts[constraint["status"] or "MISSING"] += 1
            item["contributors"].append(_run_reference(run, constraint))
    result = []
    for item in grouped.values():
        conditions = {}
        for key, counts in sorted(item["conditions"].items()):
            conditions[key] = {
                **counts,
                "calculable_result_count": counts["PASS"] + counts["PARTIAL"] + counts["FAIL"],
                "run_count": sum(counts.values()),
            }
        binary_difference = None
        control_key = next((key for key, role in condition_roles.items() if role == "CONTROL"), None)
        treatment_key = next((key for key, role in condition_roles.items() if role == "TREATMENT"), None)
        if (item["constraint_type"] in {"exact_cardinality", "exact_count"} and control_key in conditions
                and treatment_key in conditions):
            left, right = conditions[control_key], conditions[treatment_key]
            if left["calculable_result_count"] and right["calculable_result_count"]:
                binary_difference = {
                    "control_condition_key": control_key,
                    "treatment_condition_key": treatment_key,
                    "treatment_minus_control_pass_rate": (
                        right["PASS"] / right["calculable_result_count"]
                        - left["PASS"] / left["calculable_result_count"]
                    ),
                }
        result.append({
            **item,
            "block_keys": sorted(item["block_keys"]),
            "conditions": conditions,
            "run_count": len(item["contributors"]),
            "descriptive_binary_difference": binary_difference,
        })
    return sorted(result, key=lambda item: item["constraint_key"])


def _constraint_replicates(runs) -> list[dict[str, object]]:
    rows = []
    for run in runs:
        for constraint in run["constraints"]:
            rows.append({
                "constraint_key": constraint["constraint_key"],
                **_run_reference(run, constraint),
            })
    return sorted(rows, key=lambda item: (
        item["constraint_key"], item["block_key"], item["replicate_number"],
        item["condition_key"], item["run_key"],
    ))


def _exact_count_diagnostics(runs, experiment_reader) -> dict[str, object]:
    rows, by_condition = [], defaultdict(_empty_counts)
    for run in runs:
        exact = [item for item in run["constraints"] if _is_exact_count(item)]
        for constraint in exact:
            status = constraint["status"] or "MISSING"
            by_condition[run["condition_key"]][status] += 1
            experiment = experiment_reader(run["experiment_id"]) if run["experiment_id"] is not None else None
            rows.append({
                **_run_reference(run, constraint),
                "generated_track_count": None if experiment is None else experiment.get("generated_track_count"),
            })
    matched = []
    grouped = defaultdict(dict)
    for row in rows:
        grouped[(row["block_key"], row["replicate_number"])][row["condition_key"]] = row
    for (block, replicate), members in sorted(grouped.items()):
        matched.append({
            "block_key": block,
            "replicate_number": replicate,
            "conditions": [members[key] for key in sorted(members)],
            "complete_pair": len(members) == 2,
        })
    return {
        "by_condition": {key: value for key, value in sorted(by_condition.items())},
        "matched_pairs": matched,
        "non_pass_runs": [row for row in rows if row["recorded_status"] != "PASS"],
        "contributors": rows,
    }


def _constraint_concentration(matrix) -> dict[str, object]:
    totals = Counter()
    by_status = {status: [] for status in ("PASS", "PARTIAL", "FAIL", "UNKNOWN", "MISSING")}
    for constraint in matrix:
        counts = Counter()
        for values in constraint["conditions"].values():
            for status in RESULT_STATUSES:
                counts[status] += values[status]
                totals[status] += values[status]
        for status in by_status:
            by_status[status].append({
                "constraint_key": constraint["constraint_key"],
                "count": counts[status],
                "contributors": [
                    item for item in constraint["contributors"]
                    if item["recorded_status"] == status
                ],
            })
    return {"totals": dict(totals), "by_status": by_status}


def _hard_rollup(constraints) -> tuple[str, list[int]]:
    hard = [item for item in constraints if item["is_hard_constraint"]]
    statuses = [item["status"] or "MISSING" for item in hard]
    ids = [item["constraint_result_id"] for item in hard if item["constraint_result_id"] is not None]
    if not hard or any(status in {"UNKNOWN", "MISSING"} for status in statuses):
        return "UNKNOWN", ids
    if "FAIL" in statuses:
        return "FAIL", ids
    if "PARTIAL" in statuses:
        return "PARTIAL", ids
    return "PASS", ids


def _metadata_cross_view(runs) -> dict[str, object]:
    cells = defaultdict(list)
    for run in runs:
        metadata = [item for item in run["constraints"] if item["constraint_type"] == "metadata_requirement_acknowledgment"]
        if not metadata:
            continue
        item = metadata[0]
        metadata_status = item["status"] or "MISSING"
        hard_status, hard_ids = _hard_rollup(run["constraints"])
        divergence = next((outcome for outcome in run["outcomes"] if outcome["strategy"] == "METADATA_CONSTRUCTION_DIVERGENCE"), None)
        key = (run["condition_key"], metadata_status, hard_status)
        cells[key].append({
            **_run_reference(run, item),
            "hard_compliance_status": hard_status,
            "hard_constraint_result_ids": hard_ids,
            "construction_divergence_status": None if divergence is None else divergence["status"],
            "construction_divergence_value": None if divergence is None else divergence["value"],
            "divergence_source_constraint_result_ids": [] if divergence is None else divergence["source_constraint_result_ids"],
        })
    return {
        "cells": [
            {"condition_key": key[0], "metadata_status": key[1],
             "hard_compliance_status": key[2], "count": len(contributors),
             "contributors": contributors}
            for key, contributors in sorted(cells.items())
        ],
        "definition": "Descriptive contingency of recorded metadata status, deterministic hard-constraint status rollup, and frozen P3 divergence outcome.",
    }


def _synopsis(matrix, replicates, exact_count) -> dict[str, object]:
    unstable = 0
    grouped = defaultdict(set)
    for row in replicates:
        grouped[(row["constraint_key"], row["condition_key"], row["block_key"])].add(row["recorded_status"])
    unstable = sum(len(statuses) > 1 for statuses in grouped.values())
    fail_keys = [item["constraint_key"] for item in matrix if any(
        values["FAIL"] for values in item["conditions"].values()
    )]
    partial_keys = [item["constraint_key"] for item in matrix if any(
        values["PARTIAL"] for values in item["conditions"].values()
    )]
    condition_differences = [item["constraint_key"] for item in matrix if len({
        tuple(values[status] for status in RESULT_STATUSES)
        for values in item["conditions"].values()
    }) > 1]
    exact_failures = {
        key: values["FAIL"] for key, values in exact_count["by_condition"].items()
    }
    return {
        "label": "EXPLORATORY DESCRIPTIVE SUMMARY — NOT A REGISTERED STUDY CONCLUSION",
        "constraint_type_count": len(matrix),
        "constraint_keys_with_fail": fail_keys,
        "constraint_keys_with_partial": partial_keys,
        "constraint_keys_with_condition_differences": condition_differences,
        "replicate_groups_with_different_recorded_statuses": unstable,
        "exact_count_failures_by_condition": exact_failures,
    }

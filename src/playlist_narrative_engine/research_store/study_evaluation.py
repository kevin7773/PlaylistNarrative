from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from typing import Any


ExperimentReader = Callable[[int], dict[str, object] | None]
OutcomeCalculator = Callable[[int, int], dict[str, object]]
AnalysisCalculator = Callable[[int], dict[str, object]]


def evaluate_registered_study(
    protocol: dict[str, object], experiment_reader: ExperimentReader
) -> dict[str, object]:
    """Build a disposable read-only evaluation of one registered protocol version."""
    return _evaluate_legacy_study(protocol, experiment_reader)


def evaluate_calculator_governed_study(
    protocol: dict[str, object],
    experiment_reader: ExperimentReader,
    outcome_calculator: OutcomeCalculator,
    analysis_calculator: AnalysisCalculator,
) -> dict[str, object]:
    """Adapt registered E2 results into the disposable P3 projection boundary.

    This function performs no scientific calculation. Every outcome and analysis
    value is copied from the registered calculator execution projection.
    """
    contract = protocol.get("execution_contract")
    if contract is None:
        raise ValueError("calculator-governed evaluation requires an execution contract")
    definitions = {
        int(item["id"]): item for item in protocol["constraint_definitions"]
    }
    outcome_definitions = {
        item["outcome_key"]: item for item in protocol["outcome_definitions"]
    }
    outcome_plans = list(contract["outcome_calculation_plans"])
    runs = []
    for run in sorted(
        protocol["planned_runs"], key=lambda item: item["randomized_ordinal"]
    ):
        realization = run["realization"]
        experiment = (
            experiment_reader(int(realization["experiment_id"]))
            if realization is not None and realization["experiment_id"] is not None
            else None
        )
        constraints = _recorded_constraint_projection(run, definitions, experiment)
        outcomes = []
        for plan in outcome_plans:
            calculated = outcome_calculator(int(run["id"]), int(plan["id"]))
            definition = outcome_definitions[plan["outcome_key"]]
            outcomes.append(
                _calculator_outcome_projection(definition, plan, calculated)
            )
        runs.append(
            {
                "planned_run_id": run["id"],
                "run_key": run["run_key"],
                "randomized_ordinal": run["randomized_ordinal"],
                "condition_key": run["condition_key"],
                "block_key": run["block_key"],
                "replicate_number": run["replicate_number"],
                "attempts": run["attempts"],
                "realization": realization,
                "experiment_id": None if realization is None else realization["experiment_id"],
                "generation_failure_id": None if realization is None else realization["generation_failure_id"],
                "constraints": constraints,
                "outcomes": outcomes,
            }
        )
    analysis_definitions = {
        item["analysis_key"]: item for item in protocol["analysis_definitions"]
    }
    analyses = []
    for plan in contract["analysis_calculation_plans"]:
        calculated = analysis_calculator(int(plan["id"]))
        analyses.append(
            _calculator_analysis_projection(
                analysis_definitions[plan["analysis_key"]], plan, calculated
            )
        )
    realized = sum(item["realization"] is not None for item in runs)
    attempts = sum(len(item["attempts"]) for item in runs)
    disposition_counts = Counter(
        item["realization"]["disposition"]
        for item in runs
        if item["realization"] is not None
    )
    primary_keys = {
        item["outcome_key"]
        for item in protocol["outcome_definitions"]
        if item["role"] == "PRIMARY"
    }
    primary_analyses = [
        item for item in analyses if item["outcome_key"] in primary_keys
    ]
    return {
        "projection_type": "DERIVED_READ_ONLY_STUDY_EVALUATION",
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "study_id": protocol["study_id"],
        "study_key": protocol["study_key"],
        "protocol_version_id": protocol["id"],
        "protocol_version": protocol["version_number"],
        "registration_hash": protocol["registration_hash"],
        "completion": {
            "planned_runs": len(runs),
            "realized_runs": realized,
            "pending_runs": len(runs) - realized,
            "executable_runs": sum(
                item["realization"] is None
                and not any(attempt["consumes_planned_run"] for attempt in item["attempts"])
                for item in runs
            ),
            "refusal_count": disposition_counts["MAESTRO_REFUSAL_RECORDED"],
            "generation_failure_count": disposition_counts["MAESTRO_FAILURE_RECORDED"],
            "operational_attempt_count": attempts,
            "collection_complete": realized == len(runs),
            "primary_analysis_fully_calculable": bool(primary_analyses)
            and all(item["calculation_state"] == "CALCULATED" for item in primary_analyses),
        },
        "outcome_definitions": list(protocol["outcome_definitions"]),
        "analysis_definitions": list(protocol["analysis_definitions"]),
        "runs": runs,
        "analyses": analyses,
        "summary": _calculator_summary(protocol, analyses, runs),
        "provenance": {
            "study_id": protocol["study_id"],
            "protocol_version_id": protocol["id"],
            "registration_hash": protocol["registration_hash"],
            "source": "registered execution contract and unchanged E2 calculator projections",
            "persistence": "none; this projection is disposable and read-only",
        },
    }


def _recorded_constraint_projection(run, definitions, experiment):
    recorded_by_definition = {}
    if experiment is not None:
        recorded_by_definition = {
            item["study_constraint_definition_id"]: item
            for item in experiment["constraints"]
            if item["study_constraint_definition_id"] is not None
        }
    rows = []
    for definition_id, definition in definitions.items():
        if definition["constraint_key"] not in run["applicable_constraint_keys"]:
            continue
        recorded = recorded_by_definition.get(definition_id)
        result = None if recorded is None else recorded["result"]
        rows.append(
            {
                "definition_id": definition_id,
                "constraint_key": definition["constraint_key"],
                "constraint_type": definition["constraint_type"],
                "constraint_text": definition["constraint_text"],
                "is_hard_constraint": definition["is_hard_constraint"],
                "evaluation_rule": definition["evaluation_rule"],
                "unknown_handling": definition["unknown_handling"],
                "constraint_id": None if recorded is None else recorded["id"],
                "constraint_result_id": None if recorded is None else recorded["id"],
                "status": None if result is None else result["status"],
                "evidence": None if result is None else result["evidence"],
                "provenance_type": None if result is None else result["provenance_type"],
                "provenance_notes": None if result is None else result["provenance_notes"],
            }
        )
    return rows


def _calculator_state(calculated):
    if calculated["execution_state"] == "UNAVAILABLE":
        return "UNAVAILABLE"
    if calculated.get("derivability_state") == "NOT_DERIVABLE":
        return "NOT_DERIVABLE"
    return calculated.get("calculation_state") or "NOT_CALCULABLE"


def _calculator_outcome_projection(definition, plan, calculated):
    state = _calculator_state(calculated)
    return {
        "outcome_definition_id": definition["id"],
        "outcome_key": definition["outcome_key"],
        "role": definition["role"],
        "strategy": "REGISTERED_CALCULATOR",
        "calculation_plan_id": plan["id"],
        "calculator_key": plan["calculator_key"],
        "calculator_version": plan["calculator_version"],
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "execution_state": calculated["execution_state"],
        "derivability_state": calculated.get("derivability_state"),
        "calculation_state": calculated.get("calculation_state"),
        "reason_code": calculated.get("reason_code"),
        "status": state,
        "value": calculated.get("decimal_value"),
        "numerator_count": calculated.get("numerator_count"),
        "denominator_count": calculated.get("denominator_count"),
        "ratio_numerator": calculated.get("ratio_numerator"),
        "ratio_denominator": calculated.get("ratio_denominator"),
        "source_constraint_result_ids": sorted(
            item["constraint_id"]
            for item in calculated.get("contributing_inputs", [])
            if item.get("constraint_id") is not None
        ),
        "calculator_projection": calculated,
    }


def _calculator_analysis_projection(definition, plan, calculated):
    state = _calculator_state(calculated)
    aggregate = None
    if calculated.get("calculation_state") == "CALCULATED":
        aggregate = {
            key: calculated[key]
            for key in (
                "mean_difference", "valid_numeric_pair_count",
                "negative_difference_count", "zero_difference_count",
                "positive_difference_count",
            )
            if key in calculated
        }
    return {
        "analysis_definition_id": definition["id"],
        "analysis_key": definition["analysis_key"],
        "outcome_key": definition["outcome_key"],
        "calculation_plan_id": plan["id"],
        "calculator_key": plan["calculator_key"],
        "calculator_version": plan["calculator_version"],
        "execution_classification": "CALCULATOR_GOVERNED_EXECUTION",
        "execution_state": calculated["execution_state"],
        "derivability_state": calculated.get("derivability_state"),
        "calculation_state": calculated.get("calculation_state"),
        "reason_code": calculated.get("reason_code"),
        "status": state,
        "reason": calculated.get("reason_code"),
        "raw_results": calculated.get("pairs", []),
        "exclusions": calculated.get("invalid_or_incomplete_pairs", []),
        "aggregate": aggregate,
        "registered_definition": definition,
        "registered_population": definition["analysis_population"],
        "matching_dimensions": calculated.get("matching_dimensions", plan.get("dimensions", [])),
        "condition_bindings": calculated.get("condition_bindings", plan.get("condition_bindings", [])),
        "calculator_projection": calculated,
    }


def _calculator_summary(protocol, analyses, runs):
    primary = next(
        (item["outcome_key"] for item in protocol["outcome_definitions"] if item["role"] == "PRIMARY"),
        None,
    )
    primary_analysis = next(
        (item for item in analyses if item["outcome_key"] == primary), None
    )
    return {
        "primary_outcome_key": primary,
        "primary_by_condition": [],
        "primary_paired_analysis": primary_analysis,
        "primary_block_comparison": [],
        "replicate_consistency": None,
        "constraint_result_counts": _constraint_result_counts(runs),
        "disposition_counts": {},
        "metadata_acknowledgment_counts": {},
        "metadata_divergence_counts": {},
        "analysis_overview": [
            {
                "analysis_key": item["analysis_key"],
                "outcome_key": item["outcome_key"],
                "status": item["status"],
                "exclusion_count": len(item["exclusions"]),
                "aggregate": item["aggregate"],
            }
            for item in analyses
        ],
        "registered_condition_roles": {
            item["condition_key"]: item["role"] for item in protocol["conditions"]
        },
    }
def _evaluate_legacy_study(protocol, experiment_reader):
    definitions = {
        int(item["id"]): item for item in protocol["constraint_definitions"]
    }
    outcome_definitions = list(protocol["outcome_definitions"])
    strategies = {
        item["outcome_key"]: _outcome_strategy(item) for item in outcome_definitions
    }
    runs = [
        _evaluate_run(run, definitions, outcome_definitions, strategies, experiment_reader)
        for run in sorted(protocol["planned_runs"], key=lambda item: item["randomized_ordinal"])
    ]
    analyses = [
        _evaluate_analysis(item, runs, strategies, protocol["conditions"])
        for item in protocol["analysis_definitions"]
    ]
    realized = sum(item["realization"] is not None for item in runs)
    attempts = sum(len(item["attempts"]) for item in runs)
    disposition_counts = Counter(
        item["realization"]["disposition"]
        for item in runs
        if item["realization"] is not None
    )
    primary_analyses = [
        item for item in analyses if _outcome_role(outcome_definitions, item["outcome_key"]) == "PRIMARY"
    ]
    return {
        "projection_type": "DERIVED_READ_ONLY_STUDY_EVALUATION",
        "study_id": protocol["study_id"],
        "study_key": protocol["study_key"],
        "protocol_version_id": protocol["id"],
        "protocol_version": protocol["version_number"],
        "registration_hash": protocol["registration_hash"],
        "completion": {
            "planned_runs": len(runs),
            "realized_runs": realized,
            "pending_runs": len(runs) - realized,
            "executable_runs": sum(
                item["realization"] is None
                and not any(attempt["consumes_planned_run"] for attempt in item["attempts"])
                for item in runs
            ),
            "refusal_count": disposition_counts["MAESTRO_REFUSAL_RECORDED"],
            "generation_failure_count": disposition_counts["MAESTRO_FAILURE_RECORDED"],
            "operational_attempt_count": attempts,
            "collection_complete": realized == len(runs),
            "primary_analysis_fully_calculable": bool(primary_analyses)
            and all(item["status"] == "CALCULATED" and not item["exclusions"] for item in primary_analyses),
        },
        "outcome_definitions": outcome_definitions,
        "analysis_definitions": list(protocol["analysis_definitions"]),
        "runs": runs,
        "analyses": analyses,
        "summary": _summary(runs, analyses, outcome_definitions, protocol["conditions"]),
        "provenance": {
            "study_id": protocol["study_id"],
            "protocol_version_id": protocol["id"],
            "registration_hash": protocol["registration_hash"],
            "source": "registered protocol, planned runs, realizations, and realized Experiment ConstraintResults",
            "persistence": "none; this projection is disposable and read-only",
        },
    }


def _evaluate_run(run, definitions, outcome_definitions, strategies, experiment_reader):
    realization = run["realization"]
    experiment = None
    if realization is not None and realization["experiment_id"] is not None:
        experiment = experiment_reader(int(realization["experiment_id"]))
    results_by_definition = {}
    if experiment is not None:
        results_by_definition = {
            item["study_constraint_definition_id"]: item
            for item in experiment["constraints"]
            if item["study_constraint_definition_id"] is not None
        }
    applicable = []
    for definition_id, definition in definitions.items():
        if definition["constraint_key"] not in run["applicable_constraint_keys"]:
            continue
        recorded = results_by_definition.get(definition_id)
        result = None if recorded is None else recorded["result"]
        applicable.append({
            "definition_id": definition_id,
            "constraint_key": definition["constraint_key"],
            "constraint_type": definition["constraint_type"],
            "constraint_text": definition["constraint_text"],
            "is_hard_constraint": definition["is_hard_constraint"],
            "evaluation_rule": definition["evaluation_rule"],
            "unknown_handling": definition["unknown_handling"],
            "constraint_result_id": None if recorded is None else recorded["id"],
            "status": None if result is None else result["status"],
            "evidence": None if result is None else result["evidence"],
            "provenance_type": None if result is None else result["provenance_type"],
            "provenance_notes": None if result is None else result["provenance_notes"],
        })
    context = {"run": run, "realization": realization, "constraints": applicable}
    outcomes = []
    for definition in outcome_definitions:
        strategy = strategies[definition["outcome_key"]]
        value = _derive_outcome(strategy, context)
        outcomes.append({
            "outcome_definition_id": definition["id"],
            "outcome_key": definition["outcome_key"],
            "role": definition["role"],
            "strategy": strategy,
            **value,
        })
    return {
        "planned_run_id": run["id"],
        "run_key": run["run_key"],
        "randomized_ordinal": run["randomized_ordinal"],
        "condition_key": run["condition_key"],
        "block_key": run["block_key"],
        "replicate_number": run["replicate_number"],
        "attempts": run["attempts"],
        "realization": realization,
        "experiment_id": None if realization is None else realization["experiment_id"],
        "generation_failure_id": None if realization is None else realization["generation_failure_id"],
        "constraints": applicable,
        "outcomes": outcomes,
    }


def _outcome_strategy(definition: dict[str, Any]) -> str:
    text = " ".join(str(definition[key]).lower() for key in (
        "outcome_definition", "computation_rule", "missing_data_rule"
    ))
    if "terminal maestr" in text and "studyrundisposition" in text:
        return "TERMINAL_DISPOSITION"
    if "evaluated observed tracks" in text and "divide" in text:
        return "TRACK_VIOLATION_RATE_UNAVAILABLE"
    if "two applicable hard constraints" in text and "divide by 2" in text:
        return "HARD_CONSTRAINT_COMPLIANCE"
    if "number of the run" in text and "partial or fail" in text:
        return "DISTINCT_HARD_VIOLATIONS"
    if "exactly-10-tracks constraint" in text and "exact_count_10" in text:
        return "EXACT_CARDINALITY_COMPLIANCE"
    if "explicitly and unambiguously acknowledges" in text and "constraint result" in text:
        return "METADATA_ACKNOWLEDGMENT"
    if "metadata acknowledges" in text and "track construction" in text:
        return "METADATA_CONSTRUCTION_DIVERGENCE"
    return "NOT_DERIVABLE"


def _derive_outcome(strategy: str, context: dict[str, Any]) -> dict[str, Any]:
    realization = context["realization"]
    constraints = context["constraints"]
    if strategy == "TERMINAL_DISPOSITION":
        if realization is None:
            return _missing("Planned run has no terminal scientific realization.")
        return _calculated(realization["disposition"], [realization["id"]])
    if realization is None:
        return _missing("Planned run has no terminal scientific realization.")
    if realization["disposition"] != "EXPERIMENT_RECORDED":
        return _missing(f"{realization['disposition']} has no manufactured compliance outcome.")
    if strategy in {"NOT_DERIVABLE", "TRACK_VIOLATION_RATE_UNAVAILABLE"}:
        reason = (
            "ConstraintResult stores aggregate status and evidence text, not structured per-track results."
            if strategy == "TRACK_VIOLATION_RATE_UNAVAILABLE"
            else "Registered computation is not satisfied by a recognized structured derivation."
        )
        return {"status": "NOT_DERIVABLE", "value": None, "reason": reason, "source_constraint_result_ids": []}
    hard = [item for item in constraints if item["is_hard_constraint"]]
    exact = [item for item in hard if item["constraint_type"] == "exact_cardinality"]
    block_hard = [item for item in hard if item["constraint_type"] != "exact_cardinality"]
    metadata = [item for item in constraints if item["constraint_type"] == "metadata_requirement_acknowledgment"]
    if strategy == "HARD_CONSTRAINT_COMPLIANCE":
        if len(hard) != 2:
            return _not_derivable("Derivation requires exactly two applicable hard constraints.")
        missing = _missing_constraint_reason(hard)
        if missing:
            return _missing(missing)
        value = sum(item["status"] == "PASS" for item in hard) / 2
        return _calculated(value, _result_ids(hard))
    if strategy == "DISTINCT_HARD_VIOLATIONS":
        if not hard:
            return _not_derivable("No applicable hard constraints exist.")
        missing = _missing_constraint_reason(hard)
        if missing:
            return _missing(missing)
        return _calculated(sum(item["status"] in {"PARTIAL", "FAIL"} for item in hard), _result_ids(hard))
    if strategy == "EXACT_CARDINALITY_COMPLIANCE":
        if len(exact) != 1:
            return _not_derivable("Derivation requires exactly one exact-cardinality constraint.")
        if exact[0]["status"] in {None, "UNKNOWN"}:
            return _missing(f"{exact[0]['constraint_key']} has no calculable result.")
        return _calculated(1 if exact[0]["status"] == "PASS" else 0, _result_ids(exact))
    if strategy == "METADATA_ACKNOWLEDGMENT":
        if len(metadata) != 1:
            return _not_derivable("Derivation requires exactly one metadata-acknowledgment constraint.")
        if metadata[0]["status"] in {None, "UNKNOWN"}:
            return _missing(f"{metadata[0]['constraint_key']} has no calculable result.")
        return _calculated(metadata[0]["status"], _result_ids(metadata))
    if strategy == "METADATA_CONSTRUCTION_DIVERGENCE":
        if len(metadata) != 1 or len(block_hard) != 1:
            return _not_derivable("Derivation requires one metadata acknowledgment and one block hard constraint.")
        missing = _missing_constraint_reason(metadata + block_hard)
        if missing:
            return _missing(missing)
        value = int(metadata[0]["status"] == "PASS" and block_hard[0]["status"] in {"PARTIAL", "FAIL"})
        return _calculated(value, _result_ids(metadata + block_hard))
    return _not_derivable("No recognized structured derivation exists.")


def _evaluate_analysis(definition, runs, strategies, conditions):
    outcome_key = definition["outcome_key"]
    strategy = strategies[outcome_key]
    text = " ".join(str(definition[key]).lower() for key in (
        "analysis_population", "comparison_definition", "aggregation_rule", "reporting_rule"
    ))
    if strategy == "TRACK_VIOLATION_RATE_UNAVAILABLE":
        return _analysis_not_derivable(definition, "Required per-track constraint results are not structured in the governed corpus.")
    if strategy == "TERMINAL_DISPOSITION":
        return _disposition_analysis(definition, runs)
    if "replicate-1" in text and "replicate-2" in text:
        return _replicate_analysis(definition, runs, conditions)
    if "counts and proportions" in text and strategy == "METADATA_CONSTRUCTION_DIVERGENCE":
        return _condition_summary_analysis(definition, runs)
    if "minus control" in text:
        return _paired_analysis(definition, runs, conditions)
    return _analysis_not_derivable(definition, "Registered analysis is not satisfied by a recognized structured derivation.")


def _paired_analysis(definition, runs, conditions):
    control, treatment = _condition_keys(conditions)
    if control is None or treatment is None:
        return _analysis_not_derivable(definition, "Exactly one registered CONTROL and TREATMENT condition are required.")
    grouped = defaultdict(dict)
    for run in runs:
        grouped[(run["block_key"], run["replicate_number"])][run["condition_key"]] = run
    pairs, exclusions = [], []
    for (block, replicate), members in sorted(grouped.items()):
        left, right = members.get(control), members.get(treatment)
        if left is None or right is None:
            exclusions.append({"block_key": block, "replicate_number": replicate, "reason": "Registered condition pair is incomplete."})
            continue
        lv, rv = _run_outcome(left, definition["outcome_key"]), _run_outcome(right, definition["outcome_key"])
        if lv["status"] != "CALCULATED" or rv["status"] != "CALCULATED":
            exclusions.append({"block_key": block, "replicate_number": replicate, "control_run_key": left["run_key"], "treatment_run_key": right["run_key"], "reason": f"CONTROL: {lv['reason'] or lv['status']}; TREATMENT: {rv['reason'] or rv['status']}"})
            continue
        pairs.append({"block_key": block, "replicate_number": replicate, "control_run_key": left["run_key"], "treatment_run_key": right["run_key"], "control_value": lv["value"], "treatment_value": rv["value"], "difference": rv["value"] - lv["value"]})
    values = [item["difference"] for item in pairs]
    aggregate = None if not values else {"pair_count": len(values), "mean_difference": sum(values) / len(values), "negative": sum(v < 0 for v in values), "zero": sum(v == 0 for v in values), "positive": sum(v > 0 for v in values)}
    return _analysis_result(definition, "CALCULATED" if pairs else "MISSING", pairs, exclusions, aggregate)


def _replicate_analysis(definition, runs, conditions):
    paired = _paired_analysis(definition, runs, conditions)
    if not paired["raw_results"]:
        return paired
    by_block = defaultdict(list)
    for item in paired["raw_results"]:
        by_block[item["block_key"]].append(item)
    raw, exclusions = [], list(paired["exclusions"])
    for block, items in sorted(by_block.items()):
        if len(items) != 2:
            exclusions.append({"block_key": block, "reason": "Both registered replicate differences are required."})
            continue
        directions = [_direction(item["difference"]) for item in sorted(items, key=lambda x: x["replicate_number"])]
        category = f"CONCORDANT_{directions[0]}" if directions[0] == directions[1] else "DISCORDANT"
        raw.append({"block_key": block, "replicate_differences": [item["difference"] for item in items], "classification": category})
    counts = Counter(item["classification"] for item in raw)
    return _analysis_result(definition, "CALCULATED" if raw else "MISSING", raw, exclusions, dict(sorted(counts.items())))


def _disposition_analysis(definition, runs):
    counts = Counter()
    raw, exclusions = [], []
    for run in runs:
        outcome = _run_outcome(run, definition["outcome_key"])
        if outcome["status"] != "CALCULATED":
            exclusions.append({"run_key": run["run_key"], "reason": outcome["reason"]})
            continue
        counts[(run["condition_key"], run["block_key"], outcome["value"])] += 1
        raw.append({"run_key": run["run_key"], "condition_key": run["condition_key"], "block_key": run["block_key"], "disposition": outcome["value"]})
    aggregate = [{"condition_key": key[0], "block_key": key[1], "disposition": key[2], "count": value} for key, value in sorted(counts.items())]
    return _analysis_result(definition, "CALCULATED" if raw else "MISSING", raw, exclusions, aggregate)


def _condition_summary_analysis(definition, runs):
    grouped = defaultdict(list)
    exclusions = []
    for run in runs:
        outcome = _run_outcome(run, definition["outcome_key"])
        if outcome["status"] != "CALCULATED":
            exclusions.append({"run_key": run["run_key"], "reason": outcome["reason"]})
            continue
        grouped[(run["condition_key"], run["block_key"])].append(outcome["value"])
    aggregate = [{"condition_key": key[0], "block_key": key[1], "count": len(values), "sum": sum(values), "proportion": sum(values) / len(values)} for key, values in sorted(grouped.items())]
    return _analysis_result(definition, "CALCULATED" if aggregate else "MISSING", [], exclusions, aggregate)


def _summary(runs, analyses, outcome_definitions, conditions):
    primary = next((item["outcome_key"] for item in outcome_definitions if item["role"] == "PRIMARY"), None)
    by_condition = defaultdict(list)
    for run in runs:
        if primary is not None:
            value = _run_outcome(run, primary)
            if value["status"] == "CALCULATED":
                by_condition[run["condition_key"]].append(value["value"])
    primary_analysis = next((item for item in analyses if item["outcome_key"] == primary and item["analysis_key"] != "replicate_consistency"), None)
    metadata_counts = Counter()
    divergence_counts = Counter()
    for run in runs:
        for outcome in run["outcomes"]:
            if outcome["strategy"] == "METADATA_ACKNOWLEDGMENT":
                metadata_counts[str(outcome["value"] if outcome["status"] == "CALCULATED" else outcome["status"])] += 1
            elif outcome["strategy"] == "METADATA_CONSTRUCTION_DIVERGENCE":
                divergence_counts[str(outcome["value"] if outcome["status"] == "CALCULATED" else outcome["status"])] += 1
    block_differences = defaultdict(list)
    if primary_analysis is not None:
        for item in primary_analysis["raw_results"]:
            block_differences[item["block_key"]].append(item["difference"])
    return {
        "primary_outcome_key": primary,
        "primary_by_condition": [{"condition_key": key, "calculable_runs": len(values), "mean": sum(values) / len(values)} for key, values in sorted(by_condition.items())],
        "primary_paired_analysis": primary_analysis,
        "primary_block_comparison": [
            {"block_key": key, "paired_differences": values,
             "mean_difference": sum(values) / len(values)}
            for key, values in sorted(block_differences.items())
        ],
        "replicate_consistency": next(
            (item for item in analyses if "replicate" in item["analysis_key"].lower()), None
        ),
        "constraint_result_counts": _constraint_result_counts(runs),
        "disposition_counts": dict(sorted(Counter(run["realization"]["disposition"] if run["realization"] else "PENDING" for run in runs).items())),
        "metadata_acknowledgment_counts": dict(sorted(metadata_counts.items())),
        "metadata_divergence_counts": dict(sorted(divergence_counts.items())),
        "analysis_overview": [
            {"analysis_key": item["analysis_key"], "outcome_key": item["outcome_key"],
             "status": item["status"], "exclusion_count": len(item["exclusions"]),
             "aggregate": item["aggregate"]}
            for item in analyses
        ],
        "registered_condition_roles": {item["condition_key"]: item["role"] for item in conditions},
    }


def _constraint_result_counts(runs):
    counts = Counter(
        constraint["status"] or "MISSING"
        for run in runs
        for constraint in run["constraints"]
    )
    return dict(sorted(counts.items()))


def _condition_keys(conditions):
    controls = [item["condition_key"] for item in conditions if item["role"] == "CONTROL"]
    treatments = [item["condition_key"] for item in conditions if item["role"] == "TREATMENT"]
    return (controls[0], treatments[0]) if len(controls) == len(treatments) == 1 else (None, None)


def _run_outcome(run, key):
    return next(item for item in run["outcomes"] if item["outcome_key"] == key)


def _outcome_role(definitions, key):
    return next(item["role"] for item in definitions if item["outcome_key"] == key)


def _missing_constraint_reason(items):
    missing = [item["constraint_key"] for item in items if item["status"] in {None, "UNKNOWN"}]
    return None if not missing else f"Constraint results are missing or UNKNOWN: {', '.join(missing)}."


def _result_ids(items):
    return [item["constraint_result_id"] for item in items if item["constraint_result_id"] is not None]


def _calculated(value, ids):
    return {"status": "CALCULATED", "value": value, "reason": None, "source_constraint_result_ids": ids}


def _missing(reason):
    return {"status": "MISSING", "value": None, "reason": reason, "source_constraint_result_ids": []}


def _not_derivable(reason):
    return {"status": "NOT_DERIVABLE", "value": None, "reason": reason, "source_constraint_result_ids": []}


def _analysis_not_derivable(definition, reason):
    return _analysis_result(definition, "NOT_DERIVABLE", [], [], None, reason)


def _analysis_result(definition, status, raw, exclusions, aggregate, reason=None):
    return {"analysis_definition_id": definition["id"], "analysis_key": definition["analysis_key"], "outcome_key": definition["outcome_key"], "status": status, "reason": reason, "raw_results": raw, "exclusions": exclusions, "aggregate": aggregate, "registered_definition": definition}


def _direction(value):
    return "NEGATIVE" if value < 0 else "POSITIVE" if value > 0 else "ZERO"

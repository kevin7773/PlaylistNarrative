from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Mapping

from playlist_narrative_engine.research_store.study_execution_registry import (
    DECIMAL_V1_CONTRACT,
    DISPOSITION_REASON_CODES,
)


def _parameters(plan: Mapping[str, object]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in plan["parameters"]:
        result.setdefault(item["parameter_key"], []).append(item["text_value"])
    return result


def canonical_decimal(value: Decimal) -> str:
    if not value:
        return DECIMAL_V1_CONTRACT.canonical_zero
    rendered = format(value, "f")
    if "." in rendered and DECIMAL_V1_CONTRACT.strip_trailing_zeroes:
        rendered = rendered.rstrip("0").rstrip(".")
    if rendered.startswith("."):
        rendered = "0" + rendered
    if rendered.startswith("-."):
        rendered = "-0" + rendered[1:]
    return rendered


def decimal_ratio(numerator: int, denominator: int) -> str:
    with localcontext() as context:
        context.prec = DECIMAL_V1_CONTRACT.precision
        context.rounding = DECIMAL_V1_CONTRACT.rounding
        return canonical_decimal(Decimal(numerator) / Decimal(denominator))


def decimal_difference(left: str, right: str, direction: str) -> str:
    with localcontext() as context:
        context.prec = DECIMAL_V1_CONTRACT.precision
        context.rounding = DECIMAL_V1_CONTRACT.rounding
        left_value, right_value = Decimal(left), Decimal(right)
        value = right_value - left_value if direction == "RIGHT_MINUS_LEFT" else left_value - right_value
        return canonical_decimal(value)


def decimal_mean(values: list[str]) -> str:
    with localcontext() as context:
        context.prec = DECIMAL_V1_CONTRACT.precision
        context.rounding = DECIMAL_V1_CONTRACT.rounding
        return canonical_decimal(sum((Decimal(item) for item in values), Decimal(0)) / Decimal(len(values)))


def unavailable_projection(calculator_key: str, calculator_version: str) -> dict[str, object]:
    return {
        "calculator_key": calculator_key,
        "calculator_version": calculator_version,
        "execution_state": "UNAVAILABLE",
        "derivability_state": None,
        "calculation_state": None,
        "reason_code": "CALCULATOR_IMPLEMENTATION_UNAVAILABLE",
    }


def _rate_base(plan: Mapping[str, object], context: Mapping[str, object]) -> dict[str, object]:
    return {
        "projection_type": "STATUS_RATE_RESULT",
        "projection_version": "1",
        "calculator_key": plan["calculator_key"],
        "calculator_version": plan["calculator_version"],
        "execution_state": "AVAILABLE",
        "derivability_state": "DERIVABLE",
        "calculation_state": None,
        "reason_code": None,
        "numerator_count": 0,
        "denominator_count": 0,
        "ratio_numerator": None,
        "ratio_denominator": None,
        "decimal_value": None,
        "applicable_input_count": 0,
        "unknown_count": 0,
        "excluded_count": 0,
        "missing_expected_count": 0,
        "registered_outcome_plan_id": plan["id"],
        "protocol_version_id": context["protocol_version_id"],
        "registration_hash": context["registration_hash"],
        "planned_run_id": context["planned_run_id"],
        "realization": context.get("realization"),
        "disposition_policy": context.get("disposition_policy"),
        "contributing_inputs": [],
        "excluded_inputs": [],
        "missing_expected_inputs": [],
    }


def disposition_projection(plan: Mapping[str, object], context: Mapping[str, object]) -> dict[str, object] | None:
    state = context["population_state"]
    policy = next(item for item in plan["disposition_policies"] if item["population_state"] == state)
    if policy["treatment"] == "CALCULATE":
        return None
    projection = _rate_base(plan, {**context, "disposition_policy": policy})
    projection["calculation_state"] = policy["treatment"]
    projection["reason_code"] = DISPOSITION_REASON_CODES[(state, policy["treatment"])]
    return projection


def calculate_status_rate(
    plan: Mapping[str, object], context: Mapping[str, object],
    inputs: list[dict[str, object]], missing: list[dict[str, object]],
    *, incompatible_reason: str | None = None,
) -> dict[str, object]:
    disposition = disposition_projection(plan, context)
    if disposition is not None:
        return disposition
    result = _rate_base(plan, context)
    result["applicable_input_count"] = len(inputs) + len(missing)
    result["missing_expected_count"] = len(missing)
    result["missing_expected_inputs"] = sorted(missing, key=lambda item: tuple(item["sort_key"]))
    parameters = _parameters(plan)
    numerator_statuses = set(parameters["numerator_status"])
    denominator_statuses = set(parameters["denominator_status"])
    unknown_policy = parameters["unknown_policy"][0]
    contributing: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    numerator = denominator = unknown = 0
    for item in sorted(inputs, key=lambda row: tuple(row["sort_key"])):
        status = item["status"]
        if status == "UNKNOWN":
            unknown += 1
            if unknown_policy == "EXCLUDE":
                excluded.append({**item, "exclusion_reason": "UNKNOWN_EXCLUDED_BY_REGISTERED_POLICY"})
            continue
        if status in denominator_statuses:
            denominator += 1
            in_numerator = status in numerator_statuses
            numerator += int(in_numerator)
            contributing.append({**item, "numerator": in_numerator, "denominator": True})
    result.update(
        numerator_count=numerator, denominator_count=denominator,
        applicable_input_count=len(inputs) + len(missing), unknown_count=unknown,
        excluded_count=len(excluded), contributing_inputs=contributing,
        excluded_inputs=excluded,
    )
    if incompatible_reason is not None:
        result.update(derivability_state="NOT_DERIVABLE", calculation_state=None, reason_code="INCOMPATIBLE_INSTRUMENTATION")
        result["instrumentation_issue"] = incompatible_reason
        return result
    if missing:
        policy = parameters["missing_input_policy"][0]
        if policy == "NOT_DERIVABLE":
            result.update(derivability_state="NOT_DERIVABLE", calculation_state=None, reason_code="REQUIRED_INPUT_NOT_GOVERNED")
        else:
            result.update(calculation_state="NOT_CALCULABLE", reason_code="EXPECTED_INPUT_MISSING")
        return result
    if unknown and unknown_policy == "NOT_CALCULABLE":
        result.update(calculation_state="NOT_CALCULABLE", reason_code="APPLICABLE_UNKNOWN")
        return result
    if denominator == 0:
        result.update(calculation_state="NOT_CALCULABLE", reason_code="ZERO_DENOMINATOR")
        return result
    result.update(
        calculation_state="CALCULATED",
        reason_code=("UNKNOWN_EXCLUDED_BY_REGISTERED_POLICY" if excluded else None),
        ratio_numerator=numerator,
        ratio_denominator=denominator,
        decimal_value=decimal_ratio(numerator, denominator),
    )
    return result


class StudyCalculatorExecutor:
    def __init__(self, *, outcome_calculators: set[tuple[str, str]] | None = None,
                 analysis_calculators: set[tuple[str, str]] | None = None) -> None:
        self.outcome_calculators = outcome_calculators if outcome_calculators is not None else {
            ("outcome.constraint_status_rate", "1"),
            ("outcome.subject_status_rate", "1"),
        }
        self.analysis_calculators = analysis_calculators if analysis_calculators is not None else {
            ("analysis.paired_difference", "1"),
            ("analysis.paired_difference", "2"),
        }

    def outcome_available(self, plan: Mapping[str, object]) -> bool:
        return (plan["calculator_key"], plan["calculator_version"]) in self.outcome_calculators

    def analysis_available(self, plan: Mapping[str, object]) -> bool:
        return (plan["calculator_key"], plan["calculator_version"]) in self.analysis_calculators


DEFAULT_STUDY_CALCULATOR_EXECUTOR = StudyCalculatorExecutor()


def calculate_paired_difference(
    plan: Mapping[str, object], protocol: Mapping[str, object],
    run_outcomes: Mapping[int, dict[str, object]], *, available: bool = True,
) -> dict[str, object]:
    if not available:
        return unavailable_projection(plan["calculator_key"], plan["calculator_version"])
    params = _parameters(plan)
    direction = params["difference_direction"][0]
    exclusion_version = str(plan["calculator_version"]) == "2"
    conditions = {item["comparison_role"]: item["condition_key"] for item in plan["condition_bindings"]}
    dimension_keys = [item["dimension_key"] for item in sorted(plan["dimensions"], key=lambda item: item["ordinal"])]
    grouped: dict[tuple[object, ...], dict[str, list[dict[str, object]]]] = {}
    for run in protocol["planned_runs"]:
        values = tuple(run[{"BLOCK": "block_key", "REPLICATE": "replicate_number"}[key]] for key in dimension_keys)
        group = grouped.setdefault(values, {"LEFT": [], "RIGHT": []})
        for role, condition_key in conditions.items():
            if run["condition_key"] == condition_key:
                group[role].append(run)
    pairs: list[dict[str, object]] = []
    valid_differences: list[str] = []
    invalid: list[dict[str, object]] = []
    contributing_runs: list[int] = []
    for dimensions, sides in sorted(grouped.items()):
        pair = {
            "dimensions": [{"dimension_key": key, "value": value} for key, value in zip(dimension_keys, dimensions)],
            "left_planned_run_id": sides["LEFT"][0]["id"] if len(sides["LEFT"]) == 1 else None,
            "right_planned_run_id": sides["RIGHT"][0]["id"] if len(sides["RIGHT"]) == 1 else None,
            "left_realization_id": sides["LEFT"][0].get("realization", {}).get("id") if len(sides["LEFT"]) == 1 and sides["LEFT"][0].get("realization") else None,
            "right_realization_id": sides["RIGHT"][0].get("realization", {}).get("id") if len(sides["RIGHT"]) == 1 and sides["RIGHT"][0].get("realization") else None,
            "left_outcome": None, "right_outcome": None,
            "left_decimal": None, "right_decimal": None, "difference": None,
            "pair_state": "CALCULATED", "reason_code": None,
        }
        reason = None
        if not sides["LEFT"] and not sides["RIGHT"]: reason = "PAIR_BOTH_SIDES_MISSING"
        elif not sides["LEFT"]: reason = "PAIR_LEFT_MISSING"
        elif not sides["RIGHT"]: reason = "PAIR_RIGHT_MISSING"
        elif len(sides["LEFT"]) > 1: reason = "PAIR_LEFT_DUPLICATE"
        elif len(sides["RIGHT"]) > 1: reason = "PAIR_RIGHT_DUPLICATE"
        if reason is None:
            left_id, right_id = sides["LEFT"][0]["id"], sides["RIGHT"][0]["id"]
            left, right = run_outcomes[left_id], run_outcomes[right_id]
            pair["left_outcome"], pair["right_outcome"] = left, right
            if left["execution_state"] == "UNAVAILABLE" or right["execution_state"] == "UNAVAILABLE":
                return unavailable_projection(plan["calculator_key"], plan["calculator_version"])
            for role, member in (("LEFT", left), ("RIGHT", right)):
                source_reasons = sorted(set(member.get("source_reason_codes", [])))
                suffix = source_reasons[0] if source_reasons else member.get("reason_code")
                if member["derivability_state"] == "NOT_DERIVABLE": reason = f"{role}_MEMBER_NOT_DERIVABLE" if exclusion_version else "MEMBER_NOT_DERIVABLE"; break
                if member["calculation_state"] == "MISSING": reason = f"{role}_MEMBER_MISSING" if exclusion_version else "MEMBER_MISSING"; break
                if member["calculation_state"] == "NOT_CALCULABLE": reason = (f"{role}_{suffix}" if exclusion_version and suffix else f"{role}_MEMBER_NOT_CALCULABLE" if exclusion_version else "MEMBER_NOT_CALCULABLE"); break
                if member["calculation_state"] != "CALCULATED" or member.get("decimal_value") is None:
                    reason = f"{role}_MEMBER_OUTPUT_TYPE_MISMATCH" if exclusion_version else "MEMBER_OUTPUT_TYPE_MISMATCH"; break
            if reason is None:
                pair["left_decimal"], pair["right_decimal"] = left["decimal_value"], right["decimal_value"]
                pair["difference"] = decimal_difference(left["decimal_value"], right["decimal_value"], direction)
                valid_differences.append(pair["difference"])
                contributing_runs.extend((left_id, right_id))
        if reason is not None:
            pair.update(pair_state="NOT_CALCULABLE", reason_code=reason)
            invalid.append({"dimensions": pair["dimensions"], "reason_code": reason})
        pairs.append(pair)
    negative = sum(Decimal(value) < 0 for value in valid_differences)
    zero = sum(Decimal(value) == 0 for value in valid_differences)
    positive = sum(Decimal(value) > 0 for value in valid_differences)
    reason = ("ZERO_ELIGIBLE_PAIRS" if exclusion_version else "ZERO_VALID_PAIRS") if not valid_differences else (None if exclusion_version else (invalid[0]["reason_code"] if invalid else None))
    return {
        "projection_type": "PAIRED_DIFFERENCE_SUMMARY", "projection_version": "2" if exclusion_version else "1",
        "execution_state": "AVAILABLE", "derivability_state": "DERIVABLE",
        "calculation_state": "NOT_CALCULABLE" if reason else "CALCULATED",
        "reason_code": reason,
        "calculator_key": plan["calculator_key"], "calculator_version": plan["calculator_version"],
        "registered_analysis_plan_id": plan["id"],
        "registered_input_outcome": plan["outcome_key"],
        "matching_dimensions": sorted(plan["dimensions"], key=lambda item: item["ordinal"]),
        "condition_bindings": sorted(plan["condition_bindings"], key=lambda item: item["comparison_role"]),
        "difference_direction": direction,
        "registered_population_count": len(protocol["planned_runs"]),
        "total_registered_pair_count": len(pairs),
        "eligible_pair_count": len(valid_differences), "excluded_pair_count": len(invalid),
        "complete_pair_count": len(pairs) - len(invalid), "incomplete_pair_count": len(invalid),
        "valid_numeric_pair_count": len(valid_differences),
        "negative_difference_count": negative, "zero_difference_count": zero,
        "positive_difference_count": positive,
        "mean_difference": decimal_mean(valid_differences) if valid_differences else None,
        "pairs": pairs, "contributing_run_ids": sorted(set(contributing_runs)),
        "invalid_or_incomplete_pairs": invalid,
        "protocol_version_id": protocol["id"], "registration_hash": protocol["registration_hash"],
    }

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable

from playlist_narrative_engine.research_store.study_evaluator_registry import (
    DEFAULT_STUDY_EVALUATOR_REGISTRY,
    EvaluatorIdentity,
    EvaluatorRole,
    StudyEvaluatorRegistry,
)
from playlist_narrative_engine.research_store.study_structural_derivation_registry import (
    DEFAULT_STRUCTURAL_DERIVATION_REGISTRY,
)


STATUSES = frozenset({"PASS", "PARTIAL", "FAIL", "UNKNOWN"})


@dataclass(frozen=True)
class StructuredEvaluationIssue:
    code: str
    subject_key: str | None
    measurement_key: str | None
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "subject_key": self.subject_key,
            "measurement_key": self.measurement_key,
            "message": self.message,
        }


def _identity(role: EvaluatorRole, reference: dict[str, object]) -> EvaluatorIdentity:
    return EvaluatorIdentity(role, str(reference["evaluator_key"]), str(reference["evaluator_version"]))


def _parameter_values(plan: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {}
    columns = {
        "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
        "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
    }
    for item in plan.get("parameters", []):
        value = item[columns[item["value_type"]]]
        if item["value_type"] == "DATE" and isinstance(value, str):
            value = date.fromisoformat(value)
        result[item["parameter_key"]] = value
    return result


def enumerate_evaluation_subjects(
    plan: dict[str, object], experiment: dict[str, object], constraint_id: int,
    registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
) -> list[dict[str, object]]:
    selector = registry.executable(_identity(EvaluatorRole.SUBJECT_SELECTOR, plan["subject_selector"]))
    if plan["subject_kind"] not in selector.supported_subject_kinds:
        raise ValueError("registered selector does not support the frozen subject kind")
    subjects = selector.implementation(plan, experiment, constraint_id)
    logical = [(item["subject_kind"], item["experiment_track_id"], item["governed_field"]) for item in subjects]
    if len(logical) != len(set(logical)):
        raise ValueError("selector produced duplicate logical subjects")
    return subjects


def _measurement_value_is_valid(item: dict[str, object], registered_type: str) -> bool:
    columns = {
        "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
        "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
    }
    populated = [key for key in columns.values() if item.get(key) is not None]
    if item.get("value_type") == "UNAVAILABLE":
        return not populated and bool(item.get("unavailable_reason"))
    return item.get("value_type") == registered_type and populated == [columns[registered_type]] and item.get("unavailable_reason") is None


def validate_structured_measurements(
    plan: dict[str, object], subjects: list[dict[str, object]],
    measurements: Iterable[dict[str, object]], experiment: dict[str, object] | None = None,
) -> dict[str, object]:
    issues: list[StructuredEvaluationIssue] = []
    subject_by_key = {str(item["subject_key"]): item for item in subjects}
    definitions = {str(item["measurement_key"]): item for item in plan["measurement_definitions"]}
    vocabulary = {(item["vocabulary_key"], item["term_key"]) for item in plan.get("vocabulary_terms", [])}
    observed: dict[tuple[str, str], dict[str, object]] = {}
    structural_keys = {
        key for key, definition in definitions.items()
        if definition["authority"] == "STRUCTURAL_DERIVATION"
    }
    for item in measurements:
        subject_key, measurement_key = str(item.get("subject_key")), str(item.get("measurement_key"))
        pair = (subject_key, measurement_key)
        if subject_key not in subject_by_key:
            issues.append(StructuredEvaluationIssue("UNEXPECTED_SUBJECT", subject_key, measurement_key, "measurement subject is not in the frozen enumeration")); continue
        if measurement_key not in definitions:
            issues.append(StructuredEvaluationIssue("UNEXPECTED_MEASUREMENT", subject_key, measurement_key, "measurement is not registered by the plan")); continue
        if pair in observed:
            issues.append(StructuredEvaluationIssue("DUPLICATE_MEASUREMENT", subject_key, measurement_key, "measurement appears more than once")); continue
        definition = definitions[measurement_key]
        if measurement_key in structural_keys:
            issues.append(StructuredEvaluationIssue("DERIVED_VALUE_SUPPLIED", subject_key, measurement_key, "operator-supplied structural values are prohibited")); continue
        observed[pair] = item
        if item.get("authority_kind") != definition["authority"]:
            issues.append(StructuredEvaluationIssue("AUTHORITY_MISMATCH", subject_key, measurement_key, "measurement authority differs from registration"))
        if not _measurement_value_is_valid(item, str(definition["value_type"])):
            issues.append(StructuredEvaluationIssue("VALUE_SHAPE_INVALID", subject_key, measurement_key, "typed value or UNAVAILABLE shape is invalid"))
        if item.get("value_type") == "UNAVAILABLE" and definition.get("unavailable_policy") != "MAY_BE_UNAVAILABLE":
            issues.append(StructuredEvaluationIssue("UNAVAILABLE_PROHIBITED", subject_key, measurement_key, "registered measurement policy requires a value"))
        if definition["value_type"] == "VOCABULARY_TERM" and item.get("value_type") != "UNAVAILABLE":
            if (definition["vocabulary_key"], item.get("vocabulary_term_key")) not in vocabulary:
                issues.append(StructuredEvaluationIssue("VOCABULARY_TERM_UNREGISTERED", subject_key, measurement_key, "term is not in the frozen vocabulary"))
        if definition["evidence_required"] and not item.get("evidence"):
            issues.append(StructuredEvaluationIssue("EVIDENCE_REQUIRED", subject_key, measurement_key, "registered measurement requires governed evidence"))
    if structural_keys and experiment is None:
        issues.append(StructuredEvaluationIssue("DERIVATION_CONTEXT_MISSING", None, None, "governed Experiment input is required for structural derivation"))
    elif experiment is not None:
        for subject_key, subject in subject_by_key.items():
            for measurement_key in structural_keys:
                definition = definitions[measurement_key]
                derived = DEFAULT_STRUCTURAL_DERIVATION_REGISTRY.derive(plan, definition, experiment, subject)
                observed[(subject_key, measurement_key)] = {
                    "subject_key": subject_key, "measurement_key": measurement_key,
                    "authority_kind": "STRUCTURAL_DERIVATION", **derived,
                    "recorded_by": f"{derived['derivation_key']}/{derived['derivation_version']}",
                    "unavailable_reason": None, "evidence": [],
                }
    for subject_key in subject_by_key:
        for measurement_key, definition in definitions.items():
            if definition["required"] and (subject_key, measurement_key) not in observed:
                issues.append(StructuredEvaluationIssue("REQUIRED_MEASUREMENT_MISSING", subject_key, measurement_key, "required measurement is absent"))
    return {
        "valid": not issues,
        "issues": [item.as_dict() for item in issues],
        "measurements": sorted(observed.values(), key=lambda item: (str(item["subject_key"]), str(item["measurement_key"]))),
    }


def calculate_subject_results(
    plan: dict[str, object], subjects: list[dict[str, object]],
    validated_measurements: list[dict[str, object]],
    registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
) -> list[dict[str, object]]:
    evaluator_identity = _identity(EvaluatorRole.SUBJECT_EVALUATOR, plan["subject_evaluator"])
    evaluator = registry.executable(evaluator_identity)
    parameters = _parameter_values(plan)
    definitions = {str(item["measurement_key"]): item for item in plan["measurement_definitions"]}
    evaluator_measurement_keys = {
        key for key, definition in definitions.items() if definition["required"]
    }
    by_subject: dict[str, list[dict[str, object]]] = {str(item["subject_key"]): [] for item in subjects}
    for item in validated_measurements:
        if str(item["measurement_key"]) not in evaluator_measurement_keys:
            continue
        enriched = dict(item)
        enriched["registered_value_type"] = definitions[str(item["measurement_key"])]["value_type"]
        by_subject[str(item["subject_key"])].append(enriched)
    results = []
    for subject in subjects:
        subject_key = str(subject["subject_key"])
        inputs = sorted(by_subject[subject_key], key=lambda item: str(item["measurement_key"]))
        status, reason = evaluator.implementation(inputs, parameters, plan)
        if status not in STATUSES:
            raise ValueError("subject evaluator returned an unsupported status")
        if status == "PARTIAL" and not plan["allow_partial_subject_status"]:
            raise ValueError("subject evaluator returned PARTIAL but the registered plan prohibits it")
        results.append({
            "subject": subject,
            "status": status,
            "evaluator_key": evaluator_identity.evaluator_key,
            "evaluator_version": evaluator_identity.evaluator_version,
            "contributing_measurement_ids": [item.get("id") for item in inputs if item.get("id") is not None],
            "contributing_measurement_keys": [item["measurement_key"] for item in inputs],
            "reason_code": reason,
        })
    return results


def calculate_aggregate_constraint_result(
    plan: dict[str, object], subject_results: list[dict[str, object]],
    *, supplied_aggregate_status: str | None = None,
    registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
) -> dict[str, object]:
    identity = _identity(EvaluatorRole.AGGREGATE_EVALUATOR, plan["aggregate_evaluator"])
    evaluator = registry.executable(identity)
    status, reason = evaluator.implementation(subject_results, _parameter_values(plan), plan)
    if status not in STATUSES:
        raise ValueError("aggregate evaluator returned an unsupported status")
    if supplied_aggregate_status is not None and supplied_aggregate_status != status:
        raise ValueError("supplied aggregate status contradicts deterministic structured evaluation")
    return {
        "status": status,
        "evidence": "Deterministically derived from structured per-subject results.",
        "provenance_type": "DERIVED_QUERY_RESULT",
        "recorded_by": f"{identity.evaluator_key}/{identity.evaluator_version}",
        "provenance_notes": reason,
        "aggregate_evaluator_key": identity.evaluator_key,
        "aggregate_evaluator_version": identity.evaluator_version,
        "reason_code": reason,
    }


def evaluate_structured_constraint(
    plan: dict[str, object], experiment: dict[str, object], constraint_id: int,
    measurements: Iterable[dict[str, object]], *,
    supplied_aggregate_status: str | None = None,
    registry: StudyEvaluatorRegistry = DEFAULT_STUDY_EVALUATOR_REGISTRY,
) -> dict[str, object]:
    subjects = enumerate_evaluation_subjects(plan, experiment, constraint_id, registry)
    validation = validate_structured_measurements(plan, subjects, measurements, experiment)
    if not validation["valid"]:
        return {"complete": False, "subjects": subjects, "issues": validation["issues"], "measurements": validation["measurements"], "subject_results": [], "aggregate_constraint_result": None}
    results = calculate_subject_results(plan, subjects, validation["measurements"], registry)
    aggregate = calculate_aggregate_constraint_result(plan, results, supplied_aggregate_status=supplied_aggregate_status, registry=registry)
    return {"complete": True, "subjects": subjects, "issues": [], "measurements": validation["measurements"], "subject_results": results, "aggregate_constraint_result": aggregate}

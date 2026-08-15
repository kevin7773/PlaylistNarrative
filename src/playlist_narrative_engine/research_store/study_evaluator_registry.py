from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Callable, Iterable, Mapping

from playlist_narrative_engine.research_store.study_schemas import StudyProtocolInput
from playlist_narrative_engine.research_store.study_structural_derivation_registry import (
    DEFAULT_STRUCTURAL_DERIVATION_REGISTRY,
)


class EvaluatorRole(StrEnum):
    SUBJECT_SELECTOR = "SUBJECT_SELECTOR"
    SUBJECT_EVALUATOR = "SUBJECT_EVALUATOR"
    AGGREGATE_EVALUATOR = "AGGREGATE_EVALUATOR"


@dataclass(frozen=True, order=True)
class EvaluatorIdentity:
    role: EvaluatorRole
    evaluator_key: str
    evaluator_version: str


@dataclass(frozen=True)
class ExecutableEvaluator:
    identity: EvaluatorIdentity
    supported_subject_kinds: frozenset[str]
    required_measurement_value_types: tuple[str, ...]
    required_parameter_types: Mapping[str, str]
    implementation: Callable[..., object]


def _single_measurement(measurements: list[dict[str, object]], expected_type: str) -> dict[str, object]:
    if len(measurements) != 1 or measurements[0]["registered_value_type"] != expected_type:
        raise ValueError(f"evaluator requires exactly one {expected_type} measurement")
    return measurements[0]


def _unknown_or_value(measurement: dict[str, object], field: str):
    if measurement["value_type"] == "UNAVAILABLE":
        return None
    return measurement[field]


def boolean_equals(measurements, parameters, _plan):
    item = _single_measurement(measurements, "BOOLEAN")
    value = _unknown_or_value(item, "boolean_value")
    if value is None:
        return "UNKNOWN", "MEASUREMENT_UNAVAILABLE"
    return ("PASS", "BOOLEAN_EQUALS") if value == parameters["expected"] else ("FAIL", "BOOLEAN_DIFFERS")


def integer_equals(measurements, parameters, _plan):
    item = _single_measurement(measurements, "INTEGER")
    value = _unknown_or_value(item, "integer_value")
    if value is None:
        return "UNKNOWN", "MEASUREMENT_UNAVAILABLE"
    return ("PASS", "INTEGER_EQUALS") if value == parameters["expected"] else ("FAIL", "INTEGER_DIFFERS")


def lexical_standalone_token(measurements, parameters, _plan):
    item = _single_measurement(measurements, "TEXT")
    value = _unknown_or_value(item, "text_value")
    if value is None:
        return "UNKNOWN", "MEASUREMENT_UNAVAILABLE"
    token = parameters["token"]
    flags = 0 if parameters["case_sensitive"] else re.IGNORECASE
    matched = re.search(rf"(?<![\w]){re.escape(token)}(?![\w])", value, flags) is not None
    return ("PASS", "STANDALONE_TOKEN_PRESENT") if matched else ("FAIL", "STANDALONE_TOKEN_ABSENT")


def date_inclusive_window(measurements, parameters, _plan):
    item = _single_measurement(measurements, "DATE")
    value = _unknown_or_value(item, "date_value")
    if value is None:
        return "UNKNOWN", "MEASUREMENT_UNAVAILABLE"
    if isinstance(value, str):
        value = date.fromisoformat(value)
    matched = parameters["start_date"] <= value <= parameters["end_date"]
    return ("PASS", "DATE_WITHIN_INCLUSIVE_WINDOW") if matched else ("FAIL", "DATE_OUTSIDE_INCLUSIVE_WINDOW")


def vocabulary_allowed(measurements, parameters, _plan):
    item = _single_measurement(measurements, "VOCABULARY_TERM")
    value = _unknown_or_value(item, "vocabulary_term_key")
    if value is None:
        return "UNKNOWN", "MEASUREMENT_UNAVAILABLE"
    matched = value == parameters["allowed_term"]
    return ("PASS", "VOCABULARY_TERM_ALLOWED") if matched else ("FAIL", "VOCABULARY_TERM_DISALLOWED")


def single_subject(results, _parameters, _plan):
    if len(results) != 1:
        raise ValueError("SINGLE_SUBJECT requires exactly one subject result")
    return results[0]["status"], "SINGLE_SUBJECT_STATUS"


def all_subjects_required(results, parameters, _plan):
    statuses = [item["status"] for item in results]
    if any(status == "UNKNOWN" for status in statuses):
        return parameters["unknown_status"], "UNKNOWN_SUBJECT_PRESENT"
    if all(status == "PASS" for status in statuses):
        return "PASS", "ALL_SUBJECTS_PASS"
    if all(status == "FAIL" for status in statuses):
        return parameters["all_fail_status"], "ALL_SUBJECTS_FAIL"
    return parameters["mixed_status"], "MIXED_SUBJECT_RESULTS"


def select_run(plan, experiment, constraint_id):
    return [{
        "subject_key": "RUN", "experiment_id": experiment["id"],
        "constraint_id": constraint_id, "subject_kind": plan["subject_kind"],
        "experiment_track_id": None, "governed_field": None,
        "enumeration_ordinal": 1,
    }]


def select_all_placements(plan, experiment, constraint_id):
    tracks = sorted(
        experiment.get("tracks", []),
        key=lambda row: (int(row["observed_ordinal"]), int(row["id"])),
    )
    field = plan.get("subject_field") if plan["subject_kind"] == "PLACEMENT_FIELD" else None
    prefix = "FIELD" if field else "TRACK"
    return [{
        "subject_key": f"{prefix}:{track['id']}" + (f":{field}" if field else ""),
        "experiment_id": experiment["id"], "constraint_id": constraint_id,
        "subject_kind": plan["subject_kind"], "experiment_track_id": track["id"],
        "governed_field": field, "enumeration_ordinal": ordinal,
    } for ordinal, track in enumerate(tracks, start=1)]


GENERIC_EXECUTABLE_EVALUATORS = (
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_SELECTOR, "selector.run", "1"), frozenset({"RUN"}), (), {}, select_run),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_SELECTOR, "selector.all_placements", "1"), frozenset({"EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), (), {}, select_all_placements),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.boolean_equals", "1"), frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), ("BOOLEAN",), {"expected": "BOOLEAN"}, boolean_equals),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.integer_equals", "1"), frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), ("INTEGER",), {"expected": "INTEGER"}, integer_equals),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.lexical_standalone_token", "1"), frozenset({"PLACEMENT_FIELD"}), ("TEXT",), {"token": "TEXT", "case_sensitive": "BOOLEAN"}, lexical_standalone_token),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.date_inclusive_window", "1"), frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), ("DATE",), {"start_date": "DATE", "end_date": "DATE"}, date_inclusive_window),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.vocabulary_allowed", "1"), frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), ("VOCABULARY_TERM",), {"allowed_term": "VOCABULARY_TERM"}, vocabulary_allowed),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.AGGREGATE_EVALUATOR, "aggregate.single_subject", "1"), frozenset({"RUN", "EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), (), {}, single_subject),
    ExecutableEvaluator(EvaluatorIdentity(EvaluatorRole.AGGREGATE_EVALUATOR, "aggregate.all_subjects_required", "1"), frozenset({"EXPERIMENT_PLACEMENT", "PLACEMENT_FIELD"}), (), {"mixed_status": "TEXT", "all_fail_status": "TEXT", "unknown_status": "TEXT"}, all_subjects_required),
)


class StudyEvaluatorRegistry:
    """Versioned registration boundary for deterministic structured evaluators."""

    def __init__(
        self,
        identities: Iterable[EvaluatorIdentity] = (),
        executables: Iterable[ExecutableEvaluator] = (),
    ) -> None:
        executable_map = {item.identity: item for item in executables}
        self._executables = executable_map
        self._identities = frozenset(identities) | frozenset(executable_map)

    def supports(self, identity: EvaluatorIdentity) -> bool:
        return identity in self._identities

    def require(self, identity: EvaluatorIdentity) -> None:
        if not self.supports(identity):
            raise ValueError(
                "unsupported structured-evaluation evaluator identity: "
                f"{identity.role.value}/{identity.evaluator_key}/{identity.evaluator_version}"
            )

    def executable(self, identity: EvaluatorIdentity) -> ExecutableEvaluator:
        self.require(identity)
        if identity not in self._executables:
            raise ValueError(
                "structured-evaluation identity has no executable implementation: "
                f"{identity.role.value}/{identity.evaluator_key}/{identity.evaluator_version}"
            )
        return self._executables[identity]

    def validate_protocol(self, protocol: StudyProtocolInput) -> None:
        for definition in protocol.constraint_definitions:
            plan = definition.structured_evaluation_plan
            if plan is None:
                continue
            identities = (
                EvaluatorIdentity(EvaluatorRole.SUBJECT_SELECTOR, plan.subject_selector.evaluator_key, plan.subject_selector.evaluator_version),
                EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, plan.subject_evaluator.evaluator_key, plan.subject_evaluator.evaluator_version),
                EvaluatorIdentity(EvaluatorRole.AGGREGATE_EVALUATOR, plan.aggregate_evaluator.evaluator_key, plan.aggregate_evaluator.evaluator_version),
            )
            for identity in identities:
                self.require(identity)
                executable = self._executables.get(identity)
                if executable is not None and plan.subject_kind.value not in executable.supported_subject_kinds:
                    raise ValueError(f"{identity.evaluator_key}/{identity.evaluator_version} does not support {plan.subject_kind.value}")
            subject = self._executables.get(identities[1])
            aggregate = self._executables.get(identities[2])
            measurement_types = tuple(item.value_type.value for item in plan.measurement_definitions if item.required)
            if subject is not None and sorted(measurement_types) != sorted(subject.required_measurement_value_types):
                raise ValueError("registered measurement definitions do not match subject evaluator requirements")
            parameter_types = {item.parameter_key: item.value_type.value for item in plan.parameters}
            for executable in (subject, aggregate):
                if executable is not None:
                    for key, value_type in executable.required_parameter_types.items():
                        if parameter_types.get(key) != value_type:
                            raise ValueError(f"evaluator requires parameter {key} with value type {value_type}")
            values = {
                item.parameter_key: (
                    item.text_value if item.value_type.value == "TEXT" else
                    item.date_value if item.value_type.value == "DATE" else None
                ) for item in plan.parameters
            }
            if identities[1].evaluator_key == "subject.lexical_standalone_token" and not values.get("token"):
                raise ValueError("lexical standalone-token evaluator requires a non-empty token")
            if identities[1].evaluator_key == "subject.date_inclusive_window" and values["start_date"] > values["end_date"]:
                raise ValueError("date-window start_date must not follow end_date")
            if identities[2].evaluator_key == "aggregate.all_subjects_required":
                for key in ("mixed_status", "all_fail_status", "unknown_status"):
                    if values.get(key) not in {"PASS", "PARTIAL", "FAIL", "UNKNOWN"}:
                        raise ValueError(f"aggregate status parameter {key} is invalid")
            for measurement in plan.measurement_definitions:
                if measurement.unavailable_policy is None:
                    raise ValueError("structured measurement requires an explicit unavailable policy")
                DEFAULT_STRUCTURAL_DERIVATION_REGISTRY.validate_measurement(plan, measurement)


DEFAULT_STUDY_EVALUATOR_REGISTRY = StudyEvaluatorRegistry(executables=GENERIC_EXECUTABLE_EVALUATORS)

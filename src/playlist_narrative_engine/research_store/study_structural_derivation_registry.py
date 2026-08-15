from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Mapping


@dataclass(frozen=True, order=True)
class StructuralDerivationIdentity:
    derivation_key: str
    derivation_version: str


@dataclass(frozen=True)
class StructuralDerivation:
    identity: StructuralDerivationIdentity
    supported_subject_kinds: frozenset[str]
    output_value_type: str
    required_governed_inputs: tuple[str, ...]
    required_parameter_types: Mapping[str, str]
    implementation: Callable[[dict[str, object], dict[str, object], dict[str, object]], object]


def _placement_count(experiment, _subject, _parameters):
    return len(experiment.get("tracks", []))


def _distinct_field_value_count(experiment, _subject, parameters):
    field = parameters["governed_field"]
    allowed = {
        "display_title": "title",
        "display_artist": "artist",
        "explicit_flag": "explicit_flag",
        "version_or_remaster_text": "version_or_remaster_text",
    }
    if field not in allowed:
        raise ValueError("distinct-field derivation governed_field is unsupported")
    source_field = allowed[field]
    return len({row.get(source_field) for row in experiment.get("tracks", [])})


GENERIC_STRUCTURAL_DERIVATIONS = (
    StructuralDerivation(
        StructuralDerivationIdentity("structural.placement_count", "1"),
        frozenset({"RUN"}), "INTEGER", ("experiment.tracks",), {}, _placement_count,
    ),
    StructuralDerivation(
        StructuralDerivationIdentity("structural.distinct_field_value_count", "1"),
        frozenset({"RUN"}), "INTEGER", ("experiment.tracks",),
        {"governed_field": "TEXT"}, _distinct_field_value_count,
    ),
)


class StructuralDerivationRegistry:
    def __init__(self, derivations: Iterable[StructuralDerivation] = ()) -> None:
        self._derivations = {item.identity: item for item in derivations}

    def require(self, key: str, version: str) -> StructuralDerivation:
        identity = StructuralDerivationIdentity(key, version)
        if identity not in self._derivations:
            raise ValueError(f"unsupported structural derivation identity: {key}/{version}")
        return self._derivations[identity]

    def validate_measurement(self, plan, measurement) -> None:
        if measurement.authority.value != "STRUCTURAL_DERIVATION":
            if measurement.derivation_key is not None:
                raise ValueError("non-structural measurement may not declare a structural derivation")
            return
        if measurement.derivation_key is None or measurement.derivation_version is None:
            raise ValueError("STRUCTURAL_DERIVATION measurement requires a derivation identity")
        derivation = self.require(measurement.derivation_key, measurement.derivation_version)
        if plan.subject_kind.value not in derivation.supported_subject_kinds:
            raise ValueError("structural derivation does not support the registered subject kind")
        if measurement.value_type.value != derivation.output_value_type:
            raise ValueError("structural derivation output type differs from measurement type")
        parameter_types = {item.parameter_key: item.value_type.value for item in plan.parameters}
        for key, value_type in derivation.required_parameter_types.items():
            if parameter_types.get(key) != value_type:
                raise ValueError(f"structural derivation requires parameter {key} with value type {value_type}")

    def derive(self, plan: dict[str, object], measurement: dict[str, object], experiment, subject):
        derivation = self.require(str(measurement["derivation_key"]), str(measurement["derivation_version"]))
        parameters = _parameter_values(plan)
        value = derivation.implementation(experiment, subject, parameters)
        return {
            "value_type": derivation.output_value_type,
            _value_column(derivation.output_value_type): value,
            "derivation_key": derivation.identity.derivation_key,
            "derivation_version": derivation.identity.derivation_version,
        }


def _parameter_values(plan: dict[str, object]) -> dict[str, object]:
    columns = {
        "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
        "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
    }
    return {item["parameter_key"]: item[columns[item["value_type"]]] for item in plan.get("parameters", [])}


def _value_column(value_type: str) -> str:
    return {
        "BOOLEAN": "boolean_value", "INTEGER": "integer_value", "DECIMAL": "decimal_value",
        "TEXT": "text_value", "DATE": "date_value", "VOCABULARY_TERM": "vocabulary_term_key",
    }[value_type]


DEFAULT_STRUCTURAL_DERIVATION_REGISTRY = StructuralDerivationRegistry(
    GENERIC_STRUCTURAL_DERIVATIONS
)

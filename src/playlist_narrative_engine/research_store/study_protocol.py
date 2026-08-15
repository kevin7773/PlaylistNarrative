from __future__ import annotations

import hashlib
import json

from playlist_narrative_engine.research_store.study_schemas import StudyProtocolInput


def canonical_protocol_bytes(
    study_key: str,
    title: str,
    protocol: StudyProtocolInput,
) -> bytes:
    """Return the exact UTF-8 JSON hashed for a registered protocol snapshot.

    Canonicalization is deliberately mechanical: Pydantic JSON-mode values,
    lexicographically sorted object keys, preserved list order, no insignificant
    whitespace, literal Unicode, and no implicit value normalization.
    """
    protocol_document = protocol.model_dump(mode="json")
    contract = protocol_document.get("execution_contract")
    if contract is None:
        protocol_document.pop("execution_contract", None)
    else:
        contract["outcome_calculation_plans"] = sorted(
            contract["outcome_calculation_plans"], key=lambda item: item["outcome_key"]
        )
        for plan in contract["outcome_calculation_plans"]:
            plan["disposition_policies"] = sorted(
                plan["disposition_policies"], key=lambda item: item["population_state"]
            )
            plan["constraint_bindings"] = sorted(
                plan["constraint_bindings"],
                key=lambda item: (item["ordinal"], item["binding_role"], item["constraint_key"]),
            )
            plan["subject_kinds"] = sorted(plan["subject_kinds"])
            plan["parameters"] = sorted(
                plan["parameters"], key=lambda item: (item["parameter_key"], item["ordinal"])
            )
            plan["vocabulary_terms"] = sorted(
                plan["vocabulary_terms"], key=lambda item: (item["vocabulary_key"], item["term_key"])
            )
        contract["analysis_calculation_plans"] = sorted(
            contract["analysis_calculation_plans"], key=lambda item: item["analysis_key"]
        )
        for plan in contract["analysis_calculation_plans"]:
            plan["dimensions"] = sorted(
                plan["dimensions"],
                key=lambda item: (item["ordinal"], item["dimension_role"], item["dimension_key"]),
            )
            plan["condition_bindings"] = sorted(
                plan["condition_bindings"], key=lambda item: item["comparison_role"]
            )
            plan["parameters"] = sorted(
                plan["parameters"], key=lambda item: (item["parameter_key"], item["ordinal"])
            )
    for definition in protocol_document["constraint_definitions"]:
        if definition.get("structured_evaluation_plan") is None:
            definition.pop("structured_evaluation_plan", None)
            continue
        for measurement in definition["structured_evaluation_plan"]["measurement_definitions"]:
            for key in ("derivation_key", "derivation_version", "unavailable_policy"):
                if measurement.get(key) is None:
                    measurement.pop(key, None)
    document = {
        "study_key": study_key,
        "title": title,
        "protocol": protocol_document,
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def legacy_canonical_protocol_bytes(
    study_key: str,
    title: str,
    protocol: StudyProtocolInput,
) -> bytes:
    """Reconstruct the exact pre-P7 canonical representation.

    This function is an explicit historical-conformance boundary. It refuses
    protocols that contain P7 plans rather than silently discarding governed
    future content.
    """
    if any(
        item.structured_evaluation_plan is not None
        for item in protocol.constraint_definitions
    ):
        raise ValueError("legacy canonicalization cannot omit a structured-evaluation plan")
    if protocol.execution_contract is not None:
        raise ValueError("legacy canonicalization cannot omit a study execution contract")
    return canonical_protocol_bytes(study_key, title, protocol)


def protocol_registration_hash(
    study_key: str,
    title: str,
    protocol: StudyProtocolInput,
) -> str:
    return hashlib.sha256(canonical_protocol_bytes(study_key, title, protocol)).hexdigest()

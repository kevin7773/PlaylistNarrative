from __future__ import annotations

import hashlib
import json

from playlist_narrative_engine.evaluation.schemas import EvaluationReport
from playlist_narrative_engine.journey import (
    JourneyPlanArtifact,
    serialize_journey_plan_artifact,
)
from playlist_narrative_engine.sequencing.canonical import (
    construction_policy_sha256,
    construction_result_sha256,
)
from playlist_narrative_engine.sequencing.constructor import (
    CONSTRUCTION_POLICY_SCHEMA_VERSION,
    ConstructionPolicy,
    ConstructionResult,
)


def serialize_evaluation_report(report: EvaluationReport) -> bytes:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def evaluation_report_sha256(report: EvaluationReport) -> str:
    return hashlib.sha256(serialize_evaluation_report(report)).hexdigest()


def evaluation_report_matches_inputs(
    report: EvaluationReport,
    *,
    construction_result: ConstructionResult,
    journey_plan: JourneyPlanArtifact,
    construction_policy: ConstructionPolicy,
) -> bool:
    binding = report.input_binding
    return (
        binding.construction_result_schema_version
        == construction_result.schema_version
        and binding.construction_result_sha256
        == construction_result_sha256(construction_result)
        and binding.journey_id == journey_plan.journey_id
        and binding.journey_schema_version == journey_plan.schema_version
        and binding.journey_artifact_sha256
        == hashlib.sha256(
            serialize_journey_plan_artifact(journey_plan)
        ).hexdigest()
        and binding.construction_policy_schema_version
        == CONSTRUCTION_POLICY_SCHEMA_VERSION
        and binding.construction_policy_sha256
        == construction_policy_sha256(construction_policy)
    )

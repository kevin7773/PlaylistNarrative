from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from playlist_narrative_engine.journey import (
    JourneyPlanArtifact,
    serialize_journey_plan_artifact,
)
from playlist_narrative_engine.sequencing.constructor import (
    CONSTRUCTION_BINDING_SCHEMA_VERSION,
    CONSTRUCTION_POLICY_SCHEMA_VERSION,
    ConstructionInputBinding,
    ConstructionPolicy,
    ConstructionResult,
    ConstructionState,
)

if TYPE_CHECKING:
    from playlist_narrative_engine.candidate_formation.integration_schemas import (
        FormedCandidatePoolView,
    )


def serialize_construction_policy(policy: ConstructionPolicy) -> bytes:
    return _canonical_bytes(
        {
            "schema_version": CONSTRUCTION_POLICY_SCHEMA_VERSION,
            "max_tracks_per_artist": policy.max_tracks_per_artist,
            "discovery_familiarity_threshold": (
                policy.discovery_familiarity_threshold
            ),
        }
    )


def construction_policy_sha256(policy: ConstructionPolicy) -> str:
    return _sha256(serialize_construction_policy(policy))


def serialize_construction_state_authority(state: ConstructionState) -> bytes:
    """Serialize only governed pre-call state, never container identity."""

    return _canonical_bytes(
        {
            "placed_tracks": tuple(state.placed_tracks),
            "previous_track": state.previous_track,
            "elapsed_seconds": state.elapsed_seconds,
            "current_phase_index": state.current_phase_index,
            "used_track_ids": tuple(
                sorted(state.used_track_ids, key=lambda value: value.encode("utf-8"))
            ),
            "artist_counts": tuple(
                sorted(
                    state.artist_counts.items(),
                    key=lambda item: item[0].encode("utf-8"),
                )
            ),
            "discovery_count": state.discovery_count,
            "rejections": tuple(state.rejections),
            "formation_trace": state.formation_trace,
            "journey_plan_artifact": state.journey_plan_artifact,
        }
    )


def create_construction_input_binding(
    *,
    journey_plan: JourneyPlanArtifact,
    formed_pool: FormedCandidatePoolView,
    construction_policy: ConstructionPolicy,
    initial_state: ConstructionState,
) -> ConstructionInputBinding:
    return ConstructionInputBinding(
        schema_version=CONSTRUCTION_BINDING_SCHEMA_VERSION,
        journey_id=journey_plan.journey_id,
        journey_schema_version=journey_plan.schema_version,
        journey_artifact_sha256=_sha256(
            serialize_journey_plan_artifact(journey_plan)
        ),
        formation_parent_schema_version=(
            formed_pool.trace.parent_schema_version
        ),
        formation_parent_sha256=formed_pool.trace.parent_artifact_sha256,
        formation_request_id=formed_pool.trace.parent_request_id,
        construction_policy_schema_version=(
            CONSTRUCTION_POLICY_SCHEMA_VERSION
        ),
        construction_policy_sha256=construction_policy_sha256(
            construction_policy
        ),
        initial_state_sha256=_sha256(
            serialize_construction_state_authority(initial_state)
        ),
        initial_placement_count=len(initial_state.placed_tracks),
    )


def serialize_construction_result(result: ConstructionResult) -> bytes:
    return _canonical_bytes(asdict(result))


def construction_result_sha256(result: ConstructionResult) -> str:
    return _sha256(serialize_construction_result(result))


def verify_construction_result_digest(
    result: ConstructionResult,
    expected_sha256: str,
) -> bool:
    return construction_result_sha256(result) == expected_sha256


def construction_result_matches_inputs(
    result: ConstructionResult,
    *,
    journey_plan: JourneyPlanArtifact,
    formed_pool: FormedCandidatePoolView,
    construction_policy: ConstructionPolicy,
) -> bool:
    binding = result.input_binding
    return (
        binding.journey_id == journey_plan.journey_id
        and binding.journey_schema_version == journey_plan.schema_version
        and binding.journey_artifact_sha256
        == _sha256(serialize_journey_plan_artifact(journey_plan))
        and binding.formation_parent_schema_version
        == formed_pool.trace.parent_schema_version
        and binding.formation_parent_sha256
        == formed_pool.trace.parent_artifact_sha256
        and binding.formation_request_id == formed_pool.trace.parent_request_id
        and binding.construction_policy_schema_version
        == CONSTRUCTION_POLICY_SCHEMA_VERSION
        and binding.construction_policy_sha256
        == construction_policy_sha256(construction_policy)
        and result.formation_trace == formed_pool.trace
    )


def construction_result_matches_evaluation_inputs(
    result: ConstructionResult,
    *,
    journey_plan: JourneyPlanArtifact,
    construction_policy: ConstructionPolicy,
) -> bool:
    binding = result.input_binding
    return (
        binding.schema_version == CONSTRUCTION_BINDING_SCHEMA_VERSION
        and binding.journey_id == journey_plan.journey_id
        and binding.journey_schema_version == journey_plan.schema_version
        and binding.journey_artifact_sha256
        == _sha256(serialize_journey_plan_artifact(journey_plan))
        and binding.construction_policy_schema_version
        == CONSTRUCTION_POLICY_SCHEMA_VERSION
        and binding.construction_policy_sha256
        == construction_policy_sha256(construction_policy)
        and binding.formation_parent_schema_version
        == result.formation_trace.parent_schema_version
        and binding.formation_parent_sha256
        == result.formation_trace.parent_artifact_sha256
        and binding.formation_request_id
        == result.formation_trace.parent_request_id
    )


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def _json_default(value: object) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported canonical construction value: {type(value)!r}")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

from __future__ import annotations

import json

from playlist_narrative_engine.journey.schemas import (
    JourneyPlanArtifact,
    JourneyPlanningRequest,
)


def serialize_journey_planning_request(request: JourneyPlanningRequest) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return _serialize(request)


def serialize_journey_plan_artifact(artifact: JourneyPlanArtifact) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return _serialize(artifact)


def _serialize(value: object) -> bytes:
    if not hasattr(value, "model_dump"):
        raise TypeError("journey serialization requires a governed model")
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

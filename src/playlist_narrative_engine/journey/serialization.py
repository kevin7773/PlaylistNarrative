from __future__ import annotations

import json

from playlist_narrative_engine.journey.schemas import JourneyPlanArtifact


def serialize_journey_plan_artifact(artifact: JourneyPlanArtifact) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

from __future__ import annotations

import json

from playlist_narrative_engine.objective_safety.schemas import ObjectiveSafetyArtifact


def serialize_objective_safety_artifact(artifact: ObjectiveSafetyArtifact) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

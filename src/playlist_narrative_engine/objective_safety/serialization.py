from __future__ import annotations

import json

from playlist_narrative_engine.objective_safety.schemas import (
    ObjectiveIntentDeclarationArtifact,
    ObjectiveSafetyArtifact,
    ObjectiveSafetyRequest,
)


def serialize_objective_intent_declaration(
    artifact: ObjectiveIntentDeclarationArtifact,
) -> bytes:
    return _serialize(artifact)


def serialize_objective_safety_request(request: ObjectiveSafetyRequest) -> bytes:
    return _serialize(request)


def serialize_objective_safety_artifact(artifact: ObjectiveSafetyArtifact) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return _serialize(artifact)


def _serialize(value: object) -> bytes:
    if not hasattr(value, "model_dump"):
        raise TypeError("objective-safety serialization requires a governed model")

    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

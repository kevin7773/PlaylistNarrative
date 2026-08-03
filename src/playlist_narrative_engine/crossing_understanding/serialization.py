from __future__ import annotations

import json

from playlist_narrative_engine.crossing_understanding.schemas import (
    CrossingUnderstandingArtifact,
)


def serialize_crossing_understanding(
    artifact: CrossingUnderstandingArtifact,
) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

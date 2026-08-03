from __future__ import annotations

import json

from playlist_narrative_engine.curriculum_orientation.schemas import (
    CurriculumOrientationArtifact,
)


def serialize_curriculum_orientation(
    artifact: CurriculumOrientationArtifact,
) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

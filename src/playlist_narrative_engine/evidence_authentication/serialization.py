from __future__ import annotations

import json

from playlist_narrative_engine.evidence_authentication.schemas import (
    AuthenticatedStructuredCharacteristicArtifact,
    AuthenticatedStructuredCharacteristicArtifactContent,
)


def serialize_authentication_artifact_content(
    content: AuthenticatedStructuredCharacteristicArtifactContent,
) -> bytes:
    """Return canonical schema-order artifact-content JSON encoded as UTF-8."""

    return json.dumps(
        content.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def serialize_evidence_authentication(
    artifact: AuthenticatedStructuredCharacteristicArtifact,
) -> bytes:
    """Return canonical schema-order complete artifact JSON encoded as UTF-8."""

    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

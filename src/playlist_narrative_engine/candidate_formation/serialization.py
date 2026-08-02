from __future__ import annotations

import json

from playlist_narrative_engine.candidate_formation.schemas import (
    CandidateSourceEvidenceArtifact,
)


def serialize_candidate_source_evidence(
    artifact: CandidateSourceEvidenceArtifact,
) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    serialized = json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")

from __future__ import annotations

import hashlib
import json

from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CandidateFormationArtifact,
)
from playlist_narrative_engine.candidate_formation.former import (
    serialize_candidate_formation,
)
from playlist_narrative_engine.candidate_formation.integration_schemas import (
    CandidateFormationTrace,
    FormedCandidatePoolView,
    _new_formed_candidate_pool_view,
)


def derive_formed_candidate_pool(
    artifact: CandidateFormationArtifact,
) -> FormedCandidatePoolView:
    """Project the authenticated formed partition without reconstruction."""

    validated = CandidateFormationArtifact.model_validate(
        artifact.model_dump(mode="json")
    )
    canonical_bytes = serialize_candidate_formation(validated)
    return _new_formed_candidate_pool_view(
        trace=CandidateFormationTrace(
            parent_artifact_sha256=hashlib.sha256(canonical_bytes).hexdigest(),
            parent_schema_version=validated.schema_version,
            parent_request_id=validated.request_id,
            accepted_objective_artifact_id=validated.accepted_objective_artifact_id,
            objective_id=validated.objective_id,
            objective_statement=validated.objective_statement,
            journey_id=validated.journey_id,
            policy_id=validated.policy_id,
            policy_version=validated.policy_version,
            preference_rule_name=validated.preference_rule_name,
            preference_rule_version=validated.preference_rule_version,
        ),
        formed_entries=validated.formed,
    )


def serialize_formed_candidate_pool(view: FormedCandidatePoolView) -> bytes:
    return json.dumps(
        view.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

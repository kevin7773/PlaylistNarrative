from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.candidate_readiness import (
    AUTHORITY_DEFINITION_JSON, AUTHORITY_DEFINITION_SHA256,
    PREFERENCE_POLICY_JSON, PREFERENCE_POLICY_SHA256,
    SUPERSEDED_AUTHORITY_DEFINITION_SHA256, VOCABULARY_JSON,
    VOCABULARY_SHA256, ActiveFocusCandidateReadinessDeclaration,
    ReadinessField, ReadinessLevel, active_focus_candidate_formation_policy,
    project_level, verify_frozen_definitions,
)


def test_exact_frozen_authorities_and_policy_round_trip() -> None:
    assert len(VOCABULARY_JSON.encode("utf-8")) == 3882
    assert hashlib.sha256(VOCABULARY_JSON.encode()).hexdigest() == VOCABULARY_SHA256
    assert hashlib.sha256(AUTHORITY_DEFINITION_JSON.encode()).hexdigest() == AUTHORITY_DEFINITION_SHA256
    assert hashlib.sha256(PREFERENCE_POLICY_JSON.encode()).hexdigest() == PREFERENCE_POLICY_SHA256
    assert verify_frozen_definitions()
    assert active_focus_candidate_formation_policy().model_dump(mode="json") == json.loads(PREFERENCE_POLICY_JSON)
    authority = json.loads(AUTHORITY_DEFINITION_JSON)
    assert authority["authority_definition_version"] == "1.1"
    assert authority["predecessor_authority_definition_sha256"] == SUPERSEDED_AUTHORITY_DEFINITION_SHA256
    assert authority["accepted_objective_schema"] == "AcceptedObjectiveArtifact/2.0"
    assert authority["journey_plan_schema"] == "JourneyPlanArtifact/2.0"


def test_every_field_and_token_has_exact_quarter_step_projection() -> None:
    expected = [0.0, 0.25, 0.5, 0.75, 1.0]
    for field in ReadinessField:
        assert [project_level(field, level) for level in ReadinessLevel] == expected


@pytest.mark.parametrize("bad", ["level_0", " LEVEL_0", "LEVEL_0 ", "LOW", "high", "LEVEL_5", 0, 0.0, 0.25, True])
def test_declaration_rejects_normalization_synonyms_unknown_and_numeric_input(bad: object) -> None:
    with pytest.raises(ValidationError):
        ActiveFocusCandidateReadinessDeclaration(track_id="track-1", energy=bad)


def test_declaration_rejects_replacement_metadata_and_mutated_definition() -> None:
    with pytest.raises(ValidationError):
        ActiveFocusCandidateReadinessDeclaration(track_id="track-1", energy="LEVEL_2", artist_name="replacement")
    mutated = VOCABULARY_JSON.replace('"0.25"', '"0.26"', 1)
    assert hashlib.sha256(mutated.encode()).hexdigest() != VOCABULARY_SHA256

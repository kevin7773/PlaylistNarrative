from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.journey import (
    JOURNEY_PLAN_SCHEMA_VERSION,
    ActiveFocusRequest,
    JourneyPlanArtifact,
    JourneyPlanner,
    serialize_journey_plan_artifact,
)
from playlist_narrative_engine.objective_assessment import Objective


def artifact() -> JourneyPlanArtifact:
    return JourneyPlanArtifact(
        journey_id="journey-001",
        objective=Objective(
            objective_id="coding-focus",
            statement="Support a focused coding session.",
        ),
        objective_safety_artifact_id="accepted-001",
        plan=JourneyPlanner().plan_active_focus(
            ActiveFocusRequest(duration_minutes=90, discovery_percent=20)
        ),
    )


def test_journey_artifact_is_versioned_frozen_and_exactly_identified() -> None:
    result = artifact()

    assert result.schema_version == JOURNEY_PLAN_SCHEMA_VERSION
    assert result.candidate_formation_performed is False
    with pytest.raises(ValidationError):
        result.plan.duration_minutes = 30
    with pytest.raises(ValidationError, match="identities must be exact"):
        JourneyPlanArtifact(
            journey_id=" journey-001",
            objective=result.objective,
            objective_safety_artifact_id="accepted-001",
            plan=result.plan,
        )


def test_journey_artifact_serialization_is_canonical() -> None:
    result = artifact()

    first = serialize_journey_plan_artifact(result)
    second = serialize_journey_plan_artifact(result)

    assert first == second
    assert json.loads(first)["journey_id"] == "journey-001"

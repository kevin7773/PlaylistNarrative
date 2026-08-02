from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    Objective,
    ObjectiveAssessment,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
)
from playlist_narrative_engine.objective_safety import (
    OBJECTIVE_SAFETY_SCHEMA_VERSION,
    SAFETY_REASON_EXPLANATIONS,
    AcceptedObjectiveArtifact,
    DeclinedObjectiveArtifact,
    ObjectiveSafetyReason,
    ObjectiveSafetyReasonCode,
    ObjectiveSafetyRequest,
    SafetyMetadataEntry,
    serialize_objective_safety_artifact,
)


def objective() -> Objective:
    return Objective(
        objective_id="coding-focus",
        statement="Support a focused coding session.",
    )


def sufficient_assessment() -> ObjectiveAssessment:
    return ObjectiveAssessment(
        objective=objective(),
        outcome=AssessmentOutcome.SUFFICIENT,
        clarification_required=False,
        present_dimensions=(
            "listening_context",
            "duration_minutes",
            "starting_energy",
            "ending_energy",
            "discovery_percent",
        ),
        missing_dimensions=(),
        clarification_questions=(),
    )


def accepted() -> AcceptedObjectiveArtifact:
    return AcceptedObjectiveArtifact(
        artifact_id="accepted-001",
        request_id="safety-request-001",
        objective=objective(),
        safety_policy_id="objective-safety",
        safety_policy_version="1.0",
        decision_explanation="The supplied objective is permitted by policy 1.0.",
    )


def test_request_requires_sufficient_assessment_and_canonicalizes_metadata() -> None:
    zeta = SafetyMetadataEntry(key="zeta", payload_json="2")
    alpha = SafetyMetadataEntry(key="alpha", payload_json="1")
    caller_entries = [zeta, alpha]

    request = ObjectiveSafetyRequest(
        request_id="request",
        objective_assessment=sufficient_assessment(),
        objective_metadata=caller_entries,
        safety_policy_id="policy",
        safety_policy_version="1.0",
    )

    assert tuple(entry.key for entry in request.objective_metadata) == ("alpha", "zeta")
    assert [entry.key for entry in caller_entries] == ["zeta", "alpha"]

    insufficient = ObjectiveAssessor().assess(
        ObjectiveAssessmentRequest(objective=objective(), evidence=())
    )
    with pytest.raises(ValidationError, match="requires a sufficient assessment"):
        ObjectiveSafetyRequest(
            request_id="request",
            objective_assessment=insufficient,
            safety_policy_id="policy",
            safety_policy_version="1.0",
        )


def test_accepted_artifact_is_immutable_versioned_and_authorizes_planning() -> None:
    artifact = accepted()

    assert artifact.schema_version == OBJECTIVE_SAFETY_SCHEMA_VERSION
    assert artifact.decision.value == "accepted"
    assert artifact.journey_planning_authorized is True
    assert artifact.musical_content_evaluated is False
    assert artifact.candidate_formation_performed is False
    with pytest.raises(ValidationError):
        artifact.artifact_id = "changed"


def test_declined_artifact_requires_fixed_ordered_reasons() -> None:
    missing = ObjectiveSafetyReason(
        code=ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
        field_path="$.context",
        explanation=SAFETY_REASON_EXPLANATIONS[
            ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING
        ],
    )
    undetermined = ObjectiveSafetyReason(
        code=ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
        field_path="$.objective",
        explanation=SAFETY_REASON_EXPLANATIONS[
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED
        ],
    )
    artifact = DeclinedObjectiveArtifact(
        artifact_id="declined",
        request_id="request",
        objective=objective(),
        safety_policy_id="policy",
        safety_policy_version="1.0",
        reasons=(missing, undetermined),
    )

    assert artifact.journey_planning_authorized is False
    assert tuple(reason.code for reason in artifact.reasons) == (
        ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
        ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
    )
    with pytest.raises(ValidationError, match="fixed precedence"):
        DeclinedObjectiveArtifact(
            artifact_id="declined",
            request_id="request",
            objective=objective(),
            safety_policy_id="policy",
            safety_policy_version="1.0",
            reasons=(undetermined, missing),
        )


def test_safety_serialization_is_canonical_utf8() -> None:
    artifact = accepted().model_copy(
        update={"decision_explanation": "Björk objective is permitted."}
    )

    first = serialize_objective_safety_artifact(artifact)
    second = serialize_objective_safety_artifact(artifact)

    assert first == second
    assert "Björk".encode("utf-8") in first
    assert json.loads(first)["artifact_kind"] == "accepted_objective"

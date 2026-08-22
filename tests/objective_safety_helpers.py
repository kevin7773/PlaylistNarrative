from __future__ import annotations

import hashlib

from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    Objective,
    ObjectiveAssessment,
)
from playlist_narrative_engine.objective_safety import (
    OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION,
    AcceptedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyRequest,
    canonical_assessment_sha256,
    canonical_objective_sha256,
    create_objective_safety_input_binding,
)


def sufficient_assessment(objective: Objective) -> ObjectiveAssessment:
    return ObjectiveAssessment(
        objective=objective,
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


def intent_declaration(
    objective: Objective,
    *,
    category: ObjectiveIntentCategory = (
        ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION
    ),
) -> ObjectiveIntentDeclarationArtifact:
    return ObjectiveIntentDeclarationArtifact(
        declaration_id=f"intent-{objective.objective_id}",
        objective_id=objective.objective_id,
        objective_statement_sha256=hashlib.sha256(
            objective.statement.encode("utf-8")
        ).hexdigest(),
        authority_reference=f"operator-declaration:{objective.objective_id}",
        state=ObjectiveIntentEvidenceState.ESTABLISHED,
        intent_category=category,
    )


def safety_request(objective: Objective) -> ObjectiveSafetyRequest:
    assessment = sufficient_assessment(objective)
    declaration = intent_declaration(objective)
    return ObjectiveSafetyRequest(
        request_id=f"safety-request-{objective.objective_id}",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
    )


def accepted_objective(
    objective: Objective,
    *,
    artifact_id: str = "accepted-001",
) -> AcceptedObjectiveArtifact:
    request = safety_request(objective)
    return AcceptedObjectiveArtifact(
        artifact_id=artifact_id,
        input_binding=create_objective_safety_input_binding(request),
        request_id=request.request_id,
        objective=objective,
        decision_explanation=OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION,
        objective_metadata=request.objective_metadata,
        context_metadata=request.context_metadata,
    )

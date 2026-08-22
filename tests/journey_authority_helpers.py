from __future__ import annotations

import hashlib

from playlist_narrative_engine.journey import (
    JourneyPlanArtifact,
    JourneyPlanner,
    JourneyPlanningRequest,
    canonical_assessment_request_sha256,
)
from playlist_narrative_engine.objective_assessment import (
    DiscoveryPercentEvidence,
    DurationMinutesEvidence,
    EndingEnergyEvidence,
    EnergyLevel,
    EvidenceDimension,
    ListeningContextEvidence,
    Objective,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
    StartingEnergyEvidence,
)
from playlist_narrative_engine.objective_safety import (
    AcceptedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyEvaluator,
    ObjectiveSafetyRequest,
    canonical_assessment_sha256,
    canonical_objective_sha256,
)


def journey_authority(
    objective: Objective,
    *,
    context: str = "Active Focus",
    duration_minutes: int = 90,
    discovery_percent: int = 20,
    starting_energy: EnergyLevel = EnergyLevel.MEDIUM,
    ending_energy: EnergyLevel = EnergyLevel.MEDIUM,
) -> tuple[JourneyPlanningRequest, AcceptedObjectiveArtifact, JourneyPlanArtifact]:
    assessment_request = ObjectiveAssessmentRequest(
        objective=objective,
        evidence=(
            ListeningContextEvidence(
                evidence_id="journey-context",
                dimension=EvidenceDimension.LISTENING_CONTEXT,
                value=context,
            ),
            DurationMinutesEvidence(
                evidence_id="journey-duration",
                dimension=EvidenceDimension.DURATION_MINUTES,
                value=duration_minutes,
            ),
            StartingEnergyEvidence(
                evidence_id="journey-start-energy",
                dimension=EvidenceDimension.STARTING_ENERGY,
                value=starting_energy,
            ),
            EndingEnergyEvidence(
                evidence_id="journey-end-energy",
                dimension=EvidenceDimension.ENDING_ENERGY,
                value=ending_energy,
            ),
            DiscoveryPercentEvidence(
                evidence_id="journey-discovery",
                dimension=EvidenceDimension.DISCOVERY_PERCENT,
                value=discovery_percent,
            ),
        ),
    )
    assessment = ObjectiveAssessor().assess(assessment_request)
    declaration = ObjectiveIntentDeclarationArtifact(
        declaration_id=f"intent-{objective.objective_id}",
        objective_id=objective.objective_id,
        objective_statement_sha256=hashlib.sha256(
            objective.statement.encode("utf-8")
        ).hexdigest(),
        authority_reference=f"operator-declaration:{objective.objective_id}",
        state=ObjectiveIntentEvidenceState.ESTABLISHED,
        intent_category=ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
    )
    safety_request = ObjectiveSafetyRequest(
        request_id=f"safety-request-{objective.objective_id}",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
    )
    accepted = ObjectiveSafetyEvaluator().evaluate(safety_request)
    if not isinstance(accepted, AcceptedObjectiveArtifact):
        raise AssertionError("test journey authority must be accepted")
    request = JourneyPlanningRequest(
        request_id=f"journey-request-{objective.objective_id}",
        objective_assessment_request=assessment_request,
        objective_assessment_request_sha256=(
            canonical_assessment_request_sha256(assessment_request)
        ),
        objective_assessment=assessment,
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        objective_safety_request=safety_request,
        objective_safety_request_sha256=safety_request.canonical_sha256,
        accepted_objective=accepted,
        accepted_objective_sha256=accepted.canonical_sha256,
    )
    return request, accepted, JourneyPlanner().plan_authoritative(request)

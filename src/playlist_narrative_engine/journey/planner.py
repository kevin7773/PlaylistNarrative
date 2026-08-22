from __future__ import annotations

from playlist_narrative_engine.journey.schemas import (
    ActiveFocusRequest,
    EnergyLevel,
    FamiliarityAllocation,
    JourneyContext,
    JourneyPlan,
    JourneyPlanArtifact,
    JourneyPlanningRequest,
    JourneyPhase,
    create_journey_planning_input_binding,
    derive_active_focus_request,
)


class JourneyPlanningInvalidInput(ValueError):
    """The governed authority chain cannot authorize Journey Planning."""


class JourneyPlanner:
    """Translate a validated request into a deterministic listening arc."""

    def plan_authoritative(
        self,
        request: JourneyPlanningRequest,
    ) -> JourneyPlanArtifact:
        if not isinstance(request, JourneyPlanningRequest):
            raise JourneyPlanningInvalidInput(
                "authoritative planning requires a JourneyPlanningRequest"
            )
        try:
            validated = JourneyPlanningRequest.model_validate(
                request.model_dump(mode="json")
            )
            parameters = derive_active_focus_request(validated)
            plan = self.plan_active_focus(parameters)
            artifact = JourneyPlanArtifact(
                journey_id=f"journey-plan:{validated.canonical_sha256}",
                input_binding=create_journey_planning_input_binding(validated),
                objective=validated.objective_assessment_request.objective,
                objective_safety_artifact_id=(
                    validated.accepted_objective.artifact_id
                ),
                plan=plan,
            )
            return JourneyPlanArtifact.model_validate(
                artifact.model_dump(mode="json")
            )
        except (TypeError, ValueError) as exc:
            raise JourneyPlanningInvalidInput(
                "journey planning authority is invalid or unverifiable"
            ) from exc

    def plan_active_focus(self, request: ActiveFocusRequest) -> JourneyPlan:
        """Return a non-authoritative deterministic plan calculation."""
        warm_up, sustained, landing = self._phase_durations(
            request.duration_minutes
        )
        familiarity = FamiliarityAllocation(
            familiar_percent=100 - request.discovery_percent,
            discovery_percent=request.discovery_percent,
        )
        phases = (
            JourneyPhase(
                name="Settle In",
                purpose="Establish momentum without demanding immediate intensity.",
                duration_minutes=warm_up,
                start_energy=request.starting_energy,
                end_energy=EnergyLevel.MEDIUM,
                familiarity=familiarity,
            ),
            JourneyPhase(
                name="Sustained Focus",
                purpose="Maintain a stable, low-distraction working groove.",
                duration_minutes=sustained,
                start_energy=EnergyLevel.MEDIUM,
                end_energy=EnergyLevel.HIGH,
                familiarity=familiarity,
            ),
            JourneyPhase(
                name="Controlled Landing",
                purpose="Ease intensity while preserving forward motion.",
                duration_minutes=landing,
                start_energy=EnergyLevel.HIGH,
                end_energy=request.ending_energy,
                familiarity=familiarity,
            ),
        )
        return JourneyPlan(
            context=JourneyContext.ACTIVE_FOCUS,
            duration_minutes=request.duration_minutes,
            discovery_percent=request.discovery_percent,
            phases=phases,
        )

    @staticmethod
    def _phase_durations(total: int) -> tuple[int, int, int]:
        warm_up = max(5, round(total * 0.15))
        landing = max(5, round(total * 0.15))
        sustained = total - warm_up - landing
        return warm_up, sustained, landing


def verify_journey_plan_artifact(
    artifact: JourneyPlanArtifact,
    *,
    request: JourneyPlanningRequest,
) -> bool:
    if not isinstance(artifact, JourneyPlanArtifact):
        return False
    try:
        validated = JourneyPlanArtifact.model_validate(
            artifact.model_dump(mode="json")
        )
        reproduced = JourneyPlanner().plan_authoritative(request)
    except (TypeError, ValueError):
        return False
    return validated == artifact == reproduced

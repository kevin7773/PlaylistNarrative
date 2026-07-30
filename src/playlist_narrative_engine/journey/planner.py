from __future__ import annotations

from playlist_narrative_engine.journey.schemas import (
    ActiveFocusRequest,
    EnergyLevel,
    FamiliarityAllocation,
    JourneyContext,
    JourneyPlan,
    JourneyPhase,
)


class JourneyPlanner:
    """Translate a validated request into a deterministic listening arc."""

    def plan_active_focus(self, request: ActiveFocusRequest) -> JourneyPlan:
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

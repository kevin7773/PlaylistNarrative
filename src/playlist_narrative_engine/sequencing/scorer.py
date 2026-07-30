from __future__ import annotations

from dataclasses import dataclass

from playlist_narrative_engine.journey.schemas import (
    EnergyLevel,
    JourneyContext,
    JourneyPhase,
)
from playlist_narrative_engine.sequencing.schemas import (
    ScoreBreakdown,
    TrackCandidate,
    TrackRole,
    TransitionProfile,
)


@dataclass(frozen=True)
class ScoringWeights:
    """Central weights for the five positive score components."""

    preference: float = 0.25
    context: float = 0.25
    phase: float = 0.20
    transition: float = 0.20
    discovery: float = 0.10

    def __post_init__(self) -> None:
        values = (
            self.preference,
            self.context,
            self.phase,
            self.transition,
            self.discovery,
        )
        if any(value < 0 for value in values):
            raise ValueError("scoring weights cannot be negative")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError("positive scoring weights must total 1.0")


class TrackScorer:
    """Score one track for one phase without selecting or ordering a playlist."""

    _DISCOVERY_SPOTLIGHT_WEIGHTS = ScoringWeights(
        preference=0.15,
        context=0.25,
        phase=0.20,
        transition=0.20,
        discovery=0.20,
    )
    _DISCOVERY_CONTEXT_THRESHOLD = 0.45
    _DISCOVERY_PHASE_THRESHOLD = 0.65
    _DISCOVERY_TRANSITION_THRESHOLD = 0.60
    _ENERGY_TARGETS = {
        EnergyLevel.LOW: 0.30,
        EnergyLevel.MEDIUM: 0.55,
        EnergyLevel.HIGH: 0.80,
    }
    _ABRUPT_THRESHOLD = 0.45
    _ABRUPT_PENALTY_SCALE = 20.0

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or ScoringWeights()

    def score(
        self,
        candidate: TrackCandidate,
        phase: JourneyPhase,
        *,
        context: JourneyContext = JourneyContext.ACTIVE_FOCUS,
        role: TrackRole = TrackRole.JOURNEY,
        previous_track: TrackCandidate | None = None,
        transition_profile: TransitionProfile | None = None,
        constraint_penalty: float = 0.0,
        narrative_drift_penalty: float = 0.0,
    ) -> ScoreBreakdown:
        if constraint_penalty < 0 or narrative_drift_penalty < 0:
            raise ValueError("penalties cannot be negative")
        if transition_profile is not None and previous_track is None:
            raise ValueError("a transition profile requires a previous track")

        reasons: list[str] = []
        preference_quality = candidate.preference
        if candidate.preference >= 0.8:
            reasons.append("Strong listener preference")

        context_quality = self._context_quality(candidate, context, reasons)
        phase_quality = self._phase_quality(candidate, phase, reasons)
        transition_quality, abrupt_penalty = self._transition_quality(
            candidate,
            previous_track,
            transition_profile,
            role,
            reasons,
        )
        discovery_quality = self._discovery_quality(
            candidate,
            role,
            context_quality,
            phase_quality,
            transition_quality,
            previous_track is not None,
            reasons,
        )

        if role is TrackRole.OPENING_ANCHOR and candidate.familiarity >= 0.7:
            reasons.append("Familiar opening anchor")
        if (
            role is TrackRole.OPENING_ANCHOR
            and candidate.lyrical_distraction >= 0.4
        ):
            reasons.append("Lyrical distraction weakens opening anchor")

        weights = self._weights_for_role(role)
        preference_score = self._component(
            preference_quality, weights.preference
        )
        context_score = self._component(context_quality, weights.context)
        phase_score = self._component(phase_quality, weights.phase)
        transition_score = self._component(
            transition_quality, weights.transition
        )
        discovery_score = self._component(
            discovery_quality, weights.discovery
        )
        effective_constraint_penalty = constraint_penalty + abrupt_penalty
        total = (
            preference_score
            + context_score
            + phase_score
            + transition_score
            + discovery_score
            - effective_constraint_penalty
            - narrative_drift_penalty
        )

        return ScoreBreakdown(
            preference_score=preference_score,
            context_score=context_score,
            phase_score=phase_score,
            transition_score=transition_score,
            discovery_score=discovery_score,
            constraint_penalty=self._rounded(effective_constraint_penalty),
            narrative_drift_penalty=self._rounded(narrative_drift_penalty),
            total_score=self._rounded(total),
            role=role,
            reasons=tuple(reasons),
        )

    def _context_quality(
        self,
        candidate: TrackCandidate,
        context: JourneyContext,
        reasons: list[str],
    ) -> float:
        if context is not JourneyContext.ACTIVE_FOCUS:
            return candidate.context_fit
        quality = (
            0.75 * candidate.context_fit
            + 0.15 * candidate.instrumentalness
            + 0.10 * candidate.groove
            - 0.40 * candidate.lyrical_distraction
        )
        if candidate.context_fit >= 0.8:
            reasons.append("Strong Active Focus context fit")
        if candidate.lyrical_distraction >= 0.65:
            reasons.append("High lyrical distraction for Active Focus")
        return self._clamp(quality)

    def _phase_quality(
        self,
        candidate: TrackCandidate,
        phase: JourneyPhase,
        reasons: list[str],
    ) -> float:
        target = (
            self._ENERGY_TARGETS[phase.start_energy]
            + self._ENERGY_TARGETS[phase.end_energy]
        ) / 2
        quality = self._clamp(1.0 - abs(candidate.energy - target) / 0.70)
        if quality >= 0.8:
            if phase.name == "Sustained Focus":
                reasons.append("Fits sustained-focus energy")
            else:
                reasons.append(f"Fits {phase.name.lower()} energy")
        elif quality < 0.5:
            reasons.append("Energy is poorly aligned with this phase")
        return quality

    def _transition_quality(
        self,
        candidate: TrackCandidate,
        previous: TrackCandidate | None,
        profile: TransitionProfile | None,
        role: TrackRole,
        reasons: list[str],
    ) -> tuple[float, float]:
        if previous is None:
            return (1.0 if role is TrackRole.OPENING_ANCHOR else 0.5), 0.0
        effective = profile or TransitionProfile(
            energy_continuity=1.0 - abs(previous.energy - candidate.energy),
            groove_continuity=1.0 - abs(previous.groove - candidate.groove),
            emotional_continuity=0.5,
            narrative_continuity=0.5,
            intentional_contrast=0.0,
        )
        continuity = (
            0.35 * effective.energy_continuity
            + 0.30 * effective.groove_continuity
            + 0.15 * effective.emotional_continuity
            + 0.20 * effective.narrative_continuity
        )
        local_continuity = (
            effective.energy_continuity + effective.groove_continuity
        ) / 2
        penalty = (
            max(0.0, self._ABRUPT_THRESHOLD - local_continuity)
            * self._ABRUPT_PENALTY_SCALE
            * (1.0 - effective.intentional_contrast)
        )
        quality = self._clamp(
            continuity + (1.0 - continuity) * 0.35 * effective.intentional_contrast
        )
        if (
            effective.energy_continuity >= 0.75
            and effective.groove_continuity >= 0.75
        ):
            reasons.append("Smooth groove and energy transition")
        elif local_continuity < self._ABRUPT_THRESHOLD:
            if effective.intentional_contrast >= 0.65:
                reasons.append("Intentional contrast supports an abrupt transition")
            else:
                reasons.append("Abrupt transition without intentional contrast")
        return quality, penalty

    def _discovery_quality(
        self,
        candidate: TrackCandidate,
        role: TrackRole,
        context_quality: float,
        phase_quality: float,
        transition_quality: float,
        has_previous: bool,
        reasons: list[str],
    ) -> float:
        if role is TrackRole.OPENING_ANCHOR:
            quality = candidate.familiarity * min(context_quality, phase_quality)
            if candidate.familiarity <= 0.35:
                reasons.append("High novelty weakens opening anchor")
            return quality

        continuity_gate = transition_quality if has_previous else 1.0
        qualifies = (
            context_quality >= self._DISCOVERY_CONTEXT_THRESHOLD
            and phase_quality >= self._DISCOVERY_PHASE_THRESHOLD
            and continuity_gate >= self._DISCOVERY_TRANSITION_THRESHOLD
        )
        if not qualifies:
            if candidate.familiarity <= 0.35:
                reasons.append("Discovery value withheld because fit thresholds fail")
            return 0.0

        novelty = 1.0 - candidate.familiarity
        if role is TrackRole.DISCOVERY_SPOTLIGHT:
            fit = (context_quality + phase_quality + continuity_gate) / 3
        else:
            fit = min(context_quality, phase_quality, continuity_gate)
        quality = novelty * fit
        if candidate.familiarity <= 0.35:
            if role is TrackRole.DISCOVERY_SPOTLIGHT:
                reasons.append("Qualified novelty supports discovery spotlight")
            else:
                reasons.append("Discovery candidate preserves continuity")
        return quality

    def _weights_for_role(self, role: TrackRole) -> ScoringWeights:
        if role is TrackRole.DISCOVERY_SPOTLIGHT:
            return self._DISCOVERY_SPOTLIGHT_WEIGHTS
        return self.weights

    @staticmethod
    def _component(quality: float, weight: float) -> float:
        return TrackScorer._rounded(quality * weight * 100.0)

    @staticmethod
    def _clamp(value: float) -> float:
        return min(1.0, max(0.0, value))

    @staticmethod
    def _rounded(value: float) -> float:
        return round(value, 4)

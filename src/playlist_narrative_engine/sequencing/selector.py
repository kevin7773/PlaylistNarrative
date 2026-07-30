from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from playlist_narrative_engine.journey.schemas import (
    JourneyContext,
    JourneyPhase,
)
from playlist_narrative_engine.sequencing.scorer import TrackScorer
from playlist_narrative_engine.sequencing.schemas import (
    ScoreBreakdown,
    TrackCandidate,
    TrackRole,
)


@dataclass(frozen=True)
class RankedCandidate:
    candidate: TrackCandidate
    score: float
    score_breakdown: ScoreBreakdown
    rank: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class DiscoveryBudgetPolicy:
    """Transparent, phase-relative modifier for next-track ranking."""

    modifier_scale: float = 5.0

    def __post_init__(self) -> None:
        if self.modifier_scale < 0:
            raise ValueError("discovery modifier scale cannot be negative")

    def modifier(
        self,
        candidate: TrackCandidate,
        target_discovery_ratio: float,
        phase_discovery_ratio: float,
    ) -> float:
        ratio_delta = target_discovery_ratio - phase_discovery_ratio
        novelty_orientation = 1.0 - 2.0 * candidate.familiarity
        return round(
            self.modifier_scale * ratio_delta * novelty_orientation,
            4,
        )


class CandidateSelector:
    """Rank the best immediate next-track options without playlist look-ahead."""

    def __init__(
        self,
        scorer: TrackScorer | None = None,
        discovery_policy: DiscoveryBudgetPolicy | None = None,
    ) -> None:
        self.scorer = scorer or TrackScorer()
        self.discovery_policy = discovery_policy or DiscoveryBudgetPolicy()

    def select(
        self,
        *,
        context: JourneyContext,
        previous_track: TrackCandidate | None,
        phase: JourneyPhase,
        role: TrackRole,
        target_discovery_ratio: float,
        candidates: Iterable[TrackCandidate],
        top_n: int = 10,
    ) -> tuple[RankedCandidate, ...]:
        if not 0.0 <= target_discovery_ratio <= 1.0:
            raise ValueError("target discovery ratio must be between 0.0 and 1.0")
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
            raise ValueError("top_n must be a positive integer")

        phase_discovery_ratio = phase.familiarity.discovery_percent / 100.0
        scored: list[
            tuple[TrackCandidate, float, ScoreBreakdown, tuple[str, ...]]
        ] = []
        for candidate in candidates:
            breakdown = self.scorer.score(
                candidate,
                phase,
                context=context,
                role=role,
                previous_track=previous_track,
            )
            modifier = self.discovery_policy.modifier(
                candidate,
                target_discovery_ratio,
                phase_discovery_ratio,
            )
            score = round(breakdown.total_score + modifier, 4)
            reasons = breakdown.reasons + self._modifier_reasons(
                candidate,
                modifier,
            )
            scored.append((candidate, score, breakdown, reasons))

        scored.sort(
            key=lambda item: (
                -item[1],
                item[0].track_id.casefold(),
                item[0].track_id,
                item[0].artist_name.casefold(),
                item[0].artist_name,
                item[0].title.casefold(),
                item[0].title,
                item[0].model_dump_json(),
            )
        )
        return tuple(
            RankedCandidate(
                candidate=candidate,
                score=score,
                score_breakdown=breakdown,
                rank=index,
                reasons=reasons,
            )
            for index, (candidate, score, breakdown, reasons) in enumerate(
                scored[:top_n],
                start=1,
            )
        )

    @staticmethod
    def _modifier_reasons(
        candidate: TrackCandidate,
        modifier: float,
    ) -> tuple[str, ...]:
        if modifier == 0:
            return ()
        direction = "favors" if modifier > 0 else "reduces"
        quality = (
            "novelty" if candidate.familiarity < 0.5 else "familiarity"
        )
        return (
            f"Discovery budget {direction} {quality} ({modifier:+.4f})",
        )

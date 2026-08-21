from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from playlist_narrative_engine.journey.schemas import JourneyContext, JourneyPhase
from playlist_narrative_engine.sequencing.scorer import TrackScorer
from playlist_narrative_engine.sequencing.schemas import (
    ScoreBreakdown,
    TrackCandidate,
    TrackRole,
)

if TYPE_CHECKING:
    from playlist_narrative_engine.candidate_formation.formation_schemas import (
        CandidateConstraintEligibility,
        CandidateIdentitySnapshot,
    )
    from playlist_narrative_engine.candidate_formation.integration_schemas import (
        CandidateFormationTrace,
        FormedCandidatePoolView,
    )


@dataclass(frozen=True)
class RankedCandidate:
    candidate: TrackCandidate
    score: float
    score_breakdown: ScoreBreakdown
    rank: int
    reasons: tuple[str, ...]
    identity: CandidateIdentitySnapshot | None = None
    constraint_eligibility: tuple[CandidateConstraintEligibility, ...] = ()


@dataclass(frozen=True)
class RankingResultEnvelope:
    formation_trace: CandidateFormationTrace
    remaining_track_ids: tuple[str, ...]
    context: JourneyContext
    previous_track_id: str | None
    phase: JourneyPhase
    role: TrackRole
    target_discovery_ratio: float
    top_n: int
    ranked_candidates: tuple[RankedCandidate, ...]


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
        return round(self.modifier_scale * ratio_delta * novelty_orientation, 4)


class CandidateSelector:
    """Rank authenticated formed candidates for one immediate decision."""

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
        formed_pool: FormedCandidatePoolView,
        remaining_track_ids: tuple[str, ...],
        top_n: int = 10,
    ) -> RankingResultEnvelope:
        if not 0.0 <= target_discovery_ratio <= 1.0:
            raise ValueError("target discovery ratio must be between 0.0 and 1.0")
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n <= 0:
            raise ValueError("top_n must be a positive integer")

        entries = formed_pool.resolve_remaining(remaining_track_ids)
        resolved_candidates = tuple(entry.candidate for entry in entries)
        entries_by_id = {entry.candidate.track_id: entry for entry in entries}
        canonical_ids = tuple(
            candidate.track_id for candidate in resolved_candidates
        )
        if previous_track is not None:
            matching = tuple(
                candidate
                for candidate in formed_pool.candidates
                if candidate.track_id == previous_track.track_id
            )
            if len(matching) != 1 or matching[0] != previous_track:
                raise ValueError(
                    "previous track must exactly equal its formed-pool candidate"
                )

        phase_discovery_ratio = phase.familiarity.discovery_percent / 100.0
        scored: list[
            tuple[TrackCandidate, float, ScoreBreakdown, tuple[str, ...]]
        ] = []
        for candidate in resolved_candidates:
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
            reasons = breakdown.reasons + self._modifier_reasons(candidate, modifier)
            scored.append((candidate, score, breakdown, reasons))

        scored.sort(
            key=lambda item: (
                -item[1],
                item[0].track_id.encode("utf-8"),
                item[0].artist_name.encode("utf-8"),
                item[0].title.encode("utf-8"),
                item[0].model_dump_json(),
            )
        )
        ranked = tuple(
            RankedCandidate(
                candidate=candidate,
                score=score,
                score_breakdown=breakdown,
                rank=index,
                reasons=reasons,
                identity=entries_by_id[candidate.track_id].identity,
                constraint_eligibility=entries_by_id[candidate.track_id].constraint_eligibility,
            )
            for index, (candidate, score, breakdown, reasons) in enumerate(
                scored[:top_n], start=1
            )
        )
        return RankingResultEnvelope(
            formation_trace=formed_pool.trace,
            remaining_track_ids=canonical_ids,
            context=context,
            previous_track_id=(previous_track.track_id if previous_track else None),
            phase=phase,
            role=role,
            target_discovery_ratio=target_discovery_ratio,
            top_n=top_n,
            ranked_candidates=ranked,
        )

    @staticmethod
    def _modifier_reasons(
        candidate: TrackCandidate,
        modifier: float,
    ) -> tuple[str, ...]:
        if modifier == 0:
            return ()
        direction = "favors" if modifier > 0 else "reduces"
        quality = "novelty" if candidate.familiarity < 0.5 else "familiarity"
        return (f"Discovery budget {direction} {quality} ({modifier:+.4f})",)


def serialize_ranking_result(envelope: RankingResultEnvelope) -> bytes:
    """Return deterministic compact JSON for one ranking-result envelope."""

    return json.dumps(
        asdict(envelope),
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    ).encode("utf-8")


def _json_default(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"unsupported ranking serialization value: {type(value)!r}")

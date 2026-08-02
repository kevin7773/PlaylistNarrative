"""Explainable candidate scoring for future playlist sequencing."""

from playlist_narrative_engine.sequencing.constructor import (
    CandidateRejection,
    ConstructionIssue,
    ConstructionIssueSeverity,
    ConstructionPolicy,
    ConstructionResult,
    ConstructionState,
    ConstructionStatus,
    ConstructionSummary,
    PlacedTrack,
    SequentialPlaylistConstructor,
)
from playlist_narrative_engine.sequencing.scorer import ScoringWeights, TrackScorer
from playlist_narrative_engine.sequencing.selector import (
    CandidateSelector,
    DiscoveryBudgetPolicy,
    RankedCandidate,
    RankingResultEnvelope,
    serialize_ranking_result,
)
from playlist_narrative_engine.sequencing.schemas import (
    ScoreBreakdown,
    TrackCandidate,
    TrackRole,
    TransitionProfile,
)

__all__ = [
    "CandidateRejection",
    "CandidateSelector",
    "ConstructionIssue",
    "ConstructionIssueSeverity",
    "ConstructionPolicy",
    "ConstructionResult",
    "ConstructionState",
    "ConstructionStatus",
    "ConstructionSummary",
    "DiscoveryBudgetPolicy",
    "PlacedTrack",
    "RankedCandidate",
    "RankingResultEnvelope",
    "serialize_ranking_result",
    "ScoreBreakdown",
    "ScoringWeights",
    "TrackCandidate",
    "TrackRole",
    "TrackScorer",
    "TransitionProfile",
    "SequentialPlaylistConstructor",
]

"""Explainable candidate scoring for future playlist sequencing."""

from playlist_narrative_engine.sequencing.constructor import (
    CandidateRejection,
    ConstructionIssue,
    ConstructionIssueSeverity,
    ConstructionInputBinding,
    ConstructionPolicy,
    ConstructionResult,
    ConstructionState,
    ConstructionStatus,
    ConstructionSummary,
    PlacedTrack,
    SequentialPlaylistConstructor,
)
from playlist_narrative_engine.sequencing.canonical import (
    construction_policy_sha256,
    construction_result_matches_inputs,
    construction_result_matches_evaluation_inputs,
    construction_result_sha256,
    serialize_construction_policy,
    serialize_construction_result,
    verify_construction_result_digest,
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
    "ConstructionInputBinding",
    "ConstructionPolicy",
    "ConstructionResult",
    "ConstructionState",
    "ConstructionStatus",
    "ConstructionSummary",
    "construction_policy_sha256",
    "construction_result_matches_inputs",
    "construction_result_matches_evaluation_inputs",
    "construction_result_sha256",
    "DiscoveryBudgetPolicy",
    "PlacedTrack",
    "RankedCandidate",
    "RankingResultEnvelope",
    "serialize_ranking_result",
    "serialize_construction_policy",
    "serialize_construction_result",
    "ScoreBreakdown",
    "ScoringWeights",
    "TrackCandidate",
    "TrackRole",
    "TrackScorer",
    "TransitionProfile",
    "SequentialPlaylistConstructor",
    "verify_construction_result_digest",
]

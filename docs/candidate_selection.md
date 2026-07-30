# Candidate Selection

## Purpose

Candidate selection answers one immediate question: “What are the best next
tracks?” It ranks supplied candidates for the current journey phase and role. It
does not choose subsequent tracks or claim that the first result belongs in a
complete playlist.

## Architecture

`CandidateSelector` is a thin deterministic layer over `TrackScorer`.
`TrackScorer` remains responsible for listener preference, context and phase fit,
transition quality, role behavior, discovery quality, and penalties. The
selector preserves that complete `ScoreBreakdown`, applies one visible
discovery-budget modifier, and sorts the results.

Each `RankedCandidate` contains:

- the original `TrackCandidate`;
- the adjusted selection score;
- the unchanged scorer breakdown;
- a one-based rank;
- scorer explanations followed by any discovery-budget explanation.

## Selection pipeline

1. Validate the requested discovery ratio and result limit.
2. Score every candidate once with the existing `TrackScorer`.
3. Compare the target discovery ratio with the current phase's planned ratio.
4. Apply a phase-relative modifier capped by the centralized five-point scale:
   targets above the phase plan slightly favor novelty, while targets below it
   slightly favor familiarity.
5. Sort by adjusted score descending.
6. Resolve equal scores by stable track identity, independent of input order.
7. Return the first `top_n` results, defaulting to ten.

The phase's planned discovery ratio is neutral. At that target, selection scores
exactly equal the scorer totals and no budget explanation is added.

## Relationship to TrackScorer

The selector does not alter scoring weights or rebuild component scores. The
budget modifier is stored only in the adjusted `score` and stated in `reasons`;
`score_breakdown.total_score` remains the direct `TrackScorer` result. This
keeps the source of every ranking difference auditable.

## Why this is not playlist generation

Selection has no history, persistence, look-ahead, branching search, or global
optimization. It does not reserve duration, enforce playlist-wide artist
limits, or simulate later transitions. Calling it repeatedly without additional
state simply answers the same next-track question again. Playlist construction
and optimization remain deliberately out of scope.

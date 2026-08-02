# Candidate Selection

## Purpose

Candidate selection answers one immediate question: “What are the best next
tracks?” In production it ranks candidates authenticated by a
`FormedCandidatePoolView` for the current journey phase and role. It does not
choose subsequent tracks or claim that the first result belongs in a complete
playlist.

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
- a one-based rank; and
- scorer explanations followed by any discovery-budget explanation.

The ordered candidates are returned inside an immutable ranking-result envelope.
Formation trace is carried once on that envelope rather than repeated on every
`RankedCandidate`. This prevents per-entry trace disagreement and avoids copying
identical parent identity into every ephemeral ranked result. A ranked candidate
has authenticated production meaning only within its envelope.

## Authenticated production input

The accepted CF-3 contract intentionally replaces raw production candidate
iterables. `CandidateSelector.select` accepts exactly one authenticated
`FormedCandidatePoolView` plus `remaining_track_ids`. No production overload,
union, compatibility adapter, or optional argument may accept arbitrary
`TrackCandidate` tuples alongside or instead of the view.

`remaining_track_ids` is a membership filter, not an ordering instruction. The
selector rejects duplicates and IDs absent from the view, then resolves valid
IDs against canonical formed-pool order. Permuting the same IDs therefore cannot
change the result. No identity is trimmed, case-folded, Unicode-normalized,
aliased, or fuzzily repaired.

## Selection pipeline

1. Validate the requested discovery ratio and result limit.
2. Validate remaining IDs and resolve them in canonical formed-pool order.
3. Score every resolved candidate once with the existing `TrackScorer`.
4. Compare the target discovery ratio with the current phase's planned ratio.
5. Apply a phase-relative modifier capped by the centralized five-point scale:
   targets above the phase plan slightly favor novelty, while targets below it
   slightly favor familiarity.
6. Sort by adjusted score descending.
7. Resolve equal scores by stable track identity, independent of input order.
8. Return the first `top_n` results in the traced envelope, defaulting to ten.

The phase's planned discovery ratio is neutral. At that target, selection scores
exactly equal the scorer totals and no budget explanation is added.

## Relationship to TrackScorer

The selector does not alter scoring weights or rebuild component scores. The
budget modifier is stored only in the adjusted `score` and stated in `reasons`;
`score_breakdown.total_score` remains the direct `TrackScorer` result. This
keeps the source of every ranking difference auditable.

`TrackScorer` remains a lower-level pure primitive and may accept synthetic
`TrackCandidate` values in isolated unit tests. That is not a production entry
point and does not weaken the authenticated selector boundary.

## Why this is not playlist generation

Selection has no history, persistence, look-ahead, branching search, or global
optimization. It does not reserve duration, enforce playlist-wide artist
limits, or simulate later transitions. Calling it repeatedly without additional
state simply answers the same next-track question again. Playlist construction
and optimization remain deliberately out of scope.

The authenticated input and trace rules are normative in the
[Candidate Formation Integration Contract](candidate_formation_integration.md).

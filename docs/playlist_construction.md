# Phase 4B: Deterministic Sequential Construction

Phase 4B is the smallest executable realization of the accepted
[Phase 4A construction ADR](playlist_construction_contract.md). It constructs a
track-count-targeted sequence one placement at a time. It does not optimize or
repair a playlist.

## Public objects

- `ConstructionState` is the only mutable domain object. It records placements,
  the previous track, elapsed duration, current phase, used tracks, artist
  counts, discovery consumption, and hard-constraint rejections.
- `ConstructionPolicy` is immutable and holds the per-artist maximum and the
  single controlled-discovery familiarity threshold.
- `SequentialPlaylistConstructor` orchestrates the placement loop.
- `PlacedTrack` preserves the selector result, assigned phase and role,
  explanations, and any higher-ranked hard-constraint rejections.
- `ConstructionResult` contains the immutable ordered snapshot, summary, and
  unmet issues.

## Placement loop

For every placement, the constructor:

1. maps the current track slot to a journey phase using the phases' planned
   duration proportions;
2. chooses an explicit role: opening anchor, phase transition, journey, or
   closing track;
3. derives the remaining discovery need from the journey target and mutable
   state;
4. requests a fresh ranking of every remaining candidate;
5. walks that ephemeral ranking until it finds the first candidate satisfying
   the artist repetition limit;
6. records rejected higher-ranked candidates;
7. places one track, removes it from the local remaining set, and updates state.

The next iteration reranks from the changed previous track, phase, discovery
balance, and candidate set. No `RankedCandidate` survives the iteration that
created it.

## Deterministic policies

- Requested track count means the final sequence length, including any initial
  placements in the supplied state.
- Pre-populated state must be internally consistent: placement positions, used
  IDs, previous track, phase, elapsed duration, artist counts, and discovery
  count must describe the same sequence.
- Candidate-pool iteration order does not affect the result.
- Remaining equal-score ties use `CandidateSelector`'s stable identity rules.
- Phase assignment uses track-slot midpoint against cumulative planned phase
  duration.
- The journey's discovery percentage becomes a whole-track target using
  deterministic half-up rounding. Each ranking receives the ratio still needed
  across the remaining slots.
- Artist identity is compared case-insensitively.

## Stopping and failure

Construction stops when it reaches the requested count, exhausts the pool, or
cannot place any remaining candidate without violating a hard constraint. The
result is `complete`, `partial`, or `infeasible`; hard failures are returned as
structured issues and are never silently relaxed.

## Deliberate limits

Phase 4B has no duration target, backtracking, look-ahead, global optimization,
persistence, randomness, repair pass, new scoring dimensions, or feedback
learning. `TrackScorer` and `CandidateSelector` are reused unchanged.

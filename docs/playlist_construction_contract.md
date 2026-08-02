# ADR: Phase 4A Playlist Construction Contract

- **Status:** Accepted
- **Decision scope:** Playlist construction architecture
- **Applies to:** Phase 4B and later construction or search strategies
- **Supersedes:** Nothing

This Architectural Decision Record is normative. Future playlist-construction
implementations must preserve its object lifetimes, mutability boundary,
ranking-lifetime invariants, constraint semantics, determinism, and
explainability requirements unless a later accepted ADR explicitly supersedes
them.

## Objective

Given an exactly corresponding Journey Plan artifact and authenticated formed
candidate pool, construct an ordered, explainable playlist that satisfies global
constraints over time.

> The constructor may sacrifice the highest-ranked immediate candidate when
> necessary to preserve the quality of the full sequence.

This contract defines the boundary. It does not implement construction.

## Architectural boundary

`TrackScorer` evaluates one candidate in context. `CandidateSelector` answers
“What are the best next tracks right now?” The constructor owns the
state that changes after each placement: elapsed time, current phase, previous
track, used track IDs, artist counts, discovery usage, roles, and soft-constraint
progress.

Rankings are ephemeral. A transition score is relative to the current previous
track, so one initial ranked list cannot govern the full playlist. At each
decision point the constructor supplies the current state and stable candidate
pool to `CandidateSelector`, then evaluates that fresh ranking against global
constraints.

### Ranking-lifetime invariants

The construction boundary has two non-negotiable invariants:

1. **The stable input is the candidate pool, not a precomputed ranking.**
   `FormedCandidatePoolView` is the stable authenticated input.
   `RankedCandidate` is an explainable decision-time result. It must not be
   stored as durable construction input or consumed as a standing queue.
2. **Every placement decision is based on a ranking produced from the current
   construction state.** The ranking request reflects the current previous
   track, phase position, discovery balance, required role, and remaining
   hard-valid candidate pool.

The conceptual loop is:

```text
current construction state
    ↓
request a fresh candidate ranking
    ↓
apply construction constraints
    ↓
place one track
    ↓
update construction state
    ↓
repeat
```

The constructor must never rank once and then consume that list sequentially.
After one placement, transition scoring and global eligibility may have changed,
so the earlier ranking has expired.

**Construction state is the only mutable object in the playlist-construction
process; journey definitions, candidate metadata, and scoring logic remain
immutable.**

The constructor may reject the first-ranked candidate. It must record why and
may choose the next valid candidate. Candidate scores remain selector outputs;
the constructor must not secretly rescore or add hidden weights.

## Inputs

The construction request must contain:

- `journey_plan`: a validated `JourneyPlanArtifact` whose phases define duration,
  familiarity allocation, and energy contour and whose journey, objective, and
  accepted-safety identities exactly correspond to Candidate Formation;
- `formed_pool`: the sole authenticated `FormedCandidatePoolView`, derived from
  a validated `CandidateFormationArtifact` and containing every and only formed
  entry;
- `target`: exactly one of:
  - a duration target with inclusive minimum and maximum seconds; or
  - a positive target track count;
- `target_discovery_ratio`: a value from `0.0` through `1.0`;
- `repetition_limits`: at minimum, a positive maximum number of tracks per
  artist;
- deterministic construction policy values such as selector result limit and
  the centralized familiarity threshold used to classify discovery tracks.

The constructor accepts no raw-candidate production input and no transitional
overload. The view's canonical formed order is stable. Remaining track IDs are
resolved against that order, so their supplied order must not affect the result.
`track_id` is the exact identity used for duplicate prevention and deterministic
tie resolution.

For this contract, a discovery track is a candidate whose familiarity is at or
below the scorer's established controlled-discovery threshold of `0.35`.
Phase 4B must define that threshold once in policy rather than repeat the number
throughout construction logic.

### Target modes

Duration mode is complete only when total duration lies inside the inclusive
bounds. The target duration guides soft choices inside that interval; it does
not authorize exceeding the hard maximum.

Track-count mode is complete only at the requested count. Duration is reported
but is not constrained unless a future request explicitly combines the modes.

## Outputs

The construction result must contain:

### Ordered playlist

Each placed-track record includes:

- one-based position;
- original `TrackCandidate`;
- assigned journey phase and `TrackRole`;
- selector rank and adjusted selection score at placement time;
- unchanged `ScoreBreakdown`;
- placement rationale;
- any higher-ranked candidates rejected at that decision and their rejection
  reasons.

The construction result carries the formation trace once, including the exact
parent canonical-artifact digest, request, objective, journey, formation-policy,
and preference-rule identities. Ranking trace is likewise carried once on each
ranking-result envelope rather than repeated on individual ranked candidates.

Placement rationale must distinguish:

- positive scorer and selector reasons;
- role or phase need;
- global-state reasons, such as preserving artist capacity or discovery balance;
- a soft compromise accepted to keep construction feasible.

### Construction summary

The summary includes:

- completion status: `complete`, `partial`, or `infeasible`;
- total duration and track count;
- target mode and achieved target;
- achieved discovery count and ratio;
- per-artist counts;
- per-phase track counts and durations;
- role counts;
- hard-constraint rejection counts by reason;
- soft compromises by category.

### Unmet constraints and compromises

Every issue includes:

- stable machine-readable code;
- human-readable explanation;
- severity: `hard_unmet` or `soft_compromise`;
- affected phase or position when applicable;
- observed value and requested bound when numeric.

A hard constraint is never silently relaxed. If the pool cannot produce a
complete result, the constructor returns a deterministic partial or infeasible
result with the unmet hard constraints. A soft constraint may be compromised,
but the output must say where and why.

## Construction state

Phase 4B may use an in-memory state object containing only:

- placed tracks;
- elapsed duration;
- current phase and phase allocation progress;
- previous track;
- used track IDs;
- artist occurrence counts;
- discovery count;
- assigned role counts;
- accumulated rejections and compromises.

This state exists for one construction call. It is not persisted and contains no
learning or cross-playlist history.

A resumed state must carry the same formation trace and journey identity as the
current request. Every placed candidate and previous track must exist in the
formed view and equal its candidate in every typed field. Track-ID equality
alone is insufficient. Used IDs must correspond exactly to placed tracks.
Withheld, unknown, duplicate, normalized, or caller-created candidates invalidate
the state; construction must not repair them.

## Hard constraints

Every returned playlist track must satisfy all applicable hard constraints:

1. **Candidate validity**
   - The candidate belongs to the authenticated formed view and exactly equals
     its provenance-bearing formed entry.
   - Eligibility was established by Candidate Formation and is not reevaluated
     or converted into a construction penalty.
   - Candidate identity is non-empty and unambiguous.
2. **No duplicate tracks**
   - A `track_id` may appear at most once.
3. **Artist repetition limit**
   - Placements may not exceed the configured per-artist maximum.
4. **Total duration or count**
   - A completed duration-mode result falls within the inclusive duration
     bounds.
   - A completed track-count result has exactly the requested number of tracks.
5. **Valid placement**
   - Every placement references a journey phase and a supported `TrackRole`.
   - Every stored score and rationale comes from the decision that placed it.

If no candidate can satisfy the next placement without violating a hard
constraint, construction stops rather than inserting an invalid track.

## Soft constraints

Soft constraints guide choices among hard-valid candidates:

1. **Phase alignment**
   - Tracks support the purpose, energy, and familiarity allocation of their
     assigned phase.
2. **Transition quality**
   - Adjacent tracks maintain coherent energy, groove, emotion, and narrative,
     allowing explained intentional contrast.
3. **Anchor spacing**
   - Opening, phase-transition, reset, epic-event, and closing roles occur at
     purposeful positions rather than clustering accidentally.
4. **Discovery distribution**
   - Discovery approaches the target ratio and is spread through appropriate
     phases instead of being accumulated at the end.
5. **Energy contour**
   - The sequence follows phase energy direction over time, not merely the
     average energy target of each isolated track.
6. **Attention continuity**
   - Lyrical distraction, abrupt intensity, and other attention demands remain
     appropriate for the journey and do not cluster into a disruptive run.

Soft constraints require observable measures in Phase 4B. They must not be
implemented as undocumented adjustments to `TrackScorer`.

## Determinism and auditability

For identical validated inputs and policy:

- output order is identical;
- placement ranks and scores are identical;
- rejection order and reasons are identical;
- summaries and issue ordering are identical.

Remaining-ID input order must not change the result. Stable identifiers break any
remaining ties. No randomness, current time, external state, or provider calls
may influence construction.

## Phase 4B baseline contract

The future deterministic greedy constructor will:

1. walk through planned phases;
2. determine the next required role;
3. ask `CandidateSelector` for a current ranking;
4. reject candidates that violate hard constraints;
5. choose the highest-ranked hard-valid candidate, subject to an explicit
   global-feasibility guard;
6. update construction state;
7. repeat until the target is met or no valid placement remains;
8. return the ordered playlist, rationales, summary, and issues.

The global-feasibility guard is the narrow mechanism that permits passing over
the immediate winner to preserve remaining duration, artist capacity, phase
coverage, role needs, or discovery distribution. Its rules must be explicit and
tested in Phase 4B. It is not permission to introduce beam search, backtracking,
or hidden optimization.

## Explicit non-goals

Phase 4 construction does not include:

- persistence or cross-playlist state;
- feedback learning;
- streaming-provider integration;
- global catalog search;
- external metadata or audio analysis;
- beam search, graph search, dynamic programming, or backtracking in the greedy
  baseline;
- automatic changes to Taste Model ratings, `TrackScorer`, or
  `CandidateSelector`.
- access to withheld Candidate Formation entries;
- source-evidence rejoins, preference remapping, or identity normalization; or
- raw `TrackCandidate` production pools or compatibility overloads that accept
  them.

The CF-3 integration decisions supplement this ADR. See the
[Candidate Formation Integration Contract](candidate_formation_integration.md).

## Phase 4A acceptance criteria

Phase 4A is complete when this contract is approved. No constructor code,
construction schemas, or Phase 4B tests are part of this deliverable.

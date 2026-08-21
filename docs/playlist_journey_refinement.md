# Phase 6: Deterministic Playlist Journey Refinement

- **Status:** Proposed design note
- **Scope:** Bounded revision driven by deterministic evaluation evidence
- **Depends on:** Accepted Phase 4A construction ADR, Phase 4B construction,
  and Phase 5 evaluation schema `1.0`

## Purpose

Define how a complete or partial playlist journey may be revised using evidence
from deterministic journey evaluation.

Refinement consumes construction results and evaluation reports without changing
scoring, candidate selection, sequential construction, or evaluation behavior.
It may apply a bounded change only when current evidence identifies a supported
opportunity.

> Refinement may improve measured objective attainment or correct documented
> issues. It must not claim to improve playlist quality.

No change is preferable to an unjustified change.

Refinement inherits Phase 5's multidimensional-quality principle. Narrative
continuity, objective attainment, discovery value, familiarity, and attention
demand remain independent evidence dimensions. A targeted improvement in one
dimension does not authorize a general claim that playlist quality improved,
and refinement must not collapse those dimensions into an acceptance score.

### Inherited normative terminology

Phase 6 uses the Phase 5 definitions without reinterpretation:

- **`measured`** requires supported current evidence, an applicable sample, and
  a numeric observed value with its evidence source and applicable denominator.
- **`not_applicable`** means a supported metric has no applicable sample or
  context in this artifact. It is not failure, zero, or an evidence gap.
- **`unavailable`** means the current model or artifact cannot support the
  measurement. It cannot motivate refinement, be replaced with a proxy, or be
  treated as `not_applicable`.
- **improvement** is strictly local: one named measured objective metric becomes
  strictly better, or one exact documented issue disappears, while stated
  non-regression rules hold.
- **quality** remains a multidimensional descriptive concept. It is never a
  scalar, composite score, acceptance criterion, or synonym for improvement.

Accordingly, Phase 6 may report a targeted improvement or issue correction. It
must not report that playlist quality improved.

## Core contract

Given:

- the exact playlist objective;
- the stable candidate pool;
- an immutable construction result;
- its corresponding immutable evaluation report;

return either:

- a new deterministic construction result, its new evaluation report, and an
  explainable change record; or
- an explicit unchanged outcome explaining why no supported refinement is
  available.

All inputs remain unchanged. A refined result is a new artifact, never a
mutation of the original result or evaluation report.

## Layer boundary

Refinement is a consumer of evaluation, not part of evaluation.

The existing layers remain authoritative:

- `TrackScorer` defines stored candidate evidence;
- `CandidateSelector` ranks an immediate decision from current state;
- `SequentialPlaylistConstructor` owns placement and hard-constraint behavior;
- `PlaylistJourneyEvaluator` observes results without revising them;
- refinement decides whether a documented, bounded reconstruction attempt is
  permitted and whether its measured outcome is acceptable.

Refinement must not:

- alter scorer weights or component values;
- rescore retained tracks;
- reconstruct expired rankings;
- add construction rules inside the selector;
- add repair behavior inside the evaluator;
- reinterpret unavailable metrics as evidence.

## Input contract

The proposed immutable refinement request contains:

- `journey_plan`: the exact journey objective;
- `construction_policy`: the exact policy used to construct and evaluate;
- `candidate_formation`: the exact authenticated `CandidateFormationArtifact`;
- `formed_pool`: its exact `FormedCandidatePoolView` projection; raw
  `TrackCandidate` collections are not an authority boundary;
- `construction_result`: the source `ConstructionResult`;
- `evaluation_report`: the source schema-versioned `EvaluationReport`;
- a frozen refinement policy defining permitted operation types and maximum
  changed positions.

Candidate-pool order must not affect the outcome. Track IDs must be unique.
Every placed track must resolve to an identical `ELIGIBLE` formed entry under
the authenticated parent artifact; the refiner must not substitute metadata by
matching only an ID or accept `UNKNOWN`/`INELIGIBLE` entries.

### Correspondence validation

Before opportunity detection, the refiner reruns the pure evaluator over the
supplied construction result, journey plan, and policy. The canonical report
must equal the supplied evaluation report and serialize to identical schema-1.0
JSON bytes.

A stale, mismatched, modified, or differently versioned evaluation report makes
the request invalid. The refiner returns an explicit no-change or invalid-input
outcome; it does not guess which artifact is authoritative.

## Output contract

The proposed immutable refinement outcome contains:

### Status

- `refined`: one supported change was accepted;
- `unchanged`: no change was necessary or a permitted attempt did not improve
  its targeted measured outcome;
- `unsupported`: an issue exists, but current evidence or operations cannot
  support a bounded repair;
- `invalid_input`: objective, pool, result, policy, or report correspondence
  failed validation.

### Artifacts

- original construction result and evaluation report references or stable
  identities;
- resulting construction result;
- resulting evaluation report;
- ordered change records;
- ordered refinement issues and no-change reasons;
- refinement schema version.

For non-refined outcomes, resulting artifacts equal the original artifacts.

### Change record

Every accepted change records:

- stable operation code;
- affected original and resulting positions;
- removed and added track IDs;
- preserved prefix length;
- motivating evaluation issue codes and metric codes;
- before and after metric observations, targets, denominators, and
  applicability;
- construction rejections encountered during the attempt;
- concise deterministic rationale;
- explicit statement of which positions were not changed.

The record says “target metric improved” or “documented issue resolved,” never
“playlist quality improved.”

## Evidence rules

A refinement opportunity requires all of:

1. a documented construction or evaluation issue, or a measured objective
   metric below its explicit target;
2. a supported operation mapped to that evidence code;
3. sufficient current metadata to evaluate the operation;
4. at least one eligible alternative candidate when replacement or extension is
   required;
5. a deterministic after-evaluation proving the targeted measured outcome
   improved or the documented issue disappeared;
6. no new hard-constraint failure and no regression in completion fidelity.

Unsupported and not-applicable metrics cannot motivate refinement. Descriptive
series do not become objectives merely because they are numeric.

## Initial operation boundary

Phase 6 should begin with the smallest operations that today’s contracts can
support without hidden downstream claims.

### Supported: resume a partial tail

When construction ended partial because the pool was exhausted or candidates
violated active hard constraints, refinement may:

1. reconstruct a fresh `ConstructionState` from the immutable placed prefix;
2. add newly available eligible candidates from the stable refinement pool;
3. call `SequentialPlaylistConstructor` toward the original requested count;
4. reevaluate the new result;
5. accept only if completion fidelity increases and hard-constraint compliance
   does not regress.

Existing placements are preserved byte-for-byte. The constructor ranks only new
placement decisions from the current tail state.

### Conditionally supported: replace the final placement

A final track may be replaced when:

- a position-specific documented issue names the final position;
- the relevant target is measured and supported;
- an eligible alternative exists;
- there is no following retained track whose incoming transition would become
  stale;
- reconstruction starts from the unchanged prefix immediately before the final
  track;
- after-evaluation resolves the motivating issue or improves its mapped metric.

The removed final track is excluded from that attempt. The retained prefix is
not rescored.

This operation can support a bounded discovery repair or correction of a
final-position hard inconsistency. It is not general replacement.

### Unsupported initially: replace an interior placement

Replacing position `n` changes the transition into `n + 1`. The current
`CandidateSelector` can rank a new track against position `n - 1`, but existing
artifacts do not prove the effect on the following retained track without
rescoring or rebuilding downstream placements.

Interior replacement therefore returns `unsupported` in the initial phase.
It must not preserve stale downstream scores or silently become suffix
backtracking.

### Unsupported initially: repair by metric proxy

No operation may target:

- album repetition;
- vocal salience;
- emotional or narrative continuity;
- precise phase energy-contour fidelity;
- anchor-spacing fidelity;
- any other schema-1.0 metric marked `unavailable` or `not_applicable`.

## Opportunity priority

Equivalent inputs must choose the same opportunity. The proposed initial
priority is:

1. invalid correspondence or hard input inconsistency: return `invalid_input`;
2. no issues and all supported objective metrics satisfied: return `unchanged`;
3. incomplete track-count objective with a resumable tail: attempt extension;
4. documented final-position hard inconsistency: attempt final replacement;
5. under-target discovery with a supported final replacement: attempt final
   replacement;
6. all other issues: return `unsupported`.

Only one bounded refinement attempt occurs per call. Iterative refinement,
multi-operation planning, and best-of-many comparison remain out of scope.

## Acceptance and non-regression

There is no composite objective function.

An attempted result is accepted only against named metrics and issues:

- completion repair requires a strictly higher `completion_fidelity`;
- discovery repair requires a smaller absolute
  `discovery_ratio_deviation`, with both metrics measured;
- documented-issue repair requires the exact issue code to disappear;
- duplicate or artist-limit repair requires the corresponding compliance metric
  to change from false to true.

Every accepted result must also:

- retain or improve completion fidelity;
- keep duplicate and artist-repetition compliance true;
- introduce no new construction hard issue;
- preserve every position outside the declared change boundary;
- produce a valid deterministic schema-1.0 evaluation report.

Other measured components are reported before and after but are not silently
combined into a veto or quality score. If a future policy wants additional
non-regression gates, it must name them explicitly.

## No-change semantics

An unchanged outcome is first-class and explainable. Reasons include:

- no documented issue or missed supported objective;
- target evidence is unavailable or not applicable;
- issue affects an unsupported interior position;
- no eligible alternative remains;
- reconstruction reproduced the same result;
- targeted metric did not improve;
- a hard-constraint or completion regression would result;
- permitted change-bound size would be exceeded.

The original result and report are returned unchanged. No candidate scores or
evaluation artifacts are rewritten.

## Determinism and immutability

For equivalent inputs:

- opportunity choice is identical;
- attempted candidate ordering is identical;
- accepted or unchanged status is identical;
- change records and reasons are identically ordered;
- serialized output bytes are identical.

The refiner has no mutable domain state. It does not mutate the journey plan,
policy, candidate pool, construction result, or evaluation report. Temporary
construction state exists only inside a bounded attempt and is discarded after
producing immutable artifacts.

Tests must cover:

- direct and serialized determinism;
- candidate-pool-order independence;
- input and refiner immutability;
- report-correspondence rejection;
- no-change when no supported issue exists;
- partial-tail completion;
- accepted and rejected final replacements;
- unsupported interior issues;
- unavailable metrics never motivating a change;
- before-and-after evidence completeness;
- scorer, selector, constructor, and evaluator isolation.

## Explicit non-goals

Initial Phase 6 excludes:

- global playlist optimization;
- beam search, graph search, dynamic programming, or stochastic search;
- iterative multi-change improvement;
- unbounded backtracking or suffix reconstruction;
- reinforcement learning or listener-behavior modeling;
- rescoring retained tracks;
- inferred emotional, lyrical, or audio-semantic judgments;
- a composite playlist-quality score;
- claims that a refined playlist is universally better;
- persistence or cross-run refinement history.

## Proposed delivery sequence

1. **Phase 6A — Refinement contract**
   - review and accept evidence mappings, operation boundaries, correspondence
     validation, change records, and no-change semantics;
2. **Phase 6B — Bounded deterministic refinement**
   - implement only partial-tail completion and any explicitly approved
     final-position operation;
3. **Later search strategies**
   - require a separate contract and must preserve Phase 4 and Phase 5
     authority rather than redefining them.

Phase 6 is successful when it can justify a bounded change—or justify doing
nothing—using evidence the engine actually has.

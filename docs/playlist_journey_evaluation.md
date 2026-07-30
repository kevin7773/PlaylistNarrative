# Phase 5: Playlist Journey Evaluation

- **Status:** Accepted design contract
- **Scope:** Deterministic observation of construction results
- **Depends on:** Accepted Phase 4A ADR and Phase 4B construction artifacts

## Central contract

Given a construction result and the objective that produced it, return a
deterministic, immutable, explainable assessment of how well the playlist
functions as a complete journey.

Phase 5 begins as a pure observer. It may describe, aggregate, compare, and
diagnose. It may not modify the sequence or recommend a replacement.

## Design questions

### What does success mean for the entire playlist?

Success is not equivalent to a high mean track score. A successful journey has
several independently visible dimensions:

1. **Objective attainment**
   - The requested track count was reached.
   - Construction did not end partial or infeasible.
2. **Constraint integrity**
   - Hard constraints were preserved.
   - Any construction failures or compromises remain visible.
3. **Phase fidelity**
   - Placements cover the planned phases.
   - Phase-assigned tracks retain strong phase-fit evidence.
4. **Transition continuity**
   - Adjacent placements maintain coherent transition evidence.
   - Severe transition penalties and abruptness explanations are visible.
5. **Discovery fidelity**
   - Achieved discovery count and ratio are compared with the journey target.
   - Discoveries are distributed across positions and phases rather than merely
     counted.
6. **Trajectory coherence**
   - Track energy and phase evidence progress in a direction compatible with the
     journey.
7. **Attention continuity**
   - Available inputs do not reveal an unexplained cluster of attention-demanding
     placements.
8. **Explainability**
   - Every assessment traces to construction facts, stored component scores, or
     explicit evaluation rules.

These are component outcomes, not interchangeable proxies. A complete playlist
with weak transitions and a coherent partial playlist with unmet count are both
diagnosable, but neither should hide one dimension inside a single average.

### Which outcomes can existing construction data measure?

The current artifacts support the following deterministic measurements:

| Measurement | Existing evidence | Initial treatment |
| --- | --- | --- |
| Completion fidelity | requested and achieved track counts; construction status | Exact ratio and status |
| Construction issues | structured complete, partial, or infeasible issues | Preserve and classify |
| Duration observed | candidate durations and total duration | Report only; no duration objective exists |
| Artist repetition | artist counts plus `ConstructionPolicy` maximum | Exact compliance check |
| Duplicate tracks | ordered track IDs | Exact compliance check |
| Discovery attainment | journey target, policy threshold, discovery count | Exact count and ratio deviation |
| Discovery distribution | placement positions, phases, candidate familiarity | Position and phase diagnostics |
| Phase coverage | planned phases, placement phase index, counts, durations | Coverage and allocation diagnostics |
| Phase-fit evidence | stored `phase_score` per placement | Raw aggregates with sample counts |
| Transition evidence | stored `transition_score`, penalties, and reasons | Exclude the first placement; aggregate remaining transitions |
| Preference and context evidence | stored component scores | Raw aggregates by playlist and phase |
| Selection evidence | selector rank, adjusted score, placement reasons | Rank and score diagnostics |
| Energy observations | candidate energy sequence | Raw values and adjacent deltas |
| Lyrical-distraction observations | candidate local input | Descriptive distribution only |
| Role placement | role and one-based position | Distribution diagnostics |
| Rejection pressure | recorded rejected candidates and summary counts | Counts by hard-constraint reason |

The evaluator must use stored `ScoreBreakdown` values. It must not silently
rescore tracks, reconstruct expired rankings, or invoke `CandidateSelector`.

### Which measurements require future metadata or provenance?

The current model does not support defensible claims about:

- album repetition, because `TrackCandidate` has no album identity;
- vocal presence, vocal salience, lyric density, language, or lyrical content;
- acoustic key, tempo, timbre, loudness, or provider-derived audio similarity;
- emotional continuity as an independently persisted observation;
- narrative continuity as an independently persisted observation;
- the transition profile or scorer weights that produced each stored component;
- a public numeric mapping from phase `EnergyLevel` to target energy;
- intended anchor-spacing targets;
- real listener attention, fatigue, satisfaction, skips, or task performance;
- causal claims that a feature improved the listening experience.

`lyrical_distraction` is a local scoring input, not verified audio analysis.
Phase 5 may report its supplied values and their positions, but must not relabel
them as measured vocal salience. Similarly, raw energy deltas are observable;
an evaluator must not duplicate `TrackScorer`'s private energy-target mapping to
claim precise contour compliance.

## Evaluation inputs

The future evaluator should accept an immutable evaluation request containing:

- `construction_result`: the immutable `ConstructionResult`;
- `journey_plan`: the exact objective used for construction;
- `construction_policy`: the exact repetition and discovery policy used;
- optional immutable evaluation thresholds, each named and documented.

The candidate pool and `ConstructionState` are not evaluation inputs. The
result already contains the placed candidates and decision evidence. Mutable
construction state must not leak into observation.

If scorer-weight provenance or transition profiles later become required, they
must be added explicitly to construction artifacts. The evaluator must not
guess them from current defaults.

## Evaluation outputs

The proposed immutable report contains:

### Evaluation disposition

- `complete_evaluated`: the construction objective was completed and assessed;
- `partial_evaluated`: observed placements were assessed, with unmet objective
  coverage kept explicit;
- `inconclusive`: no meaningful sample exists for one or more requested
  dimensions.

Disposition is not a quality grade.

### Objective-fidelity metrics

Each metric contains:

- stable metric code;
- observed value and unit;
- target or comparison value when one exists;
- numerator, denominator, and sample count;
- applicability status: `measured`, `not_applicable`, or `unavailable`;
- concise explanation;
- evidence positions or phase names when useful.

The first implementation should report a vector of metrics rather than one
overall score. Normalized component scores are allowed only when their formula,
range, denominator, and source maximum are known. Stored raw component scores
may be aggregated, but their averages must remain labeled as raw scorer points.

### Playlist and phase diagnostics

Diagnostics include:

- playlist-level aggregates;
- per-phase aggregates;
- transition series for positions two through the end;
- discovery positions and phase distribution;
- energy and lyrical-distraction series;
- role positions;
- hard-constraint rejection pressure.

Every aggregate reports its denominator. The opening track is excluded from
transition averages because it has no incoming playlist transition.

### Evaluation issues

Issues are deterministic, ordered, and explainable. Initial issue families are:

- construction hard constraint unmet;
- partial objective coverage;
- insufficient transition sample;
- planned phase unrepresented;
- discovery target missed;
- severe transition penalty observed;
- summary and placement data inconsistent;
- metric unavailable from current metadata;
- evaluation threshold reached.

Evaluation issues do not alter the playlist and are not construction issues.
Construction issues are preserved as source evidence and referenced rather than
rewritten.

## Complete and partial results

Complete and partial results use the same evaluator. The report separates:

1. **objective attainment**, measured against the full request; and
2. **conditional observed quality**, measured only over tracks and transitions
   that actually exist.

A partial playlist must never be scaled up as though missing placements had
occurred. A strong transition average over three tracks does not erase a
ten-track objective that ended at three. Conversely, incompleteness does not
make the observed transition measurements invalid. Both facts remain visible.

Empty and single-track results are valid inputs:

- an empty result has no track, phase-fit, transition, or trajectory sample;
- a single-track result has track-level evidence but no transition sample.

## Determinism and immutability

For identical inputs, evaluation output must be byte-for-byte identical.

The evaluator:

- has no mutable domain state;
- does not mutate the construction result, journey plan, policy, or candidates;
- uses stable ordering for metrics, phases, positions, roles, and issues;
- does not depend on candidate-pool order, current time, randomness, external
  services, or process-local caches;
- produces identical reports for identical construction results created from
  differently ordered candidate pools.

Tests must prove direct determinism, input immutability, complete and partial
evaluation, and end-to-end pool-order independence.

## Explainability rules

Every measurement must identify whether it is:

- a direct fact from construction output;
- a deterministic aggregation of stored evidence;
- a comparison with an explicit objective or policy;
- unavailable because the model lacks evidence.

The evaluator must prefer “unavailable” over a fabricated estimate. It must not
translate a raw score into qualitative labels such as “excellent” without an
accepted threshold policy.

## Initial Phase 5 boundaries

### Included

- deterministic playlist-level metrics;
- objective-fidelity measurement;
- transition aggregation;
- trajectory and phase diagnostics;
- explicit evaluation issues;
- explainable component scores and raw aggregates;
- evaluation of complete, partial, empty, and single-track results;
- pool-order-independence and immutability tests.

### Excluded

- modifying the constructed playlist;
- replacing tracks or proposing repairs;
- backtracking, beam search, or stochastic optimization;
- user-preference learning;
- external audio analysis or provider calls;
- subjective machine-learned quality judgments;
- persistence or cross-run evaluation history.

## Proposed delivery sequence

1. **Phase 5A — Evaluation contract**
   - accepted metric inventory, precision limits, output shape, and issue
     taxonomy;
2. **Phase 5B — Deterministic observer**
   - implemented only the metrics supported by accepted Phase 5A evidence;
3. **Later optimization**
   - consume evaluation reports only after the pure observer is stable and
     tested.

The observer must remain useful even if no optimizer is ever built.

# Phase 5B: Deterministic Playlist Journey Evaluation

Phase 5B implements the pure observer proposed by
[Phase 5A](playlist_journey_evaluation.md). It reads a construction result, the
journey plan, and the exact construction policy. It never changes the playlist,
rescans candidates, or invokes scoring and selection.

## Public interface

`PlaylistJourneyEvaluator.evaluate(...)` returns an immutable
`EvaluationReport` containing:

- evaluation disposition and source construction status;
- ordered objective and evidence metrics;
- per-phase diagnostics;
- stored transition-score series beginning at placement two;
- descriptive energy and lyrical-distraction input series;
- discovery and role positions;
- deterministic evaluation issues.

The evaluator has no instance state. All report models are frozen and contain
only frozen nested models and tuples.

## Serialization contract

Evaluation JSON is a durable public artifact beginning at schema version `1.0`.
The top-level field order is:

1. `schema_version`;
2. `disposition`;
3. `construction_status`;
4. `metrics`;
5. `phase_diagnostics`;
6. `transition_series`;
7. `energy_series`;
8. `lyrical_distraction_series`;
9. `discovery_positions`;
10. `role_positions`;
11. `issues`.

Enum wire values are lowercase snake-case strings documented by their public
schema. Unknown fields are rejected.

Metric applicability has enforced semantics:

- `measured` requires a numeric value, supported current evidence, and an
  applicable sample;
- `not_applicable` means the metric is valid in principle but has no applicable
  sample or context; it is not a failure, zero, or evidence gap, and value,
  numerator, and denominator are null;
- `unavailable` means current evidence cannot support the measurement and must
  use the `unsupported` evidence source with null observed values; it cannot be
  converted into a proxy or used as decision evidence.

These meanings, along with the normative definitions of `improvement` and
`quality`, are inherited from the Phase 5A contract. In particular, `quality`
is multidimensional and is not a scalar output or acceptance criterion.

Changing field order, enum values, applicability semantics, or required fields
requires a schema-version decision rather than an incidental refactor.

## Measurement rules

- Completion fidelity retains requested and achieved track denominators.
- Partial results report objective attainment separately from conditional
  aggregates over observed placements.
- Stored scorer components are aggregated as raw points with sample counts.
- The opening track is excluded from transition metrics because it has no
  incoming playlist transition.
- Discovery uses the supplied construction policy threshold and the journey's
  target ratio.
- Phase diagnostics preserve planned duration share, observed count and
  duration, raw phase-score sum and mean, and evidence positions.
- Energy deltas and lyrical-distraction inputs are descriptive. They are not
  relabeled as contour compliance or vocal salience.
- Unsupported metrics remain explicit `unavailable` records with explanations.

No composite playlist-quality score is produced.

## Evaluation issues

The observer preserves construction issues as referenced source evidence and
adds evaluation-specific diagnostics for:

- partial objective coverage;
- inconsistent construction summaries;
- unrepresented planned phases;
- insufficient transition samples;
- discovery-target deviation;
- stored transition constraint penalties;
- measurements unavailable from current evidence.

Issues do not propose repairs or alter construction output.

## Purity and determinism

Identical inputs produce equal reports and identical serialized JSON bytes.
Metrics, phases, roles, positions, and issues use stable ordering. Tests verify:

- complete, partial, infeasible, empty, and resumed construction results;
- objective and conditional-evidence separation;
- transition denominator handling;
- unavailable metrics;
- no rescoring;
- input and evaluator immutability;
- end-to-end candidate-pool-order independence.

`TrackScorer`, `CandidateSelector`, and `SequentialPlaylistConstructor` remain
unchanged.

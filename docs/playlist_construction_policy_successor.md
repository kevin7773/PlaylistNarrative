# ADR: Coordinated Construction Targets and Reporting Successor

- **Status:** accepted documentation-only authority freeze; runtime conformance
  is not established.
- **Boundary version:** `1.0`.
- **Successor family:** ConstructionPolicy `2.0`, ConstructionTargetArtifact
  `1.0`, ConstructionInputBinding `2.0`, ConstructionResult `2.0`, and
  EvaluationReport `3.0`, all prospective.
- **Predecessor:** the accepted [Phase 4A ADR](playlist_construction_contract.md)
  and its historical [Phase 4B realization](playlist_construction.md), inspected
  at commit `f29ecc69a63ed04e8b72769055ee68a1ca254f04`.
- **Supersession scope:** only the successor family receives the target modes,
  bounded feasibility guarantee, and reporting semantics below. No historical
  artifact, canonical byte sequence, or meaning of count-mode `complete` changes.

## 1. Precedence and reconciliation

The Phase 4A ADR explicitly declares itself normative and requires an explicit
accepted successor to change its requirements. The later
[CF-3 integration contract](candidate_formation_integration.md) supplements it
with authenticated formed-only consumption and exact identity correspondence.
The [Phase 5 contract](playlist_journey_evaluation.md) governs independent
observation, not construction decisions. [Scoring](playlist_scoring.md) and
[selection](candidate_selection.md) describe the existing deterministic local
score and ranking boundaries; neither grants hard global-target authority.

Phase 4B implementation notes and roadmap completion labels do not repeal the
accepted ADR. The [Architectural Constitution](architectural_constitution.md)
explicitly remains unratified proposed doctrine, and
[refinement](playlist_journey_refinement.md) is proposed: neither overrides these
accepted contracts. This decision does not ratify them.

Classification: A = implemented/conforming; B = intentionally soft or
informational; C = normative but currently unimplemented; D = ambiguous or
conflicting description; E = out of scope for historical count mode.

| Requirement | Class | Reconciliation |
|---|---|---|
| Count achieved defines count-mode completion | A | ADR and implementation agree |
| Duration in historical count mode | B/E | Observed, not constrained; a 30-minute plan is not a hard construction minimum |
| Discovery distribution | B | Soft under the ADR, with a visible ranking modifier; not an exact quota |
| Half-up whole-track ranking demand | A | Phase 4B specifies it; runtime implements it |
| Phase assignment | A | Planned duration proportions determine positional phase assignment, not elapsed-time allocation |
| All phases must occur in every historical result | E | Valid phase references are hard; universal phase coverage is not historically enforced |
| Fresh rankings, exact formed-only consumption, artist cap | A | Preserved; CF-3 forbids identity normalization |
| Global-feasibility guard | C | Immediate artist-cap rejection alone is not the ADR's residual-feasibility guard |
| Explicit construction soft-compromise reporting | C | Empty issues despite missed discovery do not satisfy the ADR; separate evaluation is not a substitute |
| Independent evaluation | A | Observes count completion, duration, discovery deviation and phase coverage without changing output |
| Phase 4B's case-insensitive artist description | D | Stale description; later exact-identity CF-3 contract and runtime govern. Do not change historical bytes |
| Roadmap/Phase 4B completion implies full ADR conformance | D | Feature completion is not conformance evidence for missing guard/reporting duties |

The target-mode clauses are not mutually contradictory: the ADR explicitly
separates duration mode from count mode. Missing implementations are recorded
as gaps, not used as authority to waive requirements. No unresolved normative
precedence conflict is resolved by silently preferring runtime behavior here.

## 2. Historical applicability

Existing ConstructionPolicy/InputBinding/Result `1.0` artifacts retain their
original canonicalization, verification and interpretation:

- `requested_track_count` is the hard completion target;
- `complete` means achieved count equals requested count;
- duration is accumulated/reported but neither scored nor a completion gate;
- discovery remains a soft planning/scoring target;
- phase assignment uses journey proportions and requested positions;
- historical deterministic results, including empty issue lists, are not rewritten.

An artifact may remain an authentic, reproducible historical result while its
producer lacks full ADR conformance. The real result's count-mode `complete`
was truthful; its absent discovery-compromise report was contract-nonconforming.
Do not retroactively add issues, change its digest, or label it a successful
30-minute proof. Historical dispatch must not run successor semantics.

## 3. Minimal target modes and authority home

The successor has exactly two closed modes:

| Mode | Hard completion requirements | Soft/informational dimensions |
|---|---|---|
| `TRACK_COUNT` | Explicit positive requested count, formed-only validity, unique source-track IDs, artist cap, valid placements | Duration informational; discovery and phase coverage reported, not hard |
| `JOURNEY` | Journey-derived minimum authoritative seconds, representation of every planned phase, and the same validity/identity/cap requirements | Discovery soft with mandatory reporting; no separate caller-supplied count target |

A separate `DURATION` mode is not needed for this proof and is not authorized.
`JOURNEY` is a minimum-duration/phase-coverage successor, not the older ADR's
bounded-minimum-and-maximum duration mode. This ADR explicitly specializes the
target-mode boundary for this family; bounded duration and combined caller count
plus duration targets remain unsupported. Unknown modes fail closed.

The sole home of a hard target is a prospective immutable
`ConstructionTargetArtifact/1.0`. It binds the exact JourneyPlanArtifact `2.0`,
authenticated formed-parent digest and ConstructionPolicy `2.0` digest.
Its mode-specific content is closed:

- `TRACK_COUNT`: one explicit `requested_track_count`; no hard duration field.
- `JOURNEY`: `minimum_duration_seconds` must equal exactly
  `60 * journey.plan.duration_minutes`, and required phase indices must equal
  all indices of that exact journey. These are verified derivations, not
  independently editable operator inputs. No caller count field is permitted.

The exact journey is still the authority for planning duration and phases; the
target artifact alone grants them hard construction applicability. Policy,
orchestration and evaluation reference this target rather than accepting a
second independently mutable minimum. In the worked proof the derived hard
minimum is exactly 1,800 seconds.

Invalid/mismatched target inputs are rejected, not mislabeled as an infeasible
candidate pool. Artifact-shaped objects alone do not establish authority; the
future producer/verifier must enforce the existing authenticated input boundary.

## 4. Duration and positional strategy

Units are positive integer authoritative `TrackCandidate.duration_seconds`,
unchanged from CF-3. The source-specific millisecond authority is not reprojected
or rejoined here. No media inspection, provider-duration substitution or
fractional-second invention is authorized.

In `JOURNEY`, completion requires total seconds **at least** the minimum and
every required phase represented. Overshoot by whole tracks is permitted with
no invented upper bound. Undershoot is never complete; tolerance is zero. No
padding, trimming or partial-track playback is authorized.

The strategy retains existing scoring and positional assignment. It first
derives a finite planning horizon K from the exact pool: the smallest positive
K within artist-capped capacity for which (a) the existing positional function
represents every required phase and (b) maximum achievable K-track duration is
at least the minimum. If none exists, construction is pre-infeasible.
K is deterministic feasibility evidence, not another caller-supplied hard
target or a claim that minutes imply a fixed track count. Record it with the
exact target/formation bindings. `TRACK_COUNT` uses its requested count as K.

At every placement use the unchanged slot-midpoint phase function with K,
existing role assignment, fresh scoring, and stable identity tie-breaks. No
elapsed-time phase reassignment is introduced. In `JOURNEY`, stop immediately
when all hard requirements hold; otherwise continue only within the certified
horizon. This is not permission to append arbitrary tracks until a soft target
looks satisfactory. Planned phase coverage and achieved phase coverage remain
separate reported facts.

## 5. Exact bounded hard-feasibility guarantee

The supported hard constraints are finite distinct formed identities, positive
durations, exact per-artist caps, count or minimum duration, and positional
phase coverage in `JOURNEY`. No hard discovery constraint, per-phase feature
eligibility, album cap, maximum duration or generalized constraint solver is
authorized by this successor.

For a prefix P, remaining pool R and per-artist residual capacities:

1. Group R by exact artist identity; discard used identities.
2. For each artist keep up to its residual cap, ordered by descending duration
   and then existing exact identity tie-break. This is analysis, not a new pool.
3. The count of retained entries is remaining feasible capacity C.
4. The sum of the largest r durations across those entries is M(r), the exact
   maximum duration achievable with r additional tracks (undefined if C < r).

These are exact bounds under the supported partition-by-artist constraints:
replacing a shorter selected track of an artist with an available longer one
cannot violate any supported hard requirement. No permutation search,
backtracking, beam search or enumeration of all subsets is required.

Before construction certify capacity for K and, for `JOURNEY`, M(K) >= minimum
and positional coverage. During construction consider candidates in each fresh
selector ranking. Tentatively accepting one must preserve capacity for remaining
slots, positional coverage of missing required phases, and, when duration is
hard, `prefix_seconds + candidate_seconds + M(remaining_slots) >= minimum`.
Skip and record a higher-ranked candidate that destroys that guarantee. This
guard may change selection but never changes scorer components or pool contents.
Once hard completion is achieved no residual guarantee is needed.

If no hard-valid plan exists before any placement, return `infeasible` with a
preconstruction certificate. If placements exist and continuation fails, return
`partial` with the preserved prefix and exact residual failure. A locally greedy
dead end after a valid certificate is not evidence of original-pool infeasibility.
Under these bounded assumptions the exact guard should prevent that dead end;
an unexpected one must be reported and investigated, never silently repaired.

Resumption must retain/reverify the same original target, K, journey, policy,
formed parent and internally consistent prefix. Never derive a new horizon or
new target from only the residual pool. No durable recovery capability is added.

## 6. Discovery remains soft, with separate observable facts

Classification uses the exact bound policy familiarity threshold; the default
and real proof use `<= 0.35`. Scoring thresholds and weights are unchanged.
The journey's percentage is the single source of the requested ratio.

Record separately the requested ratio, planning horizon K, rounded ranking
target count, achieved count, achieved denominator, achieved ratio, final
exact-target comparison, structural assessment and any accepted compromise.
The ranking rule remains `floor(target_ratio * K + 0.5)` and remaining demand
remains clamped to [0,1] across remaining slots. For `TRACK_COUNT`, K is exactly
the requested track count. For `JOURNEY`, K is the certified planning horizon;
the final denominator is actual achieved count, never an imaginary K placements.

Exact final comparison has no product tolerance: for nonempty output compare
`100 * achieved_discovery_count == journey.discovery_percent * achieved_count`.
Half-up rounding does not make 20% or 33 1/3% equal to 25%. Decimal displays must
not govern equality. Empty output has no achieved ratio or exact-match claim.
This successor's exact arithmetic is distinct from the historical evaluator's
1e-9 numerical comparison; old metrics and artifacts remain unchanged.

Structural assessment is explicitly scoped to the certified K and hard target.
Use a sound cheap certificate: exact ratio may be impossible because its
K-track count is nonintegral, or because required familiar/discovery counts
exceed category capacity after artist caps. Report the arithmetic and bounds.
For example, if at most F familiar tracks fit, at least `K-F` discoveries are
required. If these tests do not prove impossibility, report
`NOT_ESTABLISHED`, not a claim of feasibility: mixed duration/category
feasibility is not solved by these necessary bounds. Do not require exhaustive
quota search or reject a hard-feasible run because a soft target is impossible.

The final result can therefore report exact-target-met, target-missed, and
structurally-infeasible without confusing them. Structural impossibility does
not override actual achieved evidence or claim impossibility at every other
track count. The real six-candidate example admits the stronger all-count proof
in section 10. No acceptable-deviation band or hard discovery mode is frozen.

## 7. Result status, issues and compromises

Reuse `complete`, `partial`, `infeasible` plus issues; do not add competing status
strings. ConstructionResult `2.0` must also carry target identity/content,
hard-target satisfaction, preconstruction/residual feasibility evidence and the
discovery report. Human-facing distinctions derive from these facts:

| Distinction | Representation |
|---|---|
| PRECONSTRUCTION_INFEASIBLE | `infeasible`, no placements, hard target false, preconstruction `global_infeasible` certificate |
| PARTIAL | `partial`, preserved nonempty prefix, hard target false, residual hard-unmet issue(s) |
| COMPLETE_WITH_COMPROMISE | `complete`, hard target true, one or more explicit soft-compromise issues |
| COMPLETE_TARGETS_SATISFIED | `complete`, hard target true, exact discovery target met, no declared target compromises |

The last label refers only to this closed target set, not universal playlist
quality, listener benefit, energy perfection or absence of evaluation warnings.

Retain the existing issue shape and severities `hard_unmet` / `soft_compromise`.
The successor's additional exact codes are necessary because no existing
construction code identifies duration failure or discovery compromise:

| Code | Severity/use |
|---|---|
| `global_infeasible` | hard_unmet; preconstruction impossibility with capacity/duration/phase certificate |
| `duration_target_missed` | hard_unmet; only where duration is hard, with observed/minimum seconds |
| `required_phase_unrepresented` | hard_unmet; only for hard required phases, identify missing indices |
| `discovery_target_missed` | soft_compromise; nonempty achieved ratio differs from requested ratio |
| `discovery_target_structurally_infeasible` | soft_compromise; include the sound K-scoped certificate |
| `global_feasibility_guard` | placement rejection, not hard_unmet; a ranked candidate would destroy residual hard feasibility |

Reuse `artist_repetition_limit` for candidate rejection and cap causes; do not
add redundant `artist_cap_limited`. Reuse `no_eligible_candidates` and
`candidate_pool_exhausted` for residual stopping. A cause and a failed target
may both be reported but must not be presented as independent failures when
they describe the same event. No duration issue is added in `TRACK_COUNT`.

Issues must identify target/phase/position where relevant, exact observed and
requested values, and why a soft compromise was retained while hard requirements
governed stopping. A zero discovery scorer component is not rejection authority.
Use deterministic issue order: preconstruction certificate, count/exhaustion,
duration, missing phases by index, structural discovery, achieved discovery.
Placement rejections retain decision/rank order. Schema-conformance failures
are rejected inputs, not soft compromises.

## 8. Constructor, evaluator and proof ownership

The constructor owns hard validity, feasibility-preserving decisions, hard
completion, and mandatory construction-compromise reporting. An optional later
evaluator must never be the only component aware of an unmet hard target.

EvaluationReport `3.0` independently checks achieved output against the exact
bound target, preserving construction issues rather than rewriting them. It
does not rescore, alter the playlist, trust `complete` as proof, or duplicate
the caller's target. Structural pool feasibility remains a constructor
certificate: the evaluator has no pool and must not invent that knowledge.
It verifies certificate correspondence, not an independent pool search.
Independent duration/discovery comparisons are observations, not new targets.

| Proof criterion | Primary semantic owner/classification |
|---|---|
| >=1,800 seconds | ConstructionTargetArtifact in JOURNEY: HARD CONSTRUCTION REQUIREMENT, derived from exact journey |
| Artist cap | ConstructionPolicy: HARD CONSTRUCTION REQUIREMENT |
| All three planned phases | JOURNEY target's derived required-phase set: HARD CONSTRUCTION REQUIREMENT |
| Requested 25% discovery | Exact journey: SOFT CONSTRUCTION TARGET; evaluator observes exact attainment |
| Deterministic replay | Versioned constructor/serialization contract: AUTHORITY/REPLAY REQUIREMENT |
| Formed-only consumption | CF-3: AUTHORITY/REPLAY REQUIREMENT |

The orchestration proof requires those assertions to be evaluated and reported;
it cannot redefine their targets. A historical proof's exact-discovery
assertion may fail even when construction validly completes with a compromise.
This successor does not relabel that failed proof as successful.

## 9. Coordinated version and canonical boundary

Inspected runtime versions: ConstructionPolicy, ConstructionInputBinding,
ConstructionResult and construction-state canonical form are `1.0`;
JourneyPlanArtifact is `2.0`; EvaluationReport is `2.0` and its input binding
is `1.0`. No serialized construction-request/target artifact currently exists.

| Component | Successor decision |
|---|---|
| ConstructionPolicy | `2.0`: same serialized cap/threshold fields, new explicit target/guard/reporting applicability; version changes canonical identity |
| ConstructionTargetArtifact | new `1.0`: binds mode and exact input/target authority; no invented historical request artifact |
| ConstructionInputBinding | `2.0`: retain existing lineage and additionally bind exact target artifact bytes/digest |
| ConstructionResult | `2.0`: retain placements/trace, add target, feasibility and discovery facts; completion dispatch by mode |
| EvaluationReport | `3.0`: understands successor target completion and exact comparison; historical `2.0` remains count-only |
| EvaluationInputBinding | retain `1.0`: existing version/digest fields can bind Result `2.0`, Policy `2.0` and Journey `2.0`; result transitively binds target |
| Scoring, selector, TrackCandidate, JourneyPlanArtifact, CF-3, readiness | unchanged; no semantic version bump or alternate acquisition path |
| Issue codes / orchestration proof | owned by result `2.0` / this ADR respectively, not new parallel registries |

Version dispatch must be explicit; no upgrade-by-relabeling, fallback to legacy
construction, or legacy evaluator acceptance of unsupported successor results.
Downstream finalizers/UI/orchestration are not declared successor-compatible
by this document. Their integration requires a later authorized tranche.

The repository uses compact UTF-8 schema-order JSON and lower-case SHA-256 for
construction policy instances, not a canonical static construction-definition
registry. Reuse that convention; do not invent another registry or digest for
this Markdown ADR. The following canonical default policy examples contain no
newline or BOM. They establish bytes for policy instances, not running authority.

Historical default ConstructionPolicy `1.0` (89 bytes):

```json
{"schema_version":"1.0","max_tracks_per_artist":2,"discovery_familiarity_threshold":0.35}
```

SHA-256: `a47bfdd7fc63f1524c38f84c5f3b07e96e292730baa0400e862fb77aeeaeb62c`.

Successor default ConstructionPolicy `2.0` (89 bytes):

```json
{"schema_version":"2.0","max_tracks_per_artist":2,"discovery_familiarity_threshold":0.35}
```

SHA-256: `5d94a0a847d6b13457d64799c46f2832eedfb7d616eb3463a64716f1c59b355b`.

The second example's predecessor is the first exact default instance; this is
not the predecessor digest for every custom policy. Preserve actual historical
bindings, not fabricated migration lineage. Concrete new artifact field order,
serializers and implementation-conformance tests remain prospective runtime
work; the semantic requirements and versions above are frozen, not an assertion
that executable schema classes already exist.

## 10. Normative worked interpretation and diagnostic evidence

The genuine proof selected source positions 110, 112, 33, 67:

| Position | Track | Exact artist | Authoritative seconds |
|---|---|---|---:|
| 110 | Lucretia My Reflection | The Sisters Of Mercy | 524 |
| 112 | This Corrosion | The Sisters Of Mercy | 617 |
| 33 | Aperture | Harry Styles | 311 |
| 67 | The Great Divide | Noah Kahan | 318 |

Total: 1,770 seconds; discovery: 2/4 = 50%; requested: 1,800 seconds and 25%.
Artist cap, phase representation, formed-only consumption and deterministic
replay passed. Historical count-mode `complete` is truthful, duration was
unconstrained, discovery was missed, and the empty construction issue list
omitted a required compromise report. Under JOURNEY these unchanged placements
cannot be complete: the hard minimum is missed by exactly 30 seconds. This is
a normative interpretation example, not an authorized new construction result.

Diagnostic cap-valid four-track alternatives were:

| Source positions | Seconds |
|---|---:|
| 33, 67, 98, 110 | 1,808 |
| 33, 67, 98, 112 | 1,901 |
| 33, 68, 98, 112 | 1,845 |
| 67, 68, 98, 112 | 1,852 |

Position 98 is This Corrosion, The Sisters Of Mercy, 655 seconds; position 68
is Porch Light, Noah Kahan, 262 seconds. These positions belong only to this
source occurrence. They are not policy constants or recommended substitutions.
They demonstrate a need for duration-aware decisions, not a reason to modify
the recorded count-mode result.

All three familiar formed tracks (98,110,112) share one exact artist. Cap 2
permits at most two familiar placements. Four tracks therefore require at least
two discoveries (50%), not the requested one (25%). This is a structural soft
target conflict, not a scoring or readiness defect. Five tracks require three
discoveries; six exceed total artist-capped capacity. At most three tracks can
total only 1,590 seconds. No available size meets both 1,800 seconds and exact
25%, and neither cap nor request may be relaxed implicitly.

The observed existing positional mapping is:

```text
3 -> 0,1,2
4 -> 0,1,1,2
5 -> 0,1,1,1,2
6 -> 0,1,1,1,1,2
```

Three already represents all phases. Four was only the smallest
duration-feasible count for this pool, not a phase-coverage necessity. Do not
replace the existing positional arithmetic with these example arrays.

## 11. Separate planning and recording-identity findings

The six-track subset offered some duration-feasible alternatives, not a
guarantee of the complete proof. Its four shortest durations totaled 1,415
seconds, and its familiar artist capacity could not supply exact discovery.
This violates the stronger combined expectations in the
[readiness subset strategy](active_focus_candidate_readiness_vocabulary.md#71-bounded-subset-selection-principle).
It is a proof-input/subset-planning gap. No capture, category, taste, withholding
or Candidate Formation semantics change here. A future subset planner must
assess applicable construction-policy feasibility before requesting annotations
and distinguish known source/taste capacity from still-unmeasured readiness.
It must not invent familiarity or promise feasibility from missing observations.

The operator attests that positions 98 and 112 are the same musical recording.
They remain separate source-track identities. Equal scoring features caused the
existing identity tie-break to prefer shorter 112; choosing 98 in that otherwise
equivalent slot would have cleared duration. Duplicate entries do not increase
familiar capacity beyond the artist cap. No duplicate suppression, evidence
transfer or recording correspondence is authorized here. The separate
[Penny recording identity / MusicBrainz boundary](penny_recording_identity_musicbrainz_correspondence.md)
is the future authority home; its positive correspondence rules remain
prospective. Construction must not infer them from this attestation.

## 12. Implementation gate and non-goals

This freeze changes documentation only. A later explicitly authorized tranche
must implement the coordinated target/binding/result family, exact bounded
guard, mandatory compromise reports, successor evaluator and version rejection,
then demonstrate deterministic replay and unchanged historical canonical bytes.
Tests must cover impossible count/duration/phase capacity, cap-limited residual
choices, duration overshoot/undershoot, exact soft-target comparisons, rounding,
sound structural certificates versus NOT_ESTABLISHED, and immutable resumption.

No runtime conformance, successful new real proof, export/playback, persistence,
provider support, source-duration expansion, generic optimization, hard discovery
quota, new readiness semantics or recording-level deduplication is claimed.

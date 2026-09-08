# First successful real governed Penny playlist proof

## Status and evidence boundary

This research/product milestone records the first successful genuine Active
Focus JOURNEY-mode proof under runtime commit
`11e42716b2555391c24cc9b4938804cf694cb991`. It is a closeout of the completed
live process **PID 121828**, not a new construction run, a synthetic regression,
or a new authority definition. A separately initiated second run is not the
evidence for this milestone.

All eleven real-proof assertions passed, including deterministic replay within
that live authority session. The historical TRACK_COUNT proof remains a
separate, valid historical result that failed the external duration criterion.
Neither run is rewritten or collapsed into the other.

The governing runtime semantics come from the
[construction-policy successor](playlist_construction_policy_successor.md),
[iTunes acquisition contract](penny_local_itunes_windows_xml_acquisition.md),
[readiness vocabulary and authority](active_focus_candidate_readiness_vocabulary.md),
and [Candidate Formation integration](candidate_formation_integration.md).
This document records evidence under those boundaries; it changes none of them.

## Source, objective, and journey

The operator selected **Penny List.xml** through the actual governed native
Windows picker. No path, bytes, stream, or synthetic picker result was injected.
Acquisition used `PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.1`.

| Source fact | Verified value |
|---|---|
| Exact byte length | 225,308 |
| Source SHA-256 | `aa7d1f91b69473db5398874339f0a7133e681426eab23be46927ee14dd0ee2e5` |
| Playlists / memberships | 1 / 159 |
| Tracks / governed identities | 159 / 159 |
| Exact artists | 65 |
| Authoritative seconds | 38,040 |
| Track Evidence validation | 159 accepted; 0 rejected |

Objective ID: `penny-first-active-focus-proof-001`.

Exact objective statement:

> Create a focused 30-minute listening journey that supports sustained concentration while remaining musically engaging.

Objective digest:
`3fa659303b7f0e00dc81f0d61f2479a7f18a381da5e25bd902dbaa825e052ef3`.

Journey digest:
`a134802d38dd7eeb91ea8d1e4f49cca247751d327507f5f0bbe489a9e3767a9c`.

The retained objective and journey independently replayed: **Active Focus,
30 minutes, 25% discovery, low → high**. Planned phases were Settle In (0–5
minutes), Sustained Focus (5–25), and Controlled Landing (25–30). Assigned
construction phases below retain the governed positional semantics; they do
not claim exact elapsed-time phase boundaries or a newly enforced energy curve.

## Taste, readiness, and the finite candidate universe

Exact persisted taste correspondence was used without mutation:

| Exact artist | Rating |
|---|---|
| The Sisters Of Mercy | Love |
| Noah Kahan | Meh |
| Harry Styles | Meh |

The separate `Sisters of Mercy` row remained Unknown and was not used as an
alias for `The Sisters Of Mercy`.

Six operator-supplied category-only observations were captured under vocabulary
1.0, readiness authority definition 1.2, declaration 1.0, and readiness
wrapper/producer/verifier 1.1. Numeric CF-1 values were reconstructed through
the governed categorical projection, not supplied as substitute observations.
The three initially unfamiliar tracks retained LEVEL_0 despite measurement
listening. Objective-specific context fit remained bound to this exact
objective/journey, not reusable intrinsic track metadata.

Readiness occurrence:
`active-focus-readiness-v11:65e9c5760285390e68ccb4a9e095d059`.

Occurrence digest:
`ccab8a557d5fdc231d0078d8b2e28b7c9ad672e187acde56986e85a75bdd31ac`.

Candidate Formation formed all **6 measured tracks** and withheld all **153
unmeasured tracks**. No measured track was withheld; no missing readiness was
inferred. CF-3 consumed formed candidates only, in exact source-position order
**67, 110, 33, 112, 68, 98**.

These are source-local positions, not policy constants. All six governed IDs
have the prefix `itunes-windows-library:9C9E2747D29AB9A8/track:`:

| Source position | Exact identity suffix |
|---|---|
| 67 | `251291F66368F1EA` |
| 110 | `411F46A1537ECF15` |
| 33 | `5D54294A82803CB5` |
| 112 | `84761B93D30767F9` |
| 68 | `C0B4C9476E129AE2` |
| 98 | `EF9D56D007A43122` |

## Successful JOURNEY construction

The run used ConstructionPolicy /2.0, ConstructionTargetArtifact /1.0,
ConstructionInputBinding /2.0, ConstructionResult /2.0, and EvaluationReport
/3.0. The target mode was **JOURNEY**, with the **1,800-second** hard minimum
derived from the authoritative journey, zero tolerance, and whole-track
overshoot permitted. No competing caller duration was supplied.

| Order | Source position | Track | Exact artist | Seconds | Assigned phase |
|---|---|---|---|---:|---|
| 1 | 110 | Lucretia My Reflection | The Sisters Of Mercy | 524 | Settle In |
| 2 | 98 | This Corrosion | The Sisters Of Mercy | 655 | Sustained Focus |
| 3 | 33 | Aperture | Harry Styles | 311 | Sustained Focus |
| 4 | 67 | The Great Divide | Noah Kahan | 318 | Controlled Landing |

Total: **1,808 seconds (30:08)**. Status: **`complete`**. Stopping reason:
**`HARD_TARGET_MET`**. Artist cap: **PASS** (2, 1, 1); required phases: **PASS**;
formed-only consumption: **PASS**; deterministic replay: **PASS**.

### Global feasibility changed the outcome

The preselection certificate was FEASIBLE, with planning horizon 4 and capped
candidate capacity 5: Harry Styles 1, Noah Kahan 2, The Sisters Of Mercy 2.
Maximum four-track duration capacity was 1,901 seconds; all required phase
indices (0, 1, 2) were attainable.

After selecting position 110, the successor rejected the higher-ranked
position 112 through residual duration feasibility: that prefix plus its best
permitted continuation could reach only **1,770 seconds**. It selected
position 98 instead, allowing the actual **1,808-second** result. This is
specific evidence that the feasibility guard materially changed construction,
not a general track-substitution policy. Scoring ordered hard-feasible choices;
there was no manual reordering, substitution instruction, or deduplication.

### Truthful discovery compromise

| Discovery fact | Result |
|---|---|
| Requested ratio | 25% |
| Ranking horizon / rounded target | 4 / 1 of 4 |
| Achieved | 2 of 4 (50%) |
| Exact target | MISSED |
| Structural outcome | STRUCTURALLY_INFEASIBLE |
| Structural reason | FAMILIAR_CAPACITY |

At this horizon, exact 25% requires three familiar placements, but the artist
cap permits only two familiar tracks. The result retained both soft issues:
`discovery_target_structurally_infeasible` and `discovery_target_missed`.
This is a truthful **soft compromise**, not a hard construction failure, and
does not establish an acceptable deviation rule for other requests.

## Independent evaluation and deterministic replay

EvaluationReport /3.0 disposition: **`complete_evaluated`**. Independent
reconstruction agreed on achieved duration, phase assignments, artist counts,
discovery arithmetic, and issue consistency; it did not merely accept the
constructor's hard-target booleans.

Certificate disposition was exactly
**`BOUND_CONSTRUCTOR_EVIDENCE_NOT_POOL_RECOMPUTED`**. The evaluator did not
independently recompute feasibility from the complete original candidate pool.

Same-session replay reproduced readiness verification and CF-1 projection,
formed/withheld outcomes, CF-3 order, target, input binding, feasibility,
selected order, phase assignments, duration, discovery, compromises, result,
and evaluation. Canonical artifact bytes matched exactly:

| Successful real-proof artifact | Bytes | SHA-256 |
|---|---:|---|
| Target /1.0 | 682 | `996e9d52bc7826ac77f7c6d7453a8f334b196a409061ab9ed02dcc98a5c6dcdd` |
| Input binding /2.0 | 1,336 | `199f40cc6818ea849cf4f263b9ece52b3a520a5f96c291b190f40c0a0ec841e3` |
| Feasibility certificate | 1,629 | `a75250cbfd1f97707c19e3984dc6d66f4516a597b8bba307164cfc252418f11d` |
| Result /2.0 | 12,746 | `ae854b433e8daa859eb6e989b24b05ca1d3ce5c2e99ea98080462efcdfa91c6f` |
| Evaluation /3.0 | 6,177 | `5a0c0f92afe44d2c2afba5076b6754a50a13a8b005461ab52b56dd52d473f9ac` |

These are **successful real-proof evidence artifact digests**, not global
authority-definition digests or durable capability-recovery credentials.
Their sizes and hashes were reproduced from the retained live PID 121828
objects during documentation closeout, without rerunning construction.

## Separate historical TRACK_COUNT proof

The earlier genuine proof selected **110, 112, 33, 67**, totaling **1,770
seconds**, with historical status **`complete`**, discovery **50%**, and
deterministic replay **PASS**. It was valid historical TRACK_COUNT completion
but failed the external 1,800-second real-proof duration criterion and missed
the requested discovery target. Historical duration was unconstrained; its
empty construction issue list also omitted the required compromise report.

That evidence motivated the JOURNEY successor. It is not invalidated,
rewritten, or superseded by this successful run. See the unchanged
[historical diagnostic evidence](playlist_construction_policy_successor.md#10-normative-worked-interpretation-and-diagnostic-evidence).
No historical TRACK_COUNT rerun was performed as part of the successful proof
or this closeout.

## Duplicate-recording finding

The operator observes that source positions 98 and 112 are the same musical
recording. They remain distinct governed source-track identities: both formed,
both entered CF-3, and only 98 was selected. Position 112 was rejected first
by residual duration feasibility, then by the artist cap at later placements.

This outcome does **not** establish recording-level deduplication, readiness
transfer, or accepted recording correspondence. The already-frozen
[Penny Recording Identity / MusicBrainz correspondence boundary](penny_recording_identity_musicbrainz_correspondence.md)
is the future home for this issue; its prospective positive correspondence and
runtime authority must not be inferred from this operator observation.

## Process-local authority limitation

The successful proof executed in **live PID 121828**. Principal, acquisition,
and readiness occurrence authority were **process-local**. This proof does not
establish restart-safe principal authority, restart-safe acquisition authority,
restart-safe readiness authority, or durable recovery of those capabilities
from serialized artifacts. Hashes and valid-looking serialized objects cannot
replace those capabilities after process loss.

Objective/journey authority was independently replayable from retained
serialized material. That distinct capability does not make the other three
authority layers restart-safe. This limitation remains a visible product
workflow gap, not an implementation claim.

## Product significance and non-claims

This bounded milestone establishes genuine multi-artist native-picker
acquisition; use of exact persisted taste and human readiness evidence;
Candidate Formation and CF-3 over real source identities; satisfaction of the
hard 30-minute JOURNEY target; honest soft discovery infeasibility reporting;
independent evaluation agreement within the stated certificate boundary; and
deterministic replay within the live authority session.

It does **not** establish a streaming-provider catalog, automated readiness,
complete production end-user UX, recording-level deduplication, durable or
restart-safe authority, provider fulfillment, playlist export, or playback.
No referenced media or network resources were accessed during the proof.

## Next-work disposition

These are strategic branches, not an implementation authorization or priority
ordering:

1. **Catalog / identity expansion:** MusicBrainz-backed provider-neutral
   catalog, Penny recording identity/correspondence, and provider rendition
   resolution, subject to the existing correspondence boundary.
2. **Readiness automation:** lawful sources for energy, groove,
   instrumentalness, lyrical characteristics, familiarity/listening-history
   evidence, and reduced manual annotation. No new source authority or
   inference permission is granted here.
3. **Evidence-backed infrastructure gap:** restart-safe principal/acquisition/
   readiness authority remains deferred unless real usage demonstrates that
   the process-local limitation materially blocks product workflow. The
   limitation is recorded; this closeout does not declare that gate satisfied.

See the [roadmap](roadmap.md). Neither strategic branch is implemented or
assigned priority by this closeout; existing acquisition backlog gates remain
intact.

# Candidate Formation Contract

- **Status:** CF-0 contract accepted; CF-1 source-evidence schemas and CF-2
  deterministic formation implemented; CF-3 integration remains unimplemented
- **Purpose:** Deterministically join validated track evidence with independently
  validated local evidence and approved rules to form the stable candidate pool
- **Artifact type:** Evidence-grounded formation and withholding, not scoring,
  selection, construction, or recommendation

## Normative invariant

Every validated track appears exactly once in either the formed or withheld
partition. Every field of every formed `TrackCandidate` must be reproducible
solely from immutable source evidence and approved versioned rules.

Candidate Formation may not:

- manufacture neutral defaults;
- infer positive preference from unknown or unrated status;
- convert a hard exclusion into a scoring penalty; or
- derive a numeric value without a named versioned rule and recorded inputs.

## Boundary

Track Evidence Validation establishes catalog-level identity, title, artist,
duration, and provenance. It explicitly does not establish preference,
eligibility, familiarity, suitability, recommendation, or playlist membership.

Candidate Formation is the deterministic join boundary where that validated
catalog evidence may be combined with independently validated evidence for taste,
familiarity, track features, and objective context. Its sole decision is whether
each validated track has corresponding evidence and passes hard eligibility
requirements sufficient to become a structurally complete `TrackCandidate`.

```text
Validated Track Evidence
        +
Immutable Taste Evidence
        +
Immutable Familiarity Evidence
        +
Immutable Track Feature Evidence
        +
Accepted Objective + Journey Plan
        +
Approved Candidate Formation Policy
        ↓
Candidate Formation Artifact
        ├── Formed TrackCandidates
        └── Withheld tracks with deterministic reasons
```

Candidate Formation performs no provider access. Acquisition, validation, and
normalization decisions must finish before evidence crosses this boundary.

## Source artifacts

The future immutable request must contain:

- an accepted Objective Safety artifact;
- the exactly corresponding Journey Plan;
- a Track Evidence Validation artifact;
- immutable local Taste Evidence;
- immutable Familiarity Evidence;
- immutable Track Feature Evidence;
- the Candidate Formation policy identifier and version; and
- the complete set of approved derivation-rule identifiers and versions used by
  that policy.

CF-1 defines the local Taste Evidence, Familiarity Evidence, Track Feature
Evidence, and Objective Context Evidence schemas. The Objective Safety and
Journey Plan artifact prerequisites, Candidate Formation request, initial
formation policy, preference derivation rule, output artifact, and deterministic
formation service are implemented for CF-2.

## Source-artifact correspondence

Before processing individual tracks, Candidate Formation must validate the
request as one coherent replay context:

- the Objective Safety artifact must be accepted;
- objective identity and statement must correspond exactly across the accepted
  objective, Journey Plan, and every objective-scoped evidence artifact;
- the Track Evidence Validation artifact must identify the exact source snapshot
  represented by the request;
- every evidence artifact must declare its identity, schema version, and evidence
  scope;
- every approved rule must be identified by exact name and version; and
- artifact identifiers and policy identifiers must be explicit and immutable.

A request-level correspondence failure invalidates the complete formation
request. It must not produce a partial `CandidateFormationArtifact`, because a
stable context for the formed/withheld partition does not exist.

Once request-level correspondence succeeds, missing or unusable evidence for an
individual validated track is a track-level withholding condition. One track's
withholding must not suppress formation of an independently complete neighboring
track.

## Exact identity requirements

Track evidence joins by exact `track_id`. Artist-scoped evidence joins by the
exact `artist_name` already carried by the validated record. Schema CF-0 approves
no trimming, case folding, Unicode normalization, punctuation folding, alias
resolution, fuzzy matching, provider lookup, or alternate-identity inference.

Evidence attached to a near-match is not evidence for the validated track. An
exact identity conflict is retained as a deterministic withholding reason; it is
never repaired inside Candidate Formation.

## Field-level evidence ownership

Every formed field has one documented evidence owner. Formation may copy a
validated value directly or apply an approved rule; it may not source the same
field opportunistically from whichever artifact happens to contain a value.

| `TrackCandidate` field | Evidence owner | Formation rule |
| --- | --- | --- |
| `track_id` | Validated Track Evidence | Copy exact validated identity |
| `title` | Validated Track Evidence | Copy exact validated title |
| `artist_name` | Validated Track Evidence | Copy exact validated artist identity |
| `duration_seconds` | Validated Track Evidence | Copy exact validated duration |
| `preference` | Local Taste Evidence | Apply an approved versioned preference rule to recorded taste inputs |
| `familiarity` | Familiarity Evidence | Copy or derive only under its named versioned rule |
| `energy` | Track Feature Evidence | Copy or derive only under its named versioned rule |
| `instrumentalness` | Track Feature Evidence | Copy or derive only under its named versioned rule |
| `lyrical_distraction` | Track Feature Evidence | Copy or derive only under its named versioned rule |
| `groove` | Track Feature Evidence | Copy or derive only under its named versioned rule |
| `context_fit` | Objective-scoped Context Evidence | Copy measured evidence, or derive only from recorded inputs under a named versioned rule |

Artist inspection scope does not establish preference. Unknown or unrated status
does not imply positive, neutral, or negative preference. A future policy may
permit controlled discovery eligibility for an unknown artist, but it must still
provide independently reproducible evidence for every required candidate field.

## Hard eligibility

Hard eligibility is evaluated before candidate formation. A track associated
with an applicable `Forbidden`, `Pencil`, or default `No Thanks` exclusion is
withheld.

An exclusion is a hard gate. Candidate Formation must not:

- form the candidate with a lower preference value;
- translate the exclusion into a scoring or ranking penalty;
- allow strong feature or context evidence to offset the exclusion; or
- send the excluded track downstream for reconsideration.

The withheld entry records the applicable exclusion evidence and deterministic
reason. Candidate Formation does not alter the user's rating or exclusion.

## Evidence-state semantics

Every required field must preserve why usable evidence was not available:

- **Unavailable:** no corresponding evidence value was supplied for the exact
  track, artist, objective, or context required by the field.
- **Conflicting:** two or more applicable source records make incompatible claims
  and no approved rule deterministically resolves them.
- **Unsupported:** evidence is present, but its schema, type, unit, range,
  provenance, or rule version is not supported by the formation policy.
- **Explicitly inapplicable:** the source artifact explicitly states that the
  evidence dimension does not apply. This is evidence, not absence, but it cannot
  populate a required numeric `TrackCandidate` field unless an approved versioned
  rule explicitly defines that transformation.

These states are distinct. They must not be collapsed into `0`, `0.5`, another
neutral value, a generic missing-evidence reason, or one another.

CF-1 represents these meanings with the fixed states `measured`, `unavailable`,
`conflicting`, `unsupported`, and `explicitly_inapplicable`. Only `measured`
evidence may carry a resolved value. Other states preserve their source
observations without a resolved substitute.

## CF-1 source-evidence schemas

The isolated `candidate_formation` package defines four immutable artifact
types:

- `LocalTasteEvidenceArtifact` preserves exact artist identity and categorical
  `Rating` evidence. It explicitly establishes neither hard eligibility nor a
  numeric preference value. `Unknown` remains an observed category, not an
  inferred score.
- `FamiliarityEvidenceArtifact` records exact track and artist identity,
  track-scoped unit-interval familiarity evidence, and the exact track snapshot
  identity it describes.
- `TrackFeatureEvidenceArtifact` records exact track and artist identity plus
  track-scoped unit-interval evidence for energy, instrumentalness, lyrical
  distraction, and groove.
- `ObjectiveContextEvidenceArtifact` records exact objective, journey, context,
  track-snapshot, track, and artist identities. It may preserve a measured
  provenance-backed `context_fit` value and named serialized context inputs, but
  does not infer fit from objective text or a Journey Plan.

Every artifact uses schema version `1.0`, frozen models, forbidden extra fields,
exact nonblank identities, UTF-8 byte ordering, and explicit false eligibility,
scoring, ranking, formation, and recommendation claims. Observations retain an
evidence ID, descriptive source type, source reference, and exact serialized
payload. Canonical serialization uses schema field order, compact JSON
separators, and UTF-8.

Collection input order is not meaningful. Records, named context inputs, and
provenance observations are canonicalized by their documented exact identity in
UTF-8 byte order. Equivalent collections therefore produce equal objects and
byte-identical serialization. Exact serialized evidence payload bytes remain
meaningful and are never normalized. Canonicalization constructs new immutable
tuples inside the deterministic schema boundary; it never sorts or otherwise
mutates caller-owned collections in place.

CF-1 values remain source evidence, not direct `TrackCandidate` values. Even a
measured unit-interval value must pass future CF-2 correspondence, eligibility,
field-ownership, and derivation-policy checks before it could populate a
candidate. Categorical Taste Evidence has no numeric preference mapping in
CF-1, and `Unknown` remains `Unknown`.

CF-1 validates evidence-artifact structure only. It does not establish
cross-artifact correspondence, apply eligibility policy, approve derivation
rules, form candidates, or produce withheld reasons.

## Formed and withheld partitions

The output artifact contains the exact UTF-8-ordered validated track identities,
a formed partition, a withheld partition, and counts proving:

```text
validated_track_count = formed_count + withheld_count
```

The partitions are disjoint, and their union equals the exact validated-track
set. Input ordering has no effect on either partition.

CF-2 validates request-level correspondence before partitioning. The accepted
objective, Journey Plan, track validation, objective-context evidence, track
snapshot identities, journey identity, and profile identities must correspond
exactly. Evidence scoped to an unvalidated track invalidates the request rather
than being silently ignored.

### Formed entry

A formed entry contains:

- one complete immutable `TrackCandidate`;
- the source record identity for every copied field;
- the rule name, rule version, and recorded inputs for every derived field;
- the hard-eligibility evidence and policy decision;
- a deterministic field-level formation explanation; and
- a contiguous one-based ordinal in UTF-8 `track_id` byte order.

No field may be present without a reproducible evidence chain.

### Withheld entry

A withheld entry contains:

- the exact validated track record;
- all applicable deterministic withholding reasons;
- the source evidence identities relevant to each reason; and
- no partial `TrackCandidate`.

Withholding is lossless and explanatory. It does not discard valid catalog
evidence, mutate source artifacts, or select one convenient reason when multiple
reasons apply.

## Fixed withholding-reason precedence

Reasons use this CF-0 precedence:

1. `HARD_ELIGIBILITY_EXCLUDED`
2. `TRACK_IDENTITY_CONFLICTING`
3. `ARTIST_IDENTITY_CONFLICTING`
4. `EVIDENCE_CONFLICTING`
5. `EVIDENCE_UNAVAILABLE`
6. `EVIDENCE_UNSUPPORTED`
7. `EVIDENCE_INAPPLICABLE`
8. `DERIVATION_RULE_UNAPPROVED`
9. `DERIVATION_INPUT_UNAVAILABLE`
10. `DERIVED_VALUE_INVALID`

All applicable reasons are retained. A hard exclusion does not suppress evidence
quality reasons that are independently observable from the immutable request.
Repeated codes are ordered by candidate-field path using UTF-8 bytes, then by
source-artifact identity using UTF-8 bytes. Duplicate reason keys are forbidden.
Each code has one fixed explanation owned by the Candidate Formation policy
version; explanations are not generated dynamically.

## Derivation governance

A derivation is permitted only when the request's Candidate Formation policy
names an approved rule and exact version. Every derived value must record:

- the output field;
- the rule name and version;
- every immutable source artifact and record identity used;
- the exact serialized input values;
- the resulting value; and
- the deterministic explanation required by the rule.

The same serialized inputs, source-artifact versions, formation-policy version,
and derivation-rule versions must reproduce an equal artifact and byte-identical
canonical serialization.

Candidate Formation may not use current time, randomness, environment state,
network access, mutable database reads, unrecorded provider behavior, learned
affinity, or model-generated judgment. A rule that changes requires a new
version; it must not silently reinterpret an existing artifact.

### Initial CF-2 policy

CF-2 supports direct copying of measured familiarity, track-feature, and
objective-context evidence. Its only numeric derivation is categorical artist
taste to `preference`, and the request must supply an explicit named, versioned
mapping for exactly `Love`, `Like`, and `Meh`. Penny supplies no production
default values.

`Unknown` has no mapping and is withheld. `No Thanks`, `Pencil`, and `Forbidden`
are hard exclusions in fixed order; they are never translated into low scores or
penalties. Non-measured states retain their distinct withholding reasons.

Every formed field records its source artifact, source record, evidence IDs,
exact serialized inputs, exact result, formation basis, explanation, and—when
derived—the rule name and version. Artifact validation rejects any candidate
field that differs from its recorded result.

## Explicit non-claims

A formed `TrackCandidate` means only that the track is structurally complete,
reproducible, and hard-eligible for downstream scoring under the recorded
formation policy. Formation makes no claim that:

- the track is recommended;
- the track belongs in a soundtrack;
- the track is suitable for every phase or placement;
- one candidate is better than another;
- the candidate will be selected;
- the final soundtrack will contain the track; or
- the soundtrack satisfies its objective.

The artifact must explicitly record that scoring, ranking, selection,
construction, evaluation, and refinement were not performed.

## Isolation and non-goals

Candidate Formation does not acquire or validate source evidence, access
providers, modify taste, resolve aliases, infer missing values, score or rank
candidates, construct a soundtrack, evaluate a journey, refine a result, learn
from outcomes, or persist mutable state.

CF-0 through CF-2 authorize the contract, source-evidence schemas, prerequisite
artifacts, and isolated deterministic formation service. CF-3 downstream
integration requires separate approval. Construction and scoring continue to
accept caller-supplied candidate pools and are not wired to CF-2 automatically.

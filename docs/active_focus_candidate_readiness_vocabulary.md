# Active Focus Candidate-Readiness Vocabulary v1

- **Status:** authority contract frozen; implementation not established
- **Vocabulary ID:** `pne.active-focus.candidate-readiness`
- **Vocabulary version:** `1.0`
- **Schema version:** `1.0`
- **Boundary:** category-only manual readiness evidence for one exact Active Focus objective and Journey Plan

## 1. Purpose and invariant

This contract defines the smallest authority boundary that can transform manual
categorical observations into the existing Candidate Formation evidence for
familiarity, energy, instrumentalness, lyrical distraction, groove, and
objective-specific Active Focus context fit.

The categorical observation is authoritative evidence. Its numeric value is
only a deterministic projection under this exact vocabulary. No governed
capture path may accept a numeric readiness value directly.

This contract does not change Candidate Formation, CF-3, `TrackCandidate`,
taste, acquisition, Track Evidence Validation, scoring, selection, or
construction. Candidate Formation remains the sole boundary authorized to
create a `TrackCandidate`.

## 2. Vocabulary authority

### 2.1 Closed levels and projection

| Exact token | Exact decimal projection |
| --- | ---: |
| `LEVEL_0` | `0.00` |
| `LEVEL_1` | `0.25` |
| `LEVEL_2` | `0.50` |
| `LEVEL_3` | `0.75` |
| `LEVEL_4` | `1.00` |

Tokens are exact and case-sensitive. There are no aliases, abbreviations,
synonyms, numeric inputs, interpolation, or intermediate levels. Projection
consumes an exact governed field identity and one exact token. It returns the
corresponding unit-interval value without time, locale, external state,
inference, or caller-supplied rules.

The decimal strings are the normative vocabulary lexemes. Existing CF-1 numeric
fields receive their exact numeric values; JSON may render endpoints as `0.0`
and `1.0` without changing their numeric meaning.

### 2.2 Field-specific semantics

The common level structure does not give a level one common conceptual meaning.
Each field owns its definitions independently.

#### Familiarity

Familiarity describes the current local principal's recognition and ability to
anticipate the track. It is not preference, quality, play count, or inferred
from an artist rating.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | No reliable recognition of the track. |
| `LEVEL_1` | Slight recognition, but the track's structure cannot be anticipated reliably. |
| `LEVEL_2` | The track is recognizable and partially predictable. |
| `LEVEL_3` | The track is well known; its major structure and changes are predictable. |
| `LEVEL_4` | The track is deeply familiar; its structure, entries, major changes, and ending are readily anticipated. |

#### Energy

Energy describes perceived activation, intensity, and forward drive. It is not
tempo or loudness; neither may be substituted for the observation.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | Near-still experience with minimal activation or forward drive. |
| `LEVEL_1` | Restrained or gentle activation and drive. |
| `LEVEL_2` | Steady, moderate activation and forward drive. |
| `LEVEL_3` | Strong, active, sustained forward drive. |
| `LEVEL_4` | Maximal or near-maximal sustained activation, intensity, and forward drive. |

#### Instrumentalness

Instrumentalness describes the prevalence and prominence of intelligible sung
or spoken verbal content. It is not genre. Non-lexical vocal sound does not by
itself prevent a high observation; intelligible verbal content is the governed
distinction.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | Intelligible sung or spoken words dominate the track. |
| `LEVEL_1` | The track is mostly verbal, with limited instrumental-only space. |
| `LEVEL_2` | Verbal and instrumental content are both substantial. |
| `LEVEL_3` | The track is mostly instrumental; intelligible words are occasional or secondary. |
| `LEVEL_4` | The track contains no intelligible sung or spoken verbal content. |

#### Lyrical distraction

Lyrical distraction describes the observed tendency of verbal content to claim
the current local principal's attention during cognitively focused listening.
It is attention demand, not sentiment, topic, quality, or lyric classification.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | Verbal content does not pull attention away from focused activity. |
| `LEVEL_1` | Verbal content causes occasional mild attention pull. |
| `LEVEL_2` | Verbal content creates repeated, noticeable but manageable attention pull. |
| `LEVEL_3` | Verbal content frequently competes with focused attention. |
| `LEVEL_4` | Verbal content dominates attention or reliably prevents focused activity. |

#### Groove

Groove describes perceived rhythmic stability and propulsion. It is not
danceability, tempo, genre, preference, or quality.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | No stable rhythmic pulse or propulsion is perceived. |
| `LEVEL_1` | Rhythmic propulsion is weak, diffuse, or irregular. |
| `LEVEL_2` | A clear, steady degree of rhythmic movement is perceived. |
| `LEVEL_3` | Rhythmic propulsion is strong and consistent. |
| `LEVEL_4` | Rhythmic propulsion is dominant and highly driving. |

#### Active Focus context fit

Active Focus context fit describes residual suitability for the exact accepted
objective and exact Journey Plan after separately measured familiarity, energy,
instrumentalness, lyrical distraction, groove, and preference are set aside.
It must not repackage or average those dimensions.

| Level | Definition |
| --- | --- |
| `LEVEL_0` | The track strongly conflicts with the exact objective and journey for reasons not represented by the separately measured dimensions. |
| `LEVEL_1` | The track is more likely to interfere with than support the exact objective and journey for such residual reasons. |
| `LEVEL_2` | The track provides mixed, conditional, or neutral residual support for the exact objective and journey. |
| `LEVEL_3` | The track reliably supports the exact objective and journey for residual reasons. |
| `LEVEL_4` | The track provides exceptionally strong residual support for the exact objective and journey. |

Context fit is evidence about one exact objective/journey occurrence. It is not
intrinsic metadata and may not be copied, cached, or reused for another
objective, another Journey Plan, or a generic Active Focus profile.

### 2.3 Canonical vocabulary definition

Canonical serialization is UTF-8 JSON in the exact field and array order shown,
with `ensure_ascii=false`, no insignificant whitespace, separators `,` and `:`,
and no trailing newline. The digest excludes any digest field. This line is the
complete canonical vocabulary content:

```json
{"schema_version":"1.0","artifact_kind":"active_focus_candidate_readiness_vocabulary","vocabulary_id":"pne.active-focus.candidate-readiness","vocabulary_version":"1.0","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0","levels":[{"token":"LEVEL_0","projection":"0.00"},{"token":"LEVEL_1","projection":"0.25"},{"token":"LEVEL_2","projection":"0.50"},{"token":"LEVEL_3","projection":"0.75"},{"token":"LEVEL_4","projection":"1.00"}],"dimensions":[{"field":"familiarity","levels":[{"token":"LEVEL_0","definition":"No reliable recognition of the track."},{"token":"LEVEL_1","definition":"Slight recognition, but the track's structure cannot be anticipated reliably."},{"token":"LEVEL_2","definition":"The track is recognizable and partially predictable."},{"token":"LEVEL_3","definition":"The track is well known; its major structure and changes are predictable."},{"token":"LEVEL_4","definition":"The track is deeply familiar; its structure, entries, major changes, and ending are readily anticipated."}]},{"field":"energy","levels":[{"token":"LEVEL_0","definition":"Near-still experience with minimal activation or forward drive."},{"token":"LEVEL_1","definition":"Restrained or gentle activation and drive."},{"token":"LEVEL_2","definition":"Steady, moderate activation and forward drive."},{"token":"LEVEL_3","definition":"Strong, active, sustained forward drive."},{"token":"LEVEL_4","definition":"Maximal or near-maximal sustained activation, intensity, and forward drive."}]},{"field":"instrumentalness","levels":[{"token":"LEVEL_0","definition":"Intelligible sung or spoken words dominate the track."},{"token":"LEVEL_1","definition":"The track is mostly verbal, with limited instrumental-only space."},{"token":"LEVEL_2","definition":"Verbal and instrumental content are both substantial."},{"token":"LEVEL_3","definition":"The track is mostly instrumental; intelligible words are occasional or secondary."},{"token":"LEVEL_4","definition":"The track contains no intelligible sung or spoken verbal content."}]},{"field":"lyrical_distraction","levels":[{"token":"LEVEL_0","definition":"Verbal content does not pull attention away from focused activity."},{"token":"LEVEL_1","definition":"Verbal content causes occasional mild attention pull."},{"token":"LEVEL_2","definition":"Verbal content creates repeated, noticeable but manageable attention pull."},{"token":"LEVEL_3","definition":"Verbal content frequently competes with focused attention."},{"token":"LEVEL_4","definition":"Verbal content dominates attention or reliably prevents focused activity."}]},{"field":"groove","levels":[{"token":"LEVEL_0","definition":"No stable rhythmic pulse or propulsion is perceived."},{"token":"LEVEL_1","definition":"Rhythmic propulsion is weak, diffuse, or irregular."},{"token":"LEVEL_2","definition":"A clear, steady degree of rhythmic movement is perceived."},{"token":"LEVEL_3","definition":"Rhythmic propulsion is strong and consistent."},{"token":"LEVEL_4","definition":"Rhythmic propulsion is dominant and highly driving."}]},{"field":"active_focus_context_fit","levels":[{"token":"LEVEL_0","definition":"The track strongly conflicts with the exact objective and journey for reasons not represented by the separately measured dimensions."},{"token":"LEVEL_1","definition":"The track is more likely to interfere with than support the exact objective and journey for such residual reasons."},{"token":"LEVEL_2","definition":"The track provides mixed, conditional, or neutral residual support for the exact objective and journey."},{"token":"LEVEL_3","definition":"The track reliably supports the exact objective and journey for residual reasons."},{"token":"LEVEL_4","definition":"The track provides exceptionally strong residual support for the exact objective and journey."}]}],"categorical_observation_authority":true,"direct_numeric_capture_authorized":false}
```

Canonical SHA-256:
`63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d`.

Any change to identity, version, tokens, projections, field identities,
definitions, ordering, categorical authority, direct-input rule, or
canonicalization requires a new vocabulary version.

## 3. Readiness-occurrence authority

### 3.1 Required authority chain

```text
current applicable PENNY_LOCAL_INSTALLATION principal
        +
exact accepted-objective authority
        +
exact governed acquisition and Track Evidence Validation snapshot
        +
exact immutable Candidate-Readiness Vocabulary v1 definition
        +
exact authoritative Active Focus Journey Plan
        +
category-only manual declaration
        ↓
readiness occurrence
        ↓
verified readiness authority
        ↓
existing Candidate Formation evidence artifacts
```

Principal authority establishes an authorized local-principal action. It does
not establish physical-human, legal, biological, account, or operating-system
identity.

### 3.2 Immutable occurrence bindings

Each occurrence binds immutably:

1. producer-generated occurrence identity and schema version;
2. exact local-principal artifact identity and canonical SHA-256;
3. verified principal-lineage prefix SHA-256 terminating at that artifact;
4. unique-current-tip status when capture began and when the declaration was accepted;
5. exact iTunes acquisition-authority artifact identity and canonical SHA-256;
6. exact embedded source-neutral acquisition identity and canonical SHA-256;
7. exact Evidence Snapshot identity and its existing canonical SHA-256;
8. exact complete Track Evidence Validation artifact canonical SHA-256;
9. each governed track identity selected for observation;
10. title and artist derived from the validated track, never the declaration;
11. authoritative duration copied from the validated track;
12. vocabulary identity, version, complete canonical content, and digest;
13. each original field/category observation without numeric input;
14. accepted-objective artifact identity and canonical SHA-256;
15. objective identity and exact statement;
16. Journey Plan identity, schema version, and canonical SHA-256;
17. literal context `Active Focus`, corresponding to `JourneyContext.ACTIVE_FOCUS`; and
18. the domain-separated occurrence digest.

Track Evidence Validation SHA-256 covers the complete existing
`serialize_track_evidence_validation` bytes. Acquisition SHA-256 covers the
complete existing `serialize_acquisition_result` bytes. Nothing is omitted or
normalized.

### 3.3 Occurrence digest

The occurrence digest is lower-case SHA-256 over:

```text
UTF8("pne.active-focus-candidate-readiness-occurrence/1.0")
+ NUL
+ canonical_occurrence_content_without_digest
```

`NUL` is byte `0x00`. Occurrence content uses
`pne.canonical-json.utf8-schema-order/1.0`. The domain, separator, included
fields, and ordering are immutable under version `1.0`.

### 3.4 Establishment and succession

A schema-valid object, content digest, or matching vocabulary does not prove a
capture occurred. Authority additionally requires exact recovery from
producer-controlled occurrence authority and verification of every binding.
The implementation may use bounded process-local authority; persistent or
restart-safe authority is not established.

Historical principal verification may verify recorded historical evidence but
cannot authorize new capture. New capture requires the unique current principal
tip and current-tip lineage-prefix verification at capture time.

A correction is a new immutable occurrence. Mutation, replacement in place, or
timestamp precedence is forbidden. Conflicting simultaneously applicable
observations fail closed as `conflicting` unless a separately governed
selection authority chooses one. Recency alone is not a selection rule.

### 3.5 Canonical readiness-authority definition

```json
{"schema_version":"1.0","definition_kind":"active_focus_candidate_readiness_authority","authority_definition_id":"pne.candidate-readiness-authority.active-focus","authority_definition_version":"1.0","vocabulary_id":"pne.active-focus.candidate-readiness","vocabulary_version":"1.0","vocabulary_sha256":"63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d","principal_scope":"PENNY_LOCAL_INSTALLATION_CURRENT_TIP_AT_CAPTURE","accepted_objective_schema":"AcceptedObjectiveArtifact/1.0","source_acquisition_authority_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.0","acquisition_schema":"SourceNeutralAcquisitionResult/1.0_UNCHANGED","track_validation_schema":"TrackEvidenceValidationArtifact/1.0_UNCHANGED","journey_plan_schema":"JourneyPlanArtifact/1.0","journey_context":"Active Focus","declaration_schema":"ActiveFocusCandidateReadinessDeclaration/1.0","wrapper_schema":"ActiveFocusCandidateReadinessAuthorityArtifact/1.0","producer":"pne.producer.active-focus-candidate-readiness/1.0","verifier":"pne.verifier.active-focus-candidate-readiness/1.0","occurrence_digest":"NUL_DOMAIN_SEPARATED_SHA256/1.0","cf1_outputs":["FamiliarityEvidenceArtifact/1.0","TrackFeatureEvidenceArtifact/1.0","ObjectiveContextEvidenceArtifact/1.0"],"categorical_observation_authority":true,"direct_numeric_capture_authorized":false,"context_fit_reusable":false,"missing_evidence_default_authorized":false,"persistent_restart_safe_authority_established":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Canonical SHA-256:
`02b62bc079c9ef912ba6e94ce343e2346e0486a9ba8f34e15a86c52f6c581e7d`.

Matching the definition identity without complete content and digest is not
readiness-occurrence authority.

## 4. Manual capture contract

The capture surface may display exact governed track identity, validated title
and artist, authoritative duration, field definitions, five exact category
choices per field, and the exact Active Focus objective and journey relevant to
context fit.

The declaration may supply only governed track identity plus zero or one exact
categorical selection per field. An omitted field remains missing; a track with
all six categories omitted is not measured.

Capture rejects numeric readiness values, replacement title/artist metadata,
media paths or bytes, referenced-media access, free-form synonyms, provider
feature metadata, inferred/defaulted values, and unvalidated, duplicate,
normalized, repaired, or near-match track identities.

Missing evidence remains absent or `unavailable` under existing CF-1 semantics.
No missing value becomes `0`, `0.50`, an inferred category, or another resolved
value.

## 5. Deterministic CF-1 projection

Verified readiness authority may project only into the existing
`FamiliarityEvidenceArtifact`, `TrackFeatureEvidenceArtifact`, and
`ObjectiveContextEvidenceArtifact`.

For every measured value, the wrapper retains and makes provable the occurrence
identity/digest, track and field identities, vocabulary identity/version/full
content/digest, original category, and exact projection.

`EvidenceObservation` is descriptive provenance, not independent occurrence
authority. The wrapper verifies every projected value against its category. A
caller-supplied CF-1 artifact or `UnitIntervalEvidence` value cannot establish
readiness authority through plausible provenance text.

Familiarity and Track Feature evidence bind the exact validated snapshot.
Objective Context Evidence additionally binds the exact accepted objective,
statement, Journey Plan, and `Active Focus` context. Its context input preserves
those canonical digests and the occurrence reference.

Tracks without applicable readiness records remain absent. Partially observed
tracks use existing `unavailable` states where an enclosing record is needed.
Candidate Formation applies its existing withholding behavior. The readiness
boundary performs no eligibility, scoring, ranking, formation, or recommendation.

Governed integration accepts verified readiness authority, derives CF-1
artifacts internally, then invokes existing Candidate Formation assembly. It
does not accept numeric CF-1 artifacts as substitutes. Lower-level schema
constructors remain structural/test tools and confer no governed readiness
authority.

## 6. Existing artist-rating projection

Taste continues to use the existing closed `Rating` vocabulary. No new taste
vocabulary is created. Persisted artist identity correspondence is exact;
trimming, case folding, normalization, aliasing, fuzzy matching, and repair are
forbidden.

| Persisted evidence | Local Taste state | Candidate Formation consequence |
| --- | --- | --- |
| `Love` | measured `Love` | preference `1.00` under the policy below |
| `Like` | measured `Like` | preference `0.75` under the policy below |
| `Meh` | measured `Meh` | preference `0.50` under the policy below |
| `No Thanks` | measured `No Thanks` | hard exclusion and withholding |
| `Pencil` | measured `Pencil` | hard exclusion and withholding |
| `Forbidden` | measured `Forbidden` | hard exclusion and withholding |
| `Unknown` | measured `Unknown` | unsupported-rating withholding |
| no exact row | unavailable | evidence-unavailable withholding |

Numeric preference is not readiness-vocabulary content and is not produced by
Local Taste Evidence. Candidate Formation alone applies this versioned policy:

```json
{"schema_version":"1.0","policy_id":"pne.candidate-formation.active-focus-readiness","policy_version":"1.0","preference_rule":{"rule_name":"pne.preference-map.local-artist-rating","rule_version":"1.0","mappings":[{"rating":"Like","value":0.75},{"rating":"Love","value":1.0},{"rating":"Meh","value":0.5}]},"hard_excluded_ratings":["No Thanks","Pencil","Forbidden"],"unsupported_ratings":["Unknown"]}
```

Canonical SHA-256:
`0628fc50befbcbf97db026c06f8ca5d71a5d7cc45e450b26fd1402591fee66d0`.

Mapping order is exact rating value in UTF-8 order. Changing a value, rating
set, rule identity, policy identity, or version requires a new policy version.

## 7. Bounded real construction proof

```text
governed iTunes acquisition
→ validated finite universe
→ governed accepted Active Focus objective
→ authoritative 30-minute Journey Plan
→ bounded manually measured subset
→ verified readiness authority
→ existing CF-1 evidence
→ Candidate Formation
→ CF-3 FormedCandidatePoolView
→ SequentialPlaylistConstructor
→ deterministic ordered playlist artifact
```

The proof demonstrates that unmeasured tracks are withheld, only formed
candidates reach construction, all three phases are represented, at least 1,800
authoritative seconds are represented, artist repetition remains satisfied,
and replay reproduces the same governed outputs.

It does not authorize referenced-media access, playback, writing an iTunes
playlist, acquisition changes, or construction-policy changes.

### 7.1 Bounded subset-selection principle

The implementation may calculate the smallest feasible subset only after a
genuine conforming multi-artist universe exists. Beginning with the smallest
output count capable of all three phases and minimum explicit slack, proposed
output count `N` and measured subset `S` require at least:

```text
N >= 3
|S| >= N + 1
sum(the N shortest authoritative durations in S) >= 1800 seconds
sum over exact artists of min(track_count_in_S, 2) >= N + 1
```

Tracks expected to form also require supported exact artist ratings and all six
observations. Familiarity must permit an opening anchor and the exact discovery
allocation. This is a minimization rule, not a fixed track count.

### 7.2 Current proof-input blocker

The 79,886-byte, 59-track Sisters of Mercy fixture remains valid acquisition
conformance evidence. All tracks share one exact artist. The constructor permits
two tracks per artist; the two longest total 1,272 seconds. The three longest
total 1,796 seconds, below the 1,800-second proof minimum.

It therefore cannot support the real proof. Policy must not be weakened. A
separately reviewed genuine conforming multi-artist iTunes export is required,
and no such fixture is authorized or added by this tranche.

## 8. Explicit non-claims and non-goals

This contract does not establish generalized semantic, mood, emotion, moment,
need, or accompaniment classification; automatic inference; embeddings or LLM
classification; audio/media/lyric inspection; provider features; generic
annotation/import; full-library annotation; reusable context fit; artist-name
normalization; acquisition or validation changes; Candidate Formation,
`TrackCandidate`, or CF-3 changes; scoring, selection, sequencing, or
construction-policy changes; playlist export; playback; readiness-boundary
preference/eligibility/recommendation/success claims; or persistent/restart-safe
occurrence authority.

Implementation conformance remains unestablished until a runtime producer,
verifier, category-only capture seam, deterministic projectors, governed
Candidate Formation integration, and bounded tests reproduce this exact
authority contract.

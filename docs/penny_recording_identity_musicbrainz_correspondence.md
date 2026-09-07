# Penny Recording Identity and MusicBrainz Correspondence Boundary v1

- **Status:** frozen documentation-only architectural authority boundary.
- **Boundary version:** `1.0` (v1).
- **Basis:** the completed MusicBrainz source-authority research and approved
  Penny Recording Identity and MusicBrainz Correspondence Boundary v0 design.
- **Production correspondence:** not established by this document.

## Authority and scope

This document freezes source-neutral semantic boundaries and prohibitions for
future catalog, local-library, and streaming-provider integrations. It does not
freeze a positive MusicBrainz/provider correspondence acceptance rule, an
acquisition profile, executable schemas, or an admission/recovery implementation.
The artifact names below remain prospective contracts. No canonical artifact
JSON, digest, or implementation-conformance authority is established here.

The following claims MUST remain separate:

| Layer | Permitted role |
|---|---|
| Catalog observation | What an identified source asserts about an entity at an observation/version |
| Penny recording handle/admission | An admitted source-neutral reference and immutable revision, not proof of correspondence |
| Correspondence evidence | Source-attributed assertions relevant to an explicitly scoped correspondence claim |
| Correspondence decision | Zero or one accepted target under an approved rule and complete required evidence |
| Musical selection | The recording selected for a particular playlist decision |
| Provider rendition/availability | A provider item and separately observed playability in its relevant context |
| Construction-duration authority | The duration evidence and projection authorized for a particular construction |

Catalog observations do not become accepted correspondence, selection,
availability, or readiness merely by crossing a schema boundary. An unresolved
correspondence must remain representable without forcing an MBID assignment.

## Recording identity handle

The semantic role of prospective `PennyRecordingIdentityArtifact/1.0` is an
immutable, source-neutral Penny recording handle/revision. Its ID MUST be opaque,
namespaced, and collision-resistant. It MUST NOT be derived from title, artist,
ISRC, MBID, duration, or provider item ID. The ID-generation and durable admission
mechanisms remain prospective.

Creating the handle establishes none of the following: MusicBrainz, provider, or
local-track correspondence; recording existence independently of referenced
evidence; provider availability; or readiness/taste evidence. Unresolved handles
may exist without accepted cross-source correspondence.

A future representation must preserve handle/admission provenance, exact
revision lineage, source observation/version references, and the decisions on
which accepted bindings depend. Title, ordered artist credits, disambiguation,
ISRC assertions, and relevant release/track/version/rendition constraints remain
source-attributed observations or scoped constraint references, not identity keys.
Unknown information must not be filled by inference. Constraints on a particular
selection must not silently become intrinsic properties of every use of a handle.

The model must support accepted MusicBrainz correspondence, unresolved catalog
identity, ambiguous candidates, conflicting identifiers, and provider-scoped or
local-scoped subjects without accepted MusicBrainz correspondence. Converging
external identifiers do not automatically consolidate Penny handles.

## Correspondence outcomes and lifecycle

The following outcome vocabulary is separate from existing `EvidenceState`:

| Outcome | Meaning |
|---|---|
| `ACCEPTED` | Exactly one correspondence target is accepted under an approved rule and complete required evidence set |
| `UNRESOLVED` | No target is accepted because required evidence is insufficient |
| `AMBIGUOUS` | Multiple plausible targets remain and available evidence cannot discriminate sufficiently |
| `CONFLICTING` | Material evidence makes incompatible assertions that remain unresolved |

Only `ACCEPTED` carries an accepted target. Candidate targets may be retained in
other outcomes but MUST NOT be exposed as accepted targets. Numerical confidence,
search scores, and ordering do not confer authority.

Lifecycle is independent: current decision at an explicit revision, historical
decision, and supersession through explicit predecessor/successor lineage.
`SUPERSEDED` is not a correspondence outcome. A historical accepted decision is
not the same thing as current acceptance. Corrections create new decision
revisions; they do not mutate historical decisions.

## MusicBrainz entity role

Ordinary MusicBrainz Recording is the preferred external recording-level catalog
anchor, not Penny's final canonical identity authority. Artist identifies a
contributor; Work is broader than playable recording identity; Track is a
release-medium occurrence; Release and Release Group provide edition/grouping
context. Recording is normally the appropriate performance/mix/edit-level anchor.

The researched distinctions that future integrations MUST preserve are:

| Case | Boundary |
|---|---|
| Remaster | May share a Recording; mastering/rendition requirements remain separate |
| Live performance | Distinct Recording |
| Remix | Distinct Recording |
| Alternate take | Distinct Recording |
| Rerecording | Distinct Recording |
| Structurally different edit | Distinct Recording |
| Clean/explicit audio edits | Distinct where editing changes the audio |
| Compilation/reissue Track | May reuse the same Recording |
| Cover | Distinct Recording even when linked to the same Work |

These distinctions concern the recorded audio relationship. Title suffixes such
as "live", "remaster", or "clean" are not sufficient identity evidence.
MetaBrainz's derived representative "canonical recording" mappings MUST NOT serve
as exact recording identity authority.

## Local and provider identity coexistence

Existing source-local identities such as
`itunes-windows-library:<library>/track:<persistent-id>` MUST be preserved.
They remain valid under their own governed source contracts regardless of
MusicBrainz correspondence. Future correspondence may relate a local source track
to a Penny handle and a MusicBrainz Recording observation, but MUST NOT replace or
rewrite local identity or historical acquisition/readiness evidence. No
MusicBrainz match must not invalidate that independent local evidence.

Provider-scoped identities receive the same treatment. All new correspondence
edges bind exact source observations/occurrences. Persistent identifiers alone
do not prove that a source item's audio or metadata remained unchanged. Accepted
correspondence does not automatically transfer evidence between occurrences,
recordings, renditions, users, or objective/journey contexts.

Accepted A-to-B and accepted B-to-C MUST NOT automatically establish A-to-C.
An approved composition rule must prove compatible claim scope and evidence.
Every cross-source identity edge is an independently governed claim.

## Duration authority

The following scopes MUST remain distinct:

| Scope | Meaning |
|---|---|
| `CATALOG_RECORDING` | A source's recording-level length observation |
| `LOCAL_SOURCE_TRACK` | Duration asserted for an exact local source track occurrence |
| `RELEASE_TRACK` | Duration asserted for an exact release/medium/track occurrence |
| `PROVIDER_RENDITION` | Duration asserted for an exact provider-item occurrence |
| `CONSTRUCTION_BINDING` | Duration evidence and projection authorized for an identified construction |

Every duration must retain its exact source/subject, value, unit, precision, and
any derivation. "Exact" means exact to the source assertion, not independently
measured acoustic truth. MusicBrainz Recording length, which may be an aggregate
of track lengths, is not automatically local, provider, release-track, or
construction duration. Duration agreement cannot prove identity.

A future nonlocal playlist MUST NOT claim construction duration merely from a
MusicBrainz recording-length observation. Its construction binding must identify
the selected subject/rendition, duration evidence, governing projection and rule
version, and construction occurrence. Provider fulfillment may require a new
binding; changed duration cannot silently preserve an incompatible previous
construction claim.

Existing iTunes millisecond-duration authority and integer-floor seconds
projection remain unchanged. No source-neutral or construction schema is changed
by this boundary.

## MBID history

Originally observed MBIDs and their historical observations MUST be retained.
Documented merges/redirects become new source observations. Prior Penny decisions
MUST NOT be rewritten merely because current MusicBrainz resolves a different
MBID. Any accepted successor binding requires its own governed decision.

Deletion or no-result does not authorize title/artist-based replacement. A
no-result observation does not by itself prove deletion; lookup failure is not
entity absence. Contradictory current state must remain visible in a new
assessment rather than erasing historical acceptance.

Historical replay is distinct from current authorization. Verifying an old
decision against old evidence does not grant current use when current-use
prerequisites are unmet. A generic HTTP redirect MUST NOT automatically be treated
as an entity merge. The valid source-specific merge-evidence representation and
current-use/freshness rules remain prospective.

## Search and identity separation

Discovery/search returns candidate catalog entities. Correspondence evaluation
determines zero or one accepted target under an approved rule. There MUST be no
automatic "top result equals identity" path.

Discovery artifacts MUST NOT contain an authoritative accepted target. Downstream
identity consumers must require verified correspondence decisions. Changing
MusicBrainz search score/order cannot itself change accepted correspondence.
Search implementation and acquisition are not frozen here.

## Correspondence evidence and contradictions

Permissible future evidence categories include exact source-supplied Recording
MBIDs, exact recording-level provider relationships, ISRC observations, exact
MusicBrainz Release/Medium/Track-to-Recording relations, structured artist credits,
exact title/disambiguation, scoped duration, release context, and explicit external
identifier relationships. This enumeration establishes no positive sufficiency
rule or first-match hierarchy.

Every evidence item MUST preserve source, entity scope, occurrence/version and
provenance. A release, work, artist, or Discogs relationship cannot silently be
promoted to recording equivalence. Evidence derived from the same upstream
assertion must not be falsely counted as independent corroboration. Known material
contradictory evidence MUST NOT be omitted from an acceptance bundle.

Artist/title/duration agreement cannot independently establish correspondence.
ISRC does not automatically establish one-to-one identity. A provider URL or
relationship does not automatically establish current playability.

Unresolved material contradictions MUST fail closed: no accepted target while the
contradiction remains unresolved. There is no "first source wins" rule. Examples:

| Evidence situation | Required handling |
|---|---|
| Multiple ISRCs resolving incompatibly | Preserve incompatible assertions; `CONFLICTING` |
| One ISRC with multiple plausible Recordings | `AMBIGUOUS` unless material assertions conflict, then `CONFLICTING` |
| Provider relationship and release-track evidence disagree | `CONFLICTING` |
| Matching text but incompatible performance/version evidence | `CONFLICTING` |
| Current state contradicts historical acceptance | New conflicting assessment; preserve the historical decision |

Exact positive acceptance sufficiency, required evidence closure, and materiality
rules remain prospective. No arbitrary confidence threshold or convenient matching
logic may fill those gaps.

## Provider rendition and availability

Prospective `ProviderRenditionObservationArtifact/1.0` is a source-scoped provider
item observation, not musical selection or automatic correspondence authority.
It may represent provider namespace, item ID/type, market/storefront, title/credit
observations, duration, ISRC assertions, provider-supplied explicit/version
indicators, observation occurrence/time/version, and a correspondence decision
reference. Missing indicators must not be inferred.

Availability is a separate observation with states `PLAYABLE`, `UNPLAYABLE`, and
`UNKNOWN`. It must bind relevant market/storefront, time, and user-entitlement
context. Missing evidence MUST NOT default to `PLAYABLE`. Identity correspondence
and availability status are independent.

A resolver may find zero, one, or multiple renditions of the selected recording.
Multiple accepted correspondences do not authorize arbitrary rendition choice or
waiver of mastering, version, or duration constraints. Provider-specific schemas,
access methods, and rendition-choice rules remain prospective.

## Substitution boundary

**Fulfillment failure does not alter musical selection.**

If the selected recording cannot be fulfilled, Penny MUST NOT silently use a live
version, remix, cover, another clean/explicit edit, or representative "canonical"
recording. Substitution requires a separate future governed selection/substitution
decision. This document does not freeze that policy. Unresolved rendition
constraints are not permission to substitute.

## Commercial field disposition

The initial commercially eligible categories are closed to those below, subject
to later exact acquisition-profile and retention-rights review. Eligibility here
is not authorization to acquire or promote a field into production authority.

- Recording MBID, title, disambiguation, and audio/video indicator.
- Ordered artist credit, credited names/join phrases, and artist MBIDs.
- ISRC observations and scoped recording length.
- Release/Track/Release Group identifiers; medium/track positions.
- Track title, credit, and length.
- Necessary release/edition metadata, whose exact fields must be enumerated later.
- Explicitly enumerated core relationships and typed external identifiers/URLs.
- Genre vocabulary entity names/MBIDs/aliases only if separately authorized later.

Unknown fields and relationship types gain no authority. Disambiguation is not
annotation. A typed URL does not authorize fetching or using its target content.

Exclude from the initial commercial Penny production profile: genre assignments,
tags, tag counts, ratings, annotations, the NC-SA cover-art metadata archive,
actual artwork, edit history, user data, and non-core derived statistics.
Representative canonical-recording mappings are excluded from exact identity
authority because of their semantics, not because all such mappings are NC data.

There is no "all MusicBrainz JSON is allowed" rule. Filtering restricted fields
after durable capture does not retroactively make an unrestricted response
core-only. Future production acquisition must ensure retained source content is
authorized or obtain appropriate commercial rights. Filtered bytes must not be
represented as exact original response bytes. The exact API profile remains
prospective.

## Genre separation

- iTunes Genre evidence remains exact receipt-scoped `PRESENT`/`ABSENT` source
  observation under its existing contract.
- A MusicBrainz Genre entity is an external vocabulary observation.
- A MusicBrainz genre assignment is restricted/community-derived association,
  excluded from the initial commercial profile.

This boundary authorizes no automatic normalization, synonym equivalence,
artist-to-recording inheritance, genre eligibility, or genre-based readiness
inference.

## Admission and verified authority

Schema-valid objects and deterministic digests alone do not create authority.
Correspondence decisions require an approved evaluator/authority path. Verified
decision authority must bind exact evidence and rule version. Deserializing a
valid-looking object MUST NOT automatically restore production authority.

Trusted durable admission/recovery is an unresolved prerequisite before production
recording-identity implementation. This boundary does not freeze its mechanism
and MUST NOT be read as adopting process-local readiness occurrence authority as
the long-term catalog authority model.

## Prospective artifact contracts

Only semantic roles and boundaries are established here. These names do not imply
implemented schemas or separately frozen executable artifact contracts:

| Prospective name | Role |
|---|---|
| `PennyRecordingIdentityArtifact/1.0` | Source-neutral immutable handle/admission revision; no automatic correspondence |
| `MusicBrainzRecordingObservationArtifact/1.0` | Exact source-attributed Recording observation |
| `RecordingCorrespondenceEvidenceArtifact/1.0` | Claim-scoped supporting and opposing evidence bundle |
| `RecordingCorrespondenceDecisionArtifact/1.0` | Outcome under an approved rule, exact inputs and revision lineage |
| `ProviderRenditionObservationArtifact/1.0` | Provider-item observation with rendition scope |
| `ProviderAvailabilityObservationArtifact/1.0` | Separate time/context-bound playability observation |
| `ConstructionDurationBindingArtifact/1.0` | Authorized construction-specific duration evidence/projection |

Observations and decisions are immutable. New evidence or corrections create new
occurrences/revisions with explicit lineage where applicable. Future structural
schema changes and semantic rule changes require explicitly versioned successors;
they must not silently reinterpret historical evidence. Canonical serialization,
digests, concrete fields, and executable conformance remain for separate freezes.

## Required later proof corpus

The following logical case types are required; no real records or fixtures are
identified or acquired here. `ACCEPTED` below is an expected outcome only when a
later approved positive rule and its required verified evidence are present.
Otherwise acceptance remains withheld. Distinct valid anchors do not establish
correspondence between those anchors.

| # | Required case | Expected outcome class and fail-closed principle |
|---|---|---|
| 1 | Ordinary studio recording | Conditional accepted catalog anchor; no implied local/provider match |
| 2 | Compilation reuse | Conditional shared Recording anchor; do not transfer track duration |
| 3 | Remaster | Conditional shared Recording; unresolved mastering constraint stays unresolved |
| 4 | Live version | Distinct anchors; incompatible studio equivalence is conflicting |
| 5 | Remix | Distinct anchors; text/length agreement cannot collapse them |
| 6 | Alternate take | Distinct anchors; missing take-specific evidence yields unresolved correspondence |
| 7 | Rerecording | Distinct anchors; same artist/work does not prove equivalence |
| 8 | Radio/structural edit | Distinct anchor; duration alone cannot identify the edit |
| 9 | Clean/explicit differing audio | Distinct edited anchors; a badge alone leaves correspondence unresolved |
| 10 | Cover of same Work | Distinct Recording; Work equality cannot authorize substitution |
| 11 | Provider item with one ISRC | No automatic acceptance; unresolved until an approved sufficient rule is met |
| 12 | Ambiguous/multiple ISRCs | Ambiguous or conflicting according to evidence; no arbitrary target choice |
| 13 | MBID merge/redirect | Historical original retained; successor evaluated with valid merge evidence |
| 14 | Deleted/unresolved MBID | Current correspondence unresolved without valid replacement lineage |
| 15 | No MusicBrainz match | MB correspondence unresolved; independent local/provider identity preserved |
| 16 | Multiple search candidates | Ambiguous; score/order cannot resolve identity |
| 17 | Conflicting identifiers | Conflicting; correction needs new evidence and decision revision |
| 18 | Same title/artist/duration, distinct recording identity | Distinct anchors; incompatible equivalence fails closed |

Later proofs must include boundary rejection of forged objects, substituted
evidence, omitted material contradictions, wrong-scope relationships and invalid
history/duration bindings. Synthetic mechanics tests must remain explicitly
non-production and must not be reported as acquired real-world correspondence
evidence.

## Explicit non-claims

- A Penny ID does not independently prove recording existence.
- Accepted MusicBrainz correspondence does not prove provider availability.
- An MBID does not prove exact mastering/rendition.
- ISRC is not guaranteed one-to-one.
- Title is not unique identity; artist-credit similarity is not identity.
- Duration agreement is not identity; MusicBrainz length is not fulfillment duration.
- A search result is not correspondence authority.
- MusicBrainz absence does not prove recording nonexistence.
- Correspondence does not transfer taste/readiness automatically.
- Catalog identity does not establish energy, mood, groove, familiarity, lyrical
  distraction, context fit, or preference.
- Correspondence edges do not compose automatically.

## Deliberate production blockers

The following remain unresolved prerequisites, not permissions to invent defaults:

1. Exact MusicBrainz API/response field profile and commercial retention rights.
2. First positive MusicBrainz correspondence acceptance rule.
3. Exact merge/redirect evidence representation.
4. Real proof-corpus examples.
5. Trusted durable admission/recovery authority.
6. Nonlocal construction-duration projection/binding.

These block production correspondence, not this architectural boundary freeze.
No production MusicBrainz correspondence is currently established by this tranche.

## Protected contracts and non-goals

This boundary does not change existing Source Receipt definitions, source-neutral
acquisition schemas, iTunes acquisition/mapping, source-local identity, readiness,
Candidate Formation, Track Evidence, or construction behavior. Existing local
contracts keep their exact jurisdiction. Relevant existing documents:

- [Source Receipt authority](source_receipt_authority.md).
- [iTunes Windows XML acquisition](penny_local_itunes_windows_xml_acquisition.md).
- [iTunes source-relative Genre evidence](penny_local_itunes_windows_xml_genre_evidence.md).
- [Active Focus Candidate-Readiness](active_focus_candidate_readiness_vocabulary.md).

Non-goals are API access, database downloads, fuzzy matching, ISRC auto-matching,
catalog persistence implementation, provider adapters/availability implementation,
genre normalization or assignments, lyrics ingestion, source-local identity
replacement, and production correspondence claims. No runtime, tests, schemas,
configuration, database, research-store, CLI, Workbench, or orchestration behavior
is changed.

## Research references

The completed research and v0 design are the approved basis. These primary-source
references explain the researched distinctions; live upstream changes do not
silently amend this frozen boundary:

- [MusicBrainz Recording](https://musicbrainz.org/doc/Recording).
- [Recording style](https://musicbrainz.org/doc/Style/Recording).
- [MusicBrainz identifiers](https://musicbrainz.org/doc/MusicBrainz_Identifier).
- [Entity removal and merging](https://musicbrainz.org/doc/How_to_Remove_Entities).
- [Canonical MusicBrainz data](https://musicbrainz.org/doc/Canonical_MusicBrainz_data).
- [Core and supplementary data](https://musicbrainz.org/doc/MusicBrainz_Database).
- [Data licenses](https://musicbrainz.org/doc/About/Data_License).
- [JSON dump field licenses](https://musicbrainz.org/doc/Development/JSON_Data_Dumps).

The research basis was inspected on 2026-09-07. This freeze performs no new
catalog acquisition and makes no blanket current-service or retention-rights grant.

# Candidate Formation Integration Contract

- **Status:** CF-3 documentation contract accepted; implementation not started
- **Decision scope:** Authenticated integration from Candidate Formation into
  scoring, selection, and construction
- **Applies to:** Production selector and constructor entry points

## Question answered

CF-3 answers one question:

> How does the existing scoring, selection, and construction pipeline consume
> only the formed-candidate output from a validated
> `CandidateFormationArtifact`?

The sole authenticated production boundary is a `FormedCandidatePoolView`:

```text
validated CandidateFormationArtifact
        ↓ deterministic projection
FormedCandidatePoolView
        ↓ formed candidates only
CandidateSelector
        ↓ fresh state-relative ranking
SequentialPlaylistConstructor
```

The view is not a second formation artifact and makes no new eligibility,
preference, evidence, or recommendation decision.

## FormedCandidatePoolView

`FormedCandidatePoolView` is an immutable, versioned projection derivable only
from a successfully validated `CandidateFormationArtifact`. Production callers
may not construct or populate it from raw `TrackCandidate` values, source
evidence, provider records, or a mixture of an artifact and caller-supplied
candidates.

The derivation must:

- consume the complete validated parent artifact;
- project every and only `artifact.formed` entry;
- expose no withheld entry, withholding reason, or withheld track payload;
- retain each complete `FormedCandidateEntry`, including field provenance;
- preserve the exact formed-entry order, ordinal, `TrackCandidate` value, and
  string identity already validated by CF-2;
- perform no sorting, normalization, alias resolution, evidence join,
  preference mapping, eligibility evaluation, or numeric derivation; and
- leave the parent artifact and caller-owned values unchanged.

An empty formed partition produces a valid empty view. It does not authorize a
fallback to withheld or caller-supplied candidates.

## Exact parent identity

The view identifies its exact parent with the SHA-256 digest of the canonical
Candidate Formation artifact bytes produced by the existing CF-2 canonical
serializer. The digest input is the complete canonical byte sequence without
preprocessing, reserialization, newline insertion, encoding conversion, or
field omission.

The view also carries the parent's exact:

- Candidate Formation `request_id`;
- schema version;
- objective ID and statement;
- accepted Objective Safety artifact ID;
- journey ID;
- policy ID and version; and
- preference-rule name and version.

The canonical digest identifies the exact parent artifact; `request_id` alone
does not. Equal validated parent artifacts yield equal views and identical
canonical view bytes. Any change to a formed or withheld entry, provenance,
policy identity, rule identity, correspondence field, or other serialized
parent content changes the parent digest even though withheld content remains
inaccessible through the view.

## Exact correspondence

Before selection or construction, production integration must fail closed
unless all applicable identities correspond exactly. Exact means byte-for-byte
string equality with no trimming, case folding, punctuation folding, Unicode
normalization, alias resolution, fuzzy repair, or provider lookup.

The required correspondence is:

- the Journey Plan artifact's `journey_id`, objective ID, objective statement,
  and accepted Objective Safety artifact ID equal the values traced through the
  formed-pool parent;
- the view's formation policy ID and version equal its parent's recorded values;
- the view's preference-rule name and version equal its parent's recorded
  values;
- every exposed entry exactly equals the corresponding parent formed entry,
  including ordinal, candidate value, and field provenance; and
- every candidate identity used by selector or constructor exists exactly once
  in the view.

Neither selector nor constructor may rejoin CF-1 evidence or recreate a
preference mapping to establish correspondence.

## Remaining-candidate semantics

`remaining_track_ids` is a set-like membership filter over the stable formed
pool. Its caller-supplied order has no semantic meaning. The selector validates
that the IDs are unique and that every ID exactly exists in the view, then
resolves them in the canonical formed-pool order.

Therefore, permutations of the same valid remaining IDs produce equal ranking
requests and byte-identical ranking results. Duplicate IDs and unknown or
near-match IDs fail closed. The selector never accepts replacement
`TrackCandidate` values alongside the IDs.

Canonical pool order is only the deterministic input traversal order. Final
ranking order remains governed by scoring and the selector's documented stable
tie-break rules.

## Ranking result and formation trace

Formation trace is carried once on an immutable ranking-result envelope, not
repeated on each `RankedCandidate`. The envelope contains:

- the parent-artifact SHA-256 digest and exact formation identity projection;
- the canonical resolved remaining-track IDs;
- the ordered `RankedCandidate` results; and
- the ranking context required by the selection contract.

This avoids redundant trace data, prevents trace fields from disagreeing across
ranked entries, and keeps `RankedCandidate` focused on one ephemeral,
state-relative scoring result. A ranked candidate has authenticated production
meaning only inside its envelope. Construction must retain the same trace once
on its result and must not detach ranked entries into a durable standing queue.

## Production API break

CF-3 intentionally removes raw-candidate production inputs:

- `CandidateSelector.select` will accept the authenticated formed-pool view and
  remaining exact track IDs, not `Iterable[TrackCandidate]`;
- `SequentialPlaylistConstructor.construct` will accept the authenticated
  formed-pool view, not a raw candidate pool; and
- neither API may provide a transitional production overload, optional
  `candidates` argument, adapter, union type, or fallback that accepts arbitrary
  candidate tuples.

The constructor owns the stable view for the complete run and supplies only
remaining IDs when requesting each fresh ranking. This preserves the existing
rule that the stable candidate pool outlives each ephemeral ranking.

## Resumed ConstructionState

A resumed state is valid only when it belongs to the same exact formation and
journey context. Validation must establish that:

- its formation trace equals the view's full trace, including parent digest;
- its journey identity equals the corresponding Journey Plan artifact;
- every placed candidate and `previous_track` exists in the view;
- each stored candidate equals the view's candidate in every typed field, not
  merely by `track_id`;
- used-track IDs equal the exact identities implied by placed tracks;
- placed-track provenance remains reachable through the matching formed entry;
  and
- no withheld, unknown, duplicate, normalized, or caller-created candidate has
  entered the state.

Failure invalidates the resumed request. It must not be repaired by replacing,
dropping, or normalizing state values.

## Scoring boundary

`TrackScorer` remains a lower-level pure primitive. Its isolated unit tests may
construct synthetic `TrackCandidate` values to verify scoring mathematics.
That testing allowance is not a production integration path and does not permit
selector or constructor production APIs to accept synthetic or raw candidates.

Scoring does not inspect withheld entries, provenance sources, formation rules,
or source evidence. It receives candidate values authenticated by the enclosing
formed-pool and ranking boundaries.

## Explicit prohibitions

CF-3 must not:

- change CF-2 formation, withholding, hard-eligibility, or reason semantics;
- expose or score withheld entries;
- treat withholding as a low score or construction rejection;
- bypass or discard `FormedCandidateEntry` provenance;
- reconstruct preference values or other candidate fields;
- rejoin source evidence;
- normalize or repair identity;
- mix an artifact or view with arbitrary candidate values;
- allow resumed state to cross artifact, journey, objective, policy, or rule
  boundaries; or
- change evaluation or refinement.

## Documentation-phase acceptance

This contract authorizes documentation only. Integration schemas, derivation
services, selector changes, constructor changes, migrations, and production
tests require a separately approved implementation phase.

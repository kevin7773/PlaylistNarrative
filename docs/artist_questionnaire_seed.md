# Deterministic Artist Questionnaire Seed

- **Status:** Initial implementation contract
- **Purpose:** Produce a starting artist list for manual rating
- **Artifact type:** Elicitation and testing, not recommendation

## Normative invariant

The artifact must never contain an artist whose inclusion cannot be reproduced
solely from the serialized input and documented approved local rules.

Schema `1.0` approves no local derivation rules. The generator therefore emits
only artist names that occur verbatim in supplied seed evidence.

## Closed-world boundary

```text
Serialized seed evidence
        +
Approved fixed local rules (none in schema 1.0)
        ↓
Deterministic artist questionnaire seed
```

The generator performs deterministic interpretation of a closed evidence set.
It does not perform catalog expansion, related-artist inference, model
association, provider lookup, learned affinity, alias resolution, case folding,
or creative completion.

Exact duplicate artist names are consolidated. Case variants and other
near-matches remain distinct because treating them as aliases would introduce
an unapproved identity rule.

### Deduplication identity

Two artist entries are duplicates only when their supplied `artist_name`
strings are exactly equal in the serialized representation: the same Unicode
code-point sequence with the same whitespace, punctuation, and capitalization.
Schema `1.0` performs no trimming, Unicode normalization, punctuation folding,
case folding, or alternate-spelling resolution.

Rather than preprocess input, validation rejects surrounding whitespace.
Different valid strings remain different entries even when a person might
interpret them as the same artist. Any future preprocessing or alias rule must
be introduced as an approved local transformation and must not silently change
schema `1.0`.

## Inputs

The immutable request contains:

- schema version;
- a fixed objective identifier and statement;
- immutable seed-evidence records with unique evidence IDs;
- an explicitly empty collection of approved local rules.

Each evidence record supplies an artist name, source, and rationale. Text fields
reject surrounding whitespace so normalization cannot silently change identity.

## Output and ordering

The immutable output records:

- its schema version, artifact kind, and elicitation-only purpose;
- the unchanged objective;
- the approved rule set;
- the ordering rule;
- ordered questionnaire entries;
- an explicit false recommendation-claims flag.

Entries are ordered by the UTF-8 bytes of the verbatim artist name. Evidence for
an exact duplicate is ordered by evidence ID using the same rule. Every entry
records all source evidence, an explicit-seed inclusion basis, an unset rating,
and an explanation limited to the fact that supplied evidence named the artist.

Canonical serialization uses schema field order, UTF-8, no optional whitespace,
and no environment-dependent values. Equivalent evidence collections therefore
produce equal objects and byte-for-byte identical JSON regardless of input
ordering.

## Interpretation boundary

Presence in this artifact means only that the artist is available for manual
rating. It does not claim:

- that the user likes or dislikes the artist;
- that the artist is recommended;
- that the artist belongs in a playlist;
- that any track by the artist is a valid `TrackCandidate`.

The governing principle is:

> Artist identity may define where to search; track-level evidence determines
> what belongs.

## Layer isolation

This capability belongs to `elicitation`. It does not call or modify
`TrackScorer`, `CandidateSelector`, `SequentialPlaylistConstructor`, or
`PlaylistJourneyEvaluator`.

It is not a Phase 6 refinement result. The accepted Phase 6A contract remains
evaluation-driven and authoritative. Any future connection between elicitation
and refinement requires a separate explicit contract.

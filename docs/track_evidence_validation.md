# Deterministic Track Evidence Validation

- **Status:** Schema 1.0 implementation contract
- **Purpose:** Partition source-neutral serialized track evidence into validated
  and rejected records
- **Artifact type:** Evidence validation, not discovery allocation, Candidate
  Formation, scoring, selection, or construction

## Normative meaning

Presence in the validated partition means only:

> This track has sufficient serialized evidence to enter a candidate-formation
> input pool.

It does not mean that a `TrackCandidate` exists or that the track belongs in a
playlist.

Artist scope limits inspection; it never establishes preference, eligibility,
suitability, familiarity, recommendation, or playlist membership.

## Request and snapshot-level failure

The immutable request contains:

- schema version `1.0`;
- a sufficient Objective Assessment;
- an Artist Questionnaire Seed with an exactly corresponding objective;
- an Evidence Snapshot in the `track` domain;
- an empty approved-local-rules tuple.

Objective ID and statement must match exactly between the Objective Assessment
and Artist Questionnaire. A clarification-required assessment, correspondence
failure, nonempty local rules, invalid snapshot envelope, or duplicate record ID
rejects the complete request. These are snapshot-level failures because a stable
validation context or identifiable input partition does not exist.

The Artist Questionnaire establishes exact artist inspection strings only. It
does not provide preference or track facts.

## Record contract

Each identifiable snapshot record is inspected independently. Its payload must
be a JSON object containing exactly:

- `track_id`: explicit nonblank string without surrounding whitespace;
- `title`: explicit nonblank string without surrounding whitespace;
- `artist_name`: exact artist-scope string without normalization;
- `duration_seconds`: strict positive integer;
- `provenance`: object containing exactly three explicit nonblank strings:
  `source_type`, `source_reference`, and `rationale`.

The validator treats `source_type` as descriptive data. Known, unknown, future,
provider, local, acoustic, manual, and imported sources follow identical rules.

Schema 1.0 performs no trimming, case folding, Unicode normalization, alias
resolution, identity reconciliation, metadata lookup, repair, calculation, or
inference.

## Deterministic partitioning

Every identifiable input record appears exactly once in either
`validated_records` or `rejected_records`. The artifact enforces:

```text
input_record_count
    = validated_record_count
    + rejected_record_count
```

The validated and rejected record-ID sets are disjoint, and their union equals
the exact snapshot record-ID set. Both partitions use UTF-8 record-ID byte order.
Validated ordinals are contiguous and one-based.

An empty snapshot produces two empty partitions and a zero-count summary.

## Lossless rejection

Every rejected entry retains its exact `payload_json` string, including original
whitespace and line endings. Validation never replaces the rejected payload with
a parsed, normalized, repaired, or reserialized substitute.

Malformed JSON, duplicate JSON object keys, non-object JSON, missing facts,
invalid facts, unsupported fields, invalid provenance, and exact artist-scope
failures are record-level rejections. They do not suppress valid neighboring
records.

## Duplicate track identity

Every record containing the same valid exact `track_id` participates in the
duplicate. All participants receive `DUPLICATE_TRACK_ID` and are rejected,
including otherwise complete records. No first record wins, identical duplicates
are not consolidated, and input order has no effect.

## Fixed issue precedence

Issues use this schema 1.0 precedence:

1. `EVIDENCE_RECORD_INVALID_JSON`
2. `EVIDENCE_RECORD_DUPLICATE_KEY`
3. `EVIDENCE_RECORD_NOT_OBJECT`
4. `EVIDENCE_RECORD_EXTRA_FIELD`
5. `TRACK_ID_MISSING`
6. `TRACK_ID_INVALID`
7. `TRACK_TITLE_MISSING`
8. `TRACK_TITLE_INVALID`
9. `TRACK_ARTIST_MISSING`
10. `TRACK_ARTIST_INVALID`
11. `TRACK_ARTIST_OUT_OF_SCOPE`
12. `TRACK_DURATION_MISSING`
13. `TRACK_DURATION_INVALID`
14. `EVIDENCE_PROVENANCE_MISSING`
15. `EVIDENCE_PROVENANCE_INVALID`
16. `DUPLICATE_TRACK_ID`

Repeated issue codes use UTF-8 field-path byte order. Issue explanations are
fixed by code. Output validation rejects reordered, duplicate, or altered issue
contracts.

## Output

The immutable `TrackEvidenceValidationArtifact` records:

- version, artifact kind, snapshot and objective identity;
- exact UTF-8-ordered artist inspection scope;
- exact input record IDs;
- validated and rejected partitions;
- partition counts;
- ordering rules;
- explicit false flags for preference, eligibility, suitability, familiarity,
  recommendation, playlist membership, scoring, selection, and construction.

Validated entries preserve their source payload and provenance but contain only
catalog-level identity, title, artist, and duration facts. They do not contain
preference, familiarity, context fit, energy, groove, instrumentalness, lyrical
distraction, roles, scores, ranks, or placement state.

Canonical serialization uses schema field order, UTF-8, compact JSON separators,
and no environment-dependent values.

## Isolation and non-goals

Track Evidence Validation performs no evidence acquisition, provider access,
database access, Candidate Formation, taste eligibility, artist elicitation,
scoring, ranking, candidate selection, construction, evaluation, refinement,
persistence, caching, learning, or playlist generation.

The package does not import provider APIs, sequencing services, evaluation, or
refinement. A future Candidate Formation contract must explicitly join validated
catalog evidence with independently validated local taste, familiarity, context,
and eligibility evidence before constructing `TrackCandidate` objects.

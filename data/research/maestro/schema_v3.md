# Maestro research-store schema version 3

Schema version 3 preserves a strict subject boundary:

- `Experiment` is a historical generation event.
- `PersistedPlaylistArtifact` is a presently observed persisted playlist.
- `PersistedArtifactExperimentLink` is evidence of a relationship only.

No field, placement, completeness conclusion, count, persistence state, or
evidence source propagates between the experiment and artifact domains.

## Persisted artifacts

Artifacts retain raw current title, description, visibility, displayed count,
displayed duration, persistence state, segments, and placements. They reuse the
`COMPLETE`, `PARTIAL`, and `NOT_OBSERVED` tracklist-completeness vocabulary, but
the subject is always the artifact rather than a historical generated output.

Artifact `COMPLETE` requires an established start and end, no unknown gaps,
contiguous absolute positions beginning at 1, and agreement between displayed
count and observed placements. An end can be established through a
provenance-qualified count reconciliation; that assessment does not claim a
visible bottom-of-list marker.

Current primary evidence uses evidence standard `CURRENT_PRIMARY_EVIDENCE`.
Locally accessible bytes require a verified SHA-256 checksum.

## Correlation

Schema version 3 supports only `USER_ATTESTED_CORRELATION`. It records that the
user associates an artifact with an experiment. It does not establish content
identity, playlist equivalence, unchanged contents, original generation
metadata, or historical saved status. `unchanged_since_generation` defaults to
`UNKNOWN` and requires independent relationship-owned evidence to assert any
other value.

Correlation evidence is owned by and targets the relationship record. It does
not support either endpoint.

## Canonical tracks

A shared canonical `track_id` correlates track identity only. It never transfers
placement, ordering, raw display strings, version text, or provenance between
artifact and experiment placements. Truncated current display titles remain
raw and use a null canonical track link unless another admissible source
establishes the complete identity.

## Migration

Migration from version 2 creates no artifacts or correlations. Existing
experiment records and evidence IDs are retained. The REC-CHAT-007 normalized
experiment representation is unchanged.

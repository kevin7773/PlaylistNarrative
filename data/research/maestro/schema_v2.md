# Maestro research-store schema version 2

Schema version 2 remains isolated from every production playlist-generation
boundary. Its purpose is faithful evidence retention, including successful
generations whose surviving evidence is incomplete.

## Time semantics

- `recorded_at` is the system-managed research-store insertion time.
- `generated_at` is the historical generation time and is nullable.
- The store never substitutes `recorded_at`, screenshot clock time, or
  conversation activity time for an unknown `generated_at`.

## Tracklist evidence

`tracklist_completeness` is `COMPLETE`, `PARTIAL`, or `NOT_OBSERVED`.
`NOT_OBSERVED` describes a supported successful generation for which no
playlist placements survive; it is not a failure and does not mean an empty
playlist.

Evidence segments preserve screenshot-supported continuity. Each segment has an
experiment-wide ordinal, a relationship to its predecessor (`FIRST`,
`CONTIGUOUS`, or `GAP_UNKNOWN_SIZE`), and tri-state `YES`, `NO`, or `UNKNOWN`
knowledge of whether it captures the playlist start and end.

Placements preserve experiment-wide observed order, segment-relative order, and
nullable absolute playlist position independently. Raw readable display fields
do not require a canonical track link. A canonical track is created only when
both title and artist identity are sufficiently established.

`COMPLETE` requires established start and end boundaries, no unknown gaps,
contiguous absolute positions beginning at 1, and equality between generated
track count and observed placements. Any surviving but incomplete track
evidence is `PARTIAL`.

## Provenance

Recovered historical fields are supported by structured evidence sources and
field-level evidence links. Provenance classifications are
`DIRECT_OBSERVATION`, `HUMAN_ASSESSMENT`, `DERIVED_QUERY_RESULT`, and
`MIGRATION_DERIVATION`. The last classification is reserved for facts created
by deterministic schema migration.

Evidence sources can reference external material or local bytes. A local path
requires a SHA-256 checksum, which is verified during ingestion. Raw evidence
files are not transformed by the importer.

Generation failures and refusals remain independent records with no experiment
or playlist placement. Their prompt, message, source, and historical time may
be null when the recovered evidence does not establish them.

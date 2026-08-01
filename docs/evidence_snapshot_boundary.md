# Evidence Snapshot Boundary

- **Status:** Accepted boundary for schema 1.0 track evidence validation
- **Purpose:** Separate external evidence acquisition from deterministic evidence
  processing
- **Implementation status:** Snapshot contract only; no acquisition adapters

## Boundary

Evidence may eventually originate from provider metadata, local metadata,
acoustic analysis, manual evidence, imported evidence, or another documented
source. Acquisition owns access to those sources and must finish before the
deterministic core begins.

```text
External evidence sources
          ↓
Evidence acquisition and source-specific adapters
          ↓
Immutable EvidenceSnapshot
          ↓
Deterministic TrackEvidenceValidator
```

The validator receives only a snapshot. It has no provider interface and does
not know how, when, or from where the snapshot was acquired. Source type and
source reference are preserved as provenance data and never control validation
behavior.

## Schema 1.0 snapshot

An `EvidenceSnapshot` contains:

- explicit schema version `1.0`;
- an exact, nonblank snapshot ID;
- evidence domain `track`;
- a finite immutable tuple of identifiable records.

Each envelope record contains an exact, unique `record_id` and a
`payload_json` string. The string is the lossless serialized evidence boundary.
It may be valid, incomplete, malformed, or unsupported track evidence; those
conditions are record-level validation results rather than snapshot-envelope
failures.

The snapshot schema rejects an unsupported version, malformed envelope,
unsupported domain, missing or invalid record ID, duplicate record ID, or extra
envelope field. Those failures prevent deterministic identification and
partitioning of all records, so the request fails closed.

## Replay invariant

For identical request artifacts and validation policy, validation produces an
equal artifact and byte-identical canonical JSON without access to any external
source.

Snapshot record order is not meaningful. Record IDs establish deterministic
partition order. No current time, environment state, provider availability,
filesystem state, database state, locale, or randomness may influence the
result.

## Acquisition responsibilities

A future acquisition subsystem may call external sources and serialize their
responses. It must own:

- authentication and provider-specific APIs;
- source-specific parsing;
- acquisition failures and retries;
- source identity and source references;
- disclosure of transformations performed before serialization;
- snapshot creation and storage.

Acquisition must not be added to `track_evidence`. No provider SDK, network
client, repository, callback, lazy loader, or live source handle may cross the
snapshot boundary.

# Evidence Snapshot Boundary

- **Status:** Accepted boundary for schema 1.0 track evidence validation
- **Purpose:** Separate external evidence acquisition from deterministic evidence
  processing
- **Implementation status:** Snapshot contract and source-neutral acquisition
  envelope implemented; no acquisition adapters

## Boundary

Evidence may eventually originate from provider metadata, local metadata,
acoustic analysis, manual evidence, imported evidence, or another documented
source. Acquisition owns access to those sources and must finish before the
deterministic core begins.

```text
External evidence sources
          ↓
Future source-specific adapter
          ↓
SourceNeutralAcquisitionResult
  ├── exact source receipt and digest
  ├── adapter identity and version
  ├── frozen capability declaration
  ├── immutable EvidenceSnapshot
  └── corresponding CandidateIdentityMetadataArtifact
          ↓
Deterministic TrackEvidenceValidator
```

The source-neutral envelope is implemented in `evidence_acquisition`. It is an
authority and replay contract, not an adapter. No provider-specific acquisition
implementation exists in the repository.

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

## Metadata authority

An acquisition capability declaration explicitly states whether the exact
adapter version can authoritatively supply catalog identity, release/version
identity, and displayed Explicit state. Capability is not inferred from whether
one response contains a value.

- A supported field may be `measured`, `unavailable`, or `conflicting`.
- An unsupported field must remain `unsupported`.
- A measured value requires exact source-receipt observations.
- Missing displayed Explicit metadata never means `false` or clean.
- Title suffixes never establish release/version identity.
- Similar title and artist text never establishes catalog equivalence.

The envelope binds its metadata artifact to the exact snapshot ID and canonical
snapshot SHA-256. Metadata observations must carry the envelope's exact source
type and reference.

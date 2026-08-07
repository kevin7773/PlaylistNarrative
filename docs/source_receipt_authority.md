# Source Receipt Authority — Provisional Contract

## Status

This document is a provisional contract for a receipt-edge authority. It was
identified while pressure-testing the prerequisites for Prompt Evidence
Preservation.

The contract is not an implementation and does not create executable
jurisdiction. No acquisition adapter, governed source-receipt policy, or source
receipt artifact currently exists in production. Publication of this document
would record a contract for review; it would not authorize receipt processing.

This boundary is deliberately independent of authorship, interaction identity,
entrusted-case membership, semantic interpretation, and downstream access.

## Purpose

Source Receipt Authority answers exactly one question:

> What exact material and associated metadata did one governed acquisition
> interface observe at one explicitly identified capture point during one
> receipt event?

It records receipt at an acquisition edge before deterministic interpretation
begins. It does not decide that the received material is a prompt, belongs to a
person, belongs to an entrusted case, or may be inspected by another boundary.

## Positive claim

A valid `SourceReceiptArtifact` may make only this positive claim:

> At capture point P, acquisition interface I at version V observed this
> receipt event R comprising these exact bounded items. For each item, the
> artifact records either the exact finite byte sequence exposed at that point
> or an explicitly permitted no-content capture state, preserves permitted
> interface-local order and complete capture accounting, and records
> interface-attested metadata and transport assertions separately.

The word `exact` applies only to the bounded items and byte sequences observed
at the named capture point. It does not imply identity or correspondence with
material before or after that observation, or with material perceived or
intended by a person.

The artifact authenticates a receipt record. It does not authenticate the
source material's author, truth, meaning, completeness, or admissibility to any
later process.

## Authority

Source Receipt Authority gains one authority:

> Attest what a governed acquisition interface observed at its governed capture
> point in one immutable receipt event.

Within that authority it may establish:

- its own exact receipt-event identity under the referenced governed receipt
  identity profile and the policy permission to use it;
- the exact acquisition-interface identity and version established by the
  referenced interface registry;
- the exact capture-point identity established by the referenced capture-point
  registry;
- the exact item boundaries exposed at that capture point;
- for each item, one exact finite byte sequence or one explicitly permitted
  no-content capture state;
- interface-local item order when the governing policy authorizes that order;
- metadata whose governed field definition and conditional policy grant permit
  direct attestation by that acquisition interface and capture point;
- transport-provided metadata preserved explicitly as assertions;
- complete accounting of every item expected under the governed capture-point
  definition; and
- capture failures without repair, completion, or inferred replacement.

## Refusal

Source Receipt Authority shall not:

- establish or infer authorship, speaker identity, account identity, principal
  identity, or session identity;
- authenticate any interaction identity;
- assign material to an entrusted case;
- infer case membership from temporal, transport, interface, or physical
  proximity;
- establish that two receipt events are edits, retries, replacements, or
  successors merely because a transport assertion relates them;
- interpret text, images, audio, attachments, metadata, or silence;
- classify captured bytes by content kind, format, media type, payload role,
  attachment role, rendering status, transcript status, derivation status, or
  any equivalent taxonomy;
- establish a transformation definition, transformation occurrence, provenance
  relationship, or correspondence between distinct objects;
- classify any item as context, activity, constraint, metaphor, emotion,
  cognition, objective, request, or other experience facet;
- establish the truth, intent, safety, feasibility, completeness, or
  authorization of received material;
- repair captured bytes, fill unavailable content, normalize observed values,
  resolve aliases, or substitute semantic equivalence for exact identity;
- grant storage, retrieval, inspection, disclosure, reuse, association, or
  cross-case access rights;
- authorize Prompt Evidence Preservation or any later interpretive boundary;
- produce an Accepted Objective, authenticated characteristic, crossing,
  orientation, need, accompaniment, journey, candidate, explanation, or media
  result.

## Exact authoritative prerequisites

Source Receipt Authority has no person, identity, or case artifact as an
authoritative parent. Its claim is intentionally valid without knowing who
authored the material or where it may later be admitted.

Before executable jurisdiction can exist, all of the following must exist and
remain in exact correspondence.

### 1. Approved Source Receipt contract

The governing contract must define the boundary's one claim, refusals, artifact
semantics, and conformance requirements. This provisional document does not
satisfy approval merely by existing.

### 2. Independently governed definitions

The concepts referenced by receipt policy must already have independently
governed identities, versions, definitions, and canonical digests. The required
definition authorities cover:

- acquisition interfaces and their declared capabilities;
- capture points and their exact observation semantics;
- capture-state identities and meanings;
- receipt-metadata field identities and typed schemas;
- receipt-event identity formats;
- interface-local ordering semantics;
- canonical serialization and digest mechanics; and
- clock or transport-time identities and scopes when authoritative time is
  permitted.

These are governed vocabularies, registries, or profiles. They define canonical
concepts. They do not claim that a receipt occurred, conditionally permit a
receipt claim, or perform acquisition.

This contract identifies the required kinds of definition. It does not define
their contents, topology, schemas, or implementation.

### 3. Immutable Source Receipt Policy

A versioned, immutable `SourceReceiptPolicy` may only compose exact references
to those independently governed definitions into conditional attestation
grants. For one exact acquisition interface and capture point, it may specify:

- which governed metadata fields may be attested and which must remain
  transport assertions;
- which governed capture states are permitted and their deterministic
  precedence;
- whether the governed interface-local order may be attested and within what
  scope;
- whether an independently governed time authority may support a particular
  time claim.

The complete policy must have a canonical SHA-256 digest. Any change to a
conditional grant, precedence rule, or referenced governed definition requires
versioned policy succession and a new digest.

The policy defines what the acquisition interface is conditionally permitted to
attest. It defines no interface, capture point, byte meaning, content kind,
state, metadata field, identity format, transformation, serialization
mechanism, or clock. It does not claim that any receipt occurred.

### 4. Corresponding acquisition adapter

A source-specific adapter must operate at the capture point established by the
exact governed definition and referenced by the exact policy. The adapter must
preserve each exact finite byte sequence exposed at that point without
classification, normalization, repair, reconstruction, or substitution.

An adapter name, implementation, network response, callback, or caller-created
model is not sufficient by itself. The complete observed event must be
validated against the independently governed definitions and exact policy
before authority is exercised.

### 5. Exact receipt-event input

The adapter must supply one finite receipt event whose bounded items, exact byte
sequences or permitted no-content states, order, metadata assertions, and
failures can be completely accounted for. Material not observed at the governed
capture point cannot be included as received material.

### 6. Time authority, only when time is attested

Authoritative wall-clock claims require a separately governed clock or
transport-time authority established independently and referenced by the Source
Receipt Policy. Without it, the artifact may preserve timestamp values only as
source or transport assertions.

Receipt-event identity and interface-local sequence may exist without
authoritative wall-clock time.

None of these prerequisites supplies authorship, interaction identity,
entrusted-case membership, or downstream inspection rights. Those remain
separate authorities even after Source Receipt Authority becomes executable.

## Trust boundary

```text
External material and transport assertions
                 ↓
Governed acquisition interface and capture point
                 +
Independently governed definitions
                 +
Immutable Source Receipt Policy
                 ↓
Source Receipt Authority
                 ↓
Immutable SourceReceiptArtifact
```

Identity and case authorities do not enter this derivation:

```text
SourceReceiptArtifact        InteractionIdentityArtifact
          │                              │
          └──────────────┬───────────────┘
                         │
              separately authorized association
                         │
                         ▼
                Entrusted-case admission
```

The association shown above is future adjacent authority, not part of this
contract. Receipt does not imply association, and association must never be
reconstructed from proximity.

## Exact captured items

Source Receipt treats captured bytes as opaque finite byte sequences. It
defines no canonical content kind and depends on no representation vocabulary.

The governed capture-point definition establishes which item boundaries are
observable and which items are expected for complete accounting. Source Receipt
may attest only the exact bounded items actually observed under that definition.

For each item, the receipt record contains exactly one of:

- the exact finite byte sequence exposed at the governed capture point; or
- one explicitly permitted no-content capture state.

The byte sequence carries no receipt-authorized claim that it is text, binary,
media, a payload, an attachment, a rendering, a transcript, derived content, or
any other content kind. Transport-supplied labels such as filename or declared
media type remain metadata assertions unless separately authorized metadata
rules permit a direct attestation about the observed event.

If a capture point exposes only a decoded, parsed, rendered, or otherwise
semantically typed object rather than an exact finite byte sequence, that
capture point cannot satisfy this contract. Source Receipt shall not convert the
object into bytes and present the conversion as observed source material.

If the bytes exposed at a capture point were produced earlier by some process,
Source Receipt records only those observed bytes. It establishes nothing about
what produced them, what preceded them, whether they correspond to another
object, or whether any transformation occurred.

## Capture states and complete accounting

Every identifiable item in the governed receipt event must appear exactly once
in a fixed capture-state partition. A separately governed capture-state
vocabulary must remain small and exact. Without defining canonical entries
here, it must distinguish successful capture at the governed point, declared
truncation, and unavailable content.

Final names and meanings belong to the governed capture-state vocabulary.
Deterministic precedence among permitted states belongs to the Source Receipt
Policy. Runtime may apply those definitions and permissions but may not create
states, change their meanings, or alter their precedence.

`Captured` means captured as observed at the governed point. It does not mean
complete as authored, transmitted, displayed, intended, or perceived.

Unavailable material remains explicitly unavailable. For a declared truncation,
the boundary must preserve any exact bytes it did receive and the exact observed
failure record. It must not guess, repair, decode, reconstruct, or replace
missing content with metadata.

## Metadata authority

Metadata must be partitioned by origin and authority.

### Interface-attested metadata

An independently governed metadata vocabulary defines each field and its typed
schema. Source Receipt Policy may conditionally permit an acquisition interface
and capture point to attest only fields that their governed definitions can
directly establish, such as interface-local item order or a capture failure
generated by that interface. Source Receipt Authority establishes the actual
field value only from the observed receipt event.

### Transport assertions

Source name, sender label, filename, declared media type, client timestamp,
transport message identifier, predecessor identifier, and similar values remain
transport assertions unless a separate authority authenticates them.

Preservation of an assertion does not authenticate its contents.

## Temporal semantics

The artifact must not collapse distinct time claims. A separately governed time
vocabulary must distinguish time asserted by transport, interface receipt time
supported by an independent clock or transport-time authority, and
interface-local order that establishes only a local sequence. Source Receipt
Policy may conditionally permit a governed time claim; it defines none of these
time concepts and establishes no time value. Source Receipt does not inspect
captured bytes for temporal meaning or establish a time outside the governed
capture-point observation.

Absence of time authority must produce absence of an authoritative time claim,
not a default timestamp.

## Requests

A future immutable, versioned `SourceReceiptRequest` may contain only:

- exact request identity;
- the complete `SourceReceiptPolicy` and its canonical SHA-256;
- the complete independently governed definitions referenced by that policy and
  their canonical SHA-256 digests;
- the exact acquisition-interface and capture-point identities selected from
  those definitions and conditionally permitted by that policy;
- one complete adapter-produced receipt event;
- exact item boundaries, byte sequences or permitted no-content capture states,
  metadata partitions, permitted local order, and complete capture accounting
  observed for that event.

Unknown fields are forbidden. The request shall contain no person, speaker,
interaction, entrusted-case, objective, experience-facet, meaning, permission,
or downstream-processing claim.

Caller-provided models must be structurally revalidated from complete serialized
content before authority is exercised. Object possession is not object
legitimacy.

## Artifact

A future immutable, versioned `SourceReceiptArtifact` must contain:

- schema version and artifact kind;
- exact artifact, request, and receipt-event identities;
- complete Source Receipt Policy identity, version, canonical content, and
  SHA-256;
- complete identity, version, and digest lineage for every independently
  governed definition applied;
- exact acquisition-interface and capture-point identities;
- canonically recorded bounded items in permitted interface-local order;
- per-item exact finite byte sequence or exact permitted no-content capture
  state;
- metadata partitioned into interface attestations and transport assertions;
- exact local-order and optional governed time lineage;
- complete capture accounting;
- explicit non-claims;
- canonical serialization.

Receipt order is evidentiary within this boundary and must therefore be
preserved. Canonical object-field ordering must not reorder observed items.

## Canonical serialization

Canonical artifact bytes must use the exact referenced canonical serialization
profile. That profile, rather than Source Receipt Policy, defines object-field
ordering, encoding, and the artifact encoding of captured byte sequences.
Canonical artifact bytes are record mechanics and must never be substituted for
the exact byte sequences observed at the capture point.

Construction copies all caller-owned inputs into new immutable structures and
does not mutate them. Equivalent valid receipt events under the same exact
policy produce equal artifacts and byte-identical canonical serialization.

## Succession

Receipt artifacts are immutable historical events.

- An edit creates a new receipt event.
- A retry creates a new receipt event.
- A replacement creates a new receipt event.
- A later successful capture does not rewrite an earlier failed capture.
- Transport-provided predecessor or replacement identifiers remain assertions.

Only a separately authorized succession or association boundary may establish a
relationship among receipt events. This contract preserves asserted
relationships but does not authenticate them.

## Access and downstream use

Creation or possession of a `SourceReceiptArtifact` grants no right to inspect,
retrieve, disclose, associate, interpret, or reuse its contents.

Any downstream consumer must separately establish:

- authority to access the artifact;
- authority to associate it with an authenticated interaction identity;
- authority to admit it to an entrusted case;
- authority to perform its own bounded operation.

Source Receipt Authority neither grants nor evaluates those permissions.

## Core invariants

- Receipt authority is limited to one governed interface, capture point, and
  receipt event.
- Every positive claim is reproducible from the exact observed event, exact
  independently governed definitions, and exact Source Receipt Policy.
- The complete policy is immutable, versioned, canonically serialized, and
  digest-addressed.
- Every observed item is completely accounted for in exactly one capture state.
- Observed item order is preserved and never treated as rank or semantic
  priority.
- Interface attestations and transport assertions remain structurally distinct.
- Captured bytes remain content-opaque and receive no canonical content kind.
- No normalization, aliasing, repair, semantic equivalence, or inferred default
  changes the exact bytes observed at the capture point.
- Failure and partial capture remain visible.
- Time claims never exceed their exact time authority.
- Receipt establishes neither authorship nor case membership.
- Artifact existence establishes no downstream inspection or reuse right.
- New receipt events produce new artifacts; history is never rewritten.

## Explicit non-claims

The artifact must record literal non-claims that it did not establish:

- authorship, speaker, principal, account, or session identity;
- interaction identity;
- entrusted-case identity, membership, scope, or succession;
- meaning, intent, truth, relevance, applicability, or experience facets;
- completeness beyond the exact capture state at the governed point;
- equivalence between preserved material and what was authored, transmitted,
  rendered, perceived, or intended;
- content kind, format, media identity, payload role, attachment role,
  rendering status, transcript status, or derivation status;
- transformation definition, transformation occurrence, provenance, or
  correspondence between distinct objects;
- safety, feasibility, authorization, or accepted objective;
- access, inspection, retrieval, disclosure, association, or reuse permission;
- Prompt Evidence Preservation;
- any interpretation, explanation, crossing, orientation, need,
  accompaniment, journey, candidate, or media operation.

## Constitutional audit question

> Does every artifact claim describe only what the governed acquisition
> interface observed at its exact capture point, or has receipt classified
> content or established authorship, identity, case membership, transformation,
> provenance, object correspondence, meaning, completeness, access, or
> downstream authority?

Any field, validation rule, outcome, or consumer path that permits the second
case is outside this boundary's jurisdiction.

## Architectural test plan

### Policy authority

- Complete policy identity, version, content, and digest correspond exactly.
- Every referenced interface, capture-point, state, metadata, identity,
  ordering, serialization, and optional time definition independently
  corresponds by identity, version, content, and digest.
- Policy contains only conditional grants over governed references and no
  embedded definition, clock, observed value, or runtime operation.
- Any substantive policy grant or governed-reference change changes its digest
  and requires versioned succession.
- An unchecked copied policy object is revalidated before use.

### Exact receipt

- Exact opaque bytes survive byte-for-byte.
- Observed item order survives construction and canonical serialization.
- Every item records exactly one finite byte sequence or one permitted
  no-content capture state.
- Item boundaries reproduce the exact governed capture-point observation.

### Content opacity

- Canonical artifact serialization cannot masquerade as observed source bytes.
- No request, artifact, policy grant, or validation outcome assigns a canonical
  content kind to captured bytes.
- No receipt field records transformation definition, transformation
  occurrence, provenance, or correspondence with another object.
- Transport-declared media types and filenames remain assertions.

### Complete accounting and failure

- Every identifiable item appears exactly once in one capture-state partition.
- Captured, declared-truncated, and unavailable states remain distinguishable.
- Failure never triggers guessing, repair, normalization, decoding,
  reconstruction, or fallback substitution.
- A later successful receipt cannot mutate an earlier failed artifact.

### Negative authority

- No request or artifact field can establish author, speaker, person, account,
  session, interaction, or case identity.
- Temporal proximity cannot establish shared identity or case membership.
- Transport predecessor assertions cannot establish succession.
- No captured bytes participate in content classification, semantic matching,
  objective formation, or interpretation.
- No receipt path establishes a transformation occurrence, provenance, or
  correspondence between distinct objects.
- Artifact possession cannot authorize inspection or reuse.
- No Prompt Evidence Preservation or downstream cognitive operation is
  reachable.

### Time

- Transport assertions and governed interface-receipt time remain distinct.
- Missing clock authority yields no authoritative timestamp.
- Local receipt sequence cannot be presented as global chronology.

### Determinism and immutability

- Equivalent valid events and policies produce equal artifacts and
  byte-identical canonical bytes.
- Construction does not mutate caller-owned items, metadata, policy, or event
  collections.

### Structural isolation

- Production import audits prove no dependency on interaction identity,
  entrusted-case membership, Prompt Evidence Preservation, objective,
  curriculum, accompaniment, journey, provider, candidate, explanation, or
  media packages.
- Repository-wide reference audits prove no alternate component can mint a
  `SourceReceiptArtifact`.

## Compatibility impact

This contract changes no existing production behavior or artifact.

The existing track-domain `EvidenceSnapshot` is not a Source Receipt parent or
compatibility artifact. It begins after acquisition and cannot prove a
receipt event, capture point, interface observation, bounded-item capture, or
receipt-time claim.

Existing CLI arguments, request models, objective statements, source labels,
and payload strings must not be re-blessed as receipt artifacts. A future
implementation requires an explicit adapter at a governed capture point and
shall provide no compatibility overload that reconstructs receipt authority
from legacy application objects.

## Stop point

This phase stops at a provisional Source Receipt Authority contract.

It does not implement:

- `SourceReceiptPolicy`;
- acquisition-interface, capture-point, capture-state, metadata,
  receipt-identity, serialization, or time definitions;
- an acquisition adapter;
- `SourceReceiptRequest` or `SourceReceiptArtifact`;
- clock authority;
- interaction identity;
- entrusted-case membership or admission;
- access and inspection authority;
- Prompt Evidence Preservation;
- any semantic or expressive boundary.

Source Receipt Authority remains constitutionally nonexistent at runtime until
the contract is approved, the independent governed definitions and conditional
policy exist, the corresponding acquisition adapter is implemented, and all
prerequisites remain in exact correspondence.

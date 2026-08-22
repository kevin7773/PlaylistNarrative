# Capture Point Registry — Provisional Contract

## Status

### Executable frozen subset

One capture-point definition is now frozen directly, without a general
registry:

`pne.capture-point.pre-interpretation-response-items/1.1`

The logical point is after a complete source response exposes its bounded items
and before decoding, parsing, normalization, or interpretation. Each observable
unit is the exact opaque byte sequence within one interface-exposed item
boundary; interface-local response order is authoritative. No conforming
runtime implementation is currently established.

The bounded observation also exposes the interface-assigned request-local
observation handle associated with each payload and position. This handle is
accounting provenance only and carries no metadata or domain meaning.

The generalized Capture Point Registry, publication and conformance authority,
and additional capture-point definitions remain provisional.

This document is a provisional contract for a definition-only governance
boundary. It follows the no-change authority audit of capture-point identity and
observation-boundary semantics required by Source Receipt Authority.

The audit found that a capture point possesses independently defensible
semantic ownership when it defines one canonical observation boundary within
one exact Acquisition Interface definition. This meaning cannot be replaced by
the interface reference alone without losing location, observable-unit,
complete-accounting, byte-exposure, and optional local-order semantics.

The contract is not an implementation and creates no executable jurisdiction.
No authoritative Acquisition Interface Registry, Capture Point Registry,
publication event, implementation, deployment, adapter, Source Receipt Policy,
or Source Receipt runtime currently exists.

## Purpose

The Capture Point Registry answers exactly one question:

> Which immutable, versioned definitions identify canonical observation
> boundaries within exact Acquisition Interface definitions, and what would
> each boundary encompass if a conforming implementation and observation later
> existed?

It provides stable governed language for identifying a possible observation
boundary. It does not claim that an implementation, deployment, observation,
receipt event, item, byte sequence, or permission exists.

## Positive claim

A valid published registry may make only this positive claim about an entry:

> Within exact Acquisition Interface definition I at definition version V and
> digest D, this exact governed definition identifies canonical Capture Point C
> at capture-point definition version P. It defines the exact contract-level
> location, the selected parent-defined observable units, the complete-
> accounting domain, whether those units expose opaque finite byte sequences,
> and any exact reference to separately governed local-order semantics.

The entry is authoritative as a definition. It is not authoritative as evidence
that anything implements, deploys, exposes, observes, invokes, or conforms to
that definition.

## Authority

The registry gains one authority:

> Establish canonical capture-point definition identities and their immutable
> definition-version succession within exact Acquisition Interface definitions.

Within that authority it may define:

- one exact capture-point identity scoped to one exact Acquisition Interface
  identity, definition version, and digest;
- one exact capture-point definition version;
- one exact contract-level observation location;
- an exact selection of observable units already defined by the parent
  interface contract or its exact governed definition parents;
- the exact domain used to determine which selected units would be expected for
  complete accounting;
- whether each selected unit exposes an opaque finite byte sequence;
- one exact reference to separately governed local-order semantics when order
  is part of the definition;
- exact referenced protocol or framing lineage when parent-defined unit
  boundaries require it;
- exact predecessor definition lineage when the entry is a successor;
- canonical definition and registry digests under an independently governed
  serialization profile; and
- explicit non-claims.

The registry defines a canonical observation boundary. It establishes no
runtime fact and grants no permission.

## Definition version

`capture_point_definition_version` means exactly:

> The version of one governed capture-point definition under one exact parent
> Acquisition Interface definition.

It does not mean or encode:

- Acquisition Interface definition version;
- source-code version;
- package, library, or build version;
- adapter version;
- deployment or host version;
- process or runtime identity;
- configuration revision;
- protocol-provider version;
- Source Receipt Policy version;
- Source Receipt request or artifact schema version;
- observation-event or receipt-event identity; or
- serialization-profile version.

Those values may be related only through their own exact governed lineage. A
coincidentally equal string grants no identity, applicability, or
correspondence.

## Canonical capture-point identity

A capture-point identity names one governed line of observation-boundary
definitions within one exact Acquisition Interface definition.

The complete authoritative reference is therefore at least:

```text
Capture Point Registry identity
+ Capture Point Registry version
+ Capture Point Registry digest
+ Acquisition Interface Registry identity
+ Acquisition Interface Registry version
+ Acquisition Interface Registry digest
+ Acquisition Interface identity
+ Acquisition Interface definition version
+ Acquisition Interface definition digest
+ capture-point identity
+ capture-point definition version
+ capture-point definition digest
```

A capture-point name without the complete parent-interface and registry lineage
is not an authoritative capture-point reference.

Capture-point identity is not global. The same local label under another parent
interface definition has a different complete identity and carries no
correspondence by textual equality.

## Exact parent interface

Every capture-point definition has exactly one authoritative Acquisition
Interface definition as its semantic parent.

The parent must be supplied as a complete, published definition with exact
registry identity, registry version, registry digest, interface identity,
interface definition version, interface definition digest, definition content,
and publication lineage.

The Capture Point Registry must structurally revalidate that complete parent.
It may not accept:

- a caller-reconstructed projection;
- a name and version without complete lineage;
- source code or package metadata as a substitute;
- an implementation or deployment record;
- an interface inferred from runtime traffic; or
- a compatibility adapter that re-blesses legacy identifiers.

If the exact parent contract does not contain sufficient canonical landmarks or
governed definition references to locate the proposed boundary, the proposal
must be refused. Runtime evidence cannot repair an under-specified parent.

## Contract-level location

A capture-point location must be stated entirely in terms of exact canonical
landmarks already present in the parent interface contract or its referenced
governed definitions.

Permitted forms include exact references to:

- a parent-defined operation boundary;
- a parent-defined argument or result position;
- a parent-defined protocol unit;
- a parent-defined contract surface; or
- another exact case-blind landmark whose meaning is already authoritative.

The location must not reference:

- file paths or line numbers;
- functions, classes, callbacks, or methods absent from the canonical parent;
- adapter steps;
- buffers, queues, caches, or implementation-specific processing stages;
- hosts, processes, endpoints, deployments, or environments;
- observed traffic or discovered payload shape;
- a before-or-after transformation claim; or
- any content-derived predicate.

The registry defines where a boundary would be in the canonical contract. It
does not decide whether any implementation exposes or can reach that boundary.

## Observable units and item boundaries

A capture-point definition may select only exact units already identifiable in
the parent interface contract or its governed definition parents.

The definition may:

- identify which parent-defined unit positions are within the observation
  boundary;
- define a case-blind selection over those exact positions; and
- preserve exact lineage to any independently governed protocol or framing
  definition required to identify them.

The definition shall not:

- parse bytes to discover units;
- define delimiters, frames, records, messages, attachments, payloads, or other
  content roles locally;
- infer units from runtime cardinality or observed values;
- invent a framing algorithm;
- classify selected units by content; or
- claim that any selected or expected unit existed.

If unit boundaries require semantics not present in the parent definition, an
independent governed protocol or framing definition is required. The Capture
Point Registry may reference that authority exactly. It may not absorb it.

## Complete-accounting domain

The complete-accounting domain defines which selected parent-defined units
would require an accounted-for capture state if a receipt event later occurred.

It may define only a case-blind rule over exact parent-defined units. It does
not enumerate runtime objects or establish that an item was present, absent,
captured, truncated, or unavailable.

Examples of permitted definition forms include:

- one expected item for one exact byte-valued argument position;
- one expected item for each unit identified by an exact governed protocol
  definition; or
- a finite set of exact parent-defined positions.

The registry does not define capture-state identities, meanings, precedence, or
applicability. Those remain separate from the definition of what the accounting
domain would encompass.

## Opaque finite-byte exposure

Every capture-point definition must state whether each selected observable unit
exposes one exact opaque finite byte sequence.

An affirmative declaration is permitted only when the exact parent interface
contract or one of its exact governed definition parents already defines that
selected unit as byte-valued at the referenced contract landmark. The Capture
Point Registry may apply that parent meaning to the observation boundary. It may
not create a byte view of a non-byte unit, select an encoding, serialize a value,
or infer byte exposure from an implementation.

The declaration is definition-only. It does not claim that:

- any bytes exist;
- an implementation can expose bytes;
- bytes were observed or preserved;
- the bytes possess a content kind;
- the bytes are text, binary media, a payload, an attachment, a rendering, a
  transcript, decoded content, derived content, or any similar classification;
- the bytes correspond to material before or after the boundary; or
- any transformation or provenance relationship exists.

Finite byte sequence is mathematical substrate. The registry does not define,
version, publish, or govern its mathematical meaning.

A definition that states that exact finite-byte exposure is absent may make no
claim about what alternative object or content exists. Such a capture point
cannot authorize byte-exact Source Receipt merely by being registered.

## Local order

Ordering semantics do not belong to the Capture Point Registry.

When order is part of a capture-point definition, the entry must reference one
exact independently governed local-order definition by its complete identity,
version, content, digest, and publication lineage.

The capture-point entry may identify which selected units are governed by that
reference. It may not:

- define ordering semantics locally;
- infer order from array position, storage layout, timestamps, or runtime
  arrival;
- assert that any observed order occurred;
- treat order as rank, priority, preference, chronology, or causality; or
- supply a fallback order when the reference is absent or invalid.

A capture-point definition may omit local order entirely. Local-Order Semantics
is therefore an optional authoritative parent, not a prerequisite for the
registry to exist in kind.

## Independently governed prerequisites

Before executable registry-publication jurisdiction can exist, all applicable
prerequisites must exist and remain in exact correspondence.

### 1. Approved Capture Point Registry contract

The approved contract must define the registry's one authority, parent scope,
definition semantics, refusals, succession, artifact lineage, and conformance
requirements. This provisional document does not become approved merely by
existing.

### 2. Published Acquisition Interface definition

Every entry requires one exact complete, published Acquisition Interface
definition as its authoritative semantic parent.

The current Acquisition Interface Registry contract is provisional. Its
existence does not supply an authoritative registry artifact or executable
publication jurisdiction.

### 3. Referenced protocol or framing definitions, when required

If observable-unit boundaries cannot be identified from the parent interface
definition alone, each required protocol or framing concept must already exist
in a separately governed definition source with exact identity, version,
content, digest, and publication lineage.

This prerequisite is proposal-specific. It does not imply that one universal
Framing Registry must exist.

### 4. Local-Order Semantics, when applicable

An ordered capture-point definition requires one exact independently governed
local-order definition. An unordered definition has no such prerequisite.

This contract does not establish that Local-Order Semantics is legitimate in
kind. That authority remains unresolved until independently audited.

### 5. Canonical Serialization Profile

An independently governed serialization profile must define canonical field
ordering, collection ordering, text encoding, byte-field encoding, and digest
input bytes for capture-point definitions and complete registries.

The profile supplies publication and artifact mechanics. It contributes no
capture-point meaning.

### 6. Independent Definition Publication Authority

An exact publication mandate and independently authorized publication decision
must adopt or refuse one complete proposed Capture Point Registry publication
object.

Publication binds governed status to the exact object. It does not define the
capture point, validate its semantic correctness, grant downstream use, or
create an implementation.

## Publication

Independent Definition Publication Authority may accept one complete proposed
registry and all exact governed parents. It may adopt or refuse that exact
object under an independently authoritative mandate.

The Capture Point Registry supplies no publication mandate, authorization
evidence, adoption decision, or publication status for itself.

The Capture Point Registry must not discover or publish definitions from:

- source code;
- adapter behavior;
- deployment configuration;
- network traffic;
- logs or telemetry;
- observed receipt events;
- repeated operational use; or
- caller-authored aliases.

Implementation artifacts may motivate a proposal. They cannot become canonical
capture-point definitions without independent review, mandate, and publication.

## Complete registry

A Capture Point Registry is complete relative to its declared registry identity
and version. A selected subset cannot masquerade as the complete governed
registry.

The complete registry must preserve:

- exact registry identity and version;
- the complete referenced Canonical Serialization Profile and digest;
- complete Acquisition Interface parent lineage;
- complete referenced protocol, framing, and optional local-order lineage;
- a finite canonically ordered set of capture-point definitions;
- unique complete capture-point identities and definition versions;
- unique definition digests within one registry version;
- exact predecessor correspondence for successor definitions;
- explicit non-claims;
- registry content SHA-256; and
- canonical serialization.

Canonical registry ordering carries no observation order, runtime precedence,
priority, recommendation, availability, or preference.

Duplicate complete identities, definition versions, digests, aliases, or
conflicting predecessor claims fail closed. Textual equality outside complete
lineage cannot create identity or correspondence.

## Immutability and structural validation

Published registry content is immutable.

Every complete registry, capture-point definition, parent interface definition,
and governed reference must be structurally revalidated from complete serialized
content before another boundary relies on it. A frozen or typed object is not
authoritative merely because a caller possesses it.

Validation may establish only internal correspondence with this contract and
the exact governed parents. It does not establish publication authority,
implementation existence, deployment, conformance, observation, receipt, or
permission.

## Canonical serialization and digests

The independently governed Canonical Serialization Profile defines canonical
bytes for:

- each capture-point definition excluding its own content digest;
- each complete capture-point definition including its content digest;
- registry content excluding its own content digest; and
- the complete registry including its content digest.

Definition and registry content digests are SHA-256 values calculated over the
applicable canonical content bytes.

Equivalent valid proposed content under the same exact governed parents
produces equal definitions, equal registries, identical digests, and
byte-identical canonical serialization. Publication and validation do not
mutate caller-owned collections.

Digests prove correspondence with canonical definition bytes. They do not prove
that a capture point exists in an implementation, is deployed, is observable,
was observed, or may be used.

## Succession

A published capture-point definition is never edited in place.

Any change to canonical definition content requires a new
`capture_point_definition_version`, a new definition digest, and explicit
predecessor lineage.

Successor publication is required when a change alters:

- the exact parent Acquisition Interface identity, definition version, digest,
  or lineage;
- contract-level location;
- selected observable units;
- complete-accounting domain;
- finite-byte exposure declaration;
- referenced protocol or framing definition;
- optional local-order reference;
- explicit non-claims; or
- any other canonical definition content.

A parent-interface successor never silently carries a capture-point definition
forward. Even when the local capture-point label is unchanged, governance must
publish an exact successor or a new definition with explicit predecessor and
parent correspondence.

The following do not create definition succession when canonical capture-point
meaning and all exact governed parents remain unchanged:

- deployment;
- host or process replacement;
- adapter rewrite;
- buffering or storage change;
- runtime observation;
- traffic or receipt events;
- implementation failure;
- build replacement; or
- implementation-specific code movement.

Whether an implementation still conforms after such a change belongs to a
separate implementation-conformance authority.

Runtime systems may consume a published successor and propose another. They may
not enact succession themselves.

## Definition, implementation, and observation

Canonical definition, implementation, deployment, conformance, permission, and
observation are distinct claims.

```text
Capture Point Registry
    defines one canonical observation boundary

Implementation authority
    identifies an implementation artifact

Deployment authority
    identifies a deployed instance

Implementation-conformance authority
    may compare an implementation with the canonical definition

Source Receipt Policy
    may conditionally permit attestation at the definition

Source Receipt Authority
    may establish what was observed in one exact event
```

One canonical capture-point definition may have zero, one, or many independently
identified implementations. Registry membership changes none of their empirical
status.

## Separation from Source Receipt Policy

The Capture Point Registry defines a possible observation boundary. Source
Receipt Policy may later reference an exact entry when conditionally permitting
a receipt claim.

The registry does not:

- grant permission to observe or attest;
- select a capture point for a case;
- define capture-state precedence;
- permit metadata or time claims;
- authorize an adapter;
- define a Source Receipt Policy; or
- claim that a policy exists or applies.

Definition is not permission.

## Separation from Source Receipt Authority

The Capture Point Registry shall not establish:

- that an interface or capture point exists in an implementation;
- that an observation or receipt occurred;
- observed items or byte sequences;
- actual item order;
- capture state, failure, truncation, or unavailability;
- metadata values or transport assertions;
- receipt-event identity or time;
- complete accounting for an actual event; or
- a `SourceReceiptArtifact`.

Source Receipt Authority may consume an exact published capture-point definition
only after its own policy and prerequisites independently authorize execution.
It may not reconstruct, extend, or reinterpret that definition.

## Refusal

The registry must refuse any proposal that attempts to include or derive:

- a capture-point identity without one exact complete parent-interface lineage;
- a location absent from the exact parent contract and governed parents;
- implementation, package, adapter, deployment, host, process, environment, or
  configuration identity;
- implementation conformance or runtime availability;
- an observation, receipt, item, byte, order, failure, or time occurrence;
- Source Receipt Policy permission or applicability;
- locally invented framing, ordering, or serialization semantics;
- parsing, delimiter, transformation, adapter, or capture algorithms;
- content kind or representation taxonomy;
- text, media, payload, attachment, rendering, transcript, decoded, derived, or
  similar classifications;
- transformation definition or occurrence;
- provenance or relationship between observed objects;
- semantic interpretation, validity, or meaning;
- downstream access, inspection, association, or use permission;
- runtime discovery, fallback definitions, aliases, normalization, fuzzy
  matching, or locally reconstructed parents.

Such content is outside registry jurisdiction rather than an optional extension
field.

## Registry artifact

A future immutable `CapturePointRegistryArtifact` must preserve:

- schema version and artifact kind;
- exact publication identity and lineage;
- exact registry identity and version;
- complete Canonical Serialization Profile lineage and digest;
- complete Acquisition Interface parent lineage and digests;
- complete protocol, framing, and optional local-order parent lineage and
  digests;
- the complete canonically ordered capture-point definition registry;
- definition content digests;
- explicit predecessor lineage;
- explicit non-claims;
- registry content SHA-256; and
- canonical serialization.

The artifact records published canonical definitions. It records no empirical
state, policy grant, or runtime result.

## Core invariants

- Every capture-point identity is scoped to one exact parent Acquisition
  Interface definition and complete lineage.
- Every location resolves entirely through canonical parent-contract landmarks.
- Every observable unit is selected from parent-defined units.
- Every complete-accounting rule is case-blind and defines no runtime inventory.
- Finite-byte exposure is a definition flag, not an observed-byte claim.
- Affirmative finite-byte exposure must reproduce exact byte-valued semantics
  already established by the parent interface or its governed parents.
- Finite byte sequence remains mathematical substrate, not governed vocabulary.
- Local order is absent or referenced through exact independent authority.
- No content kind, framing rule, order meaning, serialization rule,
  transformation, provenance, policy, or runtime fact is authored locally.
- Definitions are case-blind and contain no empirical instance.
- Registry publication does not discover definitions from runtime state.
- Registry membership proves neither implementation nor deployment.
- Any canonical definition-content or parent-lineage change requires explicit
  immutable succession.
- Equivalent valid content produces byte-identical canonical output.
- Runtime use never amends the registry.

## Explicit non-claims

The registry artifact must record literal non-claims that it did not establish:

- source-code, package, build, image, adapter, or implementation identity;
- implementation existence or conformance;
- deployment, host, process, environment, configuration, availability, or
  health;
- observation, receipt, source material, observed item, byte value, actual
  order, capture state, failure, or time;
- Source Receipt Policy permission or applicability;
- content kind, representation taxonomy, format, media identity, payload role,
  attachment role, rendering status, transcript status, decoding status, or
  derivation status;
- transformation definition or occurrence;
- provenance or correspondence between observed objects;
- semantic interpretation, validity, meaning, truth, or completeness of actual
  material;
- authorship, speaker, principal, account, session, interaction, or
  entrusted-case identity;
- access, inspection, storage, disclosure, association, or reuse permission;
- Prompt Evidence Preservation;
- objective, crossing, orientation, need, accompaniment, journey, candidate,
  explanation, or media operation; or
- runtime behavior of any kind.

## Constitutional audit question

> Does every registry claim define only one canonical observation boundary in
> one exact Acquisition Interface contract, or has the registry been allowed to
> invent parent semantics, framing, order, content identity, transformation,
> provenance, permission, implementation, deployment, observation, receipt, or
> runtime behavior?

Any field, validator, publication path, or consumer behavior permitting the
second case is outside this registry's jurisdiction.

## Architectural test plan

### Parent identity

- Every entry references exactly one complete Acquisition Interface definition.
- Parent registry, interface, version, digest, content, and publication lineage
  correspond exactly.
- Capture-point identity is unique only within its exact parent scope.
- Names, versions, or digests without complete parent lineage fail closed.
- A caller-reconstructed parent projection is rejected.

### Implementation independence

- Two hypothetical conforming implementations can resolve the same definition
  entirely from canonical parent-contract landmarks.
- Source paths, methods, callbacks, adapters, deployments, and runtime traffic
  cannot enter a location definition.
- A location not resolvable from exact governed parents is refused.

### Observable units and accounting

- Every selected unit resolves to an exact parent-defined unit.
- Locally parsed, inferred, or runtime-discovered unit boundaries are rejected.
- Complete-accounting domains are case-blind and contain no observed inventory.
- Actual presence, absence, failure, or capture state cannot enter a definition.

### Byte exposure and content opacity

- Finite-byte exposure is represented only as an exact definition declaration.
- Affirmative byte exposure without exact byte-valued parent semantics is
  rejected.
- No byte value appears in a registry definition as an observed instance.
- No content kind or representation taxonomy can enter any registry field.
- A false byte-exposure declaration names no alternative content object.
- Finite byte sequence has no registry identity, version, or successor.

### Local order

- Ordered definitions require complete independently governed order lineage.
- Unordered definitions contain no order fallback.
- No registry field defines or infers order semantics.
- Canonical registry ordering cannot masquerade as observation order.

### Complete registry

- The registry is finite and canonically ordered.
- Complete capture-point identity and definition-version pairs are unique.
- Duplicate definitions, aliases, and conflicting predecessor claims fail
  closed.
- A caller-selected subset cannot masquerade as the complete registry.

### Succession

- Every canonical content or governed-parent change requires a new definition
  version and explicit predecessor lineage.
- Parent-interface succession never silently carries capture-point authority.
- Deployment, implementation, adapter, traffic, and code-location changes do
  not mint definition succession.
- Runtime cannot enact or infer succession.

### Publication and serialization

- Publication requires exact independent mandate and authorization evidence.
- Canonical bytes and digests reproduce under the referenced serialization
  profile.
- Publication, validation, and serialization do not mutate caller-owned inputs.
- Git, storage, signatures, hashes, and write access cannot mint registry
  authority.

### Negative authority

- No registry field establishes implementation, deployment, conformance,
  observation, receipt, permission, content meaning, transformation,
  provenance, or runtime behavior.
- No Source Receipt request or artifact is constructible through this package.
- No legacy runtime identifier can be promoted into canonical identity.

### Structural isolation

- Future production import audits must prove no dependency on Source Receipt,
  interaction identity, entrusted-case membership, Prompt Evidence
  Preservation, objective, curriculum, accompaniment, journey, provider,
  candidate, explanation, or media packages.
- Repository-wide reference audits must prove that no alternate component can
  mint a `CapturePointRegistryArtifact`.

## Compatibility impact

This contract changes no existing production behavior or artifact.

Existing source paths, functions, classes, callbacks, adapters, logs,
telemetry, configuration values, request models, and receipt-like objects are
not canonical capture-point definitions. They must not be re-blessed through a
compatibility adapter or inferred migration.

A future implementation must begin from explicitly governed definitions and
shall provide no overload that reconstructs capture-point authority from legacy
runtime objects.

## Successor boundary

Source Receipt Policy may eventually consume exact published Acquisition
Interface and Capture Point Registry definitions when conditionally permitting
receipt claims.

Source Receipt Authority may eventually consume the same exact definitions only
after policy, adapter, and all other authoritative prerequisites independently
exist and correspond.

Neither downstream boundary may reconstruct, extend, reinterpret, or amend a
capture-point definition.

## Stop point

This phase stops at a provisional Capture Point Registry contract.

It does not implement or define:

- Capture Point Registry publication;
- Capture Point Registry schemas or artifacts;
- Acquisition Interface Registry implementation or publication;
- protocol or framing definitions;
- Local-Order Semantics;
- Canonical Serialization Profile;
- Publication Mandate Authority;
- Independent Definition Publication Authority implementation;
- implementation, deployment, configuration, or conformance authority;
- Source Receipt Policy;
- acquisition adapters;
- Source Receipt Authority runtime;
- Prompt Evidence Preservation; or
- any semantic, cognitive, expressive, provider, or media operation.

The Capture Point Registry remains constitutionally nonexistent at runtime until
this contract is approved, every exact semantic parent exists, Independent
Definition Publication Authority has executable jurisdiction, one complete
registry is validly adopted, an implementation is separately authorized and
validated, and all prerequisites remain in exact correspondence.

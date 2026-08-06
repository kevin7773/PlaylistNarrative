# Acquisition Interface Registry — Provisional Contract

## Status

This document is a provisional contract for a definition-only governance
boundary. It follows the no-change authority audit of acquisition-interface and
capture-point identity required by the Source Receipt Authority contract.

The audit found that acquisition-interface identity is legitimate in kind and
has succession semantics distinct from capture-point identity. This document
therefore covers the Acquisition Interface Registry only.

The contract is not an implementation and creates no executable jurisdiction.
No acquisition-interface registry, publication boundary, capture-point
registry, deployment record, implementation-conformance artifact, adapter, or
Source Receipt runtime currently exists.

## Purpose

The Acquisition Interface Registry answers exactly one question:

> Which immutable, versioned definitions are the canonical identities of
> acquisition interfaces that other governed artifacts may reference?

It provides stable governed language for identifying an acquisition-interface
contract. It does not assert that an implementation, deployment, host, process,
configuration, observation, or receipt exists.

## Positive claim

A valid published registry may make only this positive claim about an entry:

> This exact governed definition identifies canonical acquisition interface I
> at definition version V with this exact content and digest.

The entry is authoritative as a definition. It is not authoritative as evidence
that anything implements, deploys, invokes, or conforms to that definition.

## Authority

The registry gains one authority:

> Establish canonical acquisition-interface definition identities and their
> immutable definition-version succession.

Within that authority it may define:

- one exact acquisition-interface identity;
- one exact definition version for that identity;
- a bounded, case-blind description of the interface contract;
- the interface contract surface that a future implementation may claim to
  implement;
- exact references to separately governed capability or protocol definitions,
  when such parents exist;
- exact predecessor definition lineage when the entry is a successor;
- canonical definition and registry digests under an independently governed
  serialization profile;
- explicit non-claims.

The registry defines a canonical contract. It does not establish a runtime
fact.

## Definition version

`interface_definition_version` means exactly:

> The version of the governed acquisition-interface definition.

It does not mean or encode:

- source-code version;
- package or library version;
- build identifier;
- container-image digest;
- deployment version;
- deployment identity;
- runtime-host identity;
- process identity;
- environment identity;
- infrastructure revision;
- configuration revision;
- adapter version;
- protocol-provider version;
- capture-point version;
- schema version of a receipt request or artifact.

Those values may later be governed and related through separate implementation,
deployment, configuration, or conformance authorities. They neither define nor
alter canonical interface identity merely because a runtime system carries
them.

A definition-version value may coincidentally equal a code, package, build, or
deployment version string. That textual equality grants no correspondence. The
value functions as an interface-definition version only through exact governed
registry publication and lineage.

## Canonical interface identity

An acquisition-interface identity names one governed line of interface
definitions. Its authority is inseparable from the exact definition version and
canonical definition digest.

The complete authoritative reference is therefore at least:

```text
registry identity
+ registry version
+ registry digest
+ acquisition-interface identity
+ interface-definition version
+ interface-definition digest
```

An interface name without its exact registry and definition lineage is not an
authoritative interface reference.

Canonical identity remains stable across runtime occurrences that do not alter
the governed definition. Repeated deployment, restart, host migration, process
replacement, or implementation rebuild does not create a new canonical
interface identity merely because operational state changed.

Stability of definition identity makes no claim that those runtime occurrences
exist or conform.

## Definition content

An acquisition-interface definition may contain only case-blind canonical
contract information required to distinguish one interface definition from
another, including:

- exact interface identity;
- exact interface-definition version;
- a precise bounded description of the interface contract;
- exact references to separately governed protocol, capability, or other
  definition parents required by that contract;
- exact predecessor identity, version, and digest when published as a
  successor;
- explicit non-claims;
- definition content SHA-256;
- canonical serialization under the referenced serialization profile.

The bounded description may identify the class of acquisition edge being
defined. It may not define source-representation meanings, enumerate capture
points, describe observed values, prescribe adapter algorithms, or claim
support by a runtime implementation.

Human-readable labels and descriptions are documentation within the governed
definition. They do not create aliases, semantic matching, or alternate
identity paths.

## Independently governed prerequisites

Before executable registry-publication jurisdiction can exist, all of the
following must exist and remain in exact correspondence.

### 1. Approved Acquisition Interface Registry contract

The approved contract must define the registry's one authority, definition
semantics, refusals, succession, artifact lineage, and conformance requirements.
This provisional document does not become approved merely by existing.

### 2. Registry publication governance

An explicit governance process must authorize which complete proposed registry
may be published as the authoritative registry identity and version.

Runtime code may construct or validate a proposed registry. It may not approve
its own definitions, publish its own successor, or convert repeated operational
use into canonical status.

This contract does not define the human or institutional review workflow.

### 3. Canonical serialization profile

An independently governed serialization profile must define canonical field
ordering, collection ordering, text encoding, and digest input bytes for
interface definitions and complete registries.

The Acquisition Interface Registry references that profile. It does not define
or alter serialization mechanics.

### 4. Referenced definition parents

If an interface definition cites a protocol, capability, configuration class,
or another canonical concept, that concept must already exist in a separately
governed definition source with exact identity, version, content, and digest.

The registry may preserve and validate those references. It may not define the
referenced concepts inside an interface entry merely for convenience.

No implementation, deployment, host, observation, receipt, interaction,
entrusted case, or runtime configuration is an authoritative parent of this
registry.

## Registry publication

Publication accepts one complete proposed registry and its exact governed
parents. It either publishes that complete registry immutably or refuses the
publication request.

Publication does not discover interfaces from source code, package metadata,
running services, deployment manifests, provider documentation, traffic,
configuration, or observed use.

Implementation artifacts may motivate a future registry proposal. They cannot
be promoted into canonical interface definitions without governed publication.

## Complete registry

An Acquisition Interface Registry is complete relative to its declared
registry identity and version. Runtime callers may not submit a selected subset
and represent it as the complete governed registry.

The complete registry must preserve:

- exact registry identity and version;
- the complete referenced serialization profile and canonical digest;
- complete referenced definition-parent lineage;
- a finite canonically ordered set of interface definitions;
- unique interface identity and definition-version pairs;
- unique canonical definition digests within one registry version;
- exact predecessor correspondence for successor definitions;
- explicit non-claims;
- registry content SHA-256;
- canonical serialization.

Ordering is canonical and carries no priority, deployment preference,
availability, recommendation, or runtime precedence.

Duplicate identities, versions, definition digests, aliases, or conflicting
predecessor claims fail closed. A duplicated definition under another name does
not create another canonical interface.

## Immutability and structural validation

Published registry content is immutable.

Every complete registry and definition must be structurally revalidated from
its complete serialized content before another boundary relies on it. A frozen
or typed object is not authoritative merely because a caller possesses it.

Validation may establish only internal correspondence with this contract and
the exact governed parents. It does not establish implementation or deployment
conformance.

## Canonical serialization and digests

The independently governed serialization profile defines canonical bytes for:

- each interface definition excluding its own content digest;
- each complete interface definition including its content digest;
- registry content excluding its own content digest; and
- the complete registry including its content digest.

Definition and registry content digests are SHA-256 values calculated over the
applicable canonical content bytes.

Equivalent valid proposed content under the same exact governed parents
produces equal definitions, equal registries, identical digests, and
byte-identical canonical serialization. Publication and validation do not
mutate caller-owned collections.

Digests prove correspondence with canonical definition bytes. They do not prove
that the defined interface exists, is implemented, is deployed, or behaves as
defined.

## Succession

A published definition is never edited in place.

Any change to canonical definition content requires a new
`interface_definition_version`, a new definition digest, and explicit
predecessor lineage. This remains true whether a proposed change is described
as breaking, compatible, corrective, editorial, operational, or internal.

Successor definition is required when a change alters the governed interface
contract, including its:

- bounded contract description;
- declared contract surface;
- referenced protocol or capability definitions;
- identity correspondence;
- predecessor lineage; or
- explicit non-claims.

Operational changes alone do not require definition succession when the exact
governed interface contract is unchanged. Examples include a deployment to a
new host, process restart, infrastructure replacement, or build replacement
that makes no new registry claim.

Whether an implementation actually preserves the old contract is not decided
by this registry. A separately authorized implementation-conformance boundary
would have to establish that relationship.

A configuration change that alters governed interface semantics requires a
successor definition or an exact successor reference to an independently
governed configuration definition. A configuration change irrelevant to the
governed contract does not alter canonical interface identity.

Runtime systems may consume a published successor and may propose another.
They may not enact registry succession themselves.

## Separation from capture points

The Acquisition Interface Registry does not define capture-point identity or
observation semantics.

A future Capture Point Registry may reference one exact acquisition-interface
definition as its authoritative parent. It must own its distinct identity and
succession rules.

The interface registry shall not:

- enumerate capture points;
- assign capture-point identities or versions;
- define processing-path locations;
- define before-or-after transformation positions;
- define what representation is visible at a location;
- decide that a capture point exists in an implementation;
- grant permission to observe or attest at a capture point.

An interface definition may state that its contract permits separately governed
capture-point definitions to reference it. That statement neither creates a
capture point nor makes one applicable.

## Separation from implementation and deployment

Canonical definition, implementation, deployment, and conformance are distinct
claims.

```text
Acquisition Interface Registry
    defines the canonical interface contract

Implementation authority
    identifies an implementation artifact

Deployment authority
    identifies a deployed instance

Implementation-conformance authority
    may compare an implementation with the canonical definition
```

Only the first claim belongs to this contract. The other authorities remain
future and separate.

One canonical interface definition may have zero, one, or many independently
identified implementations. Each implementation must establish its own
existence and earn conformance to the exact definition independently. The
absence, existence, failure, or conformance of one implementation changes
neither the canonical definition nor any other implementation's status.

Registry membership cannot establish that an interface:

- has source code;
- has an adapter;
- can be instantiated;
- is configured;
- is reachable;
- is healthy;
- is deployed;
- is currently running;
- received material;
- produced an artifact;
- conforms in behavior to its definition.

## Separation from Source Receipt Policy

The registry defines canonical interface identity. Source Receipt Policy may
later reference an exact registry entry when conditionally permitting a receipt
claim.

The registry does not:

- grant permission to attest;
- classify metadata as attestable;
- permit representation kinds;
- establish capture-state precedence;
- permit time claims;
- authorize transformations;
- define a Source Receipt Policy;
- claim that a policy exists or applies.

Definition is not permission.

## Separation from Source Receipt Authority

The registry does not establish:

- an observation;
- a receipt event;
- received material;
- source-item order;
- captured metadata;
- a transformation occurrence;
- a capture failure;
- a timestamp;
- a `SourceReceiptArtifact`.

Canonical interface identity is not evidence that the interface observed
anything.

## Refusal

The registry must refuse any proposal that attempts to include or derive:

- source-code, build, package, deployment, host, process, environment, or
  infrastructure identity offered as a substitute for governed
  interface-definition publication and lineage;
- runtime configuration values;
- runtime status, health, availability, or telemetry;
- capture-point identities or observation semantics;
- representation meanings or concrete source material;
- receipt, observation, or transformation facts;
- conditional attestation permissions;
- implementation or deployment conformance claims;
- identity, authorship, interaction, entrusted-case, access, meaning, or
  downstream-processing claims;
- runtime discovery, fallback definitions, aliases, normalization, fuzzy
  identity matching, or locally reconstructed registry entries.

Such content is outside registry jurisdiction rather than an optional extension
field.

## Registry artifact

A future immutable `AcquisitionInterfaceRegistryArtifact` must preserve:

- schema version and artifact kind;
- exact publication identity;
- exact registry identity and version;
- complete governed serialization-profile lineage and digest;
- complete referenced definition-parent lineage and digests;
- the complete canonically ordered interface-definition registry;
- definition content digests;
- explicit predecessor lineage;
- explicit non-claims;
- registry content SHA-256;
- canonical serialization.

The artifact records published canonical definitions. It records no empirical
state.

## Core invariants

- The registry defines canonical interface contracts and nothing else.
- Interface version always means definition version.
- Canonical identity requires exact registry and definition lineage.
- Definitions are case-blind and contain no empirical instance.
- Registry publication does not discover definitions from runtime state.
- Registry membership proves neither implementation nor deployment.
- Interface identity is stable across operational changes that do not change
  the governed definition.
- Any definition-content change requires explicit immutable succession.
- No capture-point identity or semantics enter the registry.
- No representation meaning enters the registry except as an exact reference to
  a separately governed parent.
- No policy grant, observation, receipt fact, or runtime operation enters the
  registry.
- Equivalent valid content produces byte-identical canonical output.
- New governance creates a successor; runtime use never amends the registry.

## Explicit non-claims

The registry artifact must record literal non-claims that it did not establish:

- source-code, package, build, image, adapter, or implementation identity;
- implementation existence or conformance;
- deployment, host, process, environment, configuration, availability, or
  health;
- capture-point identity, location, semantics, existence, or applicability;
- representation identity or meaning except as a governed external reference;
- observation, receipt, source material, metadata value, order, failure,
  transformation occurrence, or time;
- attestation permission or Source Receipt Policy applicability;
- authorship, speaker, principal, session, interaction, or entrusted-case
  identity;
- access, inspection, storage, disclosure, association, or reuse permission;
- interpretation, objective, crossing, orientation, need, accompaniment,
  journey, candidate, explanation, or media operation;
- runtime behavior of any kind.

## Constitutional audit question

> Does every registry claim define only a canonical acquisition-interface
> contract and its definition succession, or has canonical identity been
> allowed to assert implementation, deployment, conformance, observation,
> receipt, capture points, permission, representation meaning, or runtime
> behavior?

Any field, validator, publication path, or consumer behavior permitting the
second case is outside this registry's jurisdiction.

## Architectural test plan

### Identity and version

- Interface version is labeled and validated only as definition version.
- A code, package, build, image, adapter, deployment, host, process,
  configuration, or schema version cannot acquire definition-version authority
  without exact governed registry publication and lineage; coincidental string
  equality creates no correspondence.
- Every authoritative reference contains exact registry identity, registry
  version, registry digest, interface identity, definition version, and
  definition digest.
- Unknown, incomplete, aliased, normalized, or locally reconstructed identities
  fail closed.

### Complete registry

- The complete registry is finite and canonically ordered.
- Interface identity and definition-version pairs are unique.
- Duplicate definition digests under different identities fail closed.
- Conflicting predecessor claims fail closed.
- Runtime-selected subsets cannot masquerade as the complete registry.

### Digest and structural correspondence

- Complete governed parents are structurally revalidated from serialized
  content.
- Definition and registry digests reproduce exact canonical content bytes.
- Any definition-content or governed-parent change changes the applicable
  digest.
- Unchecked copied objects are revalidated before use.
- Construction does not mutate caller-owned collections.

### Succession

- Changed canonical content under an unchanged definition version fails closed.
- A valid successor records exact predecessor identity, version, and digest.
- Operational redeployment without definition change does not mint a new
  interface definition.
- A definition-changing configuration revision requires explicit succession.
- Runtime cannot enact or silently infer succession.

### Negative authority

- No registry field can record implementation, deployment, host, process,
  runtime configuration, observation, receipt, or health state.
- No capture-point identity or semantics can enter an interface definition.
- No representation meaning can be authored locally.
- No policy grant or attestation permission can enter the registry.
- No registry outcome can claim that an interface exists or was used.

### Structural isolation

- Production import audits prove no dependency on acquisition adapters,
  deployment systems, capture points, Source Receipt Policy, Source Receipt
  Authority, Prompt Evidence Preservation, identity, case, cognitive, provider,
  or media packages.
- Repository-wide reference audits prove no alternate production component can
  mint an authoritative acquisition-interface registry entry.

## Compatibility impact

This contract changes no existing production behavior or artifact.

Existing provider interfaces, Python protocols, classes, CLI commands, package
versions, source labels, configuration files, and deployment identifiers are
not acquisition-interface registry entries. They must not be re-blessed as
canonical definitions through a compatibility adapter or inferred migration.

A future implementation must begin with explicit governed definitions and may
relate legacy implementation objects only through a separately authorized
conformance boundary.

## Successor boundary

A future Capture Point Registry may consume an exact published acquisition-
interface definition as an authoritative parent. It may not reconstruct,
extend, or reinterpret that definition.

Source Receipt Policy may eventually reference both registries after each has
independently earned authority. This contract does not authorize either future
boundary.

## Stop point

This phase stops at a provisional Acquisition Interface Registry contract.

It does not implement or define:

- registry publication;
- canonical serialization profile;
- protocol or capability definitions;
- acquisition-interface registry schemas or artifacts;
- capture-point registry;
- implementation, deployment, configuration, or conformance authority;
- Source Receipt Policy;
- acquisition adapters;
- Source Receipt Authority;
- Prompt Evidence Preservation;
- any runtime operation.

The Acquisition Interface Registry remains constitutionally nonexistent at
runtime until this contract is approved, its independently governed parents and
publication authority exist, an implementation is separately authorized and
validated, and all prerequisites remain in exact correspondence.

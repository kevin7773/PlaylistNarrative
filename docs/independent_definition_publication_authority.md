# Independent Definition Publication Authority — Provisional Contract

## Status

This document is a provisional contract for the authority required to publish
the first Canonical Serialization Profile without requiring that profile to
serialize itself.

It follows a no-change audit of existing publication, identity, versioning,
immutability, digest, and succession conventions. The audit found that
definition publication is legitimate in kind when publication mandate,
publication decision, preservation, and correspondence remain distinct.

This contract is not an implementation and creates no executable jurisdiction.
No publication-mandate artifact, authenticated governance-principal authority,
definition-publication boundary, publication event artifact, or publication
substrate has been implemented.

## Purpose

Independent Definition Publication Authority answers exactly one question:

> Was this exact immutable publication object adopted or refused as this exact
> governed definition identity and definition version through an exact
> authorized publication decision?

Its function is to bind governed status to one exact object. It does not create,
transform, serialize, interpret, validate, repair, or authenticate the contents
of that object.

## Governing claim

An adopted publication event may make only this positive claim:

> Under exact publication authority A and scope S, this exact immutable
> publication object O was adopted as governed definition D at definition
> version V.

The publication mechanism receives one exact immutable publication object
before the adoption decision is enacted. Publication then binds authority to
that exact object.

Receipt alone does not grant authority. Adoption does not change the object. It
changes the object's governed status.

## Authority

Independent Definition Publication Authority gains one authority:

> Enact and immutably record an authorized adoption or refusal decision for one
> exact publication object under one exact publication mandate.

For an adoption, the boundary may establish:

- that one exact authorized publication decision occurred;
- the exact immutable publication object governed by that decision;
- the exact definition class and publication scope;
- the exact canonical definition identity assigned by the decision;
- the exact definition version assigned by the decision;
- exact predecessor lineage when the decision enacts an authorized successor;
- the resulting status `adopted`;
- the exact mandate and authorization-evidence lineage supporting the decision.

For a refusal, the boundary may establish:

- that one exact authorized refusal decision occurred;
- the exact immutable publication object considered by that decision;
- the exact proposed definition class, identity, version, and scope;
- exact proposed predecessor lineage, when supplied;
- the resulting status `refused`;
- the exact mandate and authorization-evidence lineage supporting the refusal.

A refusal establishes no governed definition and creates no successor.

## Separation of responsibilities

### Publication mandate

Publication mandate answers:

> Who or what may authorize publication, for which definition classes, within
> which namespace and scope, and with which permitted actions?

The mandate is a normative prerequisite supplied by a separate authority. It
must establish at least:

- exact mandate identity and version;
- the exact authorized governance principal or decision authority;
- permitted definition classes;
- permitted definition-identity namespace and scope;
- whether definition identity and version must be supplied through independent
  authoritative lineage or may be assigned by the publication decision;
- when assignment is permitted, the exact identity and version assignment
  powers;
- whether refusal decisions are permitted;
- whether successor publication is permitted;
- any exact predecessor or succession constraints;
- mandate applicability and succession lineage.

The publication boundary may apply a mandate. It may not author, expand,
reinterpret, or approve the mandate it applies.

### Publication decision

Publication decision answers:

> Did the authorized decision authority adopt or refuse this exact object under
> this exact declaration and mandate?

The decision and the binding of governed publication status belong to one
constitutional boundary. The decision exercises mandate authority; the binding
records its result.

A storage service, Git operation, signature verifier, workflow runner, or
runtime validator may execute mechanics on behalf of the boundary. None may
substitute its own operation for the authorized decision.

### Publication preservation

Publication preservation retains the immutable historical record of:

- the exact publication object;
- the exact publication declaration;
- the exact mandate lineage;
- the exact authorization evidence;
- the adoption or refusal decision;
- predecessor lineage;
- any derived correspondence records.

Preservation is a duty of the publication boundary. Storage, replication,
retrieval, and substrate-specific retention are implementation concerns.

Preservation does not create the adoption decision. Repository or storage
presence without an authorized decision remains storage presence only.

### Correspondence records

Hashes, checksums, signatures, Git object names, repository commit identifiers,
storage keys, and other substrate-native identifiers may help retrieve or
verify the preserved object and event.

They are derived correspondence records. They do not grant publication mandate,
prove authorized adoption, establish definition identity, or authorize
downstream use.

## Why mandate and execution are separate

Publication mandate and publication execution require separate authorities.

The mandate defines conditional jurisdiction. The publication boundary applies
that already-authoritative jurisdiction to one exact proposal. If one boundary
could invent its mandate while publishing, it could authorize any object,
definition class, namespace, version, or successor it wished to publish.

The separation is:

```text
Publication Mandate Authority
    establishes who may decide what within which scope
                    ↓
Independent Definition Publication Authority
    enacts one authorized adoption or refusal
                    ↓
Immutable publication event
```

The technical executor may be part of the publication boundary's
implementation topology. It gains no independent publication authority.

## Exact authoritative prerequisites

Before executable publication jurisdiction can exist, all of the following
must exist and remain in exact correspondence.

### 1. Approved publication contract

An approved contract must define the publication boundary's one claim,
prerequisites, refusals, event semantics, preservation duties, succession, and
conformance requirements. This provisional document does not become approved
merely by existing.

### 2. Immutable Publication Mandate

The complete mandate must independently establish the permitted decision
authority, definition class, namespace, scope, identity/version mode, any
assignment powers, and succession powers.

No default, inferred, inherited-by-proximity, or self-authored mandate is
permitted.

### 3. Authenticated authorization evidence

Evidence that the decision came from the mandate-authorized governance
principal or decision authority must already have earned authentication through
a separate authority appropriate to governance decisions.

Identity evidence alone is insufficient. The evidence must correspond to:

- the exact mandate;
- the exact publication object;
- the exact publication declaration;
- the exact requested decision;
- the exact decision authority and scope.

A valid signature may contribute authentication evidence. Possession or use of
a signing key does not establish publication jurisdiction without the mandate.

### 4. Exact publication object

The boundary must receive one finite byte sequence as the exact publication
object before enacting the decision.

The publication declaration remains separate from the object's internal
contents. A title, filename, path, heading, embedded version, or assertion inside
the object cannot establish the external declaration.

### 5. Exact publication declaration

The proposal must declare separately from the object:

- exact publication-event proposal identity;
- exact definition class;
- exact requested canonical definition identity;
- exact requested definition version;
- exact independent identity/version authority lineage when the mandate requires
  supplied identity;
- exact publication scope;
- requested outcome;
- exact predecessor identity and version when succession is proposed.

The boundary validates the declaration against the mandate. It does not derive
the declaration from the publication object.

### 6. Exact preservation substrate

An implementation must provide substrate-native mechanics capable of retaining
the exact publication object and complete event history without requiring the
Canonical Serialization Profile being published.

The substrate must expose which exact bytes constitute the preserved object and
must prevent silent replacement. Its native identity and integrity mechanisms
remain preservation mechanics and correspondence records, not publication
authority.

## Publication object

The publication object may be any finite byte sequence, including:

- an empty byte sequence;
- bytes that do not decode as text;
- malformed text or structured data;
- semantically uninterpretable content;
- content that appears incomplete, incoherent, unsafe, or incorrect;
- content whose internal identity or version assertions conflict with the
  external publication declaration.

The publication boundary does not decide what those properties mean. A mandate
may require separately authoritative review or conformance evidence before an
authorized decision is issued, but the publication boundary may not perform
that review itself.

If an authorized decision adopts malformed or incoherent bytes, the publication
event may still be constitutionally valid as an adoption. It establishes no
claim that the adopted definition is useful or correct.

The boundary shall not, before or during adoption:

- decode and re-encode the object;
- normalize Unicode;
- normalize line endings;
- trim or pad content;
- reorder fields or records;
- parse and reserialize structured data;
- repair malformed material;
- replace unsupported bytes;
- render and recapture the object;
- substitute semantic equivalence for byte identity.

Publication binds authority to the exact object received.

## Receipt versus publication

Receiving the object is an input event and preservation requirement within this
boundary. It does not establish authorship, provenance before the publication
boundary, or Source Receipt Authority.

The publication boundary claims only that this is the exact object considered
by its decision. If upstream authorship, submission identity, or transport
provenance matters to a mandate, those claims must arrive through separately
authenticated authority.

Receipt without an authorized adoption decision leaves the object unadopted.

## Definition identity and version binding

Every adoption binds one exact definition identity and definition version to
the exact publication object. The source of that identity and version is
controlled by the mandate and has exactly two permitted modes.

### Mandate-authorized assignment

The publication decision may assign definition identity, definition version,
or both when—and only when—the exact mandate expressly grants the corresponding
assignment power for that definition class, namespace, and scope. In this mode,
the adopted publication decision establishes the assigned identity or version
as well as binding it to the exact object.

No pre-existing registry is required to assign the first identity in a
mandate-governed namespace. Requiring the first definition to pre-exist in the
registry being created would reproduce the bootstrap problem.

### Independently authorized identity

When the mandate requires definition identity, definition version, or both to
be supplied, those values must already have authoritative lineage from the
independent registry or governance authority named by the mandate. Publication
revalidates that exact lineage and binds the adopted object to the supplied
identity and version. It does not assign, alter, normalize, or reinterpret them.

In either mode, the external publication declaration carries the exact identity
and version presented for the decision. Identical wording inside the publication
object does not assign or authenticate identity.

A filename, path, repository directory, branch name, tag, document heading,
package name, or internal version string cannot substitute for the adopted
definition identity and version.

Where a definition registry or other identity authority supplies identity or
version, publication must preserve its exact authority and predecessor lineage
as required by the mandate. Publication does not silently append to or rewrite
a registry through filesystem placement.

## Outcomes

Exactly one publication-decision outcome exists for each valid decision event:

- `adopted`;
- `refused`.

Neither outcome is a processing failure.

Requests that cannot establish exact object identity, mandate correspondence,
authorization evidence, declaration identity, or required predecessor lineage
fail closed before a publication decision. Such malformed or unauthorized
requests are not recorded as authorized refusals because the boundary lacks
jurisdiction to make a decision about them.

## Adoption

Adoption binds governed definition identity and version to the exact publication
object under the exact mandate and scope.

Adoption does not:

- alter the object;
- validate internal assertions;
- create an implementation;
- establish conformance;
- activate downstream use;
- prove correctness, safety, coherence, or completeness.

## Refusal

An authorized refusal must be preserved as an immutable publication event.

The refusal records what exact object and declaration the authorized decision
authority refused under which exact mandate. It prevents future history from
reconstructing the absence of adoption as though no decision occurred.

Refusal does not:

- make the object invalid outside this publication event;
- prohibit a later proposal;
- create a governed definition;
- establish that the object's contents are wrong, unsafe, or incoherent;
- authorize deletion of the object or prior event.

A later proposal concerning the same bytes is a new publication event with its
own mandate, declaration, authorization evidence, and decision.

## Succession

Successor publication requires all of the following:

- an exact authoritative predecessor definition identity and version;
- exact predecessor publication-event lineage;
- the exact predecessor publication object or an immutable exact reference to
  it through the preservation substrate;
- a publication mandate explicitly permitting succession for that definition
  class, namespace, and scope;
- authenticated authorization evidence covering the proposed successor;
- a new exact publication object;
- a new definition version;
- a new authorized adoption decision.

The successor decision establishes that the newly adopted definition succeeds
the predecessor. It does not modify, invalidate, reinterpret, or delete the
predecessor.

If succession permission is absent, a publication boundary cannot infer it from
shared identity, higher version text, repository ancestry, filename similarity,
or object content.

## Immutable publication event

Every authorized adoption or refusal produces an immutable publication event
record preserving:

- event identity;
- exact publication object bytes or an immutable substrate-native reference
  that resolves to those exact bytes;
- exact publication declaration;
- complete mandate identity, version, content, and lineage;
- complete authenticated authorization evidence;
- exact decision authority;
- outcome;
- predecessor lineage when applicable;
- derived correspondence records;
- explicit non-claims.

The first event record may use the preservation substrate's native exact-object
and record mechanics. It need not use the Canonical Serialization Profile being
published.

Once a Canonical Serialization Profile is authoritative, future publication
contracts may separately authorize canonical publication artifacts. That later
capability cannot retroactively change the first event's authoritative object or
history.

## Correspondence records

A correspondence record may contain:

- a cryptographic hash over the exact preserved publication-object bytes;
- a substrate-native immutable object identifier;
- a commit or object identifier;
- a signature-verification result;
- a replication or storage-integrity checksum.

Each record must identify exactly:

- the bytes or substrate object to which it corresponds;
- the algorithm or native identity mechanism used;
- its role as correspondence rather than authority.

A digest may be calculated before or after adoption for operational purposes.
Its temporal position does not change its jurisdiction. It never grants
publication authority.

## First Canonical Serialization Profile

The first Canonical Serialization Profile may be published through
substrate-native exact-byte preservation.

The publication mechanism:

1. receives the exact profile publication object;
2. preserves those exact bytes without applying the profile;
3. validates exact mandate and authorization evidence;
4. enacts the authorized adoption decision;
5. binds the declared profile identity and definition version to those bytes;
6. records substrate-native identifiers or hashes as correspondence.

The profile does not serialize itself and supplies none of the authority for its
own adoption.

After adoption, the profile may govern canonical serialization prospectively
where separately authorized contracts reference it. It does not retroactively
replace the substrate-native publication object.

## Git and repository mechanics

Git may serve as one preservation substrate, but no Git operation establishes
publication authority by itself.

The following substitutions are forbidden:

- repository presence as adoption;
- `git commit` as an authorized publication decision;
- merge as publication authority;
- push as publication authority;
- branch or tag membership as publication status;
- commit-author or committer text as authenticated decision authority;
- Git signing-key possession as publication mandate;
- a Git object ID as definition identity;
- a filename or path as definition identity;
- write access as governance authority.

Git may preserve exact blob bytes and historical relationships. If used, the
publication event must explicitly identify which substrate-native object is the
authoritative publication object. Working-tree bytes, staged blob bytes,
committed blob bytes, and rendered text must not be treated as interchangeable.

Repository configuration, including line-ending conversion, must not leave the
publication capture point ambiguous.

## Downstream use

Publication does not automatically authorize downstream use.

An adopted definition is authoritative as the definition identity and version
established by its publication event. A downstream boundary still requires its
own contract and exact authority to:

- access the publication object;
- reference the definition;
- apply the definition;
- test conformance;
- publish a registry containing it;
- execute behavior described by it.

Publication status is not applicability or permission.

## Essential non-claims

The publication event must record literal non-claims that it did not establish
that the adopted or refused object is:

- correct;
- coherent;
- safe;
- complete;
- useful;
- valid under its internal assertions;
- executable;
- implemented;
- deployed;
- conformant;
- empirically true;
- authored by a claimed person;
- semantically understood;
- authorized for downstream access or use.

It must also record that publication did not:

- decode, normalize, repair, reorder, or semantically reconstruct the object;
- create its mandate;
- authenticate its own decision authority;
- infer definition identity or version from internal content or storage
  location;
- make any hash, signature, key, repository, or storage system a source of
  publication jurisdiction.

## Core invariants

- Publication applies an independently authoritative mandate.
- The boundary receives one exact object before deciding adoption or refusal.
- The external declaration remains separate from internal object assertions.
- Adoption binds authority to the exact unchanged object.
- Refusal binds no definition authority but remains immutable history.
- Definition identity and version assignment never exceed mandate scope.
- Succession requires exact predecessor lineage and explicit succession
  permission.
- Every decision preserves complete mandate and authorization-evidence lineage.
- Preservation mechanics do not create adoption.
- Correspondence records do not create legitimacy.
- Publication authorizes no downstream use.
- The first Canonical Serialization Profile need not serialize itself.
- New decisions create new immutable events; history is never rewritten.

## Constitutional audit question

> Did independently authorized governance adopt or refuse this exact preserved
> object under this exact declaration and mandate, or has storage, Git, a file
> path, signature, hash, write access, internal assertion, or technical operation
> been mistaken for publication authority?

Only the first case lies within this boundary's jurisdiction.

## Architectural test plan

### Mandate and authorization

- Complete mandate identity, version, content, scope, and applicability
  correspond exactly.
- Authorization evidence independently authenticates the exact decision
  authority and exact proposal.
- Identity or signature evidence without mandate authority fails closed.
- The publication boundary cannot author or expand its mandate.

### Exact object

- Every possible finite byte value, including empty and undecodable bytes, can
  be preserved without transformation.
- Line endings, Unicode, whitespace, malformed data, and unsupported content
  remain byte-identical.
- Internal filenames, headings, identities, versions, and approval assertions
  cannot enter the external publication declaration.
- Working, staged, committed, stored, and rendered representations cannot be
  conflated.

### Decision outcomes

- Exactly one adopted or refused outcome exists for every authorized decision.
- Adoption establishes exact definition identity and version under mandate.
- Refusal establishes no definition and remains immutable history.
- Unauthorized or structurally incomplete requests fail before decision and
  cannot masquerade as authorized refusals.

### Identity and succession

- Identity and version assignment remain inside the mandate-granted namespace,
  scope, and assignment powers.
- Identity and version supplied by an independent authority are bound exactly;
  publication cannot reassign or reinterpret them.
- Filename, path, branch, tag, internal text, or hash cannot assign definition
  identity.
- Successor adoption requires exact predecessor publication lineage and
  explicit mandate permission.
- A successor never mutates the predecessor.

### Preservation and correspondence

- The exact object, declaration, mandate, authorization evidence, decision, and
  lineage remain retrievable as one historical publication event.
- Substrate-native IDs and hashes reproduce their exact referenced objects.
- Changing or removing a correspondence record does not rewrite the historical
  adoption decision.
- Storage or repository presence without adoption remains non-authoritative.

### First-profile bootstrap

- The first profile is preserved and adopted without invoking its own
  serialization rules.
- Substrate-native exact-byte identity remains distinct from later
  profile-defined canonical bytes.
- A derived digest verifies correspondence but does not participate in the
  authorization decision.

### Negative authority

- Publication establishes no correctness, coherence, safety, completeness,
  execution, implementation, deployment, conformance, empirical truth, or
  downstream-use claim.
- Git commit, merge, push, signature, hash, key possession, write access, and
  internal document assertions cannot satisfy publication mandate.
- No publication path decodes, normalizes, repairs, reorders, or reconstructs
  the object.

### Structural isolation

- Production import audits prove no dependency on Source Receipt, acquisition
  interfaces, capture points, Source Receipt Policy, adapters, objective,
  curriculum, accompaniment, provider, or media packages.
- Repository-wide reference audits prove no alternate production component can
  mint an authoritative definition-publication event.

## Compatibility impact

This contract changes no existing production behavior or artifact.

Existing files, Git objects, commits, merges, pushes, tags, signed commits,
documents, registries, policy constants, and runtime schemas are not formal
definition-publication events. They must not be retroactively re-blessed through
a compatibility adapter.

Existing scoped user authorization followed by commit and push is a repository
workflow. This contract does not declare that workflow to be the missing formal
publication mandate or publication artifact.

## Stop point

This phase stops at a provisional Independent Definition Publication Authority
contract.

It does not implement or define:

- Publication Mandate Authority;
- governance-principal authentication;
- publication substrate;
- publication requests or event schemas;
- publication runtime;
- Canonical Serialization Profile;
- Source Representation Vocabulary;
- Transformation Registry;
- Local-Order Semantics;
- Acquisition Interface Registry implementation;
- Capture Point Registry;
- Source Receipt Policy or Authority;
- adapters or downstream use.

Independent Definition Publication Authority remains constitutionally
nonexistent at runtime until this contract is approved, an exact mandate and
authenticated authorization authority exist, substrate-native preservation is
implemented, and all prerequisites remain in exact correspondence.

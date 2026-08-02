# Architectural Constitution: Delegated Authority and Immutable Lineage

- **Status:** Proposed constitutional doctrine
- **Maturity:** Complete enough to test; intentionally frozen pending independent
  subsystem conformance
- **Scope:** Governance of authoritative claims throughout Penny
- **Authority:** Not yet ratified as authoritative project doctrine

> **Ambiguity is resolved at a boundary. Authority is recorded in an artifact.
> Trust moves forward; history is never reconstructed.**

## Preamble

The Playlist Narrative Engine is founded on bounded authority. Each subsystem
boundary is entrusted to resolve one class of uncertainty exactly once. When
that uncertainty is resolved, the resulting authority is recorded in an
immutable artifact that becomes the sole source of truth for that decision.

Downstream boundaries consume established authority without reconstruction. New
information produces successor artifacts with explicit lineage rather than
rewriting history. Trust advances through the system as a chain of immutable
guarantees, preserving provenance, explainability, reproducibility, and
institutional integrity.

This Constitution governs authority, not topology. A boundary may be realized
by one class, several collaborating services, a distributed workflow, or a
future execution model. Its constitutional power and duty attach to the class
of uncertainty it resolves, not to the implementation that currently realizes
it.

This Constitution does not constrain what Penny may learn to do. It constrains
where authority may be established and how that authority must be recorded,
applied, succeeded, and delegated.

> **Penny does not merely produce correct decisions. Penny produces decisions
> whose authority is constitutionally legitimate, whose applicability is
> explainable, and whose lineage is immutable.**

## Status

This document is a proposed institutional charter for the Playlist Narrative
Engine. It defines a constitutional hypothesis governing the establishment,
preservation, succession, applicability, and delegation of authority.

The doctrine is intentionally frozen pending independent conformance by at
least one subsystem beyond Candidate Formation. It is therefore not yet the
authoritative governance document for the repository.

Publication records the proposed doctrine for review and testing.
Constitutional authority will be earned through demonstrated generality rather
than publication alone.

## I. First Principle

Ambiguity shall be resolved at an authorized boundary. The authority created by
that resolution shall be recorded in an immutable artifact. Downstream
boundaries shall consume the resulting guarantee without reconstructing the
reasoning or mutable conditions that established it.

If new information genuinely changes an authoritative truth, the system shall
create a versioned successor artifact and begin a new traceable path. It shall
not silently modify, reinterpret, or replace the historical artifact.

## II. Constitutional Law: Bounded Authority

Only one boundary may resolve a particular class of uncertainty.

Every boundary receives both a power and a duty:

- **Power:** the exclusive authority to resolve one defined class of
  uncertainty.
- **Duty:** the obligation to refuse every class of uncertainty outside that
  grant.

Capability does not imply authority. A boundary shall not establish a claim
merely because it possesses sufficient data, code, access, or computational
ability to do so. A claim is legitimate only when it is established by the
boundary constitutionally authorized to resolve that uncertainty.

## III. Conservation Law: Authority Is Not Duplicated

Authority may be delegated, but it may not be duplicated.

A successor boundary may rely on an established guarantee and may add the one
new guarantee within its own grant. It may not create a parallel origin for an
existing authority, reproduce that authority through independent reasoning, or
offer an alternate production path around the authoritative boundary.

Delegation transfers a guarantee; it does not transfer permission to recreate
the authority that produced it.

## IV. Chain of Delegated Authority

Every subsystem boundary participates in the same constitutional lifecycle:

```text
Receive uncertainty and delegated guarantees
                    ↓
Perform bounded reasoning under an exclusive grant
                    ↓
Establish one new authoritative claim
                    ↓
Record that authority in an immutable artifact
                    ↓
Delegate the accumulated guarantees downstream
```

Each boundary is simultaneously a consumer of prior authority and a bounded
authority for its successor. It validates only its assigned responsibility. It
does not keep prior authority perpetually open for reinterpretation.

Every decision in Penny must be explainable by following a single, immutable
chain of delegated authority from ambiguity to applicability.

## V. Authority, Applicability, and Succession

> **Authority is immutable. Applicability is contextual. Succession determines
> applicability without altering authority.**

An authoritative artifact does not cease to be historically true when a
successor exists. It may cease to govern future decisions, but the authority it
records remains valid for the decisions and context to which it applied.

The system therefore recognizes two kinds of time:

- **Historical time** answers, “What happened?” It is immutable and records the
  artifacts, lineage, and governing context of completed decisions.
- **Operational time** answers, “What governs this decision now?” It may advance
  through explicit succession but shall never rewrite historical time.

Mutable pointers, indexes, and caches may accelerate discovery of an applicable
artifact. They are optimization structures, not authority. They shall never be
the sole explanation of why one artifact governed a decision instead of
another. Applicability must remain reconstructible from immutable lineage and
explicit succession.

## VI. Constitutional Corollaries

### Corollary I — Single Authority

Authority for a class of truth is established exactly once. No later boundary
may authenticate, reinterpret, or recreate that authority.

### Corollary II — Immutable Lineage

Every authoritative claim possesses one complete ancestry. Lineage may be
consumed and extended. It may not be rewritten.

### Corollary III — Trust Transfer

Each boundary validates only its own responsibility. After validation, it
exports immutable facts. Successors consume those facts without repeating the
reasoning that established them.

### Corollary IV — No Competing Histories

The system shall not maintain multiple authoritative representations of the
same history. Every downstream artifact shall reference the one authoritative
lineage rather than reconstructing or independently narrating it.

### Corollary V — Resume Identity

Resume establishes identity; it does not estimate similarity. If the governing
artifact lineage and applicable context cannot be proven exactly, the prior
process is not resumed. A new process and lineage must be established instead.

### Corollary VI — Boundary Ownership

Each boundary owns exactly one class of truth. It may exercise its granted power
and must observe its corresponding duty. No boundary may acquire another
boundary's authority through convenience, proximity, or implementation detail.

### Corollary VII — Authority Is Monotonic

Once an artifact becomes authoritative, it is never modified. Subsequent
reasoning creates versioned successor artifacts connected by explicit lineage.
Authority may be superseded in operational applicability, but it is never
retroactively changed. The lineage grows; history does not mutate.

### Corollary VIII — Explainable Applicability

The artifact governing any decision shall be determinable from immutable
lineage and explicit succession. Mutable state may accelerate retrieval but
shall never be the sole explanation of why one authoritative artifact governed
a decision instead of another.

### Corollary IX — Constitutional Completeness

Every authoritative claim within Penny shall be attributable to exactly one
constitutional grant of authority. Claims lacking an identifiable
constitutional origin are invalid regardless of their apparent correctness.

Correctness is necessary but insufficient. A decision is constitutionally
legitimate only when the authority establishing it, the artifact recording it,
and its applicability to the decision are all explainable.

## VII. Subsystem Charter

Every subsystem boundary shall maintain a charter answering the same nine
questions:

1. **Input** — What uncertainty and delegated guarantees does this boundary
   receive?
2. **Power** — Which uncertainty is this boundary exclusively authorized to
   resolve?
3. **Duty** — Which uncertainties is this boundary constitutionally forbidden
   from resolving?
4. **Authority** — What truth becomes authoritative at this boundary?
5. **Artifact** — What immutable record captures that authority?
6. **Guarantee** — What may downstream boundaries safely assume?
7. **Delegation** — Which successor receives the guarantee?
8. **Succession** — Under what conditions must a new authoritative artifact be
   created?
9. **Applicability** — How is the artifact governing a particular decision
   proven without rewriting history?

A boundary is incomplete if any answer depends solely on mutable system state,
undocumented inference, duplicated metadata, or authority exercised elsewhere.

## VIII. Artifact Completeness

Every authoritative artifact must permit another engineer to reconstruct why
the artifact exists and why it governed a decision without consulting mutable
system state.

An artifact is constitutionally incomplete if it omits the immutable evidence,
lineage, governing authority, succession relationship, or applicability record
required to provide that explanation. Reconstructing missing history later does
not cure the omission; it creates a competing claim about prior authority.

## IX. Constitutional Test

A feature conforms to this Constitution only if it satisfies all of the
following:

- it resolves no uncertainty outside its assigned boundary;
- it establishes authority exactly once;
- it records that authority in an immutable artifact;
- it exports a guarantee rather than mutable state;
- it does not reconstruct prior authority;
- it creates successor artifacts rather than rewriting history;
- it preserves explainable applicability through immutable lineage;
- it extends the existing chain of delegated authority rather than creating an
  alternate path; and
- every authoritative claim it makes is attributable to an identifiable
  constitutional grant.

The standing design-review question is:

> **Does this feature extend the existing chain of delegated authority, or does
> it create a competing path around it?**

A feature does not conform merely because its code is clean, its tests pass, its
output appears correct, or its behavior is desirable. Those qualities cannot
legitimize a claim established without constitutional authority.

## X. Conformance and Amendment

Doctrine, conformance, and implementation are distinct:

- **Doctrine** defines timeless governance.
- **Conformance** demonstrates that a boundary obeys the doctrine.
- **Implementation** realizes a conforming boundary using current technology.

Conformance applications should be common. Constitutional amendments should be
rare. An amendment requires demonstrated insufficiency revealed through
application to an independent subsystem. Anticipated possibilities,
implementation preference, or a desire for speculative completeness do not
justify amendment.

This proposed Constitution shall not become authoritative merely because its
language is persuasive. It must earn authority by surviving repeated subsystem
conformance without requiring its terms to be reinterpreted. Until independent
conformance demonstrates that generality, the doctrine remains proposed and
intentionally frozen.

## Closing Doctrine

Every legitimate extension of Penny shall participate in the same
constitutional lifecycle:

> **Resolve uncertainty. Establish authority. Record immutably. Transfer
> trust.**

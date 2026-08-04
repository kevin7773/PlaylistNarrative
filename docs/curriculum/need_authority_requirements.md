# Need Authority Requirements Contract

## Status

This document proposes the missing normative authority discovered during CU-3
contract review. It is not an implementation and does not authorize CU-3
production work.

The boundary is case-blind. It defines conditional sufficiency independently of
all empirical evidence. Publication records an immutable body of requirements;
it does not evaluate those requirements.

## Purpose

Need Authority Requirements answers exactly one question:

> What exact authenticated evidence grants would be sufficient before a
> proposed need type could legitimately acquire authority?

Its output is policy. It contains no assertion that any requirement has been
met, unmet, applicable, or invoked.

## Constitutional principles

> Requirements define sufficiency. They do not assert truth.

> Requirements define neither facts nor absence.

> Requirements create no authority over any individual case.

> Requirements may be applied but never rewritten by downstream conformance.

> Requirements remain independent of authenticated evidence until conformance.

Absence is meaningful only relative to an authoritative requirement. This
boundary defines the requirement side of that relation and never performs the
comparison.

## Proposed boundary conformance review

### Authority

The boundary gains one authority:

> Publish immutable, versioned sufficiency requirements that relate approved
> proposed-need-type identities to approved evidence-grant identities.

It defines only what would be sufficient under the exact governing policy.

### Refusal

The boundary must refuse to:

- inspect any person or case;
- consume an accepted objective, crossing, orientation, or uncertainty artifact;
- inspect authenticated evidence or evidence state;
- assert that an evidence grant exists, is missing, or is applicable;
- establish, infer, confirm, modify, prioritize, or reject a need;
- identify uncertainty or a jurisdictional blocker;
- orient attention;
- generate a question, prompt, response, or explanation;
- prescribe resolution or evidence acquisition;
- recommend accompaniment;
- inspect, form, score, rank, select, or sequence music;
- access providers or mutable external state;
- evaluate conformance;
- rewrite a published registry.

### Trust

The boundary may consume only normative authority:

- an immutable governing-policy artifact and canonical digest;
- an immutable proposed-need-type vocabulary and canonical digest;
- an immutable evidence-grant-definition vocabulary and canonical digest;
- exact schema, policy, vocabulary, and publication identities and versions.

None of those inputs may contain a case identifier, objective instance,
observation, evidence instance, evidence state, crossing, orientation candidate,
uncertainty, question, response, accompaniment, or music artifact.

### Audit

The constitutional audit is:

> Can the complete registry be constructed, validated, serialized, and reviewed
> without access to any individual case or empirical evidence instance?

A negative answer means normative authority and empirical authority have
collapsed into one boundary.

## Normative inputs

A future publication request must contain:

- an exact publication request identity;
- the complete governing-policy artifact and canonical SHA-256 digest;
- the complete proposed-need-type vocabulary and canonical SHA-256 digest;
- the complete evidence-grant-definition vocabulary and canonical SHA-256
  digest;
- the proposed complete requirement registry;
- an exact registry identity and version.

All parents must be structurally revalidated from their serialized content.
Frozen object possession is not proof of legitimacy.

The request must not contain optional context, metadata from a case, free-text
examples, proposed questions, expected answers, evidence observations, or
caller-authored applicability flags.

## Normative vocabularies

### Proposed-need-type vocabulary

The vocabulary defines only canonical need-type identities and versions that a
requirements registry may reference. It makes no claim that any need type is
present, desirable, applicable, or supported.

### Evidence-grant-definition vocabulary

The vocabulary defines only canonical evidence-grant identities, versions, and
typed-value schemas that a requirements registry may reference. It does not
contain evidence instances and cannot assert that any grant has been earned.

Vocabulary entries are immutable, canonically ordered, uniquely identified, and
changed only through explicit successor versions.

The exact vocabulary contracts are prerequisites and remain unimplemented.

## Requirement model

The future schema shall represent a complete
`NeedAuthorityRequirementRegistry` containing:

- registry identity and version;
- governing-policy identity, version, and canonical digest;
- proposed-need-type vocabulary identity, version, and canonical digest;
- evidence-grant vocabulary identity, version, and canonical digest;
- one or more canonically ordered `NeedAuthorityRequirement` definitions;
- explicit non-claims;
- canonical compact UTF-8 serialization;
- a SHA-256 digest of the complete canonical registry bytes.

Each requirement definition contains only:

- an exact requirement identity and version;
- one exact proposed-need-type identity and version;
- a nonempty, canonically ordered set of exact required evidence-grant identities
  and versions;
- an exact satisfaction operator authorized by the registry schema;
- exact policy lineage.

Schema version `1.0` should initially permit only the conjunction operator:

> Every listed evidence grant is required.

This deliberately excludes thresholds, weights, confidence, probabilities,
implicit alternatives, semantic similarity, and discretionary judgment. More
expressive operators require a new schema and policy lineage.

## Registry completeness and uniqueness

The registry schema must enforce:

- unique requirement identities;
- unique proposed-need-type grants within the registry;
- unique evidence-grant identities within each requirement;
- exact correspondence to both normative vocabularies;
- nonempty evidence-grant sets;
- fixed satisfaction semantics;
- deterministic UTF-8 ordering;
- complete governing-policy lineage;
- exact canonical digest verification.

A complete registry contains every requirement authorized by its declared
policy and vocabularies. Partial registries, caller-selected subsets, runtime
overrides, and fallback requirements fail closed.

## Publication artifact

The boundary produces one immutable
`NeedAuthorityRequirementRegistryArtifact` containing:

- the complete structurally revalidated normative parents;
- their canonical SHA-256 digests;
- the complete structurally revalidated registry;
- the registry's canonical SHA-256 digest;
- publication identity and version;
- explicit non-claims.

Publication has no case-dependent outcome. It either produces the exact valid
artifact or fails validation. There is no `matched`, `unmatched`, `missing`,
`satisfied`, `insufficient`, `uncertain`, or `need_established` result.

## Immutability and succession

A published registry is immutable.

Changing any requirement, proposed-need-type reference, evidence-grant
reference, satisfaction operator, policy parent, vocabulary parent, or canonical
ordering rule requires a successor registry identity/version and new digest.

Downstream consumers may:

- preserve the complete registry;
- reference its exact identity/version and digest;
- apply its requirements through a separately authorized conformance boundary.

They may not:

- edit requirements;
- omit requirements;
- add case-specific exceptions;
- reinterpret evidence-grant identities;
- substitute a locally reconstructed registry;
- retain the old identity/version after changing content.

## Independence from evidence

Requirement authority and evidence authority remain independent until
conformance:

```text
Established requirements ──┐
                           ├── Future conformance boundary
Established facts ─────────┘
```

The registry is valid without any evidence instance. An evidence artifact is
valid without judging sufficiency. Only a future conformance boundary may apply
one exact authoritative registry to one exact authoritative evidence artifact.

Conformance creates neither the rule nor the facts.

## Explicit non-claims

The artifact records literal non-claims that:

- no empirical evidence was inspected;
- no evidence grant was authenticated;
- no evidence sufficiency was evaluated;
- no requirement was applied to a case;
- no fact or absence was established;
- no need was established;
- no uncertainty was identified;
- no question or resolution strategy was generated;
- no accompaniment or music operation was performed.

## Successor boundary

This artifact may be consumed only by a separately authorized conformance
boundary together with independently authenticated evidence.

It does not directly authorize CU-3. CU-3 also requires the missing
person-specific evidence-authentication artifact and exact ancestry through
CU-1 and CU-2. Only after both normative and empirical prerequisites exist may
CU-3 contract review determine whether implementation is legitimate.

## Focused implementation test plan

Any future implementation must prove:

- exact normative-parent identity, typed-value, version, and digest
  correspondence;
- complete structural revalidation of frozen parent and registry objects;
- unique requirement, proposed-need-type, and evidence-grant identities;
- exact closed-world vocabulary correspondence;
- nonempty conjunction-only requirements in schema `1.0`;
- complete-registry enforcement with no subsets or runtime overrides;
- content changes under an unchanged identity/version fail closed;
- equivalent input permutations produce equal artifacts and byte-identical
  canonical serialization;
- caller-owned collections remain unchanged;
- no case or evidence artifact is accepted by any schema;
- no source code reads a person, objective instance, crossing, orientation,
  uncertainty, question, response, accompaniment, provider, or music artifact;
- no downstream interface can mutate or reconstruct the registry.

The decisive structural test is:

> Remove every case artifact and empirical evidence instance from the runtime.
> Can the complete requirement registry still be produced identically?

The answer must be yes.

## Stop point

This document defines the missing normative authority only. It does not define
the prerequisite vocabulary schemas, implement registry publication, inspect
evidence, evaluate sufficiency, identify uncertainty, implement CU-3, establish
a need, or authorize accompaniment.

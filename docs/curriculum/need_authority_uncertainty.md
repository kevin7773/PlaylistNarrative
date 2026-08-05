# CU-3 — Need Authority Uncertainty Contract

## Status

CU-3 is a proposed epistemic contract. It is not implemented.

Contract review identified two upstream authorities that do not yet exist in
the repository:

1. an immutable artifact authenticating person-specific evidence for the
   purpose of need authority; and
2. an immutable, versioned need-authority requirements registry defining which
   exact evidence grants are necessary for a proposed need to acquire authority.

The normative side is proposed separately in the
[Need Authority Requirements contract](need_authority_requirements.md).

CU-1 preserves an optional `particular_need`, but explicitly grants it no need
authority. EA-1 authenticates governed ending and beginning characteristics,
not person-specific need evidence. CU-2 produces unresolved orientation only.
CU-3 may not promote any of those fields into the missing authority.

Implementation is therefore prohibited until the two prerequisite contracts
exist and have been independently reviewed. This is a discovered authority gap,
not a request to expand CU-3.

The provisional [Penny Purpose](../purpose.md) supplies no missing authority and
does not make this contract executable. It is used here only to review whether
CU-3's proposed jurisdiction remains consistent with bounded accompaniment.

## Subject

CU-3's subject is not a need. It is:

> The unresolved distance between orientation and person-specific authority.

CU-3 is the boundary where Penny proves she is not yet entitled to know.
This distance describes a conformance relationship within one exact entrusted
case scope. It is not an uncertainty, deficit, obstacle, or condition attributed
to the person.

## Governing question

CU-3 answers exactly one question:

> What is the smallest remaining material uncertainty that must be resolved
> before a particular human need may legitimately gain authority?

It does not ask what question Penny should pose or how the uncertainty should
be resolved. Those are actions belonging to later boundaries.

## Governing principle

> Attention is not authority.

An orientation candidate may identify a recurring human condition worth
considering. It may never answer for the person, establish a need, or substitute
for person-specific evidence.

## Proposed boundary conformance review

### Authority

CU-3 gains one authority:

> Identify the minimal set of necessary, material, unresolved person-specific
> evidence grants that currently block need authority under an approved
> need-authority requirements registry.

It does not gain authority over the need itself.

### Refusal

CU-3 must refuse to:

- infer, confirm, modify, rank, or select a need;
- authenticate new evidence;
- treat orientation as evidence that a condition applies to the person;
- manufacture uncertainty or curiosity;
- generate a question, prompt, suggestion, or conversational turn;
- choose how uncertainty should be resolved;
- recommend a resolution workflow;
- decide that clarification is appropriate merely because CU-3 exists;
- establish accompaniment;
- create a soundtrack objective;
- inspect, form, score, rank, select, or sequence music;
- access providers or mutable external state;
- generate an explanation.

### Trust

CU-3 may consume only:

- the complete, structurally revalidated CU-1 artifact and canonical digest;
- the complete, structurally revalidated CU-2 artifact and canonical digest;
- a complete, structurally revalidated artifact containing person-specific
  evidence already authenticated for need-authority purposes;
- the complete immutable need-authority requirements registry and canonical
  SHA-256 digest;
- the exact entrusted-case scope identity authenticated by the future
  person-specific evidence authority; and
- exact policy, schema, objective, crossing, orientation, case-scope, and
  evidence lineage.

The CU-2 artifact must descend from the supplied CU-1 artifact exactly. Every
parent, policy, registry, and evidence identity must correspond without
trimming, case folding, Unicode normalization, aliases, fuzzy repair, semantic
similarity, or caller reconstruction.

### Audit

The provisional constitutional audit is:

> Has orientation answered for the person, or has CU-3 identified only the
> missing person-specific authority?

A stricter implementation audit follows:

> Can any uncertainty be emitted without an exact unmet requirement, complete
> authenticated evidence accounting, and proof that the requirement is both
> necessary and material to need authority?

## Required inputs

A future `NeedAuthorityUncertaintyRequest` must contain:

- an exact request identity;
- the accepted objective and canonical correspondence inherited through CU-1
  and CU-2;
- the complete revised `CrossingUnderstandingArtifact` and canonical SHA-256;
- the complete `CurriculumOrientationArtifact` and canonical SHA-256;
- the complete future person-specific evidence-authentication artifact and
  canonical SHA-256;
- the complete future need-authority requirements registry and canonical
  SHA-256;
- the exact entrusted-case scope identity and its authenticated lineage; and
- exact CU-3 policy identity and version.

The request shall contain no proposed question, desired answer, uncertainty
label, need value, accompaniment hint, event interpretation, free-text semantic
hint, or caller-authored evidence status.

The entrusted-case scope is a closed boundary on inspection and applicability.
It does not authorize CU-3 to inspect unrelated history, infer whole-person
characteristics, or reuse a result in another objective, experience, case,
artifact lineage, requirement version, or evidence state.

## Need-authority requirements registry

CU-3 cannot decide that something is missing without prior authority defining
what is required. The future registry must therefore be:

- immutable and versioned;
- canonically serialized and digest-addressed;
- closed-world for its declared version;
- schema-enforced for unique requirement, evidence-grant, and predicate
  identities;
- explicit about which proposed need authority each requirement governs;
- explicit about necessity and materiality;
- deterministic about jointly required evidence grants;
- free of questions, resolution advice, accompaniment, and music;
- changed only through a new registry identity/version and successor lineage.

CU-3 executes the registry. It does not author or reinterpret it.

## Person-specific evidence prerequisite

The future evidence artifact must distinguish at least:

- authenticated grant present;
- authenticated grant absent because evidence is unavailable;
- unsupported evidence;
- conflicting evidence;
- explicitly inapplicable evidence.

Those states must remain mutually exclusive and must not collapse into neutral,
typical, presumed, or inferred values. Generic supported text is insufficient.
Only a separately authorized authentication path may mint a person-specific
evidence grant for need authority.

Every grant must be bound to one exact entrusted-case scope. Evidence outside
that scope is inaccessible to CU-3; the existence of a broader history does not
authorize its inspection. A grant authenticated for one scope cannot satisfy a
requirement in another scope.

The exact schema and authentication mechanism belong to the prerequisite
contract, not CU-3.

## Minimality semantics

Every emitted uncertainty must be:

- **necessary:** removing the corresponding unmet requirement would change the
  registry's determination of whether a constitutional blocker remains;
- **material:** satisfying the corresponding evidence grant could legitimately
  change whether need authority is permitted to proceed;
- **minimal:** it identifies no broader topic, narrative, or curiosity than the
  exact missing grant requires.

When several evidence grants are jointly necessary, CU-3 records the smallest
complete set. It must not choose one arbitrarily, merge distinct grants into a
larger question-shaped uncertainty, or rank them probabilistically.

An orientation candidate may select which approved requirement set is relevant
only if the future registry explicitly and exactly authorizes that mapping.
Orientation itself remains unresolved and never supplies the missing evidence.

## Proposed immutable output

A future `NeedAuthorityUncertaintyArtifact` must preserve:

- schema and artifact identity;
- complete CU-1 and CU-2 parent artifacts and canonical digests;
- complete authenticated person-specific evidence artifact and digest;
- complete need-authority requirements registry and digest;
- exact accepted-objective, policy, and lineage correspondence;
- the exact entrusted-case scope identity and authenticated lineage;
- the exact proposed need-authority case being evaluated, supplied by an
  upstream authority rather than inferred by CU-3;
- zero or more canonically ordered unmet requirement records;
- exact evidence-grant accounting for every evaluated requirement;
- deterministic outcome and fixed reason codes;
- explicit non-claims;
- canonical compact UTF-8 serialization.

Each unmet requirement record identifies only:

- its governed requirement identity/version;
- the exact missing or non-authoritative evidence-grant identity;
- its evidence state;
- the immutable evidence and policy lineage establishing that state;
- why the requirement is necessary and material according to the registry.

It contains no question text, recommended action, expected response, emotional
interpretation, or accompaniment proposal.

An unmet record describes only the relationship between an established
requirement and authenticated evidence within the exact case scope. It does not
describe a deficiency, obstacle, condition, or unresolved issue in the person.

## Outcomes

Exactly one non-failure outcome is recorded.

### `material_uncertainty_identified`

One or more unmet requirements form the minimal complete set currently blocking
need authority.

This outcome does not authorize a question or resolution workflow.

### `no_material_uncertainty_identified`

CU-3 found no unmet requirement within its jurisdiction.

This does **not** mean:

- a need has been established;
- existing need text is authoritative;
- orientation applies to the person;
- accompaniment or expression may begin;
- the available representation is complete;
- the person is well, ready, fulfilled, or free of concern; or
- no personally meaningful uncertainty exists outside CU-3's jurisdiction.

It means only:

> No CU-3 jurisdictional blocker was found under the exact supplied authority.

A later boundary with a separate grant must determine whether person-specific
evidence actually establishes the need.

Malformed, mismatched, incomplete, forged, or unsupported authority inputs fail
request validation. They do not become uncertainty outcomes.

## Core invariants

- Attention is not authority.
- CU-3 never establishes a need.
- CU-3 never authenticates evidence.
- Every uncertainty descends from an exact unmet registry requirement.
- Every unmet requirement descends from exact authenticated person-specific
  evidence accounting.
- Orientation may route attention only through an explicitly authorized exact
  registry mapping; it cannot satisfy a requirement.
- No preserved CU-1 need text participates in uncertainty derivation.
- No event, metaphor, observation payload, free text, prior candidate wording,
  alias, normalization, or semantic similarity participates.
- Every comparison and conclusion is bound to one exact entrusted-case scope.
- No conclusion may be reused across a different objective, experience, case,
  artifact lineage, requirement version, or evidence state.
- No output characterizes the whole person or converts Penny's incomplete
  representation into a claim about the person.
- No uncertainty contains a resolution mechanism.
- No question exists in the request or artifact.
- No uncertainty is emitted merely because the boundary was invoked.
- The null outcome never establishes need authority.
- Complete parent and registry structures are revalidated, not trusted merely
  because a frozen model instance was supplied.
- Equivalent input permutations produce equal artifacts and byte-identical
  canonical serialization without mutating caller-owned inputs.

The central invariant is:

> Every recorded uncertainty must be necessary, material, and minimally
> sufficient to explain why need authority cannot yet be established.

## Explicit non-claims

CU-3 does not claim that:

- an orientation candidate applies to the person;
- a particular need exists;
- supplied need wording is valid or authoritative;
- the person should be asked anything;
- any uncertainty should be resolved now;
- a specific evidence source or interaction should resolve it;
- no blocker means a need is established;
- accompaniment or any expressive modality is appropriate;
- the person's representation is complete;
- the person is well, ready, fulfilled, or free of concern;
- the experience has a particular meaning or resonance;
- the person will respond or change in any particular way; or
- CU-3 has authority over identity, personal development, or Becoming.

## Successor boundaries

CU-3 authorizes no direct question, need, accompaniment, or music boundary.

Future work must separately define:

1. how an identified uncertainty may be resolved;
2. how resulting person-specific evidence is authenticated;
3. which boundary may establish a particular need from authenticated evidence;
4. only then, how faithful accompaniment through a separately authorized
   expressive modality may be considered.

Each requires its own authority and refusal contract.

## Focused implementation test plan

Implementation, once prerequisites exist, must prove:

- exact CU-1 and CU-2 ancestry and canonical digest correspondence;
- exact person-specific evidence authority and registry correspondence;
- exact entrusted-case scope correspondence and rejection of cross-context
  evidence or result reuse;
- complete structural revalidation of every frozen parent and registry;
- fixed accounting for every governed requirement;
- necessary, material, minimal uncertainty semantics;
- exact distinction among unavailable, unsupported, conflicting, inapplicable,
  and satisfied evidence grants;
- no orientation candidate can become evidence or need authority;
- no preserved CU-1 need can enter matching or branching;
- no event, metaphor, payload, free text, alias, or normalized value can enter;
- no question, resolution strategy, or expected answer can enter any schema;
- no fallback uncertainty is manufactured;
- null outcome semantics are literal and schema-enforced;
- null outcomes cannot encode completeness, wellness, readiness, fulfillment,
  absence of personal concern, or authority over meaning, response, change, or
  Becoming;
- deterministic UTF-8 ordering and byte-identical canonical serialization;
- caller-owned inputs remain unchanged;
- structural isolation from question generation, evidence authentication, need
  establishment, accompaniment, Journey Planning, Candidate Formation,
  sequencing, evaluation, providers, explanation, and music.

## Stop point

This document defines CU-3's proposed jurisdiction and records its missing
upstream authorities. It does not define the prerequisite schemas, implement
CU-3, generate questions, establish needs, or authorize accompaniment.

The next work is prerequisite vocabulary and person-specific evidence-authority
contract design, not CU-3 production code.

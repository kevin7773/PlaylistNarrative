# EA-1 — Evidence Authentication Contract

## Status

EA-1 is the missing authority boundary discovered during CU-2 adversarial
review. It is not presented as the next feature phase or as an expansion of
Penny's cognitive architecture.

CU-2 exposed an unproven assumption: exact rule execution is not legitimate
unless the structured characteristics entering the executor have themselves
earned authority from evidence. EA-1 records the boundary that was absent from
the trust chain.

EA-1 is implemented in isolation with immutable schema `1.0` requests and
artifacts, a governed crossing-characteristic vocabulary, exact confirmation,
six approved deterministic derivation rules, complete authenticated/withheld
accounting, digest-addressed rule-set authority, artifact content digests,
canonical serialization, and structural conformance tests.

This document defines the implemented authority boundary and the breaking impact
of inserting it before CU-1 and CU-2.

CU-2 implementation work is paused pending this prerequisite. This contract does
not authorize changes to EA-1, CU-1, CU-2, or production orchestration.

## Purpose

EA-1 gives one component exclusive responsibility for determining whether an
exact structured characteristic has legitimately been established by supplied
evidence.

It exists because neither deterministic exactness nor a `supported` label proves
that a characteristic value is authorized. A caller-authored value can be
perfectly reproducible and still lack a legitimate evidentiary origin.

EA-1 is therefore a prerequisite correction to the trust chain. It does not add
a new kind of understanding.

## What authority is missing?

Before this boundary was identified, CU-1 could accept arbitrary supported text
as an ending or beginning characteristic. CU-2 could then match that text
exactly. The executor did not interpret, but the system had not proven that the
matched value deserved to function as structured authority.

The missing authority is:

> The exclusive power to mint a governed structured characteristic from exact
> supplied evidence through an approved authentication path.

Evidence may contain, suggest, or resemble a characteristic without possessing
that authority.

The discovery arose from CU-2's adversarial review. It records why the
architecture changed, not merely where another artifact was inserted.

## What question does EA-1 answer?

EA-1 answers exactly one question:

> Which structured characteristics have legitimately earned authority from the
> supplied evidence?

Its central invariant is:

> Evidence may suggest a characteristic. Only an authorized authentication path
> may mint one.

## Constitutional authority

EA-1 derives from Foundation's doctrine of bounded authority:

> Ambiguity is resolved at a boundary. Authority is recorded in an artifact.
> Trust moves forward; history is never reconstructed.

It is the first executable boundary whose responsibility is epistemic rather
than cognitive. EA-1 does not ask what evidence means for a person's crossing.
It asks whether a governed characteristic has earned the right to participate
in later meaning-making.

CU-1 may not assume this authority because its constitutional responsibility is
crossing understanding. If CU-1 authenticates characteristic labels and derives
the crossing, it owns two classes of truth.

CU-2 may not assume this authority because its constitutional responsibility is
exact curriculum-rule execution. If CU-2 authenticates its inputs and applies
orientation rules, the executor becomes an interpreter.

Authority is therefore conserved:

- EA-1 authenticates structured characteristics;
- CU-1 derives the supported crossing;
- CU-2 executes governed curriculum orientation.

## Trust chain

### Evidence chain

```text
Raw observation
        ↓
Evidence Authentication
        ↓
AuthenticatedStructuredCharacteristicArtifact
        ↓
CU-1 Crossing Understanding
        ↓
CU-2 Curriculum Orientation
```

EA-1 establishes evidence authority. It does not establish the crossing or
apply curriculum knowledge.

### Governance chain

```text
Accepted Objective
        ↓
Authentication policy
        ↓
Authentication rule-set identity and digest
        ↓
Authorized authentication path
```

EA-1 sits at the intersection of evidence and governance. It does not create
either chain. It requires exact supplied observations and the exact immutable
authority permitted to authenticate them.

CU-2 has a separate governance chain consisting of curriculum identity,
orientation-policy identity, and orientation-rule-set digest. EA-1 does not
merge, replace, or interpret that later authority.

## Scope

### Power

EA-1 has the exclusive power to establish that one exact structured
characteristic is authorized by one approved authentication path.

### Duty

EA-1 must refuse to determine:

- what crossing is taking place;
- which recurring human condition may orient listening;
- what the person needs;
- what accompaniment may help;
- what objective music should serve;
- which music should be considered.

EA-1 authenticates characteristics. It does not interpret a life.

## Inputs

`EvidenceAuthenticationRequest` accepts only:

- an exact request identity;
- a complete `AcceptedObjectiveArtifact`;
- the accepted-objective canonical SHA-256;
- one or more immutable typed source observations;
- an exact characteristic-value schema identity and version;
- an exact authentication-policy identity and version;
- the exact approved authentication-rule-set identity, version, and canonical
  SHA-256.

Unknown fields are forbidden. No provider, curriculum, crossing, need,
accompaniment, journey, or music artifact may enter the request.

## Source observations

Every `AuthenticationSourceObservation` preserves:

- exact evidence identity;
- exact observation type;
- exact source type and source reference;
- canonical typed JSON payload;
- provenance required by its observation type.

Observation identities and payloads are preserved without trimming, case
folding, Unicode normalization, alias resolution, fuzzy matching, semantic
repair, or inferred defaults.

An observation remains evidence until an approved authentication method proves
an exact structured characteristic from it.

## Structured characteristics

An authenticated characteristic contains:

- exact characteristic identity;
- exact characteristic role;
- characteristic-value schema identity and version;
- canonical typed JSON value;
- authentication method;
- exact source-observation identities;
- exact authentication-policy identity and version;
- exact source or derivation-rule lineage.

The first characteristic roles are:

- `ending`;
- `beginning`.

Roles describe a characteristic's place in a possible crossing. They do not
assert that a crossing has been understood.

The canonical value is governed data, not free-form descriptive text. Human
display wording may be preserved separately as source evidence, but CU-1 and
CU-2 must reason only over the authenticated canonical value.

## Authorized authentication methods

EA-1 permits exactly two authentication methods in its first slice.

### Exact user confirmation

A typed `user_confirmation` observation explicitly contains:

- the exact characteristic role;
- the exact characteristic-value schema identity and version;
- the exact canonical characteristic value being confirmed.

The authenticated value must reproduce the confirmation payload exactly. A
caller-supplied claim, descriptive paraphrase, source label, or merely related
observation cannot substitute for exact confirmation.

The source type and observation type must both be authorized by the
authentication policy. Marking arbitrary evidence as `user_confirmed` is not an
authentication path.

### Named, versioned derivation

An approved deterministic rule may derive one exact characteristic from exact
recorded inputs.

Every derivation records:

- rule identity and version;
- authentication-rule-set identity, version, and canonical SHA-256;
- exact ordered or canonically ordered input evidence identities, according to
  the rule contract;
- exact canonical input payloads;
- exact canonical output role and value;
- derivation-policy identity and version.

The boundary re-executes the approved rule. It does not accept a caller's
assertion that the rule produced the declared output.

Unnamed, unversioned, unavailable, unsupported, or non-reproducible derivations
cannot mint an authenticated characteristic.

## Authentication attempts and complete accounting

EA-1 never discovers characteristics by interpreting general observations.
Every attempted authentication is introduced through either a typed exact
confirmation or an approved derivation rule whose output is defined by that
rule.

Every identifiable authentication attempt appears exactly once in one of two
partitions:

- `authenticated_characteristics`;
- `withheld_authentication_attempts`.

Absence from both partitions is invalid. Presence in both partitions is invalid.
Ordering is canonical and carries no rank, confidence, or semantic priority.

Multiple characteristics with the same role may be authenticated when separate
authorized paths legitimately establish them. EA-1 does not select among them or
resolve their compatibility. That uncertainty passes forward explicitly to
CU-1.

## Withholding reasons

Withheld attempts retain every applicable deterministic reason in fixed order:

1. `CONFIRMATION_TYPE_NOT_AUTHORIZED`;
2. `CONFIRMATION_VALUE_MISMATCH`;
3. `CHARACTERISTIC_SCHEMA_UNSUPPORTED`;
4. `DERIVATION_RULE_NOT_APPROVED`;
5. `DERIVATION_RULE_VERSION_UNSUPPORTED`;
6. `DERIVATION_INPUT_UNAVAILABLE`;
7. `DERIVATION_INPUT_UNSUPPORTED`;
8. `DERIVATION_INPUT_CONFLICTING`;
9. `DERIVATION_INPUT_MISMATCH`;
10. `DERIVATION_OUTPUT_MISMATCH`;
11. `AUTHENTICATION_PROVENANCE_INCOMPLETE`.

Request-level authority, schema, accepted-objective, policy, or rule-set digest
mismatches fail request validation. They do not become withheld attempts.

Unavailable, unsupported, conflicting, mismatched, and unauthorized evidence
remain distinct. None becomes a neutral or inferred characteristic.

## Artifact

EA-1 produces an immutable
`AuthenticatedStructuredCharacteristicArtifact` containing:

- schema version and artifact kind;
- exact artifact and request identities;
- complete accepted-objective lineage and canonical SHA-256;
- characteristic-value schema identity and version;
- authentication-policy identity and version;
- authentication-rule-set identity, version, and canonical SHA-256;
- canonically ordered authenticated characteristics;
- canonically ordered withheld attempts with all applicable reasons;
- complete source and derivation lineage;
- deterministic summary counts;
- explicit non-claims;
- artifact content SHA-256;
- canonical serialization.

## Artifact digest

An artifact cannot recursively hash bytes containing its own digest. EA-1
therefore defines two canonical forms:

1. **Canonical content bytes** contain every artifact field except
   `artifact_content_sha256`.
2. **Canonical artifact bytes** contain the complete artifact, including
   `artifact_content_sha256`.

`artifact_content_sha256` is the SHA-256 of canonical content bytes. Consumers
must verify it before accepting the artifact. Canonical artifact serialization
uses schema-order compact JSON encoded as UTF-8.

Equivalent inputs produce equal artifacts, identical content digests, and
byte-identical canonical artifact serialization. Construction copies inputs into
new immutable tuples and never mutates caller-owned collections.

## Rule-set governance

The authentication rule set is itself immutable governed authority.

Its canonical form must validate:

- unique rule identities and versions;
- unique governed output identities where required;
- exact input contracts;
- exact output roles and canonical values;
- deterministic ordering;
- no duplicate or conflicting grants of authentication authority.

The canonical rule-set SHA-256 is recorded by every request, characteristic
derived through a rule, and output artifact. Any change to a rule, input
contract, output, ordering rule, or membership creates a new rule-set identity,
version, or digest and therefore a new artifact lineage.

## Core invariants

- Only an accepted objective may enter EA-1.
- Evidence does not become authoritative merely because it appears plausible.
- Only exact user confirmation or an approved versioned derivation may mint a
  characteristic.
- Exact confirmation payload and authenticated value are byte-reproducible from
  the same canonical typed JSON value.
- Derivations are re-executed from immutable recorded inputs.
- Every authenticated characteristic has exactly one authentication method.
- Every authenticated field is reproducible from source evidence and approved
  governed authority.
- Every authentication attempt appears exactly once in the authenticated or
  withheld partition.
- EA-1 may preserve multiple authenticated characteristics without choosing
  among them.
- Free text remains evidence unless an authorized path authenticates a governed
  canonical value.
- Rule-set authority is immutable and digest-addressed.
- New evidence or governing knowledge creates a successor artifact; prior
  authority is never rewritten.

## Explicit non-claims

The artifact records literal non-claims that EA-1 did not:

- infer or establish a crossing;
- orient through the curriculum;
- establish a recurring condition;
- classify or diagnose a person;
- infer, confirm, or modify a particular need;
- infer accompaniment;
- generate an explanation;
- plan a journey;
- access a provider;
- inspect, form, score, rank, select, or sequence music.

An authenticated characteristic claims only that the governed characteristic
was legitimately established by its recorded authentication path.

## Successor authority

EA-1 authorizes only CU-1 Crossing Understanding.

CU-1 may consume authenticated characteristics and their exact lineage. It may
not reconstruct authentication, admit unauthenticated values, or mint additional
characteristic authority.

## Architectural test plan

### Exact confirmation

- Exact typed user confirmation authenticates the corresponding canonical value.
- Payload, role, schema, case, punctuation, whitespace, or Unicode differences
  fail exact correspondence.
- A generic user statement cannot masquerade as confirmation.
- A `user_confirmed` label without an authorized confirmation observation cannot
  authenticate anything.
- Descriptive free text remains evidence and is not promoted.

### Versioned derivation

- Every approved rule reproduces its documented output from exact inputs.
- Unknown rule identity or version is withheld.
- Missing, unavailable, unsupported, conflicting, and mismatched inputs retain
  distinct reasons.
- Caller-declared output is ignored or rejected unless rule execution reproduces
  it exactly.
- Rule execution cannot read objectives, crossings, curriculum, needs,
  accompaniment, providers, or music.

### Complete partition

- Every identifiable attempt appears exactly once in authenticated or withheld.
- Multiple applicable withholding reasons are retained in fixed order.
- Duplicate attempt, characteristic, observation, and provenance identities fail
  closed according to the contract.
- Multiple authenticated values for one role remain separate and unselected.

### Rule-set governance

- Rule identities, output grants, and rule membership are schema-validated for
  uniqueness.
- Reordering equivalent rule input produces equal rule sets and byte-identical
  canonical serialization.
- Any substantive rule change changes the canonical rule-set digest.
- Artifact construction rejects a mismatched rule-set identity, version, or
  digest.

### Artifact lineage and determinism

- Accepted-objective identity, typed value, and digest correspond exactly.
- Every authenticated characteristic reproduces exact source or derivation
  lineage.
- Artifact content digest verifies against canonical content bytes.
- Equivalent input permutations produce equal artifacts and byte-identical
  canonical artifact bytes.
- Construction does not mutate caller-owned inputs.

### Isolation

- No CU-1, CU-2, curriculum, need, accompaniment, Journey Planning, provider,
  Candidate Formation, scoring, selection, construction, evaluation, or
  explanation execution is reachable from EA-1.
- Repository-wide structural tests prove no alternate production component can
  mint `AuthenticatedStructuredCharacteristic` values.

## Breaking impact analysis

### CU-1 — intentional breaking migration

CU-1 schema `1.0` currently allows arbitrary supported `CrossingClaim.value`
text to act as ending and beginning characteristics. A claim requires evidence,
but it does not prove that the observation payload authenticates the claim value.
That surface cannot remain a production authority path after EA-1.

CU-1 must change so that:

- its production request accepts a complete validated
  `AuthenticatedStructuredCharacteristicArtifact` and canonical digest;
- ending and beginning values are exact authenticated-characteristic references
  or immutable projections, not arbitrary `CrossingClaim` text;
- exact accepted-objective, characteristic-schema, authentication-policy,
  rule-set, artifact, role, value, and provenance correspondence is enforced;
- the directional transition rule consumes authenticated canonical values only;
- CU-1 never replays confirmation or derivation logic;
- unauthenticated event and metaphor observations may remain historical context
  but cannot authorize transition characteristics;
- no transitional production overload accepts raw ending or beginning claims.

The current CU-1 artifact also requires a supported particular need for outcome
`understood`. The revised trust chain assigns need authority to CU-3. CU-1 must
therefore stop authenticating a particular need. It may preserve need-related
observations as non-authoritative evidence, but crossing support must not depend
on a need claim.

This likely requires a new CU-1 schema version and outcome vocabulary centered
on `crossing_supported` and `clarification_required`. Existing schema `1.0`
artifacts remain historical records but must not enter the revised production
path without an explicit versioned migration that preserves lineage.

Tests requiring migration include arbitrary supported directional claims,
particular-need resolution, direct CU-1 request construction, parent digests,
canonical serialization fixtures, and CU-2 helpers that currently construct
CU-1 from free text.

### CU-2 — paused prerequisite tightening

The uncommitted CU-2 executor correctly reads only exact resolved ending and
beginning values, but those values currently arrive as generic CU-1 strings. Its
rule set is also compiled constants without a canonical governed rule-set digest.

Before CU-2 may be committed:

- CU-2 must accept only the revised CU-1 artifact descended from EA-1;
- every matched ending and beginning characteristic must preserve exact EA-1
  artifact, role, value, and authentication lineage;
- generic `CrossingClaim.value` strings must not trigger orientation;
- the complete orientation rule set must be schema-validated, canonically
  serialized, and SHA-256 addressed;
- request and artifact must preserve exact rule-set identity, version, and
  digest;
- duplicate rule identities, candidate identities, predicates, and governed
  condition identities must fail closed;
- changing rule membership or behavior must create new governing lineage;
- CU-1 orientation candidates must remain unreadable and non-authoritative.

Current exact-match, no-match, clarification, lineage, canonicalization, and
isolation tests remain conceptually valid but must be rebuilt over authenticated
characteristics and a digest-addressed orientation rule set.

### Compatibility and migration posture

This is an intentional breaking correction to the cognitive trust chain.

There shall be no production compatibility overload that accepts arbitrary
characteristic text alongside EA-1 artifacts. Synthetic raw claims may remain
only in isolated primitive tests that do not assert production authority.

The migration sequence is:

1. approve the EA-1 contract;
2. implement and validate EA-1 in isolation;
3. migrate CU-1 to authenticated characteristics and remove need authority;
4. migrate CU-2 to revised CU-1 lineage and an immutable rule-set digest;
5. prove repository-wide that no production bypass can mint or consume
   unauthenticated crossing characteristics;
6. only then resume CU-3 design.

### Downstream cognitive boundaries

This correction changes the authority entering CU-1 and CU-2. It does not
expand or redefine downstream cognitive responsibilities.

- CU-1 still answers which crossing is supported.
- CU-2 still answers which approved curriculum rules exactly match that
  crossing.
- CU-3 still determines what remains unknown before a particular need may be
  supported.
- Faithful Accompaniment still determines what experience may serve a supported
  need.

EA-1 does not move those questions upstream. It ensures only that the
characteristics on which they depend have a legitimate immutable origin.

## Stop point

Implementation stops at isolated EA-1 authentication and the documented
CU-1/CU-2 impact analysis. CU-1 and CU-2 have not been migrated in this phase,
and no compatibility path permits them to consume EA-1 artifacts yet.

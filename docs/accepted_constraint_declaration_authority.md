# Accepted Constraint Declaration Authority v1

- **Status:** authority contract frozen; producer unimplemented
- **Boundary:** accepted structured constraint request and declaration production
- **Version:** `1.0`

## Purpose

Accepted Constraint Declaration Authority defines the product authority chain by
which Penny may eventually produce one legitimate production hard-constraint
declaration from:

- one exact accepted Objective Safety artifact;
- one exact accepted structured constraint request; and
- one exact immutable approved constraint definition.

The boundary resolves whether that exact accepted request is authorized to apply
that exact approved definition to that exact accepted objective with those exact
parameters. It records the result in an immutable declaration whose content can
be replayed and independently verified.

This contract freezes authority only. `HardConstraintDeclarationProducer` is not
implemented by this milestone. Until it is implemented together with an
approved product constraint definition, no caller-created schema `2.0`
`HardConstraintDeclarationArtifact` has production authorization merely because
its structure and digest validate.

## Governing claim

The future producer may make exactly this positive claim:

> Under Accepted Constraint Declaration Authority v1, accepted structured
> request R, authorized by A for accepted objective O, selected approved
> constraint definition D with exact parameters P; therefore declaration H is
> the deterministic product declaration corresponding to O, R, D, and P.

The producer does not decide what the objective means, infer a constraint from
prose, approve a definition, authenticate source evidence, inspect candidate
metadata, or evaluate a predicate.

## Authority chain

```text
AcceptedObjectiveArtifact
        +
AcceptedConstraintRequestArtifact
        +
ApprovedCandidateConstraintDefinitionArtifact
        ↓
HardConstraintDeclarationProducer
        ↓
Production HardConstraintDeclarationArtifact successor
        ↓
FormationRequestAssembler
        ↓
CandidateFormationRequest
```

Each input has independent authority. Possession of one input cannot substitute
for another:

- the accepted objective authorizes the objective to proceed, not a constraint;
- the accepted request authorizes one explicit selection and exact parameters,
  not the definition's product meaning;
- the approved definition authorizes one closed product constraint type, not its
  applicability to an objective that did not accept it; and
- the producer applies those authorities but may not create or expand them.

## Accepted structured constraint request

### Positive authority

`AcceptedConstraintRequestArtifact` schema `1.0` is an immutable record that an
authorized objective owner explicitly accepted one structured product constraint
request for one exact accepted objective.

It must contain, in this canonical field order:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact literal `1.0`. |
| `artifact_kind` | Exact literal `accepted_constraint_request`. |
| `request_id` | Exact nonblank identity; no trimming or normalization. |
| `request_version` | Exact nonblank version. |
| `accepted_objective_artifact_id` | Exact accepted Objective Safety artifact identity. |
| `accepted_objective_schema_version` | Exact accepted-objective schema version. |
| `accepted_objective_sha256` | SHA-256 of the canonical accepted-objective artifact bytes. |
| `constraint_definition_id` | Exact selected approved-definition identity. |
| `constraint_definition_version` | Exact selected approved-definition version. |
| `parameters` | One closed typed parameter variant permitted by the selected definition. |
| `authorization_payload_sha256` | SHA-256 of the exact pre-authorization payload defined below. |
| `authorization_type` | Exact literal `OBJECTIVE_OWNER_ATTESTATION`. |
| `authorizing_principal_id` | Exact identity of the principal whose authority is asserted. |
| `authorization_method_id` | Exact independently governed authorization-method identity. |
| `authorization_method_version` | Exact authorization-method version. |
| `authorization_evidence_id` | Exact immutable authorization-evidence artifact identity. |
| `authorization_evidence_schema_version` | Exact authorization-evidence schema version. |
| `authorization_evidence_sha256` | SHA-256 binding the exact authorization evidence. |
| `canonical_sha256` | SHA-256 of all preceding canonical request content. |

The pre-authorization payload is a canonical object with this exact field order:

1. `authorization_action`, fixed to
   `ACCEPT_PRODUCT_CONSTRAINT_REQUEST`;
2. `request_id` and `request_version`;
3. accepted-objective artifact ID, schema version, and digest;
4. selected constraint-definition ID and version; and
5. the exact canonical `parameters` variant.

It uses the same canonical JSON profile as the request. The authorization
evidence must independently bind the authorizing principal and that exact
pre-authorization payload digest. A descriptive user name, session identifier,
UI event, unchecked boolean, caller assertion, or `source_reference` is not
authorization evidence.

The authorization mechanism is an upstream prerequisite. This contract defines
the correspondence it must prove but does not implement identity,
authentication, signature verification, UI consent, or account management.

### Request parameter variants

Schema `1.0` reserves only these closed shapes:

- `ExactTypedEqualityRequestParameters`: exactly one `expected_json` member
  containing canonical typed JSON; and
- a future finite-vocabulary selection variant containing only the exact
  vocabulary identity, version, and digest already authorized by its approved
  definition.

An approved definition determines which variant is legal. Callers cannot supply
a predicate identity, governed field, matching rule, executable expression,
extension metadata, alternate vocabulary, or arbitrary parameter member in the
request.

The equality value is explicit structured input. It is never extracted from an
objective statement, prompt, chat message, provider prose, or research record.

### Canonical request identity

Canonical serialization uses the existing Candidate Formation JSON profile:

- schema field order shown above;
- UTF-8;
- `ensure_ascii=false`;
- compact separators `,` and `:`;
- JSON arrays for ordered tuples;
- JSON object field order fixed by the schema;
- finite numbers only;
- no Unicode normalization, trimming, case folding, default insertion, or
  omission of governed fields; and
- `canonical_sha256` excluded from its own digest input and appended last.

Equal request content produces byte-identical canonical content and an equal
digest. Any changed objective, definition, parameter, principal, authorization
method, or authorization evidence requires a new request version and digest.
Published request versions are immutable.

## Approved candidate constraint definition

### Positive authority

`ApprovedCandidateConstraintDefinitionArtifact` schema `1.0` is the closed
product authority for one permitted constraint type. It defines what may be
requested; it does not request or apply itself.

It must contain, in this canonical field order:

| Field | Contract |
| --- | --- |
| `schema_version` | Exact literal `1.0`. |
| `artifact_kind` | Exact literal `approved_candidate_constraint_definition`. |
| `definition_id` | Exact immutable product-definition identity. |
| `definition_version` | Exact immutable definition version. |
| `governed_field` | Exactly one existing `CandidateConstraintField` member. |
| `predicate_id` | Exactly one predicate in the closed Candidate Constraint Evaluation registry. |
| `predicate_version` | Exact supported predicate version. |
| `parameter_schema_id` | Exact closed parameter-schema identity. |
| `parameter_schema_version` | Exact parameter-schema version. |
| `allowed_json_types` | Canonically ordered closed JSON type vocabulary for equality, otherwise empty. |
| `applicability_id` | Exact closed applicability-rule identity. |
| `applicability_version` | Exact applicability-rule version. |
| `vocabulary_id` | Required only for a future finite-vocabulary definition. |
| `vocabulary_version` | Required only for a future finite-vocabulary definition. |
| `vocabulary_sha256` | Required only for a future finite-vocabulary definition. |
| `matching_contract_id` | Required only when the predicate requires matching authority. |
| `matching_contract_version` | Required only when the predicate requires matching authority. |
| `matching_contract_sha256` | Required only when the predicate requires matching authority. |
| `approval_authority_id` | Exact independent product-governance authority identity. |
| `approval_authority_version` | Exact product-governance authority version. |
| `approval_evidence_sha256` | Digest of the exact immutable approval evidence. |
| `canonical_sha256` | SHA-256 of all preceding canonical definition content. |

Fields that are inapplicable to a predicate are absent under its closed schema
variant; they are not serialized as `null`, empty strings, or caller-selected
extensions. The definition's canonical serializer and digest rules are the same
as the accepted request's profile.

### Closed behavior

An approved definition may authorize only:

- one governed field;
- one predicate identity/version;
- one closed parameter schema and permitted JSON type set;
- one closed applicability rule; and
- when applicable, one exact vocabulary and matching-contract authority.

It may not contain source code, expressions, callbacks, import paths, prompts,
templates that become executable behavior, provider instructions, research
queries, or arbitrary extension maps. Predicate execution remains owned by the
closed Candidate Constraint Evaluation registry.

### Applicability

Definition applicability is case-blind product policy. It may restrict which
accepted intent categories or product modes may select the definition. It may
never inspect objective prose, candidate values, provider metadata, research
results, or user taste to decide applicability.

The producer verifies applicability from exact already-governed fields in the
accepted objective and definition. No match fails closed; it does not invite an
interpreter to infer equivalence.

### Succession

Any change to field, predicate, parameter schema, allowed JSON types,
applicability, vocabulary, matching authority, approval authority, or approval
evidence creates a new definition version and digest. A successor identifies its
predecessor under a future additive schema; schema `1.0` does not invent
predecessor lineage when none was supplied.

Published definition versions are immutable and remain verifiable for historical
replay. A successor never reinterprets a prior request or declaration.

## First approved product constraint decision

No legitimate first exact typed-equality product constraint is approved by the
current product contracts.

The repository demonstrates equality over `displayed_explicit`, title, artist,
catalog identity, and release identity, but those uses establish evaluator and
test behavior only. No current product requirement states that an accepted
objective must require a particular equality value for any of those fields.
`displayed_explicit=false` is specifically a test fixture, not Penny product
policy.

Therefore this freeze publishes no
`ApprovedCandidateConstraintDefinitionArtifact`, no product definition registry
entry, and no default equality value. Product policy remains intentionally
unspecified. Producer implementation is blocked until a separately approved
product requirement authorizes one exact definition and its approval evidence.

## HardConstraintDeclarationProducer authority

### Sole production route

`HardConstraintDeclarationProducer` is the sole production authority permitted
to create a production-authorized hard-constraint declaration under this
contract.

Low-level schema constructors may remain available for isolated unit tests,
canonicalization tests, verifier fixtures, migrations that preserve historical
bytes, and internal construction after producer authorization. A constructor
proves structural validity only. It cannot establish accepted-request,
accepted-objective, definition, approval, or production authority.

Direct construction of `HardConstraintDeclarationArtifact`, including through
`create_hard_constraint_declaration_v2`, must not be accepted by a production
assembly path as evidence that the caller was authorized to declare a
constraint.

### Accepted inputs

The producer accepts exactly:

1. one verified `AcceptedObjectiveArtifact`;
2. one verified `AcceptedConstraintRequestArtifact` schema `1.0`; and
3. one verified `ApprovedCandidateConstraintDefinitionArtifact` schema `1.0`.

It accepts no prompt, objective text parser, free-form constraint description,
provider response, research artifact, mutable registry lookup, current time,
random value, environment-dependent default, or caller-supplied declaration.

### Deterministic production

For Authority v1, one accepted request selects exactly one definition and
produces exactly one declared constraint. The producer:

1. verifies every input's structure, canonical digest, and independent
   authority;
2. verifies exact objective, request, definition, approval, applicability, and
   parameter correspondence;
3. obtains field and predicate only from the approved definition;
4. obtains parameter values only from the accepted request;
5. validates the parameters against the definition's closed schema;
6. emits the one constraint under the fixed key `constraint-000001`;
7. copies complete objective, request, and definition lineage into the
   declaration successor;
8. canonically serializes the declaration; and
9. computes the declaration digest over every governed field except the digest
   itself.

The declaration artifact identity is
`hard-constraint-declaration:<accepted-request-canonical-sha256>` and its
declaration version is `1.0`. Replaying equal verified inputs produces an equal
artifact, byte-identical canonical serialization, and the same digest.

The legacy `source_type` and `source_reference` fields, if retained by the
successor for correspondence, are descriptive only. They cannot replace the
embedded accepted-objective, accepted-request, and approved-definition bindings.

### Failure behavior

The producer fails the complete operation without an artifact when:

- any input or digest does not verify;
- the accepted objective is declined, substituted, or does not equal the
  request's objective authority;
- the request identity, version, content, authorization, or digest is
  substituted;
- the definition identity, version, content, approval, or digest is
  substituted;
- the definition is unapproved, unsupported, superseded for this request, or
  inapplicable;
- the request parameter variant or JSON type differs from the definition;
- a finite-vocabulary or matching authority is absent or substituted;
- an extra constraint, parameter, field, predicate, vocabulary, or behavior is
  supplied; or
- canonical output cannot be reproduced exactly.

Failure never produces a partial declaration, silently drops a parameter,
selects a similar definition, repairs an identity, guesses authority, or falls
back to caller construction.

## Exact correspondence

### Producer correspondence

Before production:

- the exact accepted-objective artifact ID, schema version, and canonical digest
  must equal the request bindings;
- the request's pre-authorization payload digest must equal the exact payload
  digest bound by the authorization evidence;
- the exact definition ID/version must equal the request selection;
- the exact definition digest must resolve through approved product-definition
  authority, never through the caller;
- the parameter variant and every parameter must conform exactly to the
  definition; and
- applicability must resolve from governed fields without prose inspection.

### FormationRequestAssembler correspondence

The production assembler must independently reverify rather than trust a
producer flag. It receives the exact accepted objective, accepted request,
approved definition, and produced declaration and requires:

- each artifact and digest to verify independently;
- the same objective binding across accepted objective, request, declaration,
  Journey Plan, and other objective-scoped formation inputs;
- the same request identity/version/digest across request and declaration;
- the same definition identity/version/digest across definition, request, and
  declaration;
- exact parameter equality across request, declaration constraint, and
  definition schema;
- exact declaration content and digest reproduction from the three authorities;
  and
- use of the production-authority successor schema.

Passing a schema `2.0` declaration plus matching caller-supplied
`authorized_declaration_*` strings is insufficient production authority. Those
fields remain useful historical/test correspondence but cannot self-authorize a
new production request.

Objective substitution, request substitution, definition substitution,
parameter tampering, digest substitution, and near-match identities invalidate
the complete assembly request. No partial Candidate Formation artifact is
allowed.

## Downstream lineage

The production-authority successor must keep the following minimum lineage
recoverable:

| Boundary | Minimum recoverable authority |
| --- | --- |
| `CandidateFormationRequest` | Exact accepted-objective ID/schema/digest; accepted-request ID/version/schema/digest and canonical bytes or immutable resolver; definition ID/version/schema/digest and canonical bytes or immutable resolver; complete declaration bytes/digest. |
| `CandidateFormationArtifact` | The same authority projection plus the exact parent Formation request identity and canonical digest. |
| `FormedCandidatePoolView` | Exact Candidate Formation parent schema, request identity, and complete canonical parent digest. Resolution of that immutable parent recovers objective, request, definition, declaration, eligibility, and evidence lineage. |
| Final product authority | Exact Candidate Formation constituent schema, identity, and complete canonical digest. Resolution of that immutable constituent recovers the same authority chain. |

The formed-pool view and final product need not duplicate complete request or
definition content. Their existing complete-parent digest pattern is sufficient
only when the exact immutable parent artifact remains available and digest
verification is mandatory. A detached digest with no retained or resolvable
parent is not recoverable lineage.

Candidate Constraint Evaluation provenance remains required: declaration,
constraint, field, predicate, parameters, optional vocabulary/matching authority,
observed evidence, result, reason, and replay correspondence are not weakened or
reconstructed downstream.

## Schema and compatibility decision

### Existing schemas remain frozen

`HardConstraintDeclarationArtifact` schema `1.0` and schema `2.0` retain their
current fields, canonical bytes, digests, and meanings. Schema `1.0` remains
implicit exact typed equality. Schema `2.0` remains the explicit-predicate and
optional-vocabulary declaration implemented by Candidate Constraint Evaluation
v1.

Schema `2.0` does not contain accepted-objective, accepted-request, approved-
definition, or independent authorization bindings. Adding those governed fields
under the unchanged `2.0` identifier would change the accepted schema and make
old verifiers reject new artifacts. Optional omission would also allow a
production declaration without the required authority. That is not a compatible
extension.

### Production successor required

The producer therefore requires `HardConstraintDeclarationArtifact` schema
`3.0`, preserving the complete schema `2.0` constraint and vocabulary semantics
and adding mandatory:

- accepted-objective ID, schema version, and canonical digest;
- accepted-request ID, request version, schema version, canonical digest, and
  exact canonical request bytes or immutable resolver;
- approved-definition ID, definition version, schema version, canonical digest,
  and exact canonical definition bytes or immutable resolver; and
- producer authority ID `pne.accepted-constraint-declaration-authority`, version
  `1.0`, plus the complete declaration digest.

The future implementation also requires successor Candidate Formation request
and artifact schemas because adding the new lineage to their existing schema
`2.0` content would likewise redefine canonical authority. The existing formed-
pool and final-product schemas may remain unchanged if their parent-resolution
and complete-digest guarantees are enforced as specified above.

Schema `3.0` is not authorized to change Candidate Constraint Evaluation v1
predicate identity, matching behavior, result semantics, reason codes, evidence
ownership, or schema `2.0` historical serialization. It is an authority-lineage
successor, not a predicate-semantic successor.

## Non-authoritative conformance digest example

The following digest fixture tests only the accepted-request canonical profile.
The `example.invalid` namespace, zero objective digest, example authorization,
and selected definition have no product authority and must be rejected by a
production producer.

The fixture's canonical pre-authorization payload, shown without a trailing
newline, is:

```json
{"authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","request_id":"example.invalid/request-001","request_version":"1.0","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","parameters":{"expected_json":"\"example\""}}
```

Its expected SHA-256 is
`10ab13dd180e1c1203d668e218be456fbc8067bf4543efbb3d20e97f274abf4c`.

Canonical content, shown without a trailing newline:

```json
{"schema_version":"1.0","artifact_kind":"accepted_constraint_request","request_id":"example.invalid/request-001","request_version":"1.0","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","parameters":{"expected_json":"\"example\""},"authorization_payload_sha256":"10ab13dd180e1c1203d668e218be456fbc8067bf4543efbb3d20e97f274abf4c","authorization_type":"OBJECTIVE_OWNER_ATTESTATION","authorizing_principal_id":"example.invalid/principal-001","authorization_method_id":"example.invalid/method-001","authorization_method_version":"1.0","authorization_evidence_id":"example.invalid/evidence-001","authorization_evidence_schema_version":"1.0","authorization_evidence_sha256":"1111111111111111111111111111111111111111111111111111111111111111"}
```

Expected SHA-256:

```text
67c7a073781ee9753811e861ac076dbeb36a8859ff2b01832dddabed113f8770
```

This example cannot approve a definition, authorize a request, or support a
production declaration. Its only assertion is reproducible UTF-8 canonical
serialization and hashing.

## Explicit non-claims and stop point

This contract does not:

- implement `HardConstraintDeclarationProducer`;
- approve a first product constraint definition;
- parse prompts or objective prose;
- infer, extract, translate, or normalize natural-language constraints;
- promote Animal Vocabulary or publish finite-vocabulary product content;
- add artist-field logic;
- call providers or implement acquisition;
- orchestrate the product pipeline;
- evaluate candidate evidence;
- modify Candidate Constraint Evaluation predicates;
- modify scoring, sequencing, construction, evaluation, refinement, UI, API, or
  persistence; or
- read from or write to research, Workbench, Study, or Maestro authority.

Implementation re-entry requires an approved first product constraint definition
and its approval evidence, an independently verifiable authorization-evidence
contract, approved successor schema details, and an explicit implementation
authorization.

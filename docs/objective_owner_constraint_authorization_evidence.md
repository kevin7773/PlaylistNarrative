# Objective-Owner Constraint Authorization Evidence v1

- **Status:** authority contract frozen; implementation absent
- **Boundary:** explicit objective-owner authorization of one structured
  constraint-request payload
- **Version:** `1.0`

## Purpose and sole claim

This boundary may eventually issue one immutable
`ConstraintRequestAuthorizationArtifact` schema `1.0` making exactly this
claim:

> Principal P, acting through governed authorization method M, explicitly
> authorized pre-authorization payload H for accepted objective O.

It does not accept an objective, decide objective safety, publish a constraint
definition, authenticate research evidence, receipt a source observation, or
produce a constraint declaration. It is a dedicated authority between an
already accepted objective and an
`AcceptedConstraintRequestArtifact`.

```text
Accepted objective + independent principal authority
        +
Exact pre-authorization payload
        +
Approved authorization-method authority
        +
Immutable underlying authorization evidence
        ↓
ConstraintRequestAuthorizationBoundary
        ↓
ConstraintRequestAuthorizationArtifact 1.0
        ↓
AcceptedConstraintRequestArtifact 1.0
```

This contract freezes authority only. It implements no artifact, producer,
identity provider, signature system, key management, delegation system, UI, or
persistence.

## Jurisdiction and separation

The boundary is separate from:

- **Objective Safety**, which decides whether one declared objective may
  proceed but neither establishes a principal's identity nor authorizes a later
  constraint request;
- **Accepted Objective authority**, which binds the accepted decision and its
  inputs but does not currently bind an authenticated objective owner;
- **Evidence Authentication**, which governs authenticated characteristics in
  its own jurisdiction and does not establish consent to this action;
- **Source Receipt**, which proves deterministic capture of an observation and
  does not establish identity or consent; and
- **constraint-definition publication**, which approves a closed product rule
  but cannot authorize applying it to an objective.

Their immutable-artifact and exact-digest patterns are architectural precedent
only. An Evidence Authentication artifact, Source Receipt, accepted objective,
or definition digest cannot be relabeled as authorization evidence.

## Principal authority

### Product-contract principal

A principal is an exact stable identity established by an independent,
immutable principal-authority artifact. The principal identifier is a binding
inside that authority; a caller-supplied name, account label, session identifier,
household identifier, profile string, or matching text is not identity proof.

The authorization request must bind both roles independently:

1. `objective_owner_principal_id` and the exact identity, schema version, and
   digest of the authority establishing that principal as owner/authority of
   the exact accepted objective; and
2. `authorizing_principal_id` and the exact identity, schema version, and digest
   of the authority establishing the principal who performed the later action.

The Penny Local v1 upstream identities are now contract-frozen by
[Penny Local Principal Authority v1](penny_local_principal_authority.md) and
[Accepted Objective Owner Authority v1](accepted_objective_owner_authority.md).
Their schemas, producers, storage, and runtime verification remain
unimplemented.

### Relationship and delegation

`principal_relationship` is closed to:

- `OBJECTIVE_OWNER`: the authorizing principal and its authority must equal the
  exact objective-owner principal and authority; or
- `DELEGATE`: a separately governed immutable delegation artifact must bind the
  objective owner, delegate, exact accepted objective or permitted scope,
  permitted action, validity rules, and revocation/succession semantics.

Schema `1.0` can represent either relationship, but Penny Local v1 supports
only `OBJECTIVE_OWNER`. It approves no delegation artifact schema or delegation
authority. Every `DELEGATE` request therefore fails closed. Household
membership, shared-account access, agent operation, name similarity, or
possession of the same device never implies delegation.

## Exact pre-authorization payload

The authorized object is the following closed canonical object, in this exact
field order:

1. `authorization_action`, exact literal
   `ACCEPT_PRODUCT_CONSTRAINT_REQUEST`;
2. `accepted_objective_artifact_id`;
3. `accepted_objective_schema_version`;
4. `accepted_objective_sha256`;
5. `constraint_request_schema_version`, exact literal `1.0` for this contract;
6. `constraint_request_id`;
7. `constraint_request_version`;
8. `constraint_definition_id`;
9. `constraint_definition_version`;
10. `constraint_definition_sha256`; and
11. `parameters`, exactly one closed parameter variant permitted by that
    definition.

The object uses the Candidate Formation canonical JSON profile: UTF-8,
`ensure_ascii=false`, compact separators, schema field order, finite numbers,
and no Unicode normalization, trimming, case folding, default insertion, or
governed-field omission. Its SHA-256 is
`preauthorization_payload_sha256`.

The selected definition must be resolved through independent product authority;
the caller cannot establish it by supplying matching strings or a digest. Any
change to objective authority, proposed request identity/version/schema,
definition authority, parameter member, parameter type, or parameter value
creates a different payload and requires new authorization.

No prompt, objective statement, chat text, natural-language constraint, UI
label, or opaque `source_reference` is part of or may be interpreted into this
payload.

## Authorization-method authority

An authorization method is closed governed product authority identified by
exact `authorization_method_id`, version, and immutable canonical digest. A
method definition must prescribe:

- the supported authorization action;
- accepted principal-authority and objective-owner-authority schemas;
- accepted underlying evidence schema;
- the exact evidence verification algorithm and deterministic decision rules;
- the exact binding between principal, action, objective, and payload digest;
- replay inputs and supported verifier version; and
- succession and historical-verification rules.

Method definitions may not contain caller-defined executable behavior. A method
version change cannot reinterpret an earlier decision. Penny Local v1 now has
exactly one contract-frozen method,
`pne.constraint-authorization.local-explicit-confirmation/1.0`, governed by
[Local Explicit Constraint Confirmation Evidence v1](local_explicit_constraint_confirmation_evidence.md).
Its runtime producer and schemas remain unimplemented. No OS, account,
signature, biometric, device, or delegated method is selected.

Three authorities remain distinct:

- the **method authority** defines how evidence is evaluated;
- the **underlying evidence** is the immutable input that records the governed
  confirmation or signature event; and
- the **authorization artifact** records the deterministic boundary decision.

A SHA-256 digest proves only byte integrity. It is never, by itself, proof of a
principal's identity, authority, awareness, or consent.

## Underlying evidence

The authorization request binds the underlying evidence by exact:

- `authorization_evidence_id`;
- `authorization_evidence_schema_version`;
- `authorization_evidence_sha256`; and
- canonical evidence bytes, or an immutable resolver that is guaranteed to
  return those exact bytes for historical replay.

The approved method must independently establish from those bytes the exact
authorizing principal, action, accepted-objective authority, and
pre-authorization payload digest. Descriptive records, audit log text, checked
booleans, UI events, caller assertions, and integrity hashes have no
authorization meaning unless an approved method explicitly governs their
schema and verification.

Changing the evidence ID, schema, bytes, digest, method, principal authority,
objective, or payload invalidates correspondence. Historical verification must
retain the exact method definition and verifier required by that method version;
current ambient account or device state is not replay authority.

## Authorization request schema 1.0

`ConstraintRequestAuthorizationRequest` schema `1.0` is the immutable replay
input to the future authorization boundary. It contains, in canonical order:

| Field group | Required content |
| --- | --- |
| Request identity | `schema_version`, fixed `request_kind`, `request_id`, and `request_version`. |
| Objective binding | Accepted-objective ID, schema version, and digest. |
| Authorized object | Complete `preauthorization_payload` and its digest. |
| Objective-owner authority | Owner principal ID plus objective-owner authority artifact ID, schema, and digest. |
| Authorizing principal authority | Authorizing principal ID plus principal-authority artifact ID, schema, and digest. |
| Relationship | `principal_relationship`; the `OBJECTIVE_OWNER` variant omits delegation fields, while the `DELEGATE` variant requires independent delegation artifact ID, schema, and digest. |
| Method authority | Authorization-method ID, version, and digest. |
| Underlying evidence | Evidence ID, schema, digest, and exact bytes or immutable resolver. |

`request_kind` is exactly `constraint_request_authorization`. The conditional
delegation fields permit schema `1.0` to bind a future delegation authority but
do not define or approve that authority. All identities and versions are
nonblank exact values without normalization. Schema `1.0` forbids extra fields
and has no caller extension map.

The exact canonical field order is:

1. `schema_version`, `request_kind`, `request_id`, `request_version`;
2. `accepted_objective_artifact_id`,
   `accepted_objective_schema_version`, `accepted_objective_sha256`;
3. `preauthorization_payload`, `preauthorization_payload_sha256`;
4. `objective_owner_principal_id`,
   `objective_owner_authority_artifact_id`,
   `objective_owner_authority_schema_version`,
   `objective_owner_authority_sha256`;
5. `authorizing_principal_id`,
   `authorizing_principal_authority_artifact_id`,
   `authorizing_principal_authority_schema_version`,
   `authorizing_principal_authority_sha256`;
6. `principal_relationship`;
7. only for `DELEGATE`, `delegation_artifact_id`,
   `delegation_artifact_schema_version`, `delegation_artifact_sha256`;
8. `authorization_method_id`, `authorization_method_version`,
   `authorization_method_sha256`;
9. `authorization_evidence_id`, `authorization_evidence_schema_version`,
   `authorization_evidence_sha256`; and
10. exactly one evidence-location variant: either
    `authorization_evidence_payload_base64` or an immutable resolver identity,
    schema version, and digest under a future additive schema successor.

Schema `1.0` freezes the embedded-base64 variant. The immutable-resolver variant
requires a successor because changing this closed shape under `1.0` would
redefine its canonical bytes.

Canonical serialization follows the payload profile. Its SHA-256 covers every
field. Equal verified inputs reproduce byte-identical request content and an
equal digest. No current implementation or schema class is authorized by this
freeze.

## Authorization artifact schema 1.0

`ConstraintRequestAuthorizationArtifact` schema `1.0` contains, in canonical
order:

| Field group | Required content |
| --- | --- |
| Artifact identity | `schema_version`, fixed `artifact_kind`, deterministic `artifact_id`, and `artifact_version`. |
| Replay input | Input request ID, schema version, request version, and canonical digest. |
| Decision | `decision` and canonically ordered fixed `reasons`. |
| Principal authority | Both principal IDs, both authority artifact ID/schema/digest triples, relationship, and, for `DELEGATE`, mandatory delegation artifact ID/schema/digest. |
| Authorized action | Exact `authorization_action`. |
| Objective | Accepted-objective ID, schema, and digest. |
| Payload | Exact `preauthorization_payload_sha256`. |
| Method | Authorization-method ID, version, and digest. |
| Evidence | Underlying evidence ID, schema, and digest. |
| Artifact integrity | `canonical_sha256`, appended last and excluded from its own digest input. |

`artifact_kind` is exactly `constraint_request_authorization`;
`artifact_version` is exactly `1.0`; and `artifact_id` is
`constraint-request-authorization:sha256:<input-request-sha256>`. Published
artifacts are immutable.

The exact canonical field order is:

1. `schema_version`, `artifact_kind`, `artifact_id`, `artifact_version`;
2. `input_request_id`, `input_request_schema_version`,
   `input_request_version`, `input_request_sha256`;
3. `decision`, `reasons`;
4. `objective_owner_principal_id`,
   `objective_owner_authority_artifact_id`,
   `objective_owner_authority_schema_version`,
   `objective_owner_authority_sha256`;
5. `authorizing_principal_id`,
   `authorizing_principal_authority_artifact_id`,
   `authorizing_principal_authority_schema_version`,
   `authorizing_principal_authority_sha256`;
6. `principal_relationship`;
7. only for `DELEGATE`, `delegation_artifact_id`,
   `delegation_artifact_schema_version`, `delegation_artifact_sha256`;
8. `authorization_action`;
9. `accepted_objective_artifact_id`,
   `accepted_objective_schema_version`, `accepted_objective_sha256`;
10. `preauthorization_payload_sha256`;
11. `authorization_method_id`, `authorization_method_version`,
    `authorization_method_sha256`;
12. `authorization_evidence_id`, `authorization_evidence_schema_version`,
    `authorization_evidence_sha256`; and
13. `canonical_sha256`.

### Decisions and failure semantics

The artifact's closed decisions are:

- `AUTHORIZED`: the approved method verified affirmative authorization by the
  independently authorized owner or delegate for the exact action, objective,
  and payload;
- `REFUSED`: valid governed evidence deterministically establishes that the
  requested authorization was not granted, with one or more fixed reasons.

Schema `1.0` has one refusal reason, `AUTHORIZATION_NOT_GRANTED`. It means the
approved method verified an explicit non-authorization result for the exact
otherwise-valid request. New refusal meanings require a successor contract;
free-form reasons are forbidden.

Invalid structural, authority, correspondence, digest, method, evidence, or
replay input produces no authorization artifact. The service outcome is
`NOT_EVALUATED_INVALID_INPUT`; it is not an artifact decision. A consumer
accepts only a fully verified `AUTHORIZED` artifact. Refusal cannot be repaired
into authorization, and invalid input cannot be treated as refusal or absence
of preference.

## Deterministic verification

The future authorization boundary must:

1. verify request structure and canonical digest;
2. resolve and verify the exact accepted objective;
3. resolve independent objective-owner and authorizing-principal authorities;
4. require exact owner equality or verify exact independent delegation;
5. reproduce and digest the complete pre-authorization payload;
6. resolve and verify the exact approved constraint definition named by it;
7. resolve an approved authorization-method version from closed authority;
8. reproduce the underlying evidence bytes and digest;
9. apply only that method's deterministic verifier; and
10. canonically produce and digest the artifact.

`AcceptedConstraintRequestArtifact`, `HardConstraintDeclarationProducer`, and
`FormationRequestAssembler` must independently reverify, directly or through an
approved replay verifier:

- both principal authorities and any mandatory delegation authority;
- action equality;
- accepted-objective ID/schema/digest correspondence;
- exact recomputation of the pre-authorization payload digest;
- method ID/version/digest and its approval status;
- evidence ID/schema/digest and deterministic method result;
- authorization request ID/schema/version/digest; and
- authorization artifact ID/schema/content/digest and `AUTHORIZED` decision.

Objective substitution, request substitution, definition substitution,
parameter tampering, principal substitution, implicit delegation, method
substitution, evidence substitution, or a detached/unresolvable digest fails the
complete operation closed. A cached success flag or structurally valid artifact
is not authorization.

## Schema implications and downstream lineage

The minimum future successor set is:

1. `ConstraintRequestAuthorizationRequest` schema `1.0`;
2. `ConstraintRequestAuthorizationArtifact` schema `1.0`;
3. `AcceptedConstraintRequestArtifact` schema `1.0`;
4. `ApprovedCandidateConstraintDefinitionArtifact` schema `1.0`;
5. `HardConstraintDeclarationArtifact` schema `3.0`;
6. `CandidateFormationRequest` schema `3.0`;
7. `CandidateFormationArtifact` schema `3.0`; and
8. successor `CandidateFormationTrace` and `FormedCandidatePoolView` schemas,
   expected `2.0`, because their current parent-schema vocabulary does not admit
   Candidate Formation schema `3.0` without redefining existing canonical
   authority.

The accepted request binds the authorization artifact ID, schema, and digest;
the declaration binds the accepted request; Candidate Formation schema `3.0`
binds the objective, authorization, request, definition, and declaration chain;
and the trace/pool successor binds that exact complete parent. Final product
authority can retain its current schema shape if its constituent allowlist
admits the successor pool and exact parent resolution remains mandatory.

Existing immutable schemas remain unchanged: Objective Intent Declaration
`1.0`; Objective Safety request and accepted/declined artifacts `2.0`; Journey
Planning request `1.0` and Journey Plan `2.0`; Evidence Authentication and
Source Receipt schemas; Hard Constraint Declaration `1.0` and `2.0`; Candidate
Formation request/artifact `1.0` and `2.0`; Candidate Formation Trace and
FormedCandidatePoolView `1.0`; and existing acquisition, validation, taste,
feature, context, scoring, construction, evaluation, and final-product artifact
meanings and canonical bytes.

Candidate Constraint Evaluation v1 predicates, matching behavior, evidence
ownership, result semantics, reasons, and provenance remain unchanged.

## Non-authoritative canonical conformance examples

These `example.invalid` fixtures test canonicalization only. The principal,
method, evidence, definition, and objective have no product authority and must
be rejected by production verification.

Exact pre-authorization payload, without a trailing newline:

```json
{"authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","constraint_request_schema_version":"1.0","constraint_request_id":"example.invalid/constraint-request-001","constraint_request_version":"1.0","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","constraint_definition_sha256":"1111111111111111111111111111111111111111111111111111111111111111","parameters":{"expected_json":"\"example\""}}
```

Expected SHA-256:
`18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa`.

Underlying evidence bytes, without a trailing newline:

```json
{"authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","authorized":true}
```

Expected evidence SHA-256:
`48e330cd226864ed34e28e31e78b7cc02093ab332d4a71fb9602105ef09abb49`.
Its canonical base64 representation is
`eyJhdXRob3JpemF0aW9uX2FjdGlvbiI6IkFDQ0VQVF9QUk9EVUNUX0NPTlNUUkFJTlRfUkVRVUVTVCIsImF1dGhvcml6ZWQiOnRydWV9`.

This preserved invalid conformance fixture is not confirmation evidence. Its
bare Boolean has no authorization meaning and cannot satisfy
`pne.constraint-authorization.local-explicit-confirmation/1.0`; production
evidence must use the complete frozen confirmation-evidence schema.

Canonical authorization request content, without a trailing newline:

```json
{"schema_version":"1.0","request_kind":"constraint_request_authorization","request_id":"example.invalid/authorization-request-001","request_version":"1.0","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","preauthorization_payload":{"authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","constraint_request_schema_version":"1.0","constraint_request_id":"example.invalid/constraint-request-001","constraint_request_version":"1.0","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","constraint_definition_sha256":"1111111111111111111111111111111111111111111111111111111111111111","parameters":{"expected_json":"\"example\""}},"preauthorization_payload_sha256":"18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa","objective_owner_principal_id":"example.invalid/principal-001","objective_owner_authority_artifact_id":"example.invalid/objective-owner-authority-001","objective_owner_authority_schema_version":"1.0","objective_owner_authority_sha256":"2222222222222222222222222222222222222222222222222222222222222222","authorizing_principal_id":"example.invalid/principal-001","authorizing_principal_authority_artifact_id":"example.invalid/objective-owner-authority-001","authorizing_principal_authority_schema_version":"1.0","authorizing_principal_authority_sha256":"2222222222222222222222222222222222222222222222222222222222222222","principal_relationship":"OBJECTIVE_OWNER","authorization_method_id":"example.invalid/method-001","authorization_method_version":"1.0","authorization_method_sha256":"3333333333333333333333333333333333333333333333333333333333333333","authorization_evidence_id":"example.invalid/evidence-001","authorization_evidence_schema_version":"1.0","authorization_evidence_sha256":"48e330cd226864ed34e28e31e78b7cc02093ab332d4a71fb9602105ef09abb49","authorization_evidence_payload_base64":"eyJhdXRob3JpemF0aW9uX2FjdGlvbiI6IkFDQ0VQVF9QUk9EVUNUX0NPTlNUUkFJTlRfUkVRVUVTVCIsImF1dGhvcml6ZWQiOnRydWV9"}
```

Expected request SHA-256:
`efeec4f2c59a22c7fd9f9eb47232b22b3ac9e7fc81b94d78e73a2c6e805e349c`.

Canonical authorization artifact content, excluding `canonical_sha256` and
without a trailing newline:

```json
{"schema_version":"1.0","artifact_kind":"constraint_request_authorization","artifact_id":"constraint-request-authorization:sha256:efeec4f2c59a22c7fd9f9eb47232b22b3ac9e7fc81b94d78e73a2c6e805e349c","artifact_version":"1.0","input_request_id":"example.invalid/authorization-request-001","input_request_schema_version":"1.0","input_request_version":"1.0","input_request_sha256":"efeec4f2c59a22c7fd9f9eb47232b22b3ac9e7fc81b94d78e73a2c6e805e349c","decision":"AUTHORIZED","reasons":[],"objective_owner_principal_id":"example.invalid/principal-001","objective_owner_authority_artifact_id":"example.invalid/objective-owner-authority-001","objective_owner_authority_schema_version":"1.0","objective_owner_authority_sha256":"2222222222222222222222222222222222222222222222222222222222222222","authorizing_principal_id":"example.invalid/principal-001","authorizing_principal_authority_artifact_id":"example.invalid/objective-owner-authority-001","authorizing_principal_authority_schema_version":"1.0","authorizing_principal_authority_sha256":"2222222222222222222222222222222222222222222222222222222222222222","principal_relationship":"OBJECTIVE_OWNER","authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","preauthorization_payload_sha256":"18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa","authorization_method_id":"example.invalid/method-001","authorization_method_version":"1.0","authorization_method_sha256":"3333333333333333333333333333333333333333333333333333333333333333","authorization_evidence_id":"example.invalid/evidence-001","authorization_evidence_schema_version":"1.0","authorization_evidence_sha256":"48e330cd226864ed34e28e31e78b7cc02093ab332d4a71fb9602105ef09abb49"}
```

Expected artifact SHA-256:
`5e711443880572fc8587724999adf04120d117395c9c4e287460f191e61567ed`.

## Product-policy boundary and stop point

The approved constraint-definition registry remains intentionally empty. This
contract does not approve `displayed_explicit=false`, convert taste exclusions
into candidate equality constraints, promote Animal Vocabulary, or invent any
other product constraint. This contract does not itself approve an
authorization method; the separate local explicit-confirmation contract now
supplies Penny Local v1's one closed method authority.

Principal, objective-owner, and one local explicit-confirmation method are now
contract-frozen, with delegation explicitly unsupported. Implementation remains
blocked on explicit implementation authorization and a legitimate first product
constraint definition under separately approved product policy. The approved
definition registry remains empty.

No prompt parsing, provider/acquisition work, orchestration, Candidate
Constraint Evaluation change, scoring, sequencing, construction, refinement,
UI, API, persistence, research, Workbench, Study, Maestro, or database behavior
is authorized here.

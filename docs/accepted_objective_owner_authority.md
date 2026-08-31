# Accepted Objective Owner Authority v1

- **Status:** authority contract frozen; implementation absent
- **Boundary:** prospective Penny-local ownership of one accepted objective
- **Version:** `1.0`

## Purpose and sole claim

Accepted Objective Owner Authority may eventually issue one immutable
`AcceptedObjectiveOwnerAuthorityArtifact` schema `1.0` making exactly this
claim:

> Penny-local principal P prospectively submitted objective O through governed
> submission evidence S and its exact intent declaration D; accepted Objective
> Safety artifact A corresponds to that same objective and declaration;
> therefore P is the Penny-local owner of A for later owner-bound authority.

This boundary does not accept the objective, decide safety, reinterpret intent,
authorize a constraint request, or identify a real-world human. Objective
Safety remains the sole acceptance authority. The exact principal comes only
from [Penny Local Principal Authority v1](penny_local_principal_authority.md).

## Prospective authority

Ownership evidence must exist before Objective Safety accepts the objective.
Database locality, filesystem locality, installation identity, current active
profile, matching text, later testimony, or possession of an accepted artifact
cannot retrospectively establish ownership.

The required chronology is authority lineage, not a clock claim:

```text
Active LocalPrincipalAuthorityArtifact
        ↓ governed exact objective submission
LocalObjectiveSubmissionEvidence 1.0
        ↓ exact authority_reference
ObjectiveIntentDeclarationArtifact 1.0
        ↓ existing Objective Safety evaluation
AcceptedObjectiveArtifact 2.0
        ↓ exact correspondence only
AcceptedObjectiveOwnerAuthorityProducer
        ↓
AcceptedObjectiveOwnerAuthorityArtifact 1.0
```

No timestamp is required. The directed artifact references prove the
prospective order.

## Governed objective-submission evidence

`LocalObjectiveSubmissionEvidence` schema `1.0` is immutable capture evidence,
not an ownership decision. Its exact canonical field order is:

1. `schema_version`, exact `1.0`;
2. `evidence_kind`, exact `local_objective_submission`;
3. `evidence_id`, assigned by the sole capture producer;
4. `submission_action`, exact
   `SUBMIT_OBJECTIVE_FOR_SAFETY_EVALUATION`;
5. local-principal-authority artifact ID, schema version, and digest;
6. `objective_id`;
7. `objective_statement_sha256`;
8. intent-declaration ID, schema version, and digest;
9. `capture_method_id`, exact
   `pne.local-objective-submission.exact-structured`;
10. `capture_method_version`, exact `1.0`;
11. `capture_producer_authority_id`, exact
    `pne.local-objective-submission-capture-producer`;
12. `capture_producer_authority_version`, exact `1.0`; and
13. `canonical_sha256`, appended last and excluded from its digest input.

The capture producer resolves the one active local principal internally. It
does not accept a principal ID in public production input. The submission
evidence and intent declaration are created as one governed submission context:

- the declaration's `objective_id` equals the evidence objective ID;
- its statement digest equals the evidence statement digest;
- its `authority_reference` equals the exact submission `evidence_id`; and
- its own ID/schema/digest equal the evidence bindings.

If the declaration cannot be fully bound because its digest is not yet known,
the capture operation must use one deterministic two-step construction defined
by the future implementation contract: assign the evidence ID first, construct
and digest the declaration referencing it, then construct and digest the
evidence. No circular digest is permitted.

A request object, caller assertion, arbitrary `authority_reference`, database
row, or bare submitted Boolean is not governed submission evidence.

## Owner policy authority

The closed owner policy is:

- `policy_id`: `pne.accepted-objective-owner.local-principal`;
- `policy_version`: `1.0`; and
- canonical SHA-256:
  `a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e`.

Canonical content, without a trailing newline:

```json
{"schema_version":"1.0","definition_kind":"accepted_objective_owner_policy","policy_id":"pne.accepted-objective-owner.local-principal","policy_version":"1.0","principal_authority_schema_version":"1.0","submission_evidence_schema_version":"1.0","intent_declaration_schema_version":"1.0","accepted_objective_schema_version":"2.0","ownership_basis":"PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION","retrospective_database_locality_authority":false,"historical_objective_authorization_eligibility":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Changing any field requires a new policy version and digest.

## AcceptedObjectiveOwnerAuthorityRequest schema 1.0

The immutable replay request forbids extra fields and has this exact canonical
field order:

1. `schema_version`, exact `1.0`;
2. `request_kind`, exact `accepted_objective_owner_authority`;
3. `request_id`;
4. `request_version`, exact `1.0`;
5. local-principal-authority artifact ID, schema version, and digest;
6. objective-submission-evidence ID, schema version, and digest;
7. intent-declaration ID, schema version, and digest;
8. accepted-objective artifact ID, schema version, and digest;
9. owner-policy ID, version, and digest; and
10. `canonical_sha256`, appended last and excluded from its digest input.

The request's principal authority, submission evidence, declaration, accepted
objective, and policy must be supplied as exact complete immutable artifacts or
through immutable resolvers. Detached identifiers and digests are insufficient.

## AcceptedObjectiveOwnerAuthorityArtifact schema 1.0

The positive artifact forbids extra fields and has this exact canonical order:

1. `schema_version`, exact `1.0`;
2. `artifact_kind`, exact `accepted_objective_owner_authority`;
3. deterministic `artifact_id`;
4. `artifact_version`, exact `1.0`;
5. input-request ID, schema version, request version, and digest;
6. `owner_principal_id` copied from verified principal authority;
7. local-principal-authority artifact ID, schema version, and digest;
8. objective-submission-evidence ID, schema version, and digest;
9. intent-declaration ID, schema version, and digest;
10. accepted-objective artifact ID, schema version, and digest;
11. `ownership_basis`, exact `PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION`;
12. owner-policy ID, version, and digest;
13. `producer_authority_id`, exact
    `pne.accepted-objective-owner-authority-producer`;
14. `producer_authority_version`, exact `1.0`; and
15. `canonical_sha256`, appended last and excluded from its digest input.

`artifact_id` is
`accepted-objective-owner:sha256:<input-request-sha256>`. Equal verified input
reproduces byte-identical artifact content and digest.

## Sole producer and exact correspondence

`AcceptedObjectiveOwnerAuthorityProducer` is the sole production authority.
Low-level constructors prove structure only.

The producer and verifier must independently establish:

1. the exact principal artifact and complete installation lineage verify;
2. that principal was the one applicable principal captured by the submission
   evidence;
3. submission action, capture method, producer authority, and evidence digest
   verify;
4. evidence objective ID and statement digest equal the intent declaration;
5. declaration `authority_reference` equals submission evidence ID;
6. accepted Objective Safety input binding contains that exact declaration;
7. accepted-objective identity, objective ID, statement, declaration, request,
   policy, and canonical digest all verify under unchanged Objective Safety;
8. every request binding equals the complete supplied artifact; and
9. the owner policy and output reproduce exactly.

Objective substitution, statement substitution, principal substitution,
installation substitution, evidence substitution, declaration substitution,
accepted-artifact substitution, digest mismatch, absent prospective evidence,
or later-created evidence fails closed without an owner artifact.

The producer does not accept an `owner_id`, owner name, profile label, database
path, or `owned=true` argument. It obtains `owner_principal_id` only from the
verified principal artifact already captured in submission evidence.

## Historical accepted objectives

Existing accepted objectives without the required prospective submission
evidence remain valid under their existing Objective Safety schema and may
continue in every already-authorized non-owner-bound workflow. This contract
does not invalidate, migrate, rewrite, or reinterpret them.

They are ineligible for new owner-bound constraint authorization. Neither this
producer nor a migration may attach a current local principal merely because an
artifact exists in the same installation, directory, process, or database.

To enter the owner-bound path, the objective must be submitted again through
the governed prospective path, producing new submission, declaration, Objective
Safety request/decision, and owner-authority lineage. The historical artifact
remains unchanged.

## Non-authoritative conformance examples

All `example.invalid` authorities are fixtures only and must fail production
verification.

### Submission evidence

Canonical content excluding `canonical_sha256`, without a trailing newline:

```json
{"schema_version":"1.0","evidence_kind":"local_objective_submission","evidence_id":"example.invalid/objective-submission-001","submission_action":"SUBMIT_OBJECTIVE_FOR_SAFETY_EVALUATION","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","objective_id":"example.invalid/objective-001","objective_statement_sha256":"4444444444444444444444444444444444444444444444444444444444444444","intent_declaration_id":"example.invalid/intent-declaration-001","intent_declaration_schema_version":"1.0","intent_declaration_sha256":"5555555555555555555555555555555555555555555555555555555555555555","capture_method_id":"pne.local-objective-submission.exact-structured","capture_method_version":"1.0","capture_producer_authority_id":"pne.local-objective-submission-capture-producer","capture_producer_authority_version":"1.0"}
```

Expected SHA-256:
`d685b6fabc50ae6c042a760560d96b139649712fb7a19027ca33a0ff83534eda`.

### Owner request

Canonical content excluding `canonical_sha256`, without a trailing newline:

```json
{"schema_version":"1.0","request_kind":"accepted_objective_owner_authority","request_id":"example.invalid/objective-owner-request-001","request_version":"1.0","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","objective_submission_evidence_id":"example.invalid/objective-submission-001","objective_submission_evidence_schema_version":"1.0","objective_submission_evidence_sha256":"d685b6fabc50ae6c042a760560d96b139649712fb7a19027ca33a0ff83534eda","intent_declaration_id":"example.invalid/intent-declaration-001","intent_declaration_schema_version":"1.0","intent_declaration_sha256":"5555555555555555555555555555555555555555555555555555555555555555","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","owner_policy_id":"pne.accepted-objective-owner.local-principal","owner_policy_version":"1.0","owner_policy_sha256":"a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e"}
```

Expected SHA-256:
`29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc`.

### Owner artifact

Canonical content excluding `canonical_sha256`, without a trailing newline:

```json
{"schema_version":"1.0","artifact_kind":"accepted_objective_owner_authority","artifact_id":"accepted-objective-owner:sha256:29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc","artifact_version":"1.0","input_request_id":"example.invalid/objective-owner-request-001","input_request_schema_version":"1.0","input_request_version":"1.0","input_request_sha256":"29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc","owner_principal_id":"example.invalid/principal-001","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","objective_submission_evidence_id":"example.invalid/objective-submission-001","objective_submission_evidence_schema_version":"1.0","objective_submission_evidence_sha256":"d685b6fabc50ae6c042a760560d96b139649712fb7a19027ca33a0ff83534eda","intent_declaration_id":"example.invalid/intent-declaration-001","intent_declaration_schema_version":"1.0","intent_declaration_sha256":"5555555555555555555555555555555555555555555555555555555555555555","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","ownership_basis":"PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION","owner_policy_id":"pne.accepted-objective-owner.local-principal","owner_policy_version":"1.0","owner_policy_sha256":"a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e","producer_authority_id":"pne.accepted-objective-owner-authority-producer","producer_authority_version":"1.0"}
```

Expected SHA-256:
`9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab`.

## Explicit non-claims and stop point

This authority establishes Penny-local objective ownership only. It does not
change Objective Safety, verify a physical human, authorize a constraint,
transfer ownership, delegate authority, establish a clock, parse prose, or
modify any existing artifact.

No runtime schema, capture producer, owner producer, storage, migration, UI,
API, authentication, provider, orchestration, Candidate Formation successor,
research, Workbench, Study, scoring, sequencing, construction, or database
behavior is authorized by this freeze.

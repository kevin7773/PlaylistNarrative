# Local Explicit Constraint Confirmation Evidence v1

- **Status:** authority contract frozen; implementation absent
- **Boundary:** Penny Local exact-payload constraint-authorization confirmation
- **Authorization method:**
  `pne.constraint-authorization.local-explicit-confirmation/1.0`

## Purpose and sole claim

This boundary may eventually issue one immutable
`LocalConstraintAuthorizationConfirmationEvidence` schema `1.0` making exactly
this evidence claim:

> The one active Penny-local principal P exactly equaled accepted-objective
> owner P; the governed presentation displayed exact authorization payload H
> and its bound authorities; and the interaction-capture producer observed
> deliberate activation of the exact acceptance control for H.

This is underlying evidence for
[Objective-Owner Constraint Authorization Evidence v1](objective_owner_constraint_authorization_evidence.md).
It does not itself create a `ConstraintRequestAuthorizationArtifact`, accept a
constraint request, approve a definition, or produce a declaration.

## Closed method authority

The sole approved Penny Local v1 method is:

- `authorization_method_id`:
  `pne.constraint-authorization.local-explicit-confirmation`;
- `authorization_method_version`: `1.0`; and
- canonical SHA-256:
  `0ab7d3c9278acc79b115e7773ed3feeca36167b6f18f5a1dddfd46d50ee8a9c5`.

Canonical method content, without a trailing newline:

```json
{"schema_version":"1.0","definition_kind":"constraint_authorization_method","authorization_method_id":"pne.constraint-authorization.local-explicit-confirmation","authorization_method_version":"1.0","authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","principal_relationship":"OBJECTIVE_OWNER","principal_authority_schema_version":"1.0","objective_owner_authority_schema_version":"1.0","confirmation_evidence_schema_version":"1.0","acceptance_control_id":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","refusal_control_id":"REFUSE_PRODUCT_CONSTRAINT_REQUEST","acceptance_event":"ACCEPTANCE_CONTROL_ACTIVATED","refusal_event":"REFUSAL_CONTROL_ACTIVATED","caller_boolean_authority":false,"delegation_supported":false,"authoritative_time_claim":false,"global_order_claim":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

This method definition is closed product authority, not caller-defined
behavior. A changed action, principal relationship, schema, control, event,
decision rule, time claim, or canonical profile requires a new method version
and digest.

## Accepted authority inputs

The future capture boundary accepts exact complete authorities or immutable
resolvers for:

1. one verified active `LocalPrincipalAuthorityArtifact` schema `1.0` under
   [Penny Local Principal Authority v1](penny_local_principal_authority.md);
2. one verified `AcceptedObjectiveOwnerAuthorityArtifact` schema `1.0` under
   [Accepted Objective Owner Authority v1](accepted_objective_owner_authority.md);
3. the exact accepted Objective Safety artifact bound by the owner artifact;
4. one exact pre-authorization payload under the already-frozen authorization
   contract; and
5. one exact approved constraint-definition artifact selected by that payload.

The active principal is resolved inside the capture boundary from the complete
installation-local principal lineage. A caller cannot choose, override, label,
or supply the acting principal. The resolved principal ID and exact principal-
authority artifact ID/schema/digest must equal the owner principal and
principal authority in the accepted-objective owner artifact.

Penny Local v1 permits only `principal_relationship=OBJECTIVE_OWNER`.
`DELEGATE` is unsupported and fails before presentation. No delegation artifact
or inference exists.

## Deterministic presentation schema 1.0

`LocalConstraintAuthorizationPresentation` schema `1.0` is a closed canonical
object. It is evidence of exactly what the governed capture component was
required to present; it is not a UI layout or authorization decision.

Its exact field order is:

1. `schema_version`, exact `1.0`;
2. `presentation_kind`, exact
   `local_constraint_authorization_confirmation`;
3. `authorization_action`, exact
   `ACCEPT_PRODUCT_CONSTRAINT_REQUEST`;
4. accepted-objective artifact ID, schema version, and digest;
5. accepted-objective-owner-authority artifact ID, schema version, and digest;
6. `authorizing_principal_id`;
7. local-principal-authority artifact ID, schema version, and digest;
8. `principal_relationship`, exact `OBJECTIVE_OWNER`;
9. proposed constraint-request schema version, ID, and version;
10. approved constraint-definition ID, version, and digest;
11. exact canonical structured `parameters`;
12. `preauthorization_payload_sha256`;
13. `acceptance_control_id`, exact
    `ACCEPT_PRODUCT_CONSTRAINT_REQUEST`;
14. `acceptance_control_text`, exact
    `Authorize this exact structured constraint request`;
15. `refusal_control_id`, exact
    `REFUSE_PRODUCT_CONSTRAINT_REQUEST`;
16. `refusal_control_text`, exact
    `Do not authorize this structured constraint request`; and
17. its externally recorded canonical SHA-256.

The presentation renderer must display every semantic value in fields 3 through
16 before enabling either control. It may add non-authoritative layout,
accessibility, or explanatory framing only when that framing cannot conceal,
replace, truncate, reinterpret, or contradict the governed values.

The parameter rendering is a deterministic structural rendering of the exact
typed JSON members. It performs no prompt parsing, prose interpretation,
summarization, defaulting, localization of governed values, or semantic
translation.

The presentation SHA-256 is computed over canonical fields 1 through 16. The
same verified authorities produce byte-identical presentation content and an
equal digest.

## Presentation validity

The capture producer records an internal presentation instance associated with
the canonical presentation bytes and digest. That instance is a transient
capture capability, not identity or authorization evidence.

Before accepting a control event, the producer must re-resolve and reverify all
inputs and recompute the complete presentation. Any change to principal
applicability, owner authority, accepted objective, action, request identity or
version, definition authority, parameters, pre-authorization payload, method
definition, control identity, or presentation bytes invalidates the instance.

An invalidated presentation cannot be repaired or accepted. A fresh complete
presentation is required.

## Deliberate control activation

The positive path requires the capture producer to observe the internal event:

```text
interaction_event: ACCEPTANCE_CONTROL_ACTIVATED
activated_control_id: ACCEPT_PRODUCT_CONSTRAINT_REQUEST
```

The event is valid only when it follows successful presentation of the exact
still-valid canonical content within the governed capture instance.

Production interfaces must not expose or accept `approved=true`, `accepted=1`,
`is_authorized`, a caller-selected decision enum, a checked state, or any other
Boolean/value that substitutes for the internal control event. A public request
cannot manufacture `ACCEPTANCE_CONTROL_ACTIVATED`.

Programmatic invocation, keyboard activation, assistive technology, or another
input modality may activate the governed control only through the same capture
component and validation path. Input modality grants no alternate authority.

## Confirmation evidence schema 1.0

`LocalConstraintAuthorizationConfirmationEvidence` schema `1.0` is immutable,
forbids extra fields, embeds the complete canonical presentation, and uses this
exact field order:

1. `schema_version`, exact `1.0`;
2. `artifact_kind`, exact
   `local_constraint_authorization_confirmation_evidence`;
3. deterministic `evidence_id`;
4. `evidence_version`, exact `1.0`;
5. `decision`, `ACCEPTED` or `REFUSED`;
6. `interaction_event`;
7. `activated_control_id`;
8. authorization-method ID, version, and digest;
9. complete `presentation`;
10. `presentation_sha256`;
11. `authorizing_principal_id`;
12. local-principal-authority artifact ID, schema version, and digest;
13. objective-owner-authority artifact ID, schema version, and digest;
14. accepted-objective artifact ID, schema version, and digest;
15. `authorization_action`;
16. `preauthorization_payload_sha256`;
17. `capture_producer_authority_id`, exact
    `pne.local-constraint-confirmation-capture-producer`;
18. `capture_producer_authority_version`, exact `1.0`; and
19. `canonical_sha256`, appended last and excluded from its digest input.

For `ACCEPTED`, event and control are exactly
`ACCEPTANCE_CONTROL_ACTIVATED` and
`ACCEPT_PRODUCT_CONSTRAINT_REQUEST`. Its evidence ID is
`local-constraint-confirmation:sha256:<presentation-sha256>:accepted`.

For `REFUSED`, event and control are exactly `REFUSAL_CONTROL_ACTIVATED` and
`REFUSE_PRODUCT_CONSTRAINT_REQUEST`. Its evidence ID is
`local-constraint-confirmation:sha256:<presentation-sha256>:refused`.

The copied principal, owner, objective, action, and payload fields must equal
the embedded presentation exactly. The artifact's canonical digest covers the
complete embedded presentation and every copied authority binding.

## Refusal, cancellation, and failure

- Deliberate refusal-control activation produces immutable `REFUSED` evidence.
  The downstream authorization boundary deterministically maps valid refusal
  evidence to its existing `AUTHORIZATION_NOT_GRANTED` refusal.
- Closing, navigating away, timing out operationally, or otherwise cancelling
  without control activation produces no evidence artifact and the service
  outcome `CANCELLED`.
- Invalid structure, stale or changed presentation, authority substitution,
  digest mismatch, unsupported method, non-owner relationship, unresolved
  principal, or capture failure produces no evidence artifact and the service
  outcome `NOT_EVALUATED_INVALID_INPUT`.

Cancellation and failure never become refusal or authorization. Retry requires
a fresh verified presentation.

## Sole capture producer and deterministic verification

`LocalConstraintConfirmationCaptureProducer` is the sole production route to
confirmation evidence. Low-level constructors and caller-created event objects
have no capture authority.

The producer and verifier must:

1. verify the method definition and digest;
2. resolve exactly one active local principal without caller identity input;
3. verify the owner artifact and exact principal-owner authority equality;
4. verify the accepted objective and approved definition independently;
5. reproduce the pre-authorization payload and digest;
6. reproduce the complete presentation and digest;
7. verify that the exact internal control event belongs to that still-valid
   presentation instance;
8. enforce the decision/event/control correspondence;
9. reproduce the evidence ID, canonical bytes, and digest; and
10. reject every substitution or extra field.

Historical replay uses the embedded presentation and exact immutable authority
lineage. Current ambient profile state cannot reinterpret past evidence.
Content-addressed evidence is idempotent: repeating the same valid decision over
the same complete presentation may resolve to equal bytes and the same identity.

No authoritative timestamp or global event sequence is present. If future audit
requirements need time or ordering, a separate clock/sequence authority and a
successor evidence schema are required.

## Non-authoritative conformance examples

All `example.invalid` authorities and the empty product-definition authority are
fixtures only. These bytes cannot authorize a production request.

### Presentation

Canonical content without a trailing newline:

```json
{"schema_version":"1.0","presentation_kind":"local_constraint_authorization_confirmation","authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","objective_owner_authority_artifact_id":"accepted-objective-owner:sha256:29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc","objective_owner_authority_schema_version":"1.0","objective_owner_authority_sha256":"9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab","authorizing_principal_id":"example.invalid/principal-001","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","principal_relationship":"OBJECTIVE_OWNER","constraint_request_schema_version":"1.0","constraint_request_id":"example.invalid/constraint-request-001","constraint_request_version":"1.0","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","constraint_definition_sha256":"1111111111111111111111111111111111111111111111111111111111111111","parameters":{"expected_json":"\"example\""},"preauthorization_payload_sha256":"18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa","acceptance_control_id":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","acceptance_control_text":"Authorize this exact structured constraint request","refusal_control_id":"REFUSE_PRODUCT_CONSTRAINT_REQUEST","refusal_control_text":"Do not authorize this structured constraint request"}
```

Expected SHA-256:
`5e059ca19d11b56a4835cb7c333f96b291de333207e57662ff255d18f01b84b2`.

### Accepted confirmation evidence

Canonical content excluding `canonical_sha256`, without a trailing newline:

```json
{"schema_version":"1.0","artifact_kind":"local_constraint_authorization_confirmation_evidence","evidence_id":"local-constraint-confirmation:sha256:5e059ca19d11b56a4835cb7c333f96b291de333207e57662ff255d18f01b84b2:accepted","evidence_version":"1.0","decision":"ACCEPTED","interaction_event":"ACCEPTANCE_CONTROL_ACTIVATED","activated_control_id":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","authorization_method_id":"pne.constraint-authorization.local-explicit-confirmation","authorization_method_version":"1.0","authorization_method_sha256":"0ab7d3c9278acc79b115e7773ed3feeca36167b6f18f5a1dddfd46d50ee8a9c5","presentation":{"schema_version":"1.0","presentation_kind":"local_constraint_authorization_confirmation","authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","objective_owner_authority_artifact_id":"accepted-objective-owner:sha256:29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc","objective_owner_authority_schema_version":"1.0","objective_owner_authority_sha256":"9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab","authorizing_principal_id":"example.invalid/principal-001","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","principal_relationship":"OBJECTIVE_OWNER","constraint_request_schema_version":"1.0","constraint_request_id":"example.invalid/constraint-request-001","constraint_request_version":"1.0","constraint_definition_id":"example.invalid/definition-001","constraint_definition_version":"1.0","constraint_definition_sha256":"1111111111111111111111111111111111111111111111111111111111111111","parameters":{"expected_json":"\"example\""},"preauthorization_payload_sha256":"18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa","acceptance_control_id":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","acceptance_control_text":"Authorize this exact structured constraint request","refusal_control_id":"REFUSE_PRODUCT_CONSTRAINT_REQUEST","refusal_control_text":"Do not authorize this structured constraint request"},"presentation_sha256":"5e059ca19d11b56a4835cb7c333f96b291de333207e57662ff255d18f01b84b2","authorizing_principal_id":"example.invalid/principal-001","local_principal_authority_artifact_id":"example.invalid/local-principal-authority-001","local_principal_authority_schema_version":"1.0","local_principal_authority_sha256":"a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55","objective_owner_authority_artifact_id":"accepted-objective-owner:sha256:29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc","objective_owner_authority_schema_version":"1.0","objective_owner_authority_sha256":"9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab","accepted_objective_artifact_id":"example.invalid/objective-001","accepted_objective_schema_version":"2.0","accepted_objective_sha256":"0000000000000000000000000000000000000000000000000000000000000000","authorization_action":"ACCEPT_PRODUCT_CONSTRAINT_REQUEST","preauthorization_payload_sha256":"18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa","capture_producer_authority_id":"pne.local-constraint-confirmation-capture-producer","capture_producer_authority_version":"1.0"}
```

Expected SHA-256:
`3770969764e5a89c77a76183460c97195af3bb0f63fd90a8e759018f191930f7`.

## Product-policy boundary and stop point

This method populates only the authorization-method registry. The approved
product constraint-definition registry remains empty. The fixture definition
and parameters above have no product authority.

No runtime schemas, profile storage, capture component, UI control, API,
authentication, OS account, cloud account, signature, delegation, clock,
authorization artifact, declaration producer, Candidate Formation successor,
provider, orchestration, research, Workbench, Study, scoring, sequencing,
construction, or database behavior is authorized by this freeze.

# Penny Local Principal Authority v1

- **Status:** authority contract frozen; implementation absent
- **Boundary:** installation-local Penny profile identity
- **Version:** `1.0`

## Purpose and sole claim

Penny Local Principal Authority may eventually issue one immutable
`LocalPrincipalAuthorityArtifact` schema `1.0` making exactly this claim:

> Opaque Penny-local principal P is the one active profile principal for Penny
> Local installation I under registry policy R at this point in its explicit
> principal-successor lineage.

The principal is an application identity only. It is not a person's name and
does not establish legal identity, biological identity, OS identity, account
ownership, device ownership, or which physical human operates the installation.

This contract freezes authority only. It implements no schema class, storage,
producer, profile UI, authentication, OS integration, account, signature, key,
or database behavior.

## Jurisdiction

This boundary owns only Penny-local profile identity and installation-local
applicability. It does not:

- accept an objective or establish objective ownership;
- establish consent to a constraint request;
- authenticate a real-world person;
- authorize access to data;
- create a household or delegated identity; or
- infer identity from a caller, database row, profile label, process, session,
  environment variable, filesystem location, or device account.

Objective ownership and later constraint authorization remain separate
authorities.

## Principal policy and registry authority

The closed policy/registry definition is identified by:

- `registry_id`: `pne.local-principal-authority-registry`;
- `registry_version`: `1.0`; and
- canonical SHA-256:
  `0d132a5ba0b1e619d9c1b6b7f807878ad3e321abcbe352cc36e20c9d4d655ab3`.

Its canonical content, without a trailing newline, is:

```json
{"schema_version":"1.0","definition_kind":"local_principal_policy_registry","registry_id":"pne.local-principal-authority-registry","registry_version":"1.0","principal_scope":"PENNY_LOCAL_INSTALLATION","principal_id_assignment":"SOLE_PRODUCER_GENERATED_OPAQUE","installation_id_assignment":"SOLE_PRODUCER_GENERATED_OPAQUE","active_principal_limit":1,"initial_predecessor_required":false,"successor_predecessor_required":true,"caller_identity_authority":false,"real_world_identity_claim":false,"os_identity_claim":false,"account_identity_claim":false,"authoritative_time_claim":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

This is the complete v1 registry definition. Changing any field requires a new
registry version and digest. The registry definition is policy authority; it is
not a mutable table of profile names.

## Identity creation

The future `LocalPrincipalAuthorityProducer` is the sole production route to a
`LocalPrincipalAuthorityArtifact`.

For an initial installation lineage, it must generate both:

- an opaque `installation_id`; and
- an opaque `principal_id`.

Those values must be generated inside the producer. No public production input
may accept a proposed principal ID, installation ID, profile name, user name,
account ID, OS identity, household identity, or display label. A display name,
if a later non-authoritative UI stores one, never participates in identity,
canonicalization, correspondence, or authorization.

Opaque means the identifiers communicate no human meaning. Their collision-
resistant generation mechanism is an implementation detail constrained by this
contract; their values must be persisted exactly once generated and never
normalized or reassigned.

## LocalPrincipalAuthorityArtifact schema 1.0

The artifact is frozen and forbids extra fields. Initial-artifact canonical
field order is:

1. `schema_version`, exact `1.0`;
2. `artifact_kind`, exact `local_principal_authority`;
3. `artifact_id`;
4. `artifact_version`, exact `1.0`;
5. `installation_id`;
6. `principal_id`;
7. `principal_version`;
8. `principal_scope`, exact `PENNY_LOCAL_INSTALLATION`;
9. `principal_state_at_issuance`, exact `ACTIVE`;
10. `principal_registry_id`;
11. `principal_registry_version`;
12. `principal_registry_sha256`;
13. `producer_authority_id`, exact
    `pne.local-principal-authority-producer`;
14. `producer_authority_version`, exact `1.0`;
15. `legal_identity_established`, exact `false`;
16. `biological_identity_established`, exact `false`;
17. `os_identity_established`, exact `false`;
18. `account_ownership_established`, exact `false`;
19. `physical_operator_identity_established`, exact `false`; and
20. `canonical_sha256`, appended last and excluded from its digest input.

All identities and versions are exact nonblank strings. The canonical profile
is UTF-8, schema field order, `ensure_ascii=false`, compact separators, finite
numbers only, and no trimming, Unicode normalization, case folding, default
insertion, or governed-field omission.

`artifact_id` and `principal_version` are assigned by the producer; neither may
be caller selected. Equal artifact content has equal canonical bytes and digest.

### Successor variant

A successor uses the same field order and inserts these mandatory fields after
`principal_state_at_issuance`:

1. `predecessor_artifact_id`;
2. `predecessor_artifact_schema_version`;
3. `predecessor_artifact_sha256`; and
4. `predecessor_principal_id`.

The initial variant omits all four fields. The successor variant requires all
four. `null`, empty, partial, or caller-invented predecessor lineage is invalid.

## Exactly one active principal

An installation lineage begins with exactly one initial artifact. A successor
may be issued only when the producer verifies that:

- the exact predecessor is the one applicable tip of that installation's
  complete immutable lineage;
- no competing successor already exists;
- the predecessor and successor installation IDs are equal;
- the successor principal ID is newly generated by the producer; and
- registry policy, producer authority, and all digests verify.

The successor becomes applicable for later operations. The predecessor remains
immutable and historically authoritative for operations that already bound it;
it is not edited to say `INACTIVE`. A branch, two initial artifacts for one
installation, or two applicable tips violates the exactly-one invariant and
fails closed.

Succession does not transfer objective ownership. An objective bound to the
predecessor principal remains bound to that exact principal and is ineligible
for authorization by its successor unless a future separately governed owner-
succession contract authorizes a new lineage. v1 defines no such transfer.

The predecessor chain establishes installation-local succession only. It makes
no timestamp, duration, wall-clock, or global ordering claim.

## Sole producer and verifier

Low-level constructors may support isolated tests and canonical
deserialization, but they create no production authority.

The sole producer must:

1. load and verify the complete applicable principal lineage;
2. verify the exact registry definition and digest;
3. refuse caller-supplied identity values;
4. generate opaque IDs internally;
5. enforce initial or successor shape and the single-tip invariant;
6. serialize canonically; and
7. append the canonical digest.

The verifier independently checks structure, registry authority, producer
identity, digest, installation correspondence, predecessor chain, uniqueness of
the initial artifact and applicable tip, and every fixed non-claim. It never
accepts a matching `principal_id` string without the exact verified artifact and
lineage.

Downstream artifacts must bind:

- `principal_id`;
- principal-authority artifact ID;
- principal-authority schema version; and
- principal-authority canonical digest.

When current applicability matters, the consumer must also resolve and verify
the complete installation lineage and require the bound artifact to be its one
applicable tip. A mutable “active profile” pointer may accelerate lookup but is
never authority.

## Failure behavior

Invalid registry authority, caller-selected identity, missing or competing
lineage, a second active principal, cross-installation substitution, digest
mismatch, unsupported schema, or unreproducible canonical content produces no
artifact. Failure cannot fall back to a profile name, OS user, database owner,
current process, session token, or first row found.

## Non-authoritative conformance example

The `example.invalid` identifiers are canonicalization fixtures only. They were
not generated by the future producer and have no product authority.

Canonical initial artifact content, excluding `canonical_sha256` and without a
trailing newline:

```json
{"schema_version":"1.0","artifact_kind":"local_principal_authority","artifact_id":"example.invalid/local-principal-authority-001","artifact_version":"1.0","installation_id":"example.invalid/installation-001","principal_id":"example.invalid/principal-001","principal_version":"1.0","principal_scope":"PENNY_LOCAL_INSTALLATION","principal_state_at_issuance":"ACTIVE","principal_registry_id":"pne.local-principal-authority-registry","principal_registry_version":"1.0","principal_registry_sha256":"0d132a5ba0b1e619d9c1b6b7f807878ad3e321abcbe352cc36e20c9d4d655ab3","producer_authority_id":"pne.local-principal-authority-producer","producer_authority_version":"1.0","legal_identity_established":false,"biological_identity_established":false,"os_identity_established":false,"account_ownership_established":false,"physical_operator_identity_established":false}
```

Expected SHA-256:
`a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55`.

## Explicit non-claims and stop point

The artifact establishes only opaque Penny-local profile identity. It does not
establish a person's name, legal or biological identity, OS account, cloud
account, device ownership, household membership, authentication credential,
exclusive physical control, consent, objective ownership, delegation, or
authorization.

No runtime schema, storage, producer, profile management, authentication, UI,
API, OS integration, cloud identity, signature, key, research, Workbench,
Study, provider, orchestration, scoring, sequencing, construction, or database
behavior is authorized by this freeze.

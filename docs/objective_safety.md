# Objective Safety Policy

- **Boundary:** Objective Safety
- **Policy ID:** `pne.objective-safety.playlist-intent`
- **Policy version:** `1.0`
- **Status:** Authoritative implementation specification; evaluator not yet implemented
- **Purpose:** Decide whether one sufficiently specified objective may proceed to
  Playlist Narrative Engine Journey Planning.

This document defines the first governed Objective Safety policy. It authorizes
an implementation; it is not itself an execution record and does not create an
`AcceptedObjectiveArtifact`.

## 1. Bounded authority

Objective Safety has exactly one power:

> Given an immutable Objective Assessment and an exact operator-attested intent
> declaration for the same objective, decide whether the requested role is a
> permitted Playlist Narrative Engine listening-journey role under policy
> `pne.objective-safety.playlist-intent/1.0`.

It must refuse every adjacent authority. It does not:

- decide whether Objective Assessment evidence is sufficient;
- infer intent from words in an objective statement;
- rewrite, soften, complete, or reinterpret an objective;
- diagnose a person or assess clinical risk;
- provide crisis, therapeutic, caregiving, coaching, or guidance decisions;
- inspect music, artists, tracks, lyrics, genres, or provider metadata;
- plan a journey, form candidates, score, sequence, evaluate, or refine; or
- determine whether a future playlist succeeds.

`AssessmentOutcome.SUFFICIENT` is a necessary admission requirement. It means
only that Objective Assessment found its five readiness dimensions present. It
is never authorization and never evidence that the objective intent is
permitted.

## 2. Policy identity and succession

The canonical identity is the ordered pair:

```text
policy_id      = pne.objective-safety.playlist-intent
policy_version = 1.0
```

The policy definition must have deterministic canonical UTF-8 JSON and a
canonical SHA-256. Once an artifact cites this identity and digest, this version
is immutable.

A new policy version is required for any change to:

- the accepted or non-permitted intent vocabulary;
- any decision predicate or precedence rule;
- required input fields, states, or provenance;
- reason identifiers, explanations, or field paths;
- the accepted explanation;
- canonical serialization;
- policy applicability; or
- verifier behavior.

Spelling, formatting, examples, or commentary may change without a new version
only when canonical policy content and every normative rule remain byte-for-byte
unchanged.

No mutable "current policy" pointer is authority. Applicability requires the
exact registered policy identity and canonical digest.

### 2.1 Canonical policy definition

Policy 1.0 canonicalization is UTF-8 JSON in the exact field and array order
shown below, with `ensure_ascii=false`, no insignificant whitespace, and the
separators `,` and `:`. The following single line is the complete canonical
policy definition:

```json
{"schema_version":"1.0","artifact_kind":"objective_safety_policy","policy_id":"pne.objective-safety.playlist-intent","policy_version":"1.0","assessment_admission_outcome":"sufficient","intent_declaration_schema_version":"1.0","intent_authority_type":"OBJECTIVE_OWNER_ATTESTATION","intent_states":["ESTABLISHED","UNAVAILABLE","CONFLICTING","UNVERIFIABLE","UNSUPPORTED"],"permitted_intent_categories":["LISTENING_JOURNEY_EXPRESSION"],"non_permitted_intent_categories":["NON_PLAYLIST_ACTION_OR_OUTPUT","PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL","CLINICAL_OR_CRISIS_SUBSTITUTION"],"decision_rules":[{"rule_id":"OS-ACCEPT-001","result":"ACCEPTED","predicate":"ESTABLISHED:LISTENING_JOURNEY_EXPRESSION"},{"rule_id":"OS-DECLINE-001","result":"OBJECTIVE_INTENT_NOT_PERMITTED","predicate":"ESTABLISHED:NON_PERMITTED_CATEGORY","field_path":"$.intent_declaration.intent_category"},{"rule_id":"OS-DECLINE-002","result":"REQUIRED_CONTEXT_MISSING","predicate":"DECLARATION_ABSENT","field_path":"$.intent_declaration"},{"rule_id":"OS-DECLINE-003","result":"REQUIRED_CONTEXT_MISSING","predicate":"UNAVAILABLE","field_path":"$.intent_declaration.intent_category"},{"rule_id":"OS-DECLINE-004","result":"OBJECTIVE_INTENT_UNDETERMINED","predicate":"CONFLICTING_OR_UNSUPPORTED","field_path":"$.intent_declaration.intent_category"},{"rule_id":"OS-DECLINE-005","result":"OBJECTIVE_INTENT_UNDETERMINED","predicate":"UNVERIFIABLE","field_path":"$.intent_declaration.authority_reference"}],"reason_precedence":["OBJECTIVE_INTENT_NOT_PERMITTED","REQUIRED_CONTEXT_MISSING","OBJECTIVE_INTENT_UNDETERMINED"],"reason_secondary_order":"field_path_utf8_bytes","arbitrary_metadata_decision_authority":false,"accepted_explanation":"Objective Safety policy pne.objective-safety.playlist-intent/1.0 authorizes this established LISTENING_JOURNEY_EXPRESSION intent to proceed to Journey Planning."}
```

Its authoritative SHA-256 is:

```text
eb3f69d3a84b107b21344ce25264476f012a76ae7f7aee2116d710d9c768f592
```

The predicate tokens in this representation are closed vocabulary whose exact
semantics are the decision predicates in section 4. They are not expressions
to be interpreted by a generic rule engine.

## 3. Authoritative inputs

Evaluation consumes exactly:

1. an `ObjectiveSafetyRequest`;
2. its exact `ObjectiveAssessment`;
3. zero or one immutable `ObjectiveIntentDeclarationArtifact` described below
   (absence is a governed missing-context input, not acceptance); and
4. the exact immutable policy definition for
   `pne.objective-safety.playlist-intent/1.0`.

### 3.1 Objective Assessment authority

The assessment contributes only:

- its schema version and canonical SHA-256;
- the exact `Objective` identity and statement;
- its `outcome`;
- its ordered present/missing dimensions; and
- its clarification state.

Objective Safety does not reconstruct the assessment or use its five dimensions
as intent evidence.

An assessment with `CLARIFICATION_REQUIRED` does not enter Objective Safety. It
returns to the existing clarification path and produces neither an accepted nor
a declined safety artifact.

### 3.2 Operator-attested intent declaration

Policy 1.0 requires a separately validated immutable declaration with this
normative content:

```text
schema_version: 1.0
artifact_kind: objective_intent_declaration
declaration_id: exact nonblank identity
objective_id: exact Objective.objective_id
objective_statement_sha256: SHA-256 of canonical Objective statement UTF-8 bytes
authority_type: OBJECTIVE_OWNER_ATTESTATION
authority_reference: exact nonblank reference to the declaration event
state: ESTABLISHED | UNAVAILABLE | CONFLICTING | UNVERIFIABLE | UNSUPPORTED
intent_category: present only when state = ESTABLISHED
```

The declaration records what role the objective owner is requesting. The owner
does not declare safety acceptance. Only Objective Safety maps the established
category to a decision.

The declaration must be captured through a separately governed operator input
boundary. The safety evaluator may validate and consume it but may not create,
repair, or infer it.

### 3.3 Intent vocabulary

Policy 1.0 defines exactly these categories:

| Category | Exact meaning | Policy treatment |
|---|---|---|
| `LISTENING_JOURNEY_EXPRESSION` | Construct or organize a playlist/listening journey as an expression supporting a stated listening context, without claiming control of a person's outcome. | Permitted |
| `NON_PLAYLIST_ACTION_OR_OUTPUT` | The primary requested output is not a playlist or listening journey. | Not permitted by this product boundary |
| `PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL` | The requested role asks music or Penny to guarantee, compel, direct, or authenticate a person's feeling, belief, behavior, development, or decision. | Not permitted |
| `CLINICAL_OR_CRISIS_SUBSTITUTION` | The requested role asks a playlist or Penny to act as diagnosis, treatment, crisis response, or a substitute for professional/human support. | Not permitted |

These categories describe the requested system role, not the topic or words in
the objective. Policy 1.0 defines no catch-all accepted category.

### 3.4 Generic metadata

`objective_metadata` and `context_metadata` in the current request schema are
preserved losslessly for lineage but have **no decision authority** under policy
1.0. No arbitrary key, JSON value, keyword list, score, model output, or caller
flag may establish acceptance or decline.

Future use of a metadata field in a safety decision requires a new policy
version and an explicitly governed field schema and provenance contract.

## 4. Decision model

There are three execution dispositions:

1. `ACCEPTED` — produces `AcceptedObjectiveArtifact`.
2. `DECLINED` — produces `DeclinedObjectiveArtifact`.
3. `NOT_EVALUATED_INVALID_INPUT` — produces no safety artifact and returns a
   boundary validation failure.

The third disposition is not a safety judgment. It means the requested
authority could not legitimately execute.

### 4.1 Exact ACCEPTED predicate

`ACCEPTED` if and only if every condition below is true:

1. the request, assessment, intent declaration, and policy validate under their
   exact supported schema versions;
2. request policy ID/version and canonical policy SHA-256 equal the registered
   policy 1.0 authority;
3. `ObjectiveAssessment.outcome == SUFFICIENT` and clarification is false;
4. the assessment objective equals the request/declaration objective exactly;
5. all required canonical digests and identity bindings match;
6. the intent declaration authority type is
   `OBJECTIVE_OWNER_ATTESTATION` with an exact nonblank authority reference;
7. declaration state is `ESTABLISHED`; and
8. intent category is exactly `LISTENING_JOURNEY_EXPRESSION`.

No default, omission, fallthrough, or unknown value can satisfy this predicate.

### 4.2 Exact DECLINED predicates

For a structurally valid and corresponding request:

- `OBJECTIVE_INTENT_NOT_PERMITTED` applies only when declaration state is
  `ESTABLISHED` and its category is one of the three non-permitted categories.
- `REQUIRED_CONTEXT_MISSING` applies when the intent declaration or a required
  declaration field is absent, or declaration state is `UNAVAILABLE`.
- `OBJECTIVE_INTENT_UNDETERMINED` applies when declaration state is
  `CONFLICTING`, `UNVERIFIABLE`, or `UNSUPPORTED`.

Malformed serialization, an altered assessment, objective substitution,
unsupported artifact schema, unknown policy identity/version, policy digest
mismatch, or declaration/assessment digest mismatch is
`NOT_EVALUATED_INVALID_INPUT`, not a declined objective.

### 4.3 Decision table

| Assessment | Intent authority | Intent state/category | Result | Reason/path |
|---|---|---|---|---|
| `CLARIFICATION_REQUIRED` | any | any | Not evaluated; clarification path | No safety artifact |
| `SUFFICIENT` | missing | absent | `DECLINED` | `REQUIRED_CONTEXT_MISSING`, `$.intent_declaration` |
| `SUFFICIENT` | valid | `UNAVAILABLE` | `DECLINED` | `REQUIRED_CONTEXT_MISSING`, `$.intent_declaration.intent_category` |
| `SUFFICIENT` | valid | `CONFLICTING` | `DECLINED` | `OBJECTIVE_INTENT_UNDETERMINED`, `$.intent_declaration.intent_category` |
| `SUFFICIENT` | valid | `UNVERIFIABLE` | `DECLINED` | `OBJECTIVE_INTENT_UNDETERMINED`, `$.intent_declaration.authority_reference` |
| `SUFFICIENT` | valid | `UNSUPPORTED` | `DECLINED` | `OBJECTIVE_INTENT_UNDETERMINED`, `$.intent_declaration.intent_category` |
| `SUFFICIENT` | valid | established `LISTENING_JOURNEY_EXPRESSION` | `ACCEPTED` | No reasons |
| `SUFFICIENT` | valid | established non-permitted category | `DECLINED` | `OBJECTIVE_INTENT_NOT_PERMITTED`, `$.intent_declaration.intent_category` |
| any | substituted or digest-mismatched | any | Invalid input | No safety artifact |
| any | any | unknown schema/policy/category token | Invalid input | No safety artifact |

When multiple independently required fields produce reasons, return every
unique applicable reason. Ordering is the existing
`SAFETY_REASON_PRECEDENCE`, then UTF-8 byte order of `field_path`. A more severe
or earlier reason does not erase another established failure. Invalid-input
conditions preempt decision creation entirely.

## 5. Intent before keywords

The evaluator must never inspect objective words to assign an intent category.
It consumes the exact category already attested by the objective owner through
the governed declaration boundary.

Non-normative examples:

- "A killer playlist for interval training" can be
  `LISTENING_JOURNEY_EXPRESSION`; the word "killer" does not cause refusal.
- "Songs about therapy and recovery" can be
  `LISTENING_JOURNEY_EXPRESSION`; a topic is not a request for treatment.
- "Create music that guarantees I stop feeling depressed" is
  `CLINICAL_OR_CRISIS_SUBSTITUTION`; rejection follows the declared requested
  role, not the word "depressed".
- "Use a playlist to make my partner agree with me" is
  `PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL`; the system is asked to control
  another person's decision.
- "Write a tax filing" is `NON_PLAYLIST_ACTION_OR_OUTPUT`; policy 1.0 declines
  it because Objective Safety authorizes only this product's listening-journey
  path, not because tax content is inherently unsafe.

These examples explain the categories. They are not fixtures, pattern lists,
or authorization to classify free text.

## 6. Reason authority

Policy 1.0 uses only the existing reason identifiers and fixed explanations:

1. `OBJECTIVE_INTENT_NOT_PERMITTED`
2. `REQUIRED_CONTEXT_MISSING`
3. `OBJECTIVE_INTENT_UNDETERMINED`

Reason paths are limited to:

```text
$.intent_declaration
$.intent_declaration.intent_category
$.intent_declaration.authority_reference
```

No ad hoc reason code, explanation, or path may be generated.

## 7. Accepted artifact semantics

The exact policy-1.0 accepted explanation is:

> Objective Safety policy pne.objective-safety.playlist-intent/1.0 authorizes
> this established LISTENING_JOURNEY_EXPRESSION intent to proceed to Journey
> Planning.

An accepted artifact must preserve or bind:

- its own schema version and artifact identity;
- exact request identity and canonical SHA-256;
- exact Objective and canonical SHA-256;
- exact Objective Assessment schema version and canonical SHA-256;
- exact intent-declaration identity, schema version, and canonical SHA-256;
- exact policy ID, version, and canonical SHA-256;
- the unchanged objective/context metadata carried by the request;
- `decision = accepted`;
- the exact accepted explanation;
- `journey_planning_authorized = true`;
- `musical_content_evaluated = false`; and
- `candidate_formation_performed = false`.

The artifact does not claim that the playlist will be feasible, suitable,
effective, safe for every use, or accepted by the listener.

## 8. Construction authority

The future `ObjectiveSafetyEvaluator.evaluate(request, intent_declaration,
policy)` is the sole production decision boundary; `intent_declaration` is
explicitly `ObjectiveIntentDeclarationArtifact | None`. It returns the
appropriate accepted or declined artifact and never exposes an "accept"
argument.

Direct Pydantic construction may remain available for deserialization and test
fixtures, but constructor success is not production authority. Downstream
production APIs must require verification against the exact request,
declaration, and policy. Test helpers must remain under `tests/` and must not be
imported by product code.

If implementation adopts a private construction token, it must not prevent
canonical deserialization and independent verification. Authority comes from
reproducible bindings and the sole evaluator path, not merely from making a
Python constructor inconvenient to call.

## 9. Verification semantics

A future verifier must:

1. validate supported schema and policy versions;
2. verify canonical digests for policy, request, Objective, assessment, and
   intent declaration;
3. verify all exact objective and request identity correspondence;
4. rerun policy 1.0 over the supplied immutable authorities;
5. compare the complete reproduced artifact to the supplied artifact; and
6. verify the artifact's canonical digest when the artifact envelope stores it.

Verification fails for:

- objective, assessment, declaration, request, or policy substitution;
- policy ID/version/digest mismatch;
- altered metadata, category, state, authority reference, reason, explanation,
  or field path;
- accepted output from a non-accepted input;
- declined output from an accepted input;
- unsupported schema or policy version;
- noncanonical serialization; or
- any artifact digest mismatch.

Failure never causes reevaluation under a different policy version.

## 10. Implemented schema authority

Objective Safety schema `2.0` supplies the minimum authority required to carry
policy 1.0 without changing its semantics:

1. `ObjectiveIntentDeclarationArtifact` is an immutable, versioned,
   canonically hashed authority;
2. `ObjectiveSafetyRequest` binds the exact objective, Objective Assessment
   digest, intent-declaration identity/digest, and policy ID/version/digest;
3. accepted and declined artifacts bind the exact request, objective,
   assessment, declaration, and policy through `ObjectiveSafetyInputBinding`;
   and
4. the declaration, request, and result artifacts carry canonical SHA-256
   envelopes that independent verification recomputes.

Arbitrary objective/context metadata remains lineage-only and cannot carry or
replace any of these authorities. The production evaluator and sole accepted-
artifact construction boundary remain intentionally unimplemented; schema
support and verification do not themselves authorize an objective.

## 11. Implementation conformance

An implementation conforms only if tests prove:

- every decision-table row;
- sufficient assessment is necessary but never sufficient for acceptance;
- no keyword or objective-text classification exists;
- caller-supplied arbitrary metadata cannot affect the decision;
- declaration state and category rules are exact and exhaustive;
- all reasons and paths are fixed and ordered;
- accepted explanation is exact;
- direct hand-authored accepted artifacts fail production verification;
- every substitution and digest mutation fails;
- policy-version changes cannot replay as version 1.0; and
- downstream consumers accept only verified production authority.

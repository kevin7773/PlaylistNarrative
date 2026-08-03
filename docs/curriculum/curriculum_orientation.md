# CU-2 — Curriculum Orientation Contract

## Status

This document defines the proposed CU-2 contract and its architectural test
plan. CU-2 is not implemented.

The contract stops at authority, inputs, rule governance, artifact semantics,
outcomes, invariants, and conformance. It does not authorize production code.

## Purpose

CU-2 answers one question:

> Given a supported crossing, which recurring human conditions are legitimately
> worth considering as Penny continues listening?

CU-2 makes the curriculum executable for the first time. It is an orientation
system. It is not a classification system.

## Constitutional authority

CU-2 derives its authority from:

- [Foundation Complete](../foundation_complete.md);
- [Experience Explanation & Transparency](../experience_explanation_transparency.md);
- [Presence](../presence.md);
- [Life Transitions](life_transitions.md);
- [Crossing Model](crossing_model.md);
- [CU-1 Crossing Understanding](crossing_understanding.md).

In particular:

> Penny does not listen for events. She listens for crossings.

And:

> Recurring human conditions orient understanding. They do not define the
> person.

## Authority boundary

Only a complete, validated `CrossingUnderstandingArtifact` with outcome
`understood` authorizes CU-2. Its exact embedded `AcceptedObjectiveArtifact`
must correspond to the separately supplied accepted objective without
normalization or reconstruction.

CU-2 receives authority to orient from the resolved crossing only. It receives
no authority to establish that an orientation candidate applies to the person.

Recurring-condition candidates already present in the parent CU-1 artifact are
not rule inputs, are not promoted, and are not copied into the CU-2 result. They
remain historical orientation-only observations in their parent lineage. This
prevents CU-2 from laundering an earlier candidate into curriculum authority or
creating a competing history. CU-2 candidates must originate from CU-2 rules.

## Inputs

`CurriculumOrientationRequest` accepts only:

- an exact request identity;
- the complete `AcceptedObjectiveArtifact`;
- the complete, validated parent `CrossingUnderstandingArtifact`;
- the SHA-256 digest of the parent's canonical bytes;
- the exact curriculum identity and version;
- the exact orientation-policy identity and version.

No additional event record, context record, evidence collection, provider
response, user profile, need hypothesis, or music artifact may authorize
orientation.

The request must prove exact correspondence among:

- accepted-objective typed value and identity;
- accepted-objective canonical digest recorded by CU-1;
- CU-1 parent artifact identity and canonical digest;
- resolved transition identity;
- crossing policy identity and version;
- curriculum identity and version;
- orientation-policy identity and version.

Case folding, trimming, Unicode normalization, alias resolution, fuzzy matching,
and semantic repair are forbidden.

## Scope

CU-2 may:

- examine the exact resolved transition retained by CU-1;
- examine only the ending and beginning claims belonging to that transition;
- apply approved, named, versioned orientation rules;
- produce orientation-only `RecurringConditionCandidate` values;
- preserve exact rule and source-evidence lineage;
- preserve uncertainty and the absence of a supported orientation.

CU-2 shall not:

- classify a person;
- establish that a recurring condition applies to the person;
- infer, confirm, replace, or modify the particular need;
- infer accompaniment;
- generate explanations;
- modify or reconstruct CU-1;
- inspect visible events or metaphors independently of the resolved crossing;
- consume CU-1 recurring-condition candidates as rule evidence;
- inspect music or access providers.

## Structured crossing characteristics

Orientation rules operate only on structured crossing characteristics expressed
by the resolved transition's exact ending and beginning values. They do not
operate on event labels, objective wording, metaphor text, or source-reference
keywords.

Permitted:

```text
ending.value   = "established role"
beginning.value = "unproven role"
        ↓
uncertainty before competence
```

Forbidden:

```text
event.value = "starting school"
        ↓
uncertainty before competence
```

CU-2 performs no semantic interpretation of free text. A rule predicate uses
exact values declared by its versioned policy. Semantically similar wording does
not match. If CU-1 contains free text outside the approved structured vocabulary,
CU-2 preserves it but does not normalize or reinterpret it to force a match.

The visible event is only the doorway.

## Orientation-rule contract

Every approved rule defines:

- an exact rule identity and version;
- an exact curriculum identity and version;
- an exact orientation-policy identity and version;
- a predicate over resolved-transition ending and beginning characteristics;
- an exact recurring-condition candidate identity and pattern;
- the deterministic source-evidence projection used as candidate observations;
- explicit non-claims inherited by the candidate.

Rules are pure and closed-world. They may inspect only fields named by the
contract. They may not consult mutable state, external providers, event labels,
the particular need, CU-1 condition candidates, or another rule set.

Every matching rule produces one `RecurringConditionCandidate` with:

- `orientation_basis = versioned_rule`;
- exact `RecurringConditionRuleProvenance`;
- `outcome = unresolved_orientation`;
- `applicability_to_person_established = false`;
- `person_membership_claimed = false`;
- `diagnosis_claimed = false`;
- `authoritative_for_particular_need = false`.

Multiple rules may match. Matching does not imply rank, probability, confidence,
or person-level applicability.

## Initial rule set

The first implementation shall contain only three recurring conditions:

| Rule | Exact ending characteristic | Exact beginning characteristic | Orientation candidate |
|---|---|---|---|
| `cu2.uncertainty_before_competence` version `1.0` | `established role` | `unproven role` | `uncertainty before competence` |
| `cu2.identity_after_departure` version `1.0` | `identity anchored in a departed role or relationship` | `identity not yet established after departure` | `identity after departure` |
| `cu2.return_without_reversal` version `1.0` | `life away from a familiar place, practice, or relationship` | `return to a familiar context changed by time or experience` | `return without reversal` |

These exact predicates intentionally recognize only a narrow structured
vocabulary. They do not authorize synonym matching or inference from visible
events. The purpose is architectural validation, not curriculum completeness.

Changing a predicate, candidate, rule version, curriculum version, or policy
version creates a new artifact lineage.

## Artifact

CU-2 produces an immutable `CurriculumOrientationArtifact` containing:

- schema version and artifact kind;
- exact artifact and request identities;
- complete parent CU-1 identity and canonical SHA-256 digest;
- exact accepted-objective identity and canonical correspondence;
- exact curriculum identity and version;
- exact orientation-policy identity and version;
- exact resolved-transition identity;
- an immutable projection of the ending and beginning evidence used;
- canonically ordered `RecurringConditionCandidate` values;
- complete rule lineage for every candidate;
- deterministic outcome and reasons;
- explicit non-claims.

The artifact never mutates CU-1 and never replaces CU-1 evidence with a
curriculum interpretation. Every candidate must be reproducible solely from the
recorded parent evidence and the named versioned rule.

Canonical serialization uses schema-order compact JSON encoded as UTF-8.
Caller-owned inputs are copied into new immutable tuples and are never mutated.

## Outcomes

Exactly one outcome is recorded.

### `oriented`

One or more approved orientation rules matched. The artifact contains every
resulting candidate in canonical order.

### `no_orientation_supported`

The crossing is valid and sufficiently represented for rule evaluation, but no
approved rule matched. The artifact records
`NO_APPROVED_ORIENTATION_RULE_MATCHED`.

This is an honest closed-world result, not a failure and not permission to guess.

### `clarification_required`

The parent crossing is valid, but the resolved transition does not contain the
structured characteristic support required to determine whether an approved
rule applies. All applicable clarification reasons are retained in fixed order.

Examples include an explicitly inapplicable required direction or materially
ambiguous characteristic evidence preserved by a future compatible CU-1 schema.
Free text that simply does not equal an approved predicate produces
`no_orientation_supported`, not semantic clarification.

Malformed artifacts, digest mismatches, non-`understood` CU-1 outcomes, missing
resolved-transition correspondence, and unsupported schema or policy versions
fail request validation. They do not become artifact outcomes.

## Deterministic reasons

Reason precedence is fixed:

1. `ORIENTATION_ENDING_CHARACTERISTIC_UNAVAILABLE`;
2. `ORIENTATION_BEGINNING_CHARACTERISTIC_UNAVAILABLE`;
3. `ORIENTATION_CHARACTERISTIC_UNSUPPORTED`;
4. `ORIENTATION_CHARACTERISTIC_CONFLICTING`;
5. `ORIENTATION_CHARACTERISTIC_EXPLICITLY_INAPPLICABLE`;
6. `MATERIAL_ORIENTATION_AMBIGUITY`;
7. `NO_APPROVED_ORIENTATION_RULE_MATCHED`.

Clarification artifacts retain every applicable clarification reason. A
`no_orientation_supported` artifact contains only the no-match reason.
`oriented` contains no reason.

## Core invariants

- Only CU-1 authorizes CU-2.
- Only an `understood` CU-1 artifact with one exact resolved transition may enter.
- Rules reason from the resolved crossing, never from events.
- Every candidate identifies exactly one originating rule.
- Every candidate remains `unresolved_orientation`.
- No candidate establishes applicability, membership, diagnosis, or authority
  over the particular need.
- CU-1 recurring-condition candidates are neither inputs nor inherited output.
- Multiple candidates may coexist.
- Ordering is canonical and has no probabilistic meaning.
- No rule may read or infer the particular need.
- Unknown crossings remain unknown.
- No matching rule is an honest result.
- New curriculum or policy versions create new artifacts.
- Equivalent input permutations yield equal artifacts and byte-identical
  canonical serialization.
- Every output field is reproducible solely from immutable parent evidence and
  approved versioned rules.

The governing invariant is:

> CU-2 may establish that a recurring condition is legitimately worth
> considering. It may never establish that the person is an instance of that
> condition.

## Explicit non-claims

CU-2 does not:

- determine or modify the person's need;
- rank recurring conditions;
- resolve person-level ambiguity;
- classify, diagnose, or establish group membership;
- recommend accompaniment;
- create a soundtrack objective;
- recommend, score, form, select, or sequence music;
- plan journeys;
- invoke providers;
- generate explanations.

## Successor boundary

CU-2 authorizes only:

> CU-3 — Need Clarification

CU-3 determines what Penny must still ask before a particular need can be
considered supported. CU-3 must consume the exact CU-2 artifact without
promoting an orientation candidate into person-level truth or rewriting CU-1.

CU-3 is not defined or implemented by this contract.

## Architectural test plan

### Authority and correspondence

- Reject a CU-1 artifact whose outcome is not `understood`.
- Reject a missing or non-corresponding resolved transition.
- Reject parent CU-1 canonical-digest mismatch.
- Reject accepted-objective identity, typed-value, or digest mismatch.
- Reject unsupported curriculum, orientation-policy, or schema versions.
- Prove whitespace, case, punctuation, and Unicode normalization differences do
  not correspond.

### Rule inputs

- Prove rules read only the resolved ending and beginning characteristics.
- Prove event labels, metaphors, objective text, need text, and source-reference
  keywords cannot trigger a rule.
- Prove CU-1 recurring-condition candidates cannot trigger or seed CU-2 output.
- Prove exact approved characteristics trigger only their documented rules.
- Prove semantically similar but nonidentical values do not match.
- Prove no hidden normalization or synonym expansion occurs.

### Orientation-only semantics

- Every output candidate has `outcome = unresolved_orientation`.
- No candidate can establish person applicability, membership, or diagnosis.
- No candidate can become authoritative for the particular need.
- Supported parent observations establish rule inputs, not candidate
  applicability to the person.
- Classification-like text cannot acquire classification authority.

### Outcomes and reasons

- One matching rule produces `oriented` with one candidate.
- Multiple matching rules produce `oriented` with every candidate.
- A valid crossing with no match produces `no_orientation_supported`.
- Insufficient structured characteristics produce `clarification_required`.
- All applicable clarification reasons are retained in fixed precedence.
- No-match and clarification remain distinct.
- No artifact outcome is labeled failure.

### Lineage and reproducibility

- Every candidate identifies exactly one approved rule and version.
- Candidate observations correspond exactly to the parent evidence projection.
- Artifact transition evidence reproduces the exact parent typed values.
- Parent CU-1 identity and canonical digest are preserved exactly.
- Curriculum and orientation-policy versions are preserved exactly.
- A changed rule, curriculum, policy, or parent produces a distinct lineage.

### Determinism and immutability

- Equivalent input permutations produce equal artifacts.
- Equivalent inputs serialize to byte-identical canonical UTF-8 JSON.
- Candidate order uses the documented canonical key and carries no rank meaning.
- Construction does not mutate caller-owned collections or parent artifacts.
- Duplicate candidate, rule, and evidence identities fail closed.

### Isolation

- No provider, Journey Planning, Candidate Formation, scoring, selection,
  construction, evaluation, explanation, or accompaniment import is reachable.
- No generic claim helper can reinterpret a candidate as supported person truth.
- No production output bypasses `CurriculumOrientationArtifact`.
- Repository-wide structural searches prove CU-2 has no alternate production
  authority path.

## Stop point

This contract defines CU-2 authority, scope, invariants, artifact semantics,
outcomes, and its supporting architectural test plan only.

Do not implement CU-2 until this contract is approved.

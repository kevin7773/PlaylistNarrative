# Crossing Understanding Boundary

## Status

CU-1 is implemented as an additive, deterministic boundary. It represents the
first four steps of Penny's listening sequence:

```text
Evidence of lived experience
        ↓
Possible crossing
        ↓
Recurring human conditions
        ↓
Person-specific need
```

It does not choose accompaniment or begin musical reasoning. The conceptual
authority for this boundary is the [Crossing Model](crossing_model.md).

## Purpose

Crossing Understanding records what Penny can presently support about a
person's crossing, which recurring conditions may orient further listening, and
which person-specific need the user has stated or confirmed. It preserves
ambiguity and missing support rather than converting a visible event into an
objective or soundtrack.

An `AcceptedObjectiveArtifact` is the sole existing artifact authorized to
enter this boundary. The complete accepted artifact is embedded in the request
and output, and its exact canonical bytes are identified by SHA-256 digest.

## Inputs

`CrossingUnderstandingRequest` schema `1.0` contains:

- an exact request identity;
- the complete accepted Objective Safety artifact and canonical SHA-256 digest;
- an exact crossing-policy identity and version;
- one or more lived-evidence claims using the visible-event or metaphor role;
- zero or more transition candidates;
- zero or more recurring-condition candidates;
- an optional person-specific need.

Every source observation preserves an exact evidence identity, source type,
source reference, and typed JSON payload. The boundary does not trim, case-fold,
normalize Unicode, resolve aliases, or perform fuzzy correspondence.

## Evidence states

Lived-evidence, directional, and person-specific-need claims use five mutually
exclusive states:

1. `supported` requires an exact value, a user-stated or user-confirmed basis,
   and at least one source observation.
2. `unavailable` carries neither a value nor substitute observations.
3. `conflicting` carries no resolved value and retains at least two source
   observations.
4. `unsupported` retains the observation that failed to establish the claim.
5. `explicitly_inapplicable` retains evidence of inapplicability and is not
   treated as unavailable.

Unknown evidence never becomes neutral, typical, or presumed.

## Transition representation

A transition is represented by exact claims about what is ending or changing
and what is beginning or emerging. CU-1 does not classify an event against the
curriculum.

A transition may be directly stated, confirmed, or derived by the fixed
`crossing.directional_transition` rule version `1.0`. That derivation does not
interpret an event. It records the crossing already established by the exact
ending and beginning claims, and retains those two claim identities as its
complete inputs.

Multiple plausible transition candidates remain separate and canonically
ordered by UTF-8 candidate identity. Their order carries no ranking or
confidence meaning. More than one supported transition requires clarification;
none is selected.

Recurring conditions use a dedicated orientation-only candidate type rather
than general supported-claim semantics. A candidate records a pattern worth
considering, the observations that oriented attention toward it, and optional
named versioned rule provenance. It always records:

- `outcome = unresolved_orientation`;
- `applicability_to_person_established = false`;
- `person_membership_claimed = false`;
- `diagnosis_claimed = false`;
- `authoritative_for_particular_need = false`.

Supported source observations explain why a condition may be worth considering;
they never establish that the person is an instance of it. Direct user statements
about a condition remain source observations, not authenticated classifications.
The wording is preserved as evidence under an explicitly hypothetical structure,
not validated as person-level truth.

## Person-specific need

CU-1 resolves a need only when it is directly stated or explicitly confirmed by
the user. The package contains no derivation from event, transition, curriculum,
or recurring condition to need.

An otherwise complete crossing with an unavailable, unsupported, or conflicting
need remains on the clarification path.

## Outputs

`CrossingUnderstandingArtifact` schema `1.0` returns either:

- `understood`, with exactly one resolved retained transition and a supported
  person-specific need; or
- `clarification_required`, with no resolved transition and every applicable
  deterministic clarification reason.

Reasons retain fixed precedence, then exact UTF-8 field-path order. Missing,
unsupported, conflicting, and explicitly inapplicable evidence remain distinct.
Invalid parent digests, malformed provenance, incompatible roles, duplicate
identities, and unsupported derivation shapes fail closed at the contract rather
than becoming human clarification.

## Determinism and immutability

All CU-1 models are frozen and reject unknown fields. Caller-supplied collections
are copied into new canonically ordered tuples rather than mutated. Equivalent
input permutations produce equal artifacts and byte-identical compact UTF-8 JSON
serialization.

Every supported field is reproducible from embedded immutable observations or,
for the directional transition only, the named versioned rule and its exact
recorded inputs.

## Explicit non-claims

CU-1 does not:

- diagnose psychological state;
- classify a person;
- infer a need from the curriculum;
- establish that a recurring condition applies to the person;
- select faithful accompaniment;
- create a soundtrack objective;
- perform Journey Planning;
- access providers;
- form, score, rank, select, or sequence music;
- generate an explanation.

A later accompaniment boundary must consume this exact immutable artifact, or an
authenticated projection derived solely from it, without rewriting its claims.
New information creates a successor crossing artifact and a new traceable path.

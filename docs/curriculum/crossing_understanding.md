# Crossing Understanding Boundary

## Status

CU-1 schema `2.0` is implemented as an intentionally breaking, deterministic
boundary. Schema `1.0` accepted arbitrary ending and beginning claim text as
authoritative. The EA-1 adversarial review exposed that as an unearned
assumption, and schema `2.0` removes that production path without a compatibility
adapter. CU-1 represents the
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

Crossing Understanding derives the directional crossing supported by exact
authenticated characteristics. It also preserves lived evidence, unresolved
orientation candidates, and any person-specific need supplied by the caller,
but does not consume those preserved fields when deriving or resolving the
crossing. It preserves
ambiguity and missing support rather than converting a visible event into an
objective or soundtrack.

An `AcceptedObjectiveArtifact` authorizes the overall request. An exact
`AuthenticatedStructuredCharacteristicArtifact` produced by EA-1 is the sole
authority for every ending and beginning characteristic used by directional
crossing derivation. Both parent artifacts are embedded, digest-identified, and
required to carry exactly corresponding objective lineage.

## Inputs

`CrossingUnderstandingRequest` schema `2.0` contains:

- an exact request identity;
- the complete accepted Objective Safety artifact and canonical SHA-256 digest;
- an exact crossing-policy identity and version;
- the complete EA-1 artifact and SHA-256 digest of its canonical wrapper bytes;
- one or more lived-evidence claims using the visible-event or metaphor role;
- zero or more directional-transition requests containing only a candidate ID,
  an authenticated ending-characteristic ID, and an authenticated
  beginning-characteristic ID;
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

A transition is represented by exact immutable projections of an authenticated
ending characteristic and an authenticated beginning characteristic. CU-1 does
not accept free-text directional claims and does not classify an event against
the curriculum.

CU-1 derives a transition only through fixed rule
`crossing.directional_transition` version `1.0`. The request identifies two
characteristics already minted by EA-1; CU-1 resolves them against the embedded
authenticated partition, verifies their exact roles and values, and reproduces
them without normalization or reinterpretation. The derivation records the two
authenticated-characteristic identities as its complete inputs. Withheld EA-1
attempts and generic supported text cannot enter this path.

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

## Preserved evidence outside directional authority

Lived-event evidence, metaphors, recurring-condition candidates, and a supplied
person-specific need are carried for lineage and later boundaries. Presence is
not participation: CU-1 does not read their payloads or values for matching,
branching, comparison, directional derivation, or crossing resolution.

Their schemas continue to preserve evidence states and provenance without
granting them directional authority. A later boundary must determine whether a
person-specific need is sufficient for its own jurisdiction.

## Outputs

`CrossingUnderstandingArtifact` schema `2.0` returns either:

- `understood`, with exactly one resolved retained transition; or
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

Every directional field is reproducible solely from the embedded EA-1 artifact,
its authenticated partition, and the named directional rule with exact recorded
characteristic identities. CU-1 cannot authenticate or repair a characteristic.

## Explicit non-claims

CU-1 does not:

- authenticate ending or beginning characteristics;
- accept arbitrary directional claim text;
- normalize, alias, reinterpret, or re-bless EA-1 values;
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

# Candidate Constraint Evaluation v1 Contract

- **Status:** authority contract frozen and product evaluator implemented
- **Contract identity:** `pne.candidate-constraint-evaluation`
- **Contract version:** `1.0`
- **Boundary:** deterministic hard eligibility within Candidate Formation

## Purpose and invariant

Candidate Constraint Evaluation applies an explicitly declared, versioned
predicate to one explicitly selected governed candidate field. It produces one
of `ELIGIBLE`, `INELIGIBLE`, or `UNKNOWN` before scoring or selection.

The declaration is the sole constraint authority. Objective text, prompt text,
research records, provider prose, and arbitrary metadata cannot create or alter
a predicate, vocabulary, matching rule, field selection, or expected value.
Candidate Formation does not interpret natural-language constraints.

For every evaluation:

- exactly one registered predicate identity and version is dispatched;
- exactly one governed candidate field is selected;
- only evidence owned by that field may satisfy the predicate;
- all predicate-specific authority is immutable and digest-bound; and
- missing or unverifiable field authority never becomes compliance.

This contract governs candidate-level eligibility only. Playlist cardinality,
uniqueness, sequencing, and other construction-level constraints are outside its
scope.

## Predicate authority

The Candidate Formation implementation must expose one closed predicate
registry. Dispatch is by exact tuple `(predicate_id, predicate_version)`; no
aliases, version ranges, caller callbacks, import paths, expressions, or
executable payloads are permitted.

Candidate Constraint Evaluation v1 reserves these product predicate identities:

| Predicate identity | Version | Semantics |
| --- | --- | --- |
| `pne.candidate-constraint.exact-typed-equality` | `1.0` | The governed field value and declared JSON value are equal and have the same JSON type. |
| `pne.candidate-constraint.finite-vocabulary-membership` | `1.0` | The governed text field contains at least one complete term from the bound immutable vocabulary under the bound matching contract. |

An unsupported identity or version, a missing registry entry, an invalid
parameter shape, or a registry-authority mismatch invalidates the complete
Candidate Formation request. It is not an `UNKNOWN` candidate result and must
not fall back to equality or another predicate. Predicate execution must fail
closed on an internal dispatch or verification failure.

Registered predicate definitions are immutable. A change to accepted fields or
types, parameter meaning, comparison or matching behavior, evidence-state
mapping, result semantics, or deterministic reason requires a new predicate
version. Implementation repairs that cannot change any valid input, output, or
canonical authority may retain the version and must be covered by unchanged
conformance vectors.

The finite-vocabulary predicate is generic product machinery. No research
vocabulary, including Animal Vocabulary v1.0, is product authority under this
contract.

## Vocabulary authority

A finite-vocabulary predicate must bind one immutable product-domain vocabulary
artifact. Product vocabularies are approved inputs owned by the product request
and declaration lifecycle, not inferred by Candidate Formation and not imported
from the research store.

Each vocabulary artifact must contain:

- artifact schema and version;
- immutable vocabulary identity and version;
- a non-empty tuple of non-empty Unicode terms;
- the matching-contract identity, version, and canonical SHA-256 for which the
  terms are valid; and
- its own canonical SHA-256.

Terms may be one token or a multi-token phrase. Every term must already be NFC,
must contain at least one token under the bound matching contract, and must not
have leading or trailing delimiters. Terms that reduce to the same matched token
sequence are duplicates and invalidate the vocabulary.

Canonical vocabulary content follows the existing Candidate Formation
convention: schema-order UTF-8 JSON with no insignificant whitespace. Terms are
ordered by their exact UTF-8 bytes after NFC validation. The vocabulary digest
is SHA-256 over the canonical representation excluding the digest field itself.
Term addition, removal, spelling, case, phrase, matching-contract binding,
identity, or version changes canonical authority and requires a new vocabulary
version. Published vocabulary versions are immutable.

## Matching-contract authority

Finite-vocabulary membership v1 requires the following matching authority:

- **identity:** `pne.candidate-text-match.unicode-token-sequence`
- **version:** `1.0`
- **Unicode data version:** `16.0.0`
- **normalization:** NFC on both the governed field value and vocabulary term;
- **case behavior:** Unicode Default Case Folding under the pinned Unicode data
  version;
- **tokens:** maximal sequences beginning with a Unicode Letter (`L*`) or Number
  (`N*`) and continuing with Letters, Numbers, or attached Marks (`M*`);
- **boundaries:** every other code point, including whitespace and punctuation,
  is a delimiter and cannot be part of or bridge a token; and
- **match:** a vocabulary term's complete token sequence must occur contiguously
  in the field's token sequence.

The canonical matching-contract representation is:

```json
{"case":"unicode-default-case-fold","contract_id":"pne.candidate-text-match.unicode-token-sequence","contract_version":"1.0","normalization":"NFC","term_match":"contiguous-complete-token-sequence","tokenization":"unicode-letter-number-with-attached-marks","unicode_version":"16.0.0"}
```

Its canonical SHA-256 is recorded by the implementation registry and must match
the declaration and vocabulary bindings:
`1ca1bca3e144fee32363ed2f3be831e87287c7890501f37e083f6fe0cab2c6ed`.
The implementation must use the pinned Unicode tables; a runtime whose matching
profile cannot be verified must reject the request rather than silently use
host-dependent behavior.

There is no substring-inside-token, stemming, lemmatization, transliteration,
alias expansion, spelling correction, fuzzy matching, semantic matching, or
cross-field matching. Such behavior would require a separately governed future
predicate or matching contract.

## Field authority

The declaration selects exactly one member of the existing governed
`CandidateConstraintField` vocabulary. Evaluation reads only that field's
documented evidence owner:

| Field | Governing evidence |
| --- | --- |
| `displayed_title` | Exact validated track title and its source record |
| `displayed_artist` | Exact validated artist and its source record |
| `source_catalog_identity` | Measured candidate identity metadata |
| `release_version_identity` | Measured candidate identity metadata |
| `displayed_explicit` | Measured candidate identity metadata |

A value in any other field has no bearing on the result. In particular, a term
found in `displayed_artist` cannot satisfy a predicate declared for
`displayed_title`.

An authority-level problem—unknown field identity, incompatible field type, or
unverifiable declaration/evidence correspondence—invalidates the request. For a
valid request, a candidate whose selected field is unavailable, conflicting,
unsupported, or explicitly inapplicable produces `UNKNOWN`. Only measured or
validated field authority can produce a match or nonmatch.

Finite-vocabulary membership is valid only for a field whose governed observed
value is a JSON string. Selecting `displayed_explicit` or any future non-text
field for that predicate invalidates the request; it does not stringify the
value.

## Result semantics

The result vocabulary remains the existing Candidate Formation vocabulary:

- `ELIGIBLE`: authoritative field evidence exists and the declared predicate
  evaluates true;
- `INELIGIBLE`: authoritative field evidence exists and the declared predicate
  evaluates false; and
- `UNKNOWN`: the predicate cannot be evaluated because the selected field lacks
  usable authoritative evidence.

`UNKNOWN` is not a nonmatch. A genuine authoritative nonmatch is `INELIGIBLE`.
Candidate Formation continues to withhold both `INELIGIBLE` and `UNKNOWN`
candidates from the formed pool. Unsupported predicate authority, malformed
parameters, and digest or correspondence failures remain invalid input rather
than candidate results.

Deterministic reason authority is:

| Predicate | Condition | Reason |
| --- | --- | --- |
| Exact typed equality | equal, `displayed_explicit` | existing `PROPERTY_MATCH` |
| Exact typed equality | unequal, `displayed_explicit` | existing `PROPERTY_MISMATCH` |
| Exact typed equality | equal, any other existing field | existing `EXACT_MATCH` |
| Exact typed equality | unequal, any other existing field | existing `EXACT_MISMATCH` |
| Exact typed equality | unusable selected-field evidence | existing `REQUIRED_METADATA_UNKNOWN` |
| Finite vocabulary | one or more complete terms match | `VOCABULARY_MEMBER_MATCH` |
| Finite vocabulary | no complete term matches | `VOCABULARY_MEMBER_NONMATCH` |
| Finite vocabulary | unusable selected-field evidence | `REQUIRED_FIELD_UNKNOWN` |

A finite-vocabulary result records the canonically ordered exact vocabulary
terms whose token sequences matched. `ELIGIBLE` requires a non-empty matched
tuple; `INELIGIBLE` requires an empty tuple and authoritative observed text;
`UNKNOWN` records no observed text and no matched terms.

## Declaration authority and versioning

`HardConstraintDeclarationArtifact` schema `1.0` remains frozen. Its
`CandidateHardConstraint` entries retain their existing implicit exact typed
equality semantics and original canonical serialization. No predicate, null,
empty, default, vocabulary, matching-contract, or digest fields may be inserted
when loading or serializing a schema `1.0` declaration.

Implementation of this contract requires an additive declaration schema `2.0`.
It must bind the complete declaration canonically by SHA-256 and give each
constraint an explicit predicate identity/version plus a closed,
predicate-specific parameter variant:

- exact typed equality: one canonical typed JSON expected value;
- finite vocabulary membership: vocabulary identity/version/digest and
  matching-contract identity/version/digest.

The selected governed field is common authority for both variants. Arbitrary
JSON parameter maps, extension metadata, executable hooks, and caller-defined
predicate content are prohibited. Constraint keys remain unique and canonical
constraint ordering remains exact UTF-8 ordering by key.

The declaration digest covers schema/artifact identity, declaration identity and
version, source authority, every constraint, its field, predicate identity and
version, and every typed parameter binding. It excludes only its own digest
field. Any governed change requires a new declaration version and digest.

Historical declarations and artifacts are never rewritten into schema `2.0`.
The explicit equality predicate explains the successor model; it does not alter
the scientific or product meaning, bytes, or identity of a schema `1.0`
declaration.

## Evaluation and formation provenance

Each successor eligibility record, Candidate Formation artifact, authenticated
formed-pool view, and downstream final-product audit must retain or make
recoverable:

- declaration identity, version, schema version, and canonical digest;
- constraint key and selected governed field;
- predicate identity and version;
- vocabulary identity, version, and digest when applicable;
- matching-contract identity, version, and digest when applicable;
- exact predicate parameters;
- source-evidence artifact and record identities for the selected field;
- exact observed canonical value, or the preserved unusable evidence state;
- `ELIGIBLE`, `INELIGIBLE`, or `UNKNOWN` result and deterministic reason; and
- the Candidate Formation request and artifact correspondence needed to replay
  the evaluation.

Provenance is descriptive authority for audit and verification; it cannot
override the predicate result. A fresh verifier must reject declaration,
predicate, vocabulary, matching-contract, field, observation, evidence, result,
or formation substitution.

## Compatibility and production boundary

Existing schema `1.0` equality is preserved exactly: equality compares the
governed observed value with `expected_json` and requires both value equality
and identical JSON type. Missing metadata remains `UNKNOWN`. Existing reasons,
formation withholding, scoring, selection, and no-bypass behavior do not change.

The future explicit equality evaluator must reproduce that behavior for schema
`2.0`; it must not be used to reinterpret or reserialize historical artifacts.
The finite-vocabulary evaluator is additive and may execute only for a verified
schema `2.0` declaration.

Candidate Formation remains the sole production evaluation boundary. The
Formation Request Assembler may verify and bind declaration authority but may
not execute predicates. Providers may supply source evidence but may not decide
eligibility. Scoring and sequencing receive only the authenticated formed pool
and cannot reconsider an `INELIGIBLE` or `UNKNOWN` candidate.

## Implemented boundary

The product implementation supplies the schema `2.0` declaration and vocabulary
artifacts, closed registry, canonical digests, successor provenance, exact
legacy canonicalization protection, matching-profile conformance coverage,
substitution/tamper rejection, and structural no-bypass tests. Schema `1.0`
remains the default legacy representation and is never rewritten.

No prompt parser, research import, product vocabulary content, fuzzy matcher,
provider change, scoring change, sequencing change, construction-level
constraint, UI, or Study is authorized by this contract.

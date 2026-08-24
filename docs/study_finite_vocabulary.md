# Study finite-vocabulary field predicate

## Authority boundary

P7 registered Study protocols may evaluate whether one governed text field per
subject contains at least one member of one frozen finite vocabulary. This is a
research structured-evaluation capability. It is not a prompt parser, semantic
classifier, genre taxonomy, or Candidate Formation predicate.

The subject evaluator identity is
`subject.lexical_any_vocabulary_member/1`. A valid plan uses a
`PLACEMENT_FIELD` subject, an explicit `subject_field`, a required `TEXT`
measurement, and plan-local `vocabulary_terms`. The registered protocol and its
registration hash preserve the field, terms, evaluator, parameters, evidence
policy, and aggregate policy.

The plan must bind these additional authorities:

- `vocabulary_key`, schema version `1.0`, `vocabulary_id`, and `vocabulary_version`;
- `vocabulary_sha256`, recomputed from the exact unordered member set;
- matching contract ID `pne.lexical.standalone-vocabulary-member`;
- matching contract version `1.0` and its frozen implementation digest;
- `case_sensitive` as an explicit Boolean.

Registration and execution fail closed when the vocabulary digest or matching
contract authority does not correspond exactly.

## Vocabulary canonicalization

Finite-vocabulary schema version `1.0` treats membership as an unordered set of
exact `(term_key, term_definition)` pairs. Canonical serialization sorts those
pairs by UTF-8 bytes, emits canonical UTF-8 JSON, and hashes it with SHA-256.
Keys and definitions must be non-empty and independently unique. No trimming,
case folding, Unicode normalization, alias expansion, taxonomy lookup, or
semantic completion occurs.

Changing vocabulary identity, version, key, member key, or member definition
changes its canonical digest. Authoring order does not.

## Matching contract 1.0

The evaluator reuses the existing standalone-token rule mechanically:

`(?<![\w])re.escape(member)(?![\w])`

- Only the registered governed text measurement is inspected.
- The match is not whole-field equality and is not unrestricted substring
  matching.
- A member's internal punctuation and whitespace are literal.
- Boundaries use Python Unicode regular-expression `\w` semantics.
- Unicode is not normalized.
- Case is either exact or Python Unicode `IGNORECASE`, as frozen by the
  registered `case_sensitive` parameter.
- Multiword members retain their exact internal code-point sequence, subject
  only to that case setting.
- One or more matching members is `PASS`; zero is `FAIL`.
- Multiple matches do not alter the result.
- An unavailable required measurement is `UNKNOWN`, never an empty value or a
  match inferred from another field.

The evaluator supplies only the per-subject result. Existing registered
aggregate evaluators remain authoritative for universal behavior. A protocol
may use `aggregate.all_subjects_required/1` and register `mixed_status=FAIL`,
`all_fail_status=FAIL`, and `unknown_status=UNKNOWN` when any violating subject
must fail the constraint.

## Explicit non-claims

The capability does not supply a vocabulary. In particular, it defines no
animal list or genre classification. It does not infer vocabulary membership
from prompt prose, artist names, album names, provider metadata, or semantic
relatedness.

It also does not implement negation. A “contains no member” predicate would
require a separately registered evaluator or other already-governed inversion
contract; aggregate status parameters cannot invert individual subject
semantics safely.

The Guided Study Builder does not expose this evaluator because it has no
governed vocabulary-artifact selection workflow. Advanced protocol payloads
may use it only by supplying the complete verified authority. Product Candidate
Formation remains limited to its existing exact typed constraints.

Semantic assessment remains independent: a favorable `assessment_outcome` may
coexist with a governed hard-constraint `FAIL` without either result rewriting
the other.

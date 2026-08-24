# Animal Vocabulary v1.0

## Purpose and authority

Animal Vocabulary v1.0 is a repository-owned curated English lexical research
instrument. Its only question is whether a governed text field contains at
least one explicitly published animal-name surface form under the frozen
standalone-vocabulary matching contract.

It is not a biological taxonomy and does not decide whether a title is
animal-themed, whether a word is intended zoologically, or whether an artist,
album, lyric, prompt, or provider field supplies an animal association.

Authoritative publication:

- vocabulary key: `animal-names`
- vocabulary ID: `pne.research-vocabulary.animal-names`
- vocabulary version: `1.0`
- finite-vocabulary schema: `1.0`
- member count: 351
- canonical SHA-256:
  `c63f9de32ebfc76b4ff622f68bf3422a062a4a9afbdb120f94a4a40b8aec95cb`
- exact member publication:
  `research_store/animal_vocabulary.py::ANIMAL_VOCABULARY_TERMS`

The code constant is the exact member list and supplies exact stable term keys
and exact lexical term definitions. The literal digest and focused tests make
silent mutation under version `1.0` fail closed.

## Publication rule

The initial finite set includes ordinary common-English animal words reasonably
likely to occur as lexical units in music titles. It is intentionally broad but
reviewable rather than exhaustive.

Included scopes are:

- familiar broad nouns such as animal, bird, fish, dog, and cat;
- ordinary names for mammals, birds, fish, reptiles, amphibians, insects,
  arachnids, other commonly named invertebrates, and marine animals;
- common English names of selected extinct real-world animals;
- independently published singular, plural, and irregular surface forms;
- common compound and multiword animal names;
- legitimate animal names that also have common non-animal meanings.

Omitted are:

- breeds;
- Latin binomials;
- formal taxonomic-rank terminology not ordinarily used as an animal name;
- obscure names requiring an expanded curation policy;
- mythical creatures, fictional species, and invented creatures.

No external taxonomy, dictionary, API, website, or provider is runtime
authority. The published repository list itself is the authority.

## Morphology, compounds, and ambiguity

Every accepted surface form is explicit. There is no stemming, lemmatization,
plural inference, fuzzy matching, or NLP. For example, `wolf` and `wolves`,
`mouse` and `mice`, `monkey` and `monkeys`, and `dove` and `doves` are distinct
members.

Compounds including `blackbird`, `catfish`, `seahorse`, `ladybug`, and
`butterfly` are independently published. The evaluator never decomposes them:
`bird` does not match inside `blackbird`, and `cat` does not match inside
`catfish`.

Ambiguous terms including `seal`, `bass`, `crane`, `mole`, and `turkey` are
included because they are legitimate common English animal names. Matching is
lexical: a standalone occurrence matches regardless of its meaning in a
particular title. No contextual semantic disambiguation is claimed.

`phoenix`, `dragon`, `unicorn`, `griffin`, and other mythical or fictional
creatures are outside v1.0.

## Matching and Study use

The vocabulary binds exactly to:

- matching contract ID: `pne.lexical.standalone-vocabulary-member`
- matching contract version: `1.0`
- matching-contract SHA-256:
  `af6667117cc53f29b433ed2bbde6f6a5792e4e0460ca561b8a7e4fe1314de20d`
- case-sensitive setting: `false`

A prospective universal title constraint uses:

- subject kind `PLACEMENT_FIELD`;
- field `display_title`;
- selector `selector.all_placements/1`;
- evaluator `subject.lexical_any_vocabulary_member/1`;
- aggregate `aggregate.all_subjects_required/1`;
- `mixed_status=FAIL`;
- `all_fail_status=FAIL`;
- `unknown_status=UNKNOWN`.

Only the governed title measurement participates. An animal term appearing
only in the displayed artist remains a title-predicate failure. Unavailable
title evidence remains `UNKNOWN` under the registered evidence policy.

## Versioning and succession

Version 1.0 is immutable. Any addition, deletion, spelling change, term-key
change, definition change, membership-policy change, or matching-policy change
requires a successor vocabulary version and a new canonical digest. A
successor does not rewrite or reinterpret a Study registered against v1.0.

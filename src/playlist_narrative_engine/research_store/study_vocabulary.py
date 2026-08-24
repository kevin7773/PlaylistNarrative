from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping


FINITE_VOCABULARY_SCHEMA_VERSION = "1.0"
STANDALONE_MEMBER_MATCH_CONTRACT_ID = "pne.lexical.standalone-vocabulary-member"
STANDALONE_MEMBER_MATCH_CONTRACT_VERSION = "1.0"

_MATCH_CONTRACT = {
    "contract_id": STANDALONE_MEMBER_MATCH_CONTRACT_ID,
    "contract_version": STANDALONE_MEMBER_MATCH_CONTRACT_VERSION,
    "field_scope": "Only the registered governed TEXT measurement is inspected.",
    "matching": "A member matches (?<![\\w])re.escape(member)(?![\\w]).",
    "case_behavior": "The registered case_sensitive Boolean selects exact case or Python Unicode IGNORECASE.",
    "unicode_behavior": "No Unicode normalization; Python Unicode regular-expression semantics apply.",
    "punctuation_behavior": "Punctuation is literal inside a member and is a boundary when it is not a Unicode word character.",
    "token_behavior": "Standalone lexical membership; neither whole-field equality nor unrestricted substring matching.",
    "multiword_behavior": "Multiword members match their exact internal code-point sequence subject only to registered case behavior.",
    "multiple_matches": "One or more registered members is PASS; match count and member order do not change status.",
    "unavailable_behavior": "UNAVAILABLE is UNKNOWN.",
}


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


STANDALONE_MEMBER_MATCH_CONTRACT_SHA256 = (
    "af6667117cc53f29b433ed2bbde6f6a5792e4e0460ca561b8a7e4fe1314de20d"
)
if hashlib.sha256(_canonical_json(_MATCH_CONTRACT)).hexdigest() != STANDALONE_MEMBER_MATCH_CONTRACT_SHA256:
    raise RuntimeError("frozen standalone-vocabulary matching contract changed without a new version")


def canonical_finite_vocabulary_bytes(
    *,
    vocabulary_id: str,
    vocabulary_version: str,
    vocabulary_key: str,
    terms: Iterable[Mapping[str, object]],
) -> bytes:
    """Canonicalize one immutable plan-local finite vocabulary.

    Membership is an unordered set identified by exact term keys and exact term
    definitions. Canonical ordering is UTF-8 byte order of (term_key,
    term_definition), independent of authoring order.
    """
    members = [
        {
            "term_key": str(item["term_key"]),
            "term_definition": str(item["term_definition"]),
        }
        for item in terms
        if item.get("vocabulary_key") == vocabulary_key
    ]
    members.sort(
        key=lambda item: (
            item["term_key"].encode("utf-8"),
            item["term_definition"].encode("utf-8"),
        )
    )
    if not vocabulary_id or not vocabulary_version or not vocabulary_key or not members:
        raise ValueError("finite vocabulary identity, version, key, and members are required")
    keys = [item["term_key"] for item in members]
    definitions = [item["term_definition"] for item in members]
    if any(not value for value in keys + definitions):
        raise ValueError("finite vocabulary member keys and definitions must be non-empty")
    if len(keys) != len(set(keys)) or len(definitions) != len(set(definitions)):
        raise ValueError("finite vocabulary members must have unique keys and definitions")
    return _canonical_json({
        "schema_version": FINITE_VOCABULARY_SCHEMA_VERSION,
        "vocabulary_id": vocabulary_id,
        "vocabulary_version": vocabulary_version,
        "vocabulary_key": vocabulary_key,
        "membership_semantics": "UNORDERED_EXACT_MEMBER_SET",
        "members": members,
    })


def finite_vocabulary_sha256(**kwargs: object) -> str:
    return hashlib.sha256(canonical_finite_vocabulary_bytes(**kwargs)).hexdigest()


def verify_finite_vocabulary_plan(
    plan: Mapping[str, object], parameters: Mapping[str, object]
) -> tuple[str, ...]:
    """Verify vocabulary and matching authority frozen in a P7 plan."""
    expected_contract = (
        STANDALONE_MEMBER_MATCH_CONTRACT_ID,
        STANDALONE_MEMBER_MATCH_CONTRACT_VERSION,
        STANDALONE_MEMBER_MATCH_CONTRACT_SHA256,
    )
    actual_contract = (
        parameters.get("matching_contract_id"),
        parameters.get("matching_contract_version"),
        parameters.get("matching_contract_sha256"),
    )
    if actual_contract != expected_contract:
        raise ValueError("standalone vocabulary matching-contract authority is unsupported or substituted")
    if parameters.get("vocabulary_schema_version") != FINITE_VOCABULARY_SCHEMA_VERSION:
        raise ValueError("finite vocabulary schema version is unsupported or substituted")
    vocabulary_key = parameters.get("vocabulary_key")
    if not isinstance(vocabulary_key, str):
        raise ValueError("finite vocabulary key is required")
    terms = list(plan.get("vocabulary_terms", []))
    digest = finite_vocabulary_sha256(
        vocabulary_id=str(parameters.get("vocabulary_id") or ""),
        vocabulary_version=str(parameters.get("vocabulary_version") or ""),
        vocabulary_key=vocabulary_key,
        terms=terms,
    )
    if parameters.get("vocabulary_sha256") != digest:
        raise ValueError("finite vocabulary digest does not match its governed members")
    return tuple(
        str(item["term_definition"])
        for item in sorted(
            (item for item in terms if item.get("vocabulary_key") == vocabulary_key),
            key=lambda item: (
                str(item["term_key"]).encode("utf-8"),
                str(item["term_definition"]).encode("utf-8"),
            ),
        )
    )

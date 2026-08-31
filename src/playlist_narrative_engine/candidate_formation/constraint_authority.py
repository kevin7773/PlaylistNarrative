from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.schemas import (
    FrozenCandidateEvidenceModel,
)


EXACT_TYPED_EQUALITY_PREDICATE_ID = (
    "pne.candidate-constraint.exact-typed-equality"
)
FINITE_VOCABULARY_PREDICATE_ID = (
    "pne.candidate-constraint.finite-vocabulary-membership"
)
PREDICATE_VERSION = "1.0"
MATCHING_CONTRACT_ID = "pne.candidate-text-match.unicode-token-sequence"
MATCHING_CONTRACT_VERSION = "1.0"
MATCHING_CONTRACT_SHA256 = (
    "1ca1bca3e144fee32363ed2f3be831e87287c7890501f37e083f6fe0cab2c6ed"
)
MATCHING_UNICODE_VERSION = "16.0.0"

_MATCHING_CONTRACT_CONTENT = {
    "case": "unicode-default-case-fold",
    "contract_id": MATCHING_CONTRACT_ID,
    "contract_version": MATCHING_CONTRACT_VERSION,
    "normalization": "NFC",
    "term_match": "contiguous-complete-token-sequence",
    "tokenization": "unicode-letter-number-with-attached-marks",
    "unicode_version": MATCHING_UNICODE_VERSION,
}


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def matching_contract_bytes() -> bytes:
    return canonical_json_bytes(_MATCHING_CONTRACT_CONTENT)


def verify_matching_contract() -> None:
    digest = hashlib.sha256(matching_contract_bytes()).hexdigest()
    if digest != MATCHING_CONTRACT_SHA256:
        raise ValueError("matching-contract canonical authority is invalid")
    if unicodedata.unidata_version != MATCHING_UNICODE_VERSION:
        raise ValueError("Unicode matching authority is unsupported by this runtime")


class CandidateConstraintVocabularyArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["candidate_constraint_vocabulary"] = (
        "candidate_constraint_vocabulary"
    )
    vocabulary_id: str = Field(min_length=1, max_length=200)
    vocabulary_version: str = Field(min_length=1, max_length=100)
    terms: tuple[str, ...] = Field(min_length=1)
    matching_contract_id: Literal[
        "pne.candidate-text-match.unicode-token-sequence"
    ] = MATCHING_CONTRACT_ID
    matching_contract_version: Literal["1.0"] = MATCHING_CONTRACT_VERSION
    matching_contract_sha256: Literal[
        "1ca1bca3e144fee32363ed2f3be831e87287c7890501f37e083f6fe0cab2c6ed"
    ] = MATCHING_CONTRACT_SHA256
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("vocabulary_id", "vocabulary_version")
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("vocabulary identities must be exact")
        return value

    @field_validator("terms", mode="before")
    @classmethod
    def canonicalize_terms(cls, value: object) -> tuple[str, ...]:
        terms = tuple(value)  # type: ignore[arg-type]
        if any(not isinstance(term, str) for term in terms):
            raise ValueError("vocabulary terms must be strings")
        normalized = tuple(unicodedata.normalize("NFC", term) for term in terms)
        if normalized != terms:
            raise ValueError("vocabulary terms must already be NFC")
        return tuple(sorted(terms, key=lambda term: term.encode("utf-8")))

    @model_validator(mode="after")
    def verify_authority(self) -> CandidateConstraintVocabularyArtifact:
        verify_matching_contract()
        token_sequences: list[tuple[str, ...]] = []
        for term in self.terms:
            if not term or term != term.strip():
                raise ValueError("vocabulary terms must be nonblank and exact")
            if not _has_token_edge(term):
                raise ValueError("vocabulary terms cannot have boundary delimiters")
            tokens = tokenize_text(term)
            if not tokens:
                raise ValueError("vocabulary terms must contain at least one token")
            token_sequences.append(tokens)
        if len(token_sequences) != len(set(token_sequences)):
            raise ValueError("vocabulary matched token sequences must be unique")
        if self.canonical_sha256 != vocabulary_content_sha256(self):
            raise ValueError("vocabulary canonical digest does not match its content")
        return self


def vocabulary_content(artifact: CandidateConstraintVocabularyArtifact) -> dict[str, object]:
    return artifact.model_dump(mode="json", exclude={"canonical_sha256"})


def vocabulary_content_sha256(artifact: CandidateConstraintVocabularyArtifact) -> str:
    return hashlib.sha256(canonical_json_bytes(vocabulary_content(artifact))).hexdigest()


def create_candidate_constraint_vocabulary(
    *,
    vocabulary_id: str,
    vocabulary_version: str,
    terms: tuple[str, ...],
) -> CandidateConstraintVocabularyArtifact:
    ordered = tuple(sorted(terms, key=lambda term: term.encode("utf-8")))
    content: dict[str, object] = {
        "schema_version": "1.0",
        "artifact_kind": "candidate_constraint_vocabulary",
        "vocabulary_id": vocabulary_id,
        "vocabulary_version": vocabulary_version,
        "terms": ordered,
        "matching_contract_id": MATCHING_CONTRACT_ID,
        "matching_contract_version": MATCHING_CONTRACT_VERSION,
        "matching_contract_sha256": MATCHING_CONTRACT_SHA256,
    }
    digest = hashlib.sha256(canonical_json_bytes(content)).hexdigest()
    return CandidateConstraintVocabularyArtifact(**content, canonical_sha256=digest)


def serialize_candidate_constraint_vocabulary(
    artifact: CandidateConstraintVocabularyArtifact,
) -> bytes:
    CandidateConstraintVocabularyArtifact.model_validate(artifact.model_dump(mode="json"))
    return canonical_json_bytes(artifact.model_dump(mode="json"))


def tokenize_text(value: str) -> tuple[str, ...]:
    verify_matching_contract()
    folded = unicodedata.normalize("NFC", value).casefold()
    tokens: list[str] = []
    current: list[str] = []
    for character in folded:
        category = unicodedata.category(character)
        if category[0] in {"L", "N"}:
            current.append(character)
        elif category[0] == "M" and current:
            current.append(character)
        else:
            if current:
                tokens.append("".join(current))
                current = []
    if current:
        tokens.append("".join(current))
    return tuple(tokens)


def matched_vocabulary_terms(
    value: str,
    vocabulary: CandidateConstraintVocabularyArtifact,
) -> tuple[str, ...]:
    verified = CandidateConstraintVocabularyArtifact.model_validate(
        vocabulary.model_dump(mode="json")
    )
    value_tokens = tokenize_text(value)
    matches: list[str] = []
    for term in verified.terms:
        term_tokens = tokenize_text(term)
        width = len(term_tokens)
        if any(
            value_tokens[index : index + width] == term_tokens
            for index in range(len(value_tokens) - width + 1)
        ):
            matches.append(term)
    return tuple(matches)


def _has_token_edge(value: str) -> bool:
    normalized = unicodedata.normalize("NFC", value).casefold()
    if not normalized:
        return False
    return unicodedata.category(normalized[0])[0] in {"L", "N"} and (
        unicodedata.category(normalized[-1])[0] in {"L", "N", "M"}
    )

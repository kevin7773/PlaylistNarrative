from __future__ import annotations

import json
import hashlib
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CandidateHardConstraint,
)
from playlist_narrative_engine.candidate_formation.constraint_authority import (
    CandidateConstraintVocabularyArtifact,
    EXACT_TYPED_EQUALITY_PREDICATE_ID,
    FINITE_VOCABULARY_PREDICATE_ID,
    PREDICATE_VERSION,
    canonical_json_bytes,
)
from playlist_narrative_engine.candidate_formation.schemas import (
    FrozenCandidateEvidenceModel,
)


HARD_CONSTRAINT_DECLARATION_SCHEMA_VERSION = "1.0"
HARD_CONSTRAINT_DECLARATION_SCHEMA_VERSION_V2 = "2.0"


class HardConstraintDeclarationArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0", "2.0"] = HARD_CONSTRAINT_DECLARATION_SCHEMA_VERSION
    artifact_kind: Literal["hard_constraint_declaration"] = "hard_constraint_declaration"
    artifact_id: str = Field(min_length=1, max_length=200)
    declaration_version: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    constraints: tuple[CandidateHardConstraint, ...] = Field(min_length=1)
    vocabularies: tuple[CandidateConstraintVocabularyArtifact, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )
    canonical_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )

    @field_validator(
        "artifact_id", "declaration_version", "source_type", "source_reference"
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("constraint declaration identities must be nonblank and exact")
        return value

    @field_validator("constraints", mode="before")
    @classmethod
    def canonicalize_constraints(cls, value: object) -> tuple[object, ...]:
        return tuple(
            sorted(
                tuple(value),
                key=lambda item: _constraint_key(item).encode("utf-8"),
            )
        )

    @field_validator("vocabularies", mode="before")
    @classmethod
    def canonicalize_vocabularies(cls, value: object) -> tuple[object, ...]:
        return tuple(
            sorted(
                tuple(value),  # type: ignore[arg-type]
                key=lambda item: (
                    _vocabulary_identity(item, "vocabulary_id").encode("utf-8"),
                    _vocabulary_identity(item, "vocabulary_version").encode("utf-8"),
                ),
            )
        )

    @model_validator(mode="after")
    def require_unique_constraints(self) -> HardConstraintDeclarationArtifact:
        keys = tuple(item.constraint_key for item in self.constraints)
        if len(keys) != len(set(keys)):
            raise ValueError("declared hard constraint keys must be unique")
        if self.schema_version == "1.0":
            if self.vocabularies or self.canonical_sha256 is not None:
                raise ValueError("schema 1.0 canonical authority cannot be extended")
            if any(item.predicate_id is not None for item in self.constraints):
                raise ValueError("schema 1.0 constraints retain implicit exact equality")
            return self
        if self.canonical_sha256 is None:
            raise ValueError("schema 2.0 declarations require a canonical digest")
        if any(item.predicate_id is None for item in self.constraints):
            raise ValueError("schema 2.0 constraints require explicit predicates")
        supported = {
            (EXACT_TYPED_EQUALITY_PREDICATE_ID, PREDICATE_VERSION),
            (FINITE_VOCABULARY_PREDICATE_ID, PREDICATE_VERSION),
        }
        if any(
            (item.predicate_id, item.predicate_version) not in supported
            for item in self.constraints
        ):
            raise ValueError("unsupported candidate constraint predicate identity/version")
        vocabularies = {
            (item.vocabulary_id, item.vocabulary_version): item
            for item in self.vocabularies
        }
        if len(vocabularies) != len(self.vocabularies):
            raise ValueError("declared vocabularies must have unique identity/version")
        for constraint in self.constraints:
            if constraint.predicate_id != FINITE_VOCABULARY_PREDICATE_ID:
                continue
            vocabulary = vocabularies.get(
                (constraint.vocabulary_id, constraint.vocabulary_version)
            )
            if vocabulary is None or vocabulary.canonical_sha256 != constraint.vocabulary_sha256:
                raise ValueError("constraint vocabulary authority must resolve exactly")
            if (
                vocabulary.matching_contract_id != constraint.matching_contract_id
                or vocabulary.matching_contract_version != constraint.matching_contract_version
                or vocabulary.matching_contract_sha256 != constraint.matching_contract_sha256
            ):
                raise ValueError("constraint matching authority must resolve exactly")
        if self.canonical_sha256 != hard_constraint_declaration_content_sha256(self):
            raise ValueError("declaration canonical digest does not match its content")
        return self


def serialize_hard_constraint_declaration(
    artifact: HardConstraintDeclarationArtifact,
) -> bytes:
    artifact = HardConstraintDeclarationArtifact.model_validate(
        artifact.model_dump(mode="json")
    )
    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def hard_constraint_declaration_content(
    artifact: HardConstraintDeclarationArtifact,
) -> dict[str, object]:
    return artifact.model_dump(mode="json", exclude={"canonical_sha256"})


def hard_constraint_declaration_content_sha256(
    artifact: HardConstraintDeclarationArtifact,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(hard_constraint_declaration_content(artifact))
    ).hexdigest()


def create_hard_constraint_declaration_v2(
    *,
    artifact_id: str,
    declaration_version: str,
    source_type: str,
    source_reference: str,
    constraints: tuple[CandidateHardConstraint, ...],
    vocabularies: tuple[CandidateConstraintVocabularyArtifact, ...] = (),
) -> HardConstraintDeclarationArtifact:
    ordered_constraints = tuple(
        sorted(constraints, key=lambda item: item.constraint_key.encode("utf-8"))
    )
    ordered_vocabularies = tuple(
        sorted(
            vocabularies,
            key=lambda item: (
                item.vocabulary_id.encode("utf-8"),
                item.vocabulary_version.encode("utf-8"),
            ),
        )
    )
    content: dict[str, object] = {
        "schema_version": "2.0",
        "artifact_kind": "hard_constraint_declaration",
        "artifact_id": artifact_id,
        "declaration_version": declaration_version,
        "source_type": source_type,
        "source_reference": source_reference,
        "constraints": ordered_constraints,
    }
    if ordered_vocabularies:
        content["vocabularies"] = ordered_vocabularies
    serialized = {
        key: (
            [item.model_dump(mode="json") for item in value]
            if isinstance(value, tuple)
            else value
        )
        for key, value in content.items()
    }
    digest = hashlib.sha256(canonical_json_bytes(serialized)).hexdigest()
    return HardConstraintDeclarationArtifact(**content, canonical_sha256=digest)


def _constraint_key(item: object) -> str:
    value = item.get("constraint_key") if isinstance(item, dict) else getattr(item, "constraint_key", "")
    return value if isinstance(value, str) else ""


def _vocabulary_identity(item: object, field: str) -> str:
    value = item.get(field) if isinstance(item, dict) else getattr(item, field, "")
    return value if isinstance(value, str) else ""

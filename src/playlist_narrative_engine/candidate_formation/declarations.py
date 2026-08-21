from __future__ import annotations

import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CandidateHardConstraint,
)
from playlist_narrative_engine.candidate_formation.schemas import (
    FrozenCandidateEvidenceModel,
)


HARD_CONSTRAINT_DECLARATION_SCHEMA_VERSION = "1.0"


class HardConstraintDeclarationArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = HARD_CONSTRAINT_DECLARATION_SCHEMA_VERSION
    artifact_kind: Literal["hard_constraint_declaration"] = "hard_constraint_declaration"
    artifact_id: str = Field(min_length=1, max_length=200)
    declaration_version: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    constraints: tuple[CandidateHardConstraint, ...] = Field(min_length=1)

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

    @model_validator(mode="after")
    def require_unique_constraints(self) -> HardConstraintDeclarationArtifact:
        keys = tuple(item.constraint_key for item in self.constraints)
        if len(keys) != len(set(keys)):
            raise ValueError("declared hard constraint keys must be unique")
        return self


def serialize_hard_constraint_declaration(
    artifact: HardConstraintDeclarationArtifact,
) -> bytes:
    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _constraint_key(item: object) -> str:
    value = item.get("constraint_key") if isinstance(item, dict) else getattr(item, "constraint_key", "")
    return value if isinstance(value, str) else ""

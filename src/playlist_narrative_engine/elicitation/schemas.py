from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ARTIST_QUESTIONNAIRE_SCHEMA_VERSION = "1.0"


class FrozenElicitationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class InclusionBasis(StrEnum):
    EXPLICIT_SEED_EVIDENCE = "explicit_seed_evidence"


class ArtistQuestionnaireObjective(FrozenElicitationModel):
    objective_id: str = Field(min_length=1, max_length=100)
    statement: str = Field(min_length=1, max_length=500)

    @field_validator("objective_id", "statement")
    @classmethod
    def reject_surrounding_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text fields cannot contain surrounding whitespace")
        return value


class ArtistSeedEvidence(FrozenElicitationModel):
    evidence_id: str = Field(min_length=1, max_length=100)
    artist_name: str = Field(min_length=1, max_length=200)
    source: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("evidence_id", "artist_name", "source", "rationale")
    @classmethod
    def reject_surrounding_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text fields cannot contain surrounding whitespace")
        return value


class ArtistQuestionnaireRequest(FrozenElicitationModel):
    schema_version: Literal["1.0"] = ARTIST_QUESTIONNAIRE_SCHEMA_VERSION
    objective: ArtistQuestionnaireObjective
    seed_evidence: tuple[ArtistSeedEvidence, ...]
    approved_local_rules: tuple[str, ...] = ()

    @model_validator(mode="after")
    def enforce_closed_world_inputs(self) -> ArtistQuestionnaireRequest:
        evidence_ids = tuple(item.evidence_id for item in self.seed_evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("seed evidence IDs must be unique")
        if self.approved_local_rules:
            raise ValueError(
                "schema 1.0 approves no local derivation rules; "
                "approved_local_rules must be empty"
            )
        return self


class ArtistQuestionnaireEntry(FrozenElicitationModel):
    ordinal: int = Field(gt=0)
    artist_name: str
    inclusion_basis: InclusionBasis
    source_evidence: tuple[ArtistSeedEvidence, ...]
    inclusion_explanation: str
    rating: None = None

    @model_validator(mode="after")
    def provenance_reproduces_artist_identity(self) -> ArtistQuestionnaireEntry:
        if not self.source_evidence:
            raise ValueError("questionnaire entries require source evidence")
        if any(
            evidence.artist_name != self.artist_name
            for evidence in self.source_evidence
        ):
            raise ValueError(
                "every source evidence artist name must exactly match the entry"
            )
        evidence_ids = tuple(item.evidence_id for item in self.source_evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("entry source evidence IDs must be unique")
        stable_evidence_ids = tuple(
            sorted(evidence_ids, key=lambda item: item.encode("utf-8"))
        )
        if evidence_ids != stable_evidence_ids:
            raise ValueError("entry source evidence must use stable evidence-ID order")
        return self


class ArtistQuestionnaireSeed(FrozenElicitationModel):
    schema_version: Literal["1.0"] = ARTIST_QUESTIONNAIRE_SCHEMA_VERSION
    artifact_kind: Literal["artist_questionnaire_seed"] = "artist_questionnaire_seed"
    artifact_purpose: Literal["elicitation_test_artifact"] = (
        "elicitation_test_artifact"
    )
    objective: ArtistQuestionnaireObjective
    approved_local_rules: tuple[str, ...]
    ordering_rule: Literal["artist_name_utf8_bytes"] = "artist_name_utf8_bytes"
    entries: tuple[ArtistQuestionnaireEntry, ...]
    recommendation_claims: Literal[False] = False

    @model_validator(mode="after")
    def enforce_closed_world_artifact(self) -> ArtistQuestionnaireSeed:
        if self.approved_local_rules:
            raise ValueError(
                "schema 1.0 artifacts cannot contain local derivation rules"
            )
        expected_ordinals = tuple(range(1, len(self.entries) + 1))
        if tuple(entry.ordinal for entry in self.entries) != expected_ordinals:
            raise ValueError("entry ordinals must be contiguous and one-based")
        artist_names = tuple(entry.artist_name for entry in self.entries)
        if len(artist_names) != len(set(artist_names)):
            raise ValueError("questionnaire artist names must be unique")
        if artist_names != tuple(
            sorted(artist_names, key=lambda item: item.encode("utf-8"))
        ):
            raise ValueError("entries must use stable artist-name order")
        return self

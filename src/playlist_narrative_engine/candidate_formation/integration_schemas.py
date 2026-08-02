from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CANDIDATE_FORMATION_SCHEMA_VERSION,
    FormedCandidateEntry,
)
from playlist_narrative_engine.sequencing.schemas import TrackCandidate


FORMED_CANDIDATE_POOL_SCHEMA_VERSION = "1.0"
_POOL_DERIVATION_TOKEN = object()


class FrozenIntegrationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CandidateFormationTrace(FrozenIntegrationModel):
    parent_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parent_schema_version: Literal["1.0"] = CANDIDATE_FORMATION_SCHEMA_VERSION
    parent_request_id: str
    accepted_objective_artifact_id: str
    objective_id: str
    objective_statement: str
    journey_id: str
    policy_id: str
    policy_version: str
    preference_rule_name: str
    preference_rule_version: str

    @field_validator(
        "parent_request_id",
        "accepted_objective_artifact_id",
        "objective_id",
        "objective_statement",
        "journey_id",
        "policy_id",
        "policy_version",
        "preference_rule_name",
        "preference_rule_version",
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("formation trace identities must be nonblank and exact")
        return value


class FormedCandidatePoolView(FrozenIntegrationModel):
    schema_version: Literal["1.0"] = FORMED_CANDIDATE_POOL_SCHEMA_VERSION
    artifact_kind: Literal["formed_candidate_pool_view"] = (
        "formed_candidate_pool_view"
    )
    derivation_rule: Literal["cf3_formed_entries_projection_v1"] = (
        "cf3_formed_entries_projection_v1"
    )
    trace: CandidateFormationTrace
    formed_entries: tuple[FormedCandidateEntry, ...]

    def __init__(
        self,
        *,
        _derivation_token: object | None = None,
        **data: object,
    ) -> None:
        if _derivation_token is not _POOL_DERIVATION_TOKEN:
            raise TypeError(
                "FormedCandidatePoolView must be derived from a validated "
                "CandidateFormationArtifact"
            )
        super().__init__(**data)

    def model_copy(
        self,
        *,
        update: dict[str, object] | None = None,
        deep: bool = False,
    ) -> FormedCandidatePoolView:
        if update:
            raise TypeError("formed candidate pool views cannot be rewritten")
        return super().model_copy(deep=deep)

    @model_validator(mode="after")
    def require_canonical_entries(self) -> FormedCandidatePoolView:
        ordinals = tuple(entry.ordinal for entry in self.formed_entries)
        if ordinals != tuple(range(1, len(self.formed_entries) + 1)):
            raise ValueError("formed-pool ordinals must be contiguous and one-based")
        track_ids = tuple(entry.candidate.track_id for entry in self.formed_entries)
        if len(track_ids) != len(set(track_ids)):
            raise ValueError("formed-pool track identities must be unique")
        if track_ids != tuple(
            sorted(track_ids, key=lambda value: value.encode("utf-8"))
        ):
            raise ValueError("formed-pool entries must preserve canonical CF-2 order")
        return self

    @property
    def candidates(self) -> tuple[TrackCandidate, ...]:
        return tuple(entry.candidate for entry in self.formed_entries)

    def resolve_remaining(
        self,
        remaining_track_ids: tuple[str, ...],
    ) -> tuple[FormedCandidateEntry, ...]:
        if len(remaining_track_ids) != len(set(remaining_track_ids)):
            raise ValueError("remaining track IDs must be unique")
        available = {entry.candidate.track_id for entry in self.formed_entries}
        requested = set(remaining_track_ids)
        if not requested.issubset(available):
            raise ValueError("remaining track IDs must exactly exist in formed pool")
        return tuple(
            entry
            for entry in self.formed_entries
            if entry.candidate.track_id in requested
        )


def _new_formed_candidate_pool_view(
    *,
    trace: CandidateFormationTrace,
    formed_entries: tuple[FormedCandidateEntry, ...],
) -> FormedCandidatePoolView:
    return FormedCandidatePoolView(
        _derivation_token=_POOL_DERIVATION_TOKEN,
        trace=trace,
        formed_entries=formed_entries,
    )

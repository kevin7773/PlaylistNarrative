from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProvenanceType(StrEnum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    HUMAN_ASSESSMENT = "HUMAN_ASSESSMENT"
    DERIVED_QUERY_RESULT = "DERIVED_QUERY_RESULT"


class ConstraintStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class TrackInput(StrictModel):
    position: int = Field(gt=0)
    title: str
    artist: str
    canonical_title: str | None = None
    canonical_artist: str | None = None
    normalized_title: str | None = None
    normalized_artist: str | None = None
    explicit_flag: bool | None = None
    version_or_remaster_text: str | None = None
    notes: str | None = None


class ConstraintResultInput(StrictModel):
    status: ConstraintStatus
    evidence: str | None = None
    provenance_type: ProvenanceType = ProvenanceType.HUMAN_ASSESSMENT
    recorded_by: str | None = None
    provenance_notes: str | None = None


class ConstraintInput(StrictModel):
    constraint_type: str
    constraint_text: str
    is_hard_constraint: bool = True
    result: ConstraintResultInput | None = None


class ObservationInput(StrictModel):
    observation_type: str
    observation_text: str
    severity: str | None = None
    track_position: int | None = Field(default=None, gt=0)
    provenance_type: ProvenanceType = ProvenanceType.DIRECT_OBSERVATION
    recorded_by: str | None = None
    provenance_notes: str | None = None


class ExperimentInput(StrictModel):
    created_at: datetime | None = None
    prompt: str
    prompt_title: str | None = None
    source_system: str = "Maestro Beta"
    generated_title: str
    generated_description: str
    requested_track_count: int | None = Field(default=None, ge=0)
    saved: bool
    assessment: str | None = None
    notes: str | None = None
    tracks: list[TrackInput]
    constraints: list[ConstraintInput] = Field(default_factory=list)
    observations: list[ObservationInput] = Field(default_factory=list)
    prompt_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_observation_positions(self) -> ExperimentInput:
        positions = {track.position for track in self.tracks}
        for observation in self.observations:
            if observation.track_position is not None and observation.track_position not in positions:
                raise ValueError("observation track_position must identify an ingested track")
        return self


class GenerationFailureInput(StrictModel):
    created_at: datetime | None = None
    prompt: str
    source_system: str = "Maestro Beta"
    failure_type: str
    displayed_message: str
    notes: str | None = None

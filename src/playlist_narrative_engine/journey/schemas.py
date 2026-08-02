from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.objective_assessment import Objective


JOURNEY_PLAN_SCHEMA_VERSION = "1.0"


class FrozenJourneyModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class JourneyContext(StrEnum):
    ACTIVE_FOCUS = "Active Focus"


class EnergyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FamiliarityAllocation(FrozenJourneyModel):
    familiar_percent: int = Field(ge=0, le=100)
    discovery_percent: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def percentages_total_one_hundred(self) -> FamiliarityAllocation:
        if self.familiar_percent + self.discovery_percent != 100:
            raise ValueError("familiar and discovery percentages must total 100")
        return self


class ActiveFocusRequest(FrozenJourneyModel):
    duration_minutes: int = Field(default=90, ge=30, le=240)
    discovery_percent: int = Field(default=20, ge=0, le=50)
    starting_energy: EnergyLevel = EnergyLevel.MEDIUM
    ending_energy: EnergyLevel = EnergyLevel.MEDIUM


class JourneyPhase(FrozenJourneyModel):
    name: str
    purpose: str
    duration_minutes: int = Field(gt=0)
    start_energy: EnergyLevel
    end_energy: EnergyLevel
    familiarity: FamiliarityAllocation


class JourneyPlan(FrozenJourneyModel):
    context: JourneyContext
    duration_minutes: int
    discovery_percent: int
    phases: tuple[JourneyPhase, ...]

    @model_validator(mode="after")
    def allocations_match_plan(self) -> JourneyPlan:
        if sum(phase.duration_minutes for phase in self.phases) != self.duration_minutes:
            raise ValueError("phase durations must equal the journey duration")
        return self


class JourneyPlanArtifact(FrozenJourneyModel):
    schema_version: Literal["1.0"] = JOURNEY_PLAN_SCHEMA_VERSION
    artifact_kind: Literal["journey_plan"] = "journey_plan"
    journey_id: str = Field(min_length=1, max_length=200)
    objective: Objective
    objective_safety_artifact_id: str = Field(min_length=1, max_length=200)
    plan: JourneyPlan
    candidate_formation_performed: Literal[False] = False

    @field_validator("journey_id", "objective_safety_artifact_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("journey artifact identities must be exact")
        return value

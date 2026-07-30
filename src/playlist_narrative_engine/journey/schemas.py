from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class JourneyContext(StrEnum):
    ACTIVE_FOCUS = "Active Focus"


class EnergyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FamiliarityAllocation(BaseModel):
    familiar_percent: int = Field(ge=0, le=100)
    discovery_percent: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def percentages_total_one_hundred(self) -> FamiliarityAllocation:
        if self.familiar_percent + self.discovery_percent != 100:
            raise ValueError("familiar and discovery percentages must total 100")
        return self


class ActiveFocusRequest(BaseModel):
    duration_minutes: int = Field(default=90, ge=30, le=240)
    discovery_percent: int = Field(default=20, ge=0, le=50)
    starting_energy: EnergyLevel = EnergyLevel.MEDIUM
    ending_energy: EnergyLevel = EnergyLevel.MEDIUM


class JourneyPhase(BaseModel):
    name: str
    purpose: str
    duration_minutes: int = Field(gt=0)
    start_energy: EnergyLevel
    end_energy: EnergyLevel
    familiarity: FamiliarityAllocation


class JourneyPlan(BaseModel):
    context: JourneyContext
    duration_minutes: int
    discovery_percent: int
    phases: tuple[JourneyPhase, ...]

    @model_validator(mode="after")
    def allocations_match_plan(self) -> JourneyPlan:
        if sum(phase.duration_minutes for phase in self.phases) != self.duration_minutes:
            raise ValueError("phase durations must equal the journey duration")
        return self

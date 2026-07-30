from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


UnitFloat = Field(ge=0.0, le=1.0)


class TrackCandidate(BaseModel):
    """Local scoring inputs; values are not external metadata claims."""

    model_config = ConfigDict(frozen=True)

    track_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    artist_name: str = Field(min_length=1)
    duration_seconds: int = Field(gt=0)
    energy: float = UnitFloat
    familiarity: float = UnitFloat
    preference: float = UnitFloat
    context_fit: float = UnitFloat
    instrumentalness: float = UnitFloat
    lyrical_distraction: float = UnitFloat
    groove: float = UnitFloat


class TrackRole(StrEnum):
    OPENING_ANCHOR = "opening_anchor"
    JOURNEY = "journey"
    DISCOVERY_SPOTLIGHT = "discovery_spotlight"
    ENERGY_RESET = "energy_reset"
    PHASE_TRANSITION = "phase_transition"
    EPIC_EVENT = "epic_event"
    CLOSING_TRACK = "closing_track"


class TransitionProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    energy_continuity: float = UnitFloat
    groove_continuity: float = UnitFloat
    emotional_continuity: float = UnitFloat
    narrative_continuity: float = UnitFloat
    intentional_contrast: float = UnitFloat


class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    preference_score: float = Field(ge=0.0)
    context_score: float = Field(ge=0.0)
    phase_score: float = Field(ge=0.0)
    transition_score: float = Field(ge=0.0)
    discovery_score: float = Field(ge=0.0)
    constraint_penalty: float = Field(ge=0.0)
    narrative_drift_penalty: float = Field(ge=0.0)
    total_score: float
    role: TrackRole
    reasons: tuple[str, ...]

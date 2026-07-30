from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from playlist_narrative_engine.taste.ratings import Rating


class ArtistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    calibration_group: str | None = Field(default=None, max_length=100)
    rating: Rating = Rating.UNKNOWN
    notes: str | None = None


class ArtistRead(ArtistCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ArtistRatingUpdate(BaseModel):
    rating: Rating
    notes: str | None = None


class FeedbackScope(StrEnum):
    ARTIST = "artist"
    TRACK = "track"
    CONTEXT = "context"


class ContextFeedbackKind(StrEnum):
    DID_NOT_BELONG = "Did not belong in this context"
    GOOD_DISCOVERY = "Good discovery"
    BAD_TRANSITION = "Bad transition"
    TOO_REPETITIVE = "Too repetitive"
    ENERGY_TOO_LOW = "Energy too low"
    ENERGY_TOO_HIGH = "Energy too high"


class FeedbackDraft(BaseModel):
    """Future-ready boundary model; persistence arrives with track feedback."""

    scope: FeedbackScope
    rating: Rating | None = None
    context_key: str | None = None
    context_feedback: ContextFeedbackKind | None = None
    notes: str | None = None


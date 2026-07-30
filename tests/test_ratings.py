from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from playlist_narrative_engine.db import make_session_factory
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.taste.schemas import ArtistCreate, ArtistRatingUpdate


def test_all_seven_rating_values_are_valid() -> None:
    assert {rating.value for rating in Rating} == {
        "Love", "Like", "Meh", "No Thanks", "Pencil", "Forbidden", "Unknown"
    }
    for rating in Rating:
        assert ArtistRatingUpdate(rating=rating).rating is rating


def test_invalid_rating_is_rejected() -> None:
    with pytest.raises(ValidationError):
        ArtistRatingUpdate(rating="Maybe")  # type: ignore[arg-type]


def test_rating_creation_update_and_persistence(session: Session, engine) -> None:
    repository = ArtistRepository(session)
    repository.add(ArtistCreate(name="Rush", rating=Rating.LIKE))
    updated = repository.set_rating("Rush", Rating.LOVE, "Core work artist")
    assert updated.rating == Rating.LOVE.value

    with make_session_factory(engine)() as reopened:
        saved = ArtistRepository(reopened).get_by_name("Rush")
        assert saved is not None
        assert saved.rating == Rating.LOVE.value
        assert saved.notes == "Core work artist"


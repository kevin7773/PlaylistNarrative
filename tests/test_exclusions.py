from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from playlist_narrative_engine.seed import seed_calibration_artists
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.taste.schemas import ArtistCreate
from playlist_narrative_engine.taste.service import (
    ForbiddenArtistError,
    TasteService,
)


@pytest.mark.parametrize("rating", [Rating.NO_THANKS, Rating.PENCIL, Rating.FORBIDDEN])
def test_default_excluded_ratings_are_not_eligible(
    session: Session, rating: Rating
) -> None:
    repository = ArtistRepository(session)
    repository.add(ArtistCreate(name=f"Artist {rating.value}", rating=rating))
    assert not TasteService(repository).artist_is_normally_eligible(
        f"Artist {rating.value}"
    )


def test_unknown_artist_is_eligible_as_controlled_discovery(session: Session) -> None:
    repository = ArtistRepository(session)
    repository.add(ArtistCreate(name="New Artist", rating=Rating.UNKNOWN))
    assert TasteService(repository).artist_is_normally_eligible("New Artist")


def test_radiohead_cannot_appear_while_marked_forbidden(session: Session) -> None:
    seed_calibration_artists(session)
    repository = ArtistRepository(session)
    radiohead = repository.get_by_name("Radiohead")
    assert radiohead is not None
    assert radiohead.rating == Rating.FORBIDDEN.value
    service = TasteService(repository)
    assert not service.artist_is_normally_eligible("Radiohead")
    with pytest.raises(ForbiddenArtistError):
        service.assert_not_forbidden("Radiohead")


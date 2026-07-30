from __future__ import annotations

from playlist_narrative_engine.taste.models import Artist
from playlist_narrative_engine.taste.ratings import Rating, is_normally_eligible
from playlist_narrative_engine.taste.repository import ArtistRepository


class TasteService:
    def __init__(self, artists: ArtistRepository) -> None:
        self.artists = artists

    def rate_artist(
        self, name: str, rating: Rating, notes: str | None = None
    ) -> Artist:
        return self.artists.set_rating(name, rating, notes)

    def artist_is_normally_eligible(self, name: str) -> bool:
        artist = self.artists.get_by_name(name)
        if artist is None:
            return True  # Unrated artists are controlled discovery candidates.
        return is_normally_eligible(Rating(artist.rating))

    def assert_not_forbidden(self, name: str) -> None:
        artist = self.artists.get_by_name(name)
        if artist is not None and Rating(artist.rating) is Rating.FORBIDDEN:
            raise ForbiddenArtistError(f"{name} is Forbidden and cannot be selected")


class ForbiddenArtistError(ValueError):
    pass


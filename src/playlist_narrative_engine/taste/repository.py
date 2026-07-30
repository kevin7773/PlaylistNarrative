from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from playlist_narrative_engine.taste.models import Artist
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.schemas import ArtistCreate


class ArtistRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, draft: ArtistCreate) -> Artist:
        artist = Artist(
            name=draft.name.strip(),
            calibration_group=draft.calibration_group,
            rating=draft.rating.value,
            notes=draft.notes,
        )
        self.session.add(artist)
        self.session.commit()
        return artist

    def get_by_name(self, name: str) -> Artist | None:
        statement = select(Artist).where(Artist.name == name.strip())
        return self.session.scalar(statement)

    def list(self, rating: Rating | None = None) -> list[Artist]:
        statement = select(Artist).order_by(Artist.name)
        if rating is not None:
            statement = statement.where(Artist.rating == rating.value)
        return list(self.session.scalars(statement))

    def set_rating(
        self, name: str, rating: Rating, notes: str | None = None
    ) -> Artist:
        artist = self.get_by_name(name)
        if artist is None:
            artist = Artist(name=name.strip(), rating=rating.value, notes=notes)
            self.session.add(artist)
        else:
            artist.rating = rating.value
            if notes is not None:
                artist.notes = notes
        self.session.commit()
        return artist


from __future__ import annotations

from sqlalchemy.orm import Session

from playlist_narrative_engine.db import initialize_database, make_engine
from playlist_narrative_engine.seed import CALIBRATION_ARTISTS, seed_calibration_artists
from playlist_narrative_engine.taste.repository import ArtistRepository


def test_seed_contains_approximately_one_hundred_unique_artists() -> None:
    names = [name for name, _ in CALIBRATION_ARTISTS]
    assert 95 <= len(names) <= 110
    assert len(names) == len(set(names))


def test_seed_is_idempotent(session: Session) -> None:
    first = seed_calibration_artists(session)
    second = seed_calibration_artists(session)
    assert first == len(CALIBRATION_ARTISTS)
    assert second == 0
    assert len(ArtistRepository(session).list()) == len(CALIBRATION_ARTISTS)


def test_sqlite_database_parent_is_created(tmp_path) -> None:
    database = tmp_path / "nested" / "catalog.db"
    engine = make_engine(f"sqlite:///{database.as_posix()}")
    initialize_database(engine)
    assert database.exists()

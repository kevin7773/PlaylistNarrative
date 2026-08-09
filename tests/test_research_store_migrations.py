from __future__ import annotations

from sqlalchemy import text

from playlist_narrative_engine.research_store.database import make_research_engine
from playlist_narrative_engine.research_store.migrations import (
    CURRENT_SCHEMA_VERSION, get_schema_version, migrate_research_database,
)


def test_initial_migration_is_idempotent_and_enables_sqlite_guards(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'research.db').as_posix()}")
    assert migrate_research_database(engine) == CURRENT_SCHEMA_VERSION == 3
    assert migrate_research_database(engine) == 3
    assert get_schema_version(engine) == 3
    with engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        assert connection.scalar(text("PRAGMA journal_mode")) == "wal"
        tables = set(connection.scalars(text("SELECT name FROM sqlite_master WHERE type='table'")))
    assert {"experiments", "tracks", "generation_failures", "schema_version"} <= tables


def test_newer_schema_version_is_rejected(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'future.db').as_posix()}")
    migrate_research_database(engine)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO schema_version(version, applied_at) VALUES (99, CURRENT_TIMESTAMP)"))
    try:
        migrate_research_database(engine)
    except RuntimeError as error:
        assert "newer than supported" in str(error)
    else:
        raise AssertionError("future schema was accepted")

from __future__ import annotations

from sqlalchemy import text

from playlist_narrative_engine.research_store.database import make_research_engine
from playlist_narrative_engine.research_store.migrations import (
    CURRENT_SCHEMA_VERSION, get_schema_version, migrate_research_database,
)


def test_initial_migration_is_idempotent_and_enables_sqlite_guards(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'research.db').as_posix()}")
    assert migrate_research_database(engine) == CURRENT_SCHEMA_VERSION == 8
    assert migrate_research_database(engine) == 8
    assert get_schema_version(engine) == 8
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


def test_v3_to_v4_preserves_legacy_assessment_and_defaults_outcome(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'v3.db').as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at DATETIME NOT NULL)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE experiments (id INTEGER PRIMARY KEY, overall_assessment TEXT)"
        )
        connection.execute(text(
            "INSERT INTO schema_version(version, applied_at) VALUES (3, CURRENT_TIMESTAMP)"
        ))
        connection.execute(text(
            "INSERT INTO experiments(id, overall_assessment) VALUES (1, 'legacy prose exactly')"
        ))
    assert migrate_research_database(engine) == 8
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT overall_assessment, assessment_outcome FROM experiments WHERE id=1"
        )).one()
    assert row == ("legacy prose exactly", "INDETERMINATE")

from __future__ import annotations

from sqlalchemy import text

from playlist_narrative_engine.research_store.database import make_research_engine
from playlist_narrative_engine.research_store.migrations import (
    CURRENT_SCHEMA_VERSION, get_schema_version, migrate_research_database,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from sqlalchemy.orm import Session


def test_initial_migration_is_idempotent_and_enables_sqlite_guards(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'research.db').as_posix()}")
    assert migrate_research_database(engine) == CURRENT_SCHEMA_VERSION == 9
    assert migrate_research_database(engine) == 9
    assert get_schema_version(engine) == 9
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
    assert migrate_research_database(engine) == 9
    with engine.connect() as connection:
        row = connection.execute(text(
            "SELECT overall_assessment, assessment_outcome FROM experiments WHERE id=1"
        )).one()
    assert row == ("legacy prose exactly", "INDETERMINATE")


def test_populated_v8_to_v9_changes_only_trigger_contract_and_schema_marker(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'v8.db').as_posix()}")
    migrate_research_database(engine)
    with Session(engine) as session:
        record_id = ResearchStoreService(ResearchRepository(session)).ingest_experiment(
            ExperimentInput.model_validate({
                "source_system": "Maestro Beta",
                "tracks": [{"position": 1, "title": "Preserved", "artist": "Artist"}],
            })
        ).record_id
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM schema_version WHERE version=9"))
        connection.execute(text(
            "INSERT INTO schema_version(version, applied_at) VALUES (8, CURRENT_TIMESTAMP)"
        ))
        before = connection.execute(text(
            "SELECT id, source_system, generated_playlist_title FROM experiments ORDER BY id"
        )).all()
        track_before = connection.execute(text(
            "SELECT experiment_id, observed_ordinal, display_title, display_artist "
            "FROM experiment_tracks ORDER BY id"
        )).all()
    assert get_schema_version(engine) == 8
    assert migrate_research_database(engine) == 9
    with engine.connect() as connection:
        after = connection.execute(text(
            "SELECT id, source_system, generated_playlist_title FROM experiments ORDER BY id"
        )).all()
        track_after = connection.execute(text(
            "SELECT experiment_id, observed_ordinal, display_title, display_artist "
            "FROM experiment_tracks ORDER BY id"
        )).all()
        trigger_count = connection.scalar(text(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='trigger' "
            "AND name='constraint_evaluation_evidence_validate_insert'"
        ))
    assert record_id == 1
    assert after == before
    assert track_after == track_before
    assert trigger_count == 1

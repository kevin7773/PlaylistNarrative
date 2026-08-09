from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text

from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
from playlist_narrative_engine.research_store.migrations import get_schema_version, migrate_research_database
from playlist_narrative_engine.research_store.models import EvidenceLink, EvidenceSource, Experiment, ExperimentTrack, Track
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput, GenerationFailureInput


def _partial_document(**overrides):
    document = {
        "generated_at": None,
        "prompt": None,
        "source_system": None,
        "generated_title": None,
        "generated_description": None,
        "saved": None,
        "tracklist_completeness": "PARTIAL",
        "segments": [
            {"segment_ordinal": 1, "relationship_to_previous": "FIRST", "captures_playlist_start": "YES", "captures_playlist_end": "NO"},
            {"segment_ordinal": 2, "relationship_to_previous": "GAP_UNKNOWN_SIZE", "captures_playlist_start": "NO", "captures_playlist_end": "UNKNOWN"},
        ],
        "tracks": [
            {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1,
             "absolute_position": 1, "title": "Known", "artist": "Artist"},
            {"observed_ordinal": 2, "evidence_segment": 2, "segment_ordinal": 1,
             "absolute_position": None, "title": "Partial title", "artist": None,
             "canonical_identity_established": False},
        ],
    }
    document.update(overrides)
    return document


def test_partial_segments_unknown_positions_and_nullable_identity(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate(_partial_document()))
    result = repository.get_experiment(experiment_id)
    assert result["generated_at"] is None
    assert result["prompt"] is None and result["source_system"] is None
    assert result["tracklist_completeness"] == "PARTIAL"
    assert result["segments"][1]["relationship_to_previous"] == "GAP_UNKNOWN_SIZE"
    assert result["segments"][1]["captures_playlist_end"] == "UNKNOWN"
    assert result["tracks"][1]["absolute_position"] is None
    assert result["tracks"][1]["track_id"] is None


def test_not_observed_and_failure_without_playlist(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": None, "source_system": None, "generated_title": None,
        "generated_description": None, "saved": None, "tracks": [],
        "tracklist_completeness": "NOT_OBSERVED",
    }))
    assert repository.get_experiment(experiment_id)["observed_track_count"] == 0
    research_session.rollback()
    failure_id = repository.record_generation_failure(GenerationFailureInput(
        prompt=None, source_system=None, failure_type="REFUSAL", displayed_message=None
    ))
    assert repository.list_generation_failures()[0]["id"] == failure_id
    assert repository.list_generation_failures()[0]["generated_at"] is None


def test_recovered_failure_preserves_field_level_evidence(research_session) -> None:
    repository = ResearchRepository(research_session)
    failure_id = repository.record_generation_failure(GenerationFailureInput.model_validate({
        "prompt": None,
        "source_system": "Maestro Beta",
        "failure_type": "REFUSAL",
        "displayed_message": "Unable to create playlist",
        "generated_at": None,
        "evidence_standard": "RECOVERED_HISTORICAL",
        "evidence_sources": [{
            "source_key": "capture", "source_type": "SCREENSHOT",
            "source_reference": "external:capture"
        }],
        "evidence": [
            {"source_key": "capture", "field_name": "source_system"},
            {"source_key": "capture", "field_name": "failure_type"},
            {"source_key": "capture", "field_name": "displayed_message"},
        ],
    }))
    result = repository.list_generation_failures()[0]
    assert result["id"] == failure_id
    assert result["prompt"] is None
    assert {item["field_name"] for item in result["evidence"]} == {
        "source_system", "failure_type", "displayed_message"
    }


@pytest.mark.parametrize("change", [
    {"generated_track_count": None},
    {"generated_track_count": 2, "segments": [{"segment_ordinal": 1, "relationship_to_previous": "FIRST", "captures_playlist_start": "UNKNOWN", "captures_playlist_end": "YES"}]},
    {"generated_track_count": 2, "segments": [{"segment_ordinal": 1, "relationship_to_previous": "FIRST", "captures_playlist_start": "YES", "captures_playlist_end": "NO"}]},
])
def test_complete_invariants_reject_unsupported_completeness(change) -> None:
    document = {
        "prompt": "Complete", "generated_title": "Title", "generated_description": "Desc", "saved": False,
        "tracklist_completeness": "COMPLETE", "generated_track_count": 2,
        "segments": [{"segment_ordinal": 1, "relationship_to_previous": "FIRST", "captures_playlist_start": "YES", "captures_playlist_end": "YES"}],
        "tracks": [
            {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1, "absolute_position": 1, "title": "A", "artist": "X"},
            {"observed_ordinal": 2, "evidence_segment": 1, "segment_ordinal": 2, "absolute_position": 2, "title": "B", "artist": "Y"},
        ],
    }
    document.update(change)
    with pytest.raises(ValidationError):
        ExperimentInput.model_validate(document)


def test_local_evidence_requires_and_verifies_checksum(research_session, tmp_path) -> None:
    evidence = tmp_path / "capture.bin"
    evidence.write_bytes(b"primary evidence")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    with pytest.raises(ValidationError, match="require sha256"):
        ExperimentInput.model_validate(_partial_document(
            evidence_sources=[{"source_key": "capture", "source_type": "SCREENSHOT",
                               "source_reference": "external:1", "local_path": str(evidence)}]
        ))
    document = _partial_document(
        evidence_standard="RECOVERED_HISTORICAL",
        prompt="Exact", source_system="Maestro Beta", generated_title="Title",
        generated_description=None, saved=False,
        evidence_sources=[{"source_key": "capture", "source_type": "SCREENSHOT",
                           "source_reference": "external:1", "local_path": str(evidence), "sha256": digest}],
        evidence=[
            {"source_key": "capture", "field_name": name}
            for name in ("prompt", "source_system", "generated_title", "saved", "tracklist_completeness")
        ],
    )
    for track in document["tracks"]:
        track["evidence"] = [
            {"source_key": "capture", "field_name": field}
            for field in ("title", "artist", "absolute_position") if track.get(field) is not None
        ]
    experiment_id = ResearchRepository(research_session).insert_experiment(ExperimentInput.model_validate(document))
    source = research_session.scalar(select(EvidenceSource).where(EvidenceSource.experiment_id == experiment_id))
    assert source.sha256 == digest
    research_session.rollback()
    document["evidence_sources"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum mismatch"):
        ResearchRepository(research_session).insert_experiment(ExperimentInput.model_validate(document))


def test_recovered_historical_assertions_require_field_evidence() -> None:
    with pytest.raises(ValidationError, match="lack evidence"):
        ExperimentInput.model_validate(_partial_document(
            evidence_standard="RECOVERED_HISTORICAL", prompt="Exact"
        ))


def test_deterministic_populated_v1_to_v3_migration(tmp_path) -> None:
    path = tmp_path / "v1.db"
    engine = make_research_engine(f"sqlite:///{path.as_posix()}")
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at DATETIME NOT NULL)")
        connection.exec_driver_sql("CREATE TABLE experiments (id INTEGER PRIMARY KEY, created_at DATETIME NOT NULL, prompt_text TEXT NOT NULL, prompt_title TEXT, source_system TEXT NOT NULL, generated_playlist_title TEXT NOT NULL, generated_playlist_description TEXT NOT NULL, requested_track_count INTEGER, observed_track_count INTEGER NOT NULL, saved_by_user BOOLEAN NOT NULL, overall_assessment TEXT, notes TEXT)")
        connection.exec_driver_sql("CREATE TABLE tracks (id INTEGER PRIMARY KEY, canonical_title TEXT NOT NULL, canonical_artist TEXT NOT NULL, normalized_title TEXT, normalized_artist TEXT)")
        connection.exec_driver_sql("CREATE TABLE experiment_tracks (experiment_id INTEGER NOT NULL, track_id INTEGER NOT NULL, position INTEGER NOT NULL, display_title TEXT NOT NULL, display_artist TEXT NOT NULL, explicit_flag BOOLEAN, version_or_remaster_text TEXT, notes TEXT, PRIMARY KEY (experiment_id, position))")
        connection.exec_driver_sql("CREATE TABLE constraints (id INTEGER PRIMARY KEY, experiment_id INTEGER NOT NULL, constraint_type TEXT NOT NULL, constraint_text TEXT NOT NULL, is_hard_constraint BOOLEAN NOT NULL)")
        connection.exec_driver_sql("CREATE TABLE constraint_results (experiment_id INTEGER NOT NULL, constraint_id INTEGER NOT NULL, status VARCHAR(20) NOT NULL, evidence TEXT, provenance_type VARCHAR(30) NOT NULL, recorded_by TEXT, provenance_notes TEXT, PRIMARY KEY (experiment_id, constraint_id))")
        connection.exec_driver_sql("CREATE TABLE observations (id INTEGER PRIMARY KEY, experiment_id INTEGER NOT NULL, observation_type TEXT NOT NULL, observation_text TEXT NOT NULL, severity TEXT, track_position INTEGER, provenance_type VARCHAR(30) NOT NULL, recorded_by TEXT, provenance_notes TEXT)")
        connection.exec_driver_sql("CREATE TABLE experiment_prompt_labels (experiment_id INTEGER NOT NULL, label TEXT NOT NULL, PRIMARY KEY (experiment_id, label))")
        connection.exec_driver_sql("CREATE TABLE generation_failures (id INTEGER PRIMARY KEY, created_at DATETIME NOT NULL, prompt_text TEXT NOT NULL, source_system TEXT NOT NULL, failure_type TEXT NOT NULL, displayed_message TEXT NOT NULL, notes TEXT)")
        connection.execute(text("INSERT INTO schema_version VALUES (1, '2026-01-01')"))
        connection.execute(text("INSERT INTO experiments VALUES (7, '2026-01-02', 'Prompt', NULL, 'Maestro Beta', 'Title', 'Desc', NULL, 1, 0, NULL, NULL)"))
        connection.execute(text("INSERT INTO tracks VALUES (9, 'Raw', 'Artist', NULL, NULL)"))
        connection.execute(text("INSERT INTO experiment_tracks VALUES (7, 9, 1, 'Raw', 'Artist', NULL, NULL, NULL)"))
    assert migrate_research_database(engine) == 3
    assert migrate_research_database(engine) == 3
    assert get_schema_version(engine) == 3
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        result = ResearchRepository(session).get_experiment(7)
        assert result["recorded_at"].startswith("2026-01-02")
        assert result["generated_at"] is None
        assert result["tracklist_completeness"] == "COMPLETE"
        assert result["tracks"][0]["absolute_position"] == 1
        assert result["evidence_standard"] == "LEGACY_V1"
        assert session.scalar(select(EvidenceLink.provenance_type)) == "MIGRATION_DERIVATION"

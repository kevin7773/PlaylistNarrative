from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text

from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
from playlist_narrative_engine.research_store.exporter import export_csv_bundle, export_json
from playlist_narrative_engine.research_store.importer import import_research_export
from playlist_narrative_engine.research_store.migrations import get_schema_version, migrate_research_database
from playlist_narrative_engine.research_store.models import (
    EvidenceLink, EvidenceSource, Experiment, PersistedArtifactExperimentLink,
    PersistedArtifactTrack, PersistedPlaylistArtifact, Track,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput, FieldEvidenceInput, PersistedArtifactExperimentLinkInput,
    PersistedPlaylistArtifactInput,
)


def _artifact_document(completeness="COMPLETE", **changes):
    document = {
        "source_system": "Amazon Music",
        "display_title": "Current artifact",
        "display_description": None,
        "visibility_text": "Public",
        "persistence_state": "PRESENT",
        "displayed_track_count": 2,
        "displayed_duration_text": "7 min",
        "tracklist_completeness": completeness,
        "segments": [{
            "segment_ordinal": 1, "relationship_to_previous": "FIRST",
            "captures_playlist_start": "YES", "captures_playlist_end": "YES",
        }],
        "tracks": [
            {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1,
             "absolute_position": 1, "title": "Shared", "artist": "Artist"},
            {"observed_ordinal": 2, "evidence_segment": 1, "segment_ordinal": 2,
             "absolute_position": 2, "title": "Truncated...", "artist": "Other",
             "canonical_identity_established": False},
        ],
    }
    document.update(changes)
    return document


def test_fresh_database_is_current_schema(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'fresh.db').as_posix()}")
    assert migrate_research_database(engine) == 9
    assert migrate_research_database(engine) == 9
    assert get_schema_version(engine) == 9


def test_artifact_complete_partial_not_observed_and_tristate_boundaries() -> None:
    complete = PersistedPlaylistArtifactInput.model_validate(_artifact_document())
    assert complete.tracklist_completeness == "COMPLETE"
    partial = PersistedPlaylistArtifactInput.model_validate(_artifact_document(
        "PARTIAL", displayed_track_count=None,
        segments=[
            {"segment_ordinal": 1, "relationship_to_previous": "FIRST",
             "captures_playlist_start": "UNKNOWN", "captures_playlist_end": "NO"},
            {"segment_ordinal": 2, "relationship_to_previous": "GAP_UNKNOWN_SIZE",
             "captures_playlist_start": "NO", "captures_playlist_end": "UNKNOWN"},
        ],
        tracks=[
            {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1,
             "absolute_position": None, "title": "Only title", "artist": None,
             "canonical_identity_established": False},
            {"observed_ordinal": 2, "evidence_segment": 2, "segment_ordinal": 1,
             "absolute_position": None, "title": "Later", "artist": "Artist"},
        ],
    ))
    assert partial.segments[0].captures_playlist_start == "UNKNOWN"
    assert PersistedPlaylistArtifactInput.model_validate(_artifact_document(
        "NOT_OBSERVED", displayed_track_count=None, segments=[], tracks=[]
    )).tracks == []


@pytest.mark.parametrize("change", [
    {"displayed_track_count": 3},
    {"segments": [{"segment_ordinal": 1, "relationship_to_previous": "FIRST",
                   "captures_playlist_start": "NO", "captures_playlist_end": "YES"}]},
    {"segments": [{"segment_ordinal": 1, "relationship_to_previous": "FIRST",
                   "captures_playlist_start": "YES", "captures_playlist_end": "UNKNOWN"}]},
    {"segments": [
        {"segment_ordinal": 1, "relationship_to_previous": "FIRST",
         "captures_playlist_start": "YES", "captures_playlist_end": "NO"},
        {"segment_ordinal": 2, "relationship_to_previous": "GAP_UNKNOWN_SIZE",
         "captures_playlist_start": "NO", "captures_playlist_end": "YES"},
    ]},
])
def test_artifact_complete_invariants_reject_gaps_boundaries_and_count(change) -> None:
    document = _artifact_document()
    document.update(change)
    with pytest.raises(ValidationError):
        PersistedPlaylistArtifactInput.model_validate(document)


def test_artifact_nullable_canonical_identity_and_experiment_isolation(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": "Historical", "generated_title": "Generated", "generated_description": "Old",
        "saved": None, "tracks": [], "tracklist_completeness": "NOT_OBSERVED",
    }))
    before = repository.get_experiment(experiment_id)
    research_session.rollback()
    artifact_id = repository.insert_persisted_artifact(
        PersistedPlaylistArtifactInput.model_validate(_artifact_document())
    )
    artifact = repository.get_persisted_artifact(artifact_id)
    assert artifact["tracks"][1]["track_id"] is None
    assert artifact["tracks"][1]["title"] == "Truncated..."
    assert repository.get_experiment(experiment_id) == before


def test_correlation_evidence_is_owned_by_relationship_and_mutates_no_endpoint(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": None, "source_system": None, "generated_title": None,
        "generated_description": None, "saved": None, "tracks": [],
        "tracklist_completeness": "NOT_OBSERVED",
    }))
    artifact_id = repository.insert_persisted_artifact(
        PersistedPlaylistArtifactInput.model_validate(_artifact_document())
    )
    experiment_before = repository.get_experiment(experiment_id)
    artifact_before = repository.get_persisted_artifact(artifact_id)
    research_session.rollback()
    link_id = repository.insert_persisted_artifact_experiment_link(
        PersistedArtifactExperimentLinkInput.model_validate({
            "persisted_artifact_id": artifact_id, "experiment_id": experiment_id,
            "relationship_type": "USER_ATTESTED_CORRELATION",
            "unchanged_since_generation": "UNKNOWN",
            "evidence_sources": [{"source_key": "user", "source_type": "CONVERSATION_USER_STATEMENT",
                                  "source_reference": "conversation:item"}],
            "evidence": [{"source_key": "user", "field_name": "relationship_type"}],
        })
    )
    source = research_session.scalar(select(EvidenceSource).where(
        EvidenceSource.persisted_artifact_experiment_link_id == link_id
    ))
    evidence = research_session.scalar(select(EvidenceLink).where(
        EvidenceLink.persisted_artifact_experiment_link_id == link_id
    ))
    assert source.experiment_id is None and source.persisted_artifact_id is None
    assert evidence.experiment_id is None and evidence.persisted_artifact_id is None
    assert repository.get_experiment(experiment_id) == experiment_before
    assert repository.get_persisted_artifact(artifact_id) == artifact_before


def test_cross_domain_evidence_is_rejected_before_insert(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": None, "source_system": None, "generated_title": None,
        "generated_description": None, "saved": None, "tracks": [],
        "tracklist_completeness": "NOT_OBSERVED",
    }))
    artifact_id = repository.insert_persisted_artifact(
        PersistedPlaylistArtifactInput.model_validate(_artifact_document())
    )
    research_session.rollback()
    with pytest.raises(ValueError, match="ownership domain"):
        with research_session.begin():
            source = EvidenceSource(
                persisted_artifact_id=artifact_id, source_key="artifact", source_type="SCREENSHOT",
                source_reference="capture", experiment_id=None, generation_failure_id=None,
                persisted_artifact_experiment_link_id=None,
            )
            research_session.add(source)
            research_session.flush()
            repository._insert_links(
                {"artifact": source},
                [FieldEvidenceInput(source_key="artifact", field_name="prompt")],
                experiment_id=experiment_id,
            )
    assert research_session.scalar(select(func.count()).select_from(EvidenceLink).where(
        EvidenceLink.experiment_id == experiment_id
    )) == 0


def test_shared_canonical_track_does_not_share_placement_or_recurrence(research_session) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": "Historical", "generated_title": "Generated", "generated_description": "Description",
        "saved": False,
        "tracks": [{"position": 1, "title": "Shared", "artist": "Artist", "notes": "historical"}],
    }))
    artifact = _artifact_document(tracks=[
        {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1,
         "absolute_position": 1, "title": "Shared", "artist": "Artist", "notes": "current"},
        {"observed_ordinal": 2, "evidence_segment": 1, "segment_ordinal": 2,
         "absolute_position": 2, "title": "Other", "artist": "Else"},
    ])
    artifact_id = repository.insert_persisted_artifact(PersistedPlaylistArtifactInput.model_validate(artifact))
    historical = repository.get_experiment(experiment_id)["tracks"][0]
    current = repository.get_persisted_artifact(artifact_id)["tracks"][0]
    assert historical["track_id"] == current["track_id"]
    assert historical["notes"] == "historical" and current["notes"] == "current"
    assert repository.recurring_tracks()[0]["experiment_count"] == 1


def test_v3_json_csv_roundtrip_preserves_separation(research_session, tmp_path) -> None:
    repository = ResearchRepository(research_session)
    experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": None, "source_system": None, "generated_title": None,
        "generated_description": None, "saved": None, "tracks": [],
        "tracklist_completeness": "NOT_OBSERVED",
    }))
    artifact_id = repository.insert_persisted_artifact(
        PersistedPlaylistArtifactInput.model_validate(_artifact_document())
    )
    repository.insert_persisted_artifact_experiment_link(
        PersistedArtifactExperimentLinkInput.model_validate({
            "persisted_artifact_id": artifact_id, "experiment_id": experiment_id,
            "evidence_sources": [{"source_key": "user", "source_type": "CONVERSATION_USER_STATEMENT",
                                  "source_reference": "conversation:item"}],
            "evidence": [{"source_key": "user", "field_name": "relationship_type"}],
        })
    )
    exported = export_json(repository, tmp_path / "v3.json")
    bundle = export_csv_bundle(repository, tmp_path / "csv")
    assert (bundle / "persisted_artifact_tracks.csv").exists()
    research_session.close()
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'rebuilt.db').as_posix()}")
    migrate_research_database(engine)
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        target = ResearchRepository(session)
        result = import_research_export(target, exported)
        assert len(result["persisted_artifact_ids"]) == 1
        assert target.get_persisted_artifact(1)["tracks"][1]["track_id"] is None
        assert target.list_persisted_artifact_experiment_links()[0]["unchanged_since_generation"] == "UNKNOWN"


def test_populated_schema_v2_to_v3_preserves_experiment_and_evidence_ids(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'v2.db').as_posix()}")
    migrate_research_database(engine)
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        repository = ResearchRepository(session)
        experiment_id = repository.insert_experiment(ExperimentInput.model_validate({
            "prompt": "Legacy v2", "generated_title": "Title", "generated_description": "Description",
            "saved": False, "tracks": [{"position": 1, "title": "Track", "artist": "Artist"}],
        }))
        before = repository.get_experiment(experiment_id)
        session.rollback()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM schema_version"))
        connection.execute(text("INSERT INTO schema_version(version, applied_at) VALUES (2, CURRENT_TIMESTAMP)"))
    assert migrate_research_database(engine) == 9
    with sessions() as session:
        after = ResearchRepository(session).get_experiment(experiment_id)
        assert after == before
        assert session.scalar(select(func.count()).select_from(PersistedPlaylistArtifact)) == 0
        assert session.scalar(select(func.count()).select_from(PersistedArtifactExperimentLink)) == 0


def test_rec_chat_007_normalized_representation_survives_v2_to_v3(tmp_path) -> None:
    document = json.loads(Path(
        "data/research/maestro/experiments/rec-chat-007.json"
    ).read_text(encoding="utf-8"))
    for source in document["evidence_sources"]:
        source["local_path"] = None
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'rec007.db').as_posix()}")
    migrate_research_database(engine)
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        repository = ResearchRepository(session)
        experiment_id = repository.insert_experiment(ExperimentInput.model_validate(document))
        before = repository.get_experiment(experiment_id)
        source_ids = [item["id"] for item in before["evidence_sources"]]
        session.rollback()
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM schema_version"))
        connection.execute(text("INSERT INTO schema_version(version, applied_at) VALUES (2, CURRENT_TIMESTAMP)"))
    assert migrate_research_database(engine) == 9
    with sessions() as session:
        repository = ResearchRepository(session)
        after = repository.get_experiment(experiment_id)
        assert after == before
        assert [item["id"] for item in after["evidence_sources"]] == source_ids
        assert repository.list_persisted_artifact_ids() == []
        assert repository.list_persisted_artifact_experiment_links() == []

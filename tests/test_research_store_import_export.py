from __future__ import annotations

import csv
import json

from playlist_narrative_engine.research_store.exporter import export_csv_bundle, export_json
from playlist_narrative_engine.research_store.importer import import_experiment_documents, import_research_export
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput, GenerationFailureInput


def test_compact_import_and_lossless_exports(research_session, tmp_path) -> None:
    source = tmp_path / "input.json"
    source.write_text(json.dumps({
        "prompt": "Exact prompt", "generated_title": "Generated", "generated_description": "Description",
        "saved": True, "assessment": "mixed", "tracks": [{"position": 1, "title": "Track (Live)", "artist": "Artist", "version_or_remaster_text": "Live"}],
        "constraints": [{"constraint_type": "count", "constraint_text": "Exactly one", "is_hard_constraint": True,
                         "result": {"status": "PASS", "evidence": "One displayed"}}],
        "observations": [{"observation_type": "progression", "observation_text": "Starts quietly"}],
        "prompt_labels": ["quiet-start"],
    }, ensure_ascii=False), encoding="utf-8")
    repository = ResearchRepository(research_session)
    ids = import_experiment_documents(repository, source)
    repository.record_generation_failure(GenerationFailureInput(prompt="No playlist", failure_type="ERROR", displayed_message="Try again"))
    output = export_json(repository, tmp_path / "export.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["experiments"][0]["prompt"] == "Exact prompt"
    assert payload["experiments"][0]["tracks"][0]["position"] == 1
    assert payload["experiments"][0]["tracks"][0]["version_or_remaster_text"] == "Live"
    assert payload["experiments"][0]["observations"][0]["observation_text"] == "Starts quietly"
    assert payload["generation_failures"][0]["prompt"] == "No playlist"
    bundle = export_csv_bundle(repository, tmp_path / "csv")
    with (bundle / "experiment_tracks.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["experiment_id"] == str(ids[0])
    assert rows[0]["position"] == "1"
    assert rows[0]["title"] == "Track (Live)"


def test_v2_json_export_can_be_losslessly_reimported(research_session, tmp_path) -> None:
    repository = ResearchRepository(research_session)
    source_id = repository.insert_experiment(ExperimentInput.model_validate({
        "prompt": None, "source_system": None, "generated_title": "Recovered",
        "generated_description": None, "saved": None,
        "tracklist_completeness": "PARTIAL",
        "segments": [
            {"segment_ordinal": 1, "relationship_to_previous": "FIRST", "captures_playlist_start": "YES", "captures_playlist_end": "NO"},
            {"segment_ordinal": 2, "relationship_to_previous": "GAP_UNKNOWN_SIZE", "captures_playlist_start": "NO", "captures_playlist_end": "UNKNOWN"},
        ],
        "tracks": [
            {"observed_ordinal": 1, "evidence_segment": 1, "segment_ordinal": 1, "absolute_position": 1, "title": "Known", "artist": "Artist"},
            {"observed_ordinal": 2, "evidence_segment": 2, "segment_ordinal": 1, "absolute_position": None,
             "title": "Only title", "artist": None, "canonical_identity_established": False},
        ],
    }))
    repository.record_generation_failure(GenerationFailureInput(
        prompt=None, source_system=None, failure_type="REFUSAL", displayed_message=None
    ))
    exported = export_json(repository, tmp_path / "v2.json")
    original = repository.get_experiment(source_id)
    research_session.close()

    from playlist_narrative_engine.research_store.database import make_research_engine, make_research_session_factory
    from playlist_narrative_engine.research_store.migrations import migrate_research_database
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'roundtrip.db').as_posix()}")
    migrate_research_database(engine)
    sessions = make_research_session_factory(engine)
    with sessions() as target_session:
        target = ResearchRepository(target_session)
        ids = import_research_export(target, exported)
        restored = target.get_experiment(ids["experiment_ids"][0])
        assert restored["prompt"] == original["prompt"]
        assert restored["generated_at"] is None
        assert restored["segments"][1]["relationship_to_previous"] == "GAP_UNKNOWN_SIZE"
        assert restored["tracks"][1]["absolute_position"] is None
        assert restored["tracks"][1]["title"] == "Only title"
        assert target.list_generation_failures()[0]["displayed_message"] is None

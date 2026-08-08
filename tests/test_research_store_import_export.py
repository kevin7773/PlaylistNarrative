from __future__ import annotations

import csv
import json

from playlist_narrative_engine.research_store.exporter import export_csv_bundle, export_json
from playlist_narrative_engine.research_store.importer import import_experiment_documents
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import GenerationFailureInput


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

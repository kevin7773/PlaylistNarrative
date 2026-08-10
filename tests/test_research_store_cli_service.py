from __future__ import annotations

import json
import sys

from playlist_narrative_engine.research_store.cli import main
from playlist_narrative_engine.research_store.service import ResearchStoreService


def _run_cli(monkeypatch, capsys, database_url: str, *arguments: str) -> object:
    monkeypatch.setenv("PNE_RESEARCH_DATABASE_URL", database_url)
    monkeypatch.setattr(sys, "argv", ["pne-research", *arguments])
    main()
    return json.loads(capsys.readouterr().out)


def test_experiment_import_and_show_route_through_service_with_unchanged_output(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'research.db').as_posix()}"
    document = tmp_path / "experiments.json"
    document.write_text(json.dumps([
        {"prompt": "First", "tracklist_completeness": "NOT_OBSERVED", "tracks": []},
        {"prompt": "Second", "tracklist_completeness": "NOT_OBSERVED", "tracks": []},
    ]), encoding="utf-8")
    ingested: list[str] = []
    read: list[int] = []
    original_ingest = ResearchStoreService.ingest_experiment
    original_get = ResearchStoreService.get_experiment

    def ingest_spy(self, proposal):
        ingested.append(proposal.prompt)
        return original_ingest(self, proposal)

    def get_spy(self, record_id):
        read.append(record_id)
        return original_get(self, record_id)

    monkeypatch.setattr(ResearchStoreService, "ingest_experiment", ingest_spy)
    imported = _run_cli(
        monkeypatch, capsys, database_url, "import-json", str(document)
    )
    monkeypatch.setattr(ResearchStoreService, "get_experiment", get_spy)
    shown = _run_cli(monkeypatch, capsys, database_url, "show", "2")

    assert imported == {"experiment_ids": [1, 2]}
    assert ingested == ["First", "Second"]
    assert shown["prompt"] == "Second"
    assert read == [2]


def test_artifact_import_and_show_route_through_service_with_unchanged_output(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'research.db').as_posix()}"
    document = tmp_path / "artifact.json"
    document.write_text(json.dumps({
        "persistence_state": "UNKNOWN",
        "tracklist_completeness": "NOT_OBSERVED",
    }), encoding="utf-8")
    ingested: list[str] = []
    read: list[int] = []
    original_ingest = ResearchStoreService.ingest_persisted_artifact
    original_get = ResearchStoreService.get_persisted_artifact

    def ingest_spy(self, proposal):
        ingested.append(proposal.persistence_state.value)
        return original_ingest(self, proposal)

    def get_spy(self, record_id):
        read.append(record_id)
        return original_get(self, record_id)

    monkeypatch.setattr(ResearchStoreService, "ingest_persisted_artifact", ingest_spy)
    imported = _run_cli(
        monkeypatch, capsys, database_url, "import-artifact-json", str(document)
    )
    monkeypatch.setattr(ResearchStoreService, "get_persisted_artifact", get_spy)
    shown = _run_cli(monkeypatch, capsys, database_url, "show-artifact", "1")

    assert imported == {"persisted_artifact_ids": [1]}
    assert ingested == ["UNKNOWN"]
    assert shown["persistence_state"] == "UNKNOWN"
    assert read == [1]

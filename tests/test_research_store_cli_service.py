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


def test_recurrence_and_occurrence_commands_route_through_service(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'research.db').as_posix()}"
    document = tmp_path / "experiments.json"
    document.write_text(json.dumps([
        {"prompt": "First", "tracks": [{"position": 1, "title": "Same", "artist": "Repeat"}]},
        {"prompt": "Second", "tracks": [{"position": 1, "title": "Same", "artist": "Repeat"}]},
    ]), encoding="utf-8")
    _run_cli(monkeypatch, capsys, database_url, "import-json", str(document))

    calls: list[tuple[str, object]] = []
    original_tracks = ResearchStoreService.recurring_tracks
    original_artists = ResearchStoreService.recurring_artists
    original_track_occurrences = ResearchStoreService.track_occurrences
    original_artist_occurrences = ResearchStoreService.artist_occurrences

    def tracks_spy(self, limit=20):
        calls.append(("recurring_tracks", limit))
        return original_tracks(self, limit)

    def artists_spy(self, limit=20):
        calls.append(("recurring_artists", limit))
        return original_artists(self, limit)

    def track_occurrences_spy(self, canonical_track_id):
        calls.append(("track_occurrences", canonical_track_id))
        return original_track_occurrences(self, canonical_track_id)

    def artist_occurrences_spy(self, canonical_artist):
        calls.append(("artist_occurrences", canonical_artist))
        return original_artist_occurrences(self, canonical_artist)

    monkeypatch.setattr(ResearchStoreService, "recurring_tracks", tracks_spy)
    monkeypatch.setattr(ResearchStoreService, "recurring_artists", artists_spy)
    monkeypatch.setattr(ResearchStoreService, "track_occurrences", track_occurrences_spy)
    monkeypatch.setattr(ResearchStoreService, "artist_occurrences", artist_occurrences_spy)

    recurring_tracks = _run_cli(monkeypatch, capsys, database_url, "recurring-tracks", "--limit", "5")
    track_id = recurring_tracks[0]["id"]
    _run_cli(monkeypatch, capsys, database_url, "recurring-artists", "--limit", "6")
    track_rows = _run_cli(monkeypatch, capsys, database_url, "track-occurrences", str(track_id))
    artist_rows = _run_cli(monkeypatch, capsys, database_url, "artist-occurrences", "Repeat")

    assert calls == [
        ("recurring_tracks", 5),
        ("recurring_artists", 6),
        ("track_occurrences", track_id),
        ("artist_occurrences", "Repeat"),
    ]
    assert len(track_rows) == 2
    assert len(artist_rows) == 2
    assert track_rows[0]["absolute_position"] == 1


def test_read_only_cli_commands_do_not_run_migrations(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'research.db').as_posix()}"
    document = tmp_path / "experiment.json"
    document.write_text(json.dumps({
        "prompt": "First", "tracks": [{"position": 1, "title": "Same", "artist": "Repeat"}],
    }), encoding="utf-8")
    _run_cli(monkeypatch, capsys, database_url, "import-json", str(document))

    def unexpected_migration(_engine):
        raise AssertionError("read-only command invoked database migration")

    monkeypatch.setattr(
        "playlist_narrative_engine.research_store.cli.migrate_research_database",
        unexpected_migration,
    )
    result = _run_cli(monkeypatch, capsys, database_url, "artist-occurrences", "Repeat")
    assert len(result) == 1


def test_assessment_outcome_query_routes_through_read_only_service(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'research.db').as_posix()}"
    document = tmp_path / "experiment.json"
    document.write_text(json.dumps({
        "tracklist_completeness": "NOT_OBSERVED",
        "tracks": [],
        "assessment_outcome": "INDETERMINATE",
        "assessment": "legacy prose",
    }), encoding="utf-8")
    _run_cli(monkeypatch, capsys, database_url, "import-json", str(document))
    calls = []
    original = ResearchStoreService.query_experiments

    def query_spy(self, **filters):
        calls.append(filters)
        return original(self, **filters)

    monkeypatch.setattr(ResearchStoreService, "query_experiments", query_spy)
    rows = _run_cli(
        monkeypatch, capsys, database_url,
        "query", "--assessment-outcome", "INDETERMINATE",
    )
    assert calls == [{
        "assessment": None,
        "assessment_outcome": "INDETERMINATE",
        "constraint_status": None,
        "saved": None,
    }]
    assert rows[0]["assessment_outcome"] == "INDETERMINATE"
    assert rows[0]["assessment"] == "legacy prose"


def test_q2_analysis_commands_route_through_service(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'unused.db').as_posix()}"
    calls: list[tuple[str, object]] = []

    def track_profile(self, canonical_track_id):
        calls.append(("track_profile", canonical_track_id))
        return {"canonical_track_id": canonical_track_id}

    def artist_profile(self, canonical_artist):
        calls.append(("artist_profile", canonical_artist))
        return {"canonical_artist": canonical_artist}

    def recurring_track_profiles(self, limit=20):
        calls.append(("recurring_track_profiles", limit))
        return []

    def recurring_artist_profiles(self, limit=20):
        calls.append(("recurring_artist_profiles", limit))
        return []

    def compare_experiments(self, experiment_id_a, experiment_id_b):
        calls.append(("compare_experiments", (experiment_id_a, experiment_id_b)))
        return {"experiment_id_a": experiment_id_a, "experiment_id_b": experiment_id_b}

    monkeypatch.setattr(ResearchStoreService, "track_profile", track_profile)
    monkeypatch.setattr(ResearchStoreService, "artist_profile", artist_profile)
    monkeypatch.setattr(ResearchStoreService, "recurring_track_profiles", recurring_track_profiles)
    monkeypatch.setattr(ResearchStoreService, "recurring_artist_profiles", recurring_artist_profiles)
    monkeypatch.setattr(ResearchStoreService, "compare_experiments", compare_experiments)

    assert _run_cli(monkeypatch, capsys, database_url, "track-profile", "7") == {
        "canonical_track_id": 7,
    }
    assert _run_cli(monkeypatch, capsys, database_url, "artist-profile", "Exact Artist") == {
        "canonical_artist": "Exact Artist",
    }
    assert _run_cli(
        monkeypatch, capsys, database_url, "recurring-track-profiles", "--limit", "4"
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "recurring-artist-profiles", "--limit", "5"
    ) == []
    assert _run_cli(monkeypatch, capsys, database_url, "compare-experiments", "2", "9") == {
        "experiment_id_a": 2, "experiment_id_b": 9,
    }
    assert calls == [
        ("track_profile", 7),
        ("artist_profile", "Exact Artist"),
        ("recurring_track_profiles", 4),
        ("recurring_artist_profiles", 5),
        ("compare_experiments", (2, 9)),
    ]


def test_q3_cooccurrence_commands_route_through_service(
    monkeypatch, capsys, tmp_path
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'unused.db').as_posix()}"
    calls: list[tuple[str, object]] = []

    def track_cooccurrences(self, canonical_track_id, limit=20):
        calls.append(("track_cooccurrences", (canonical_track_id, limit)))
        return []

    def artist_cooccurrences(self, canonical_artist, limit=20):
        calls.append(("artist_cooccurrences", (canonical_artist, limit)))
        return []

    def track_pair_occurrences(self, track_a, track_b):
        calls.append(("track_pair_occurrences", (track_a, track_b)))
        return []

    def artist_pair_occurrences(self, artist_a, artist_b):
        calls.append(("artist_pair_occurrences", (artist_a, artist_b)))
        return []

    def recurring_track_pairs(self, limit=20, minimum_shared_experiments=2):
        calls.append(("recurring_track_pairs", (limit, minimum_shared_experiments)))
        return []

    def recurring_artist_pairs(self, limit=20, minimum_shared_experiments=2):
        calls.append(("recurring_artist_pairs", (limit, minimum_shared_experiments)))
        return []

    monkeypatch.setattr(ResearchStoreService, "track_cooccurrences", track_cooccurrences)
    monkeypatch.setattr(ResearchStoreService, "artist_cooccurrences", artist_cooccurrences)
    monkeypatch.setattr(ResearchStoreService, "track_pair_occurrences", track_pair_occurrences)
    monkeypatch.setattr(ResearchStoreService, "artist_pair_occurrences", artist_pair_occurrences)
    monkeypatch.setattr(ResearchStoreService, "recurring_track_pairs", recurring_track_pairs)
    monkeypatch.setattr(ResearchStoreService, "recurring_artist_pairs", recurring_artist_pairs)

    assert _run_cli(
        monkeypatch, capsys, database_url, "track-cooccurrences", "4", "--limit", "3"
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "artist-cooccurrences", "Artist A", "--limit", "5"
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "track-pair-occurrences", "4", "9"
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "artist-pair-occurrences", "Artist A", "Artist B"
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "recurring-track-pairs",
        "--limit", "7", "--minimum-shared-experiments", "3",
    ) == []
    assert _run_cli(
        monkeypatch, capsys, database_url, "recurring-artist-pairs",
        "--limit", "8", "--minimum-shared-experiments", "4",
    ) == []
    assert calls == [
        ("track_cooccurrences", (4, 3)),
        ("artist_cooccurrences", ("Artist A", 5)),
        ("track_pair_occurrences", (4, 9)),
        ("artist_pair_occurrences", ("Artist A", "Artist B")),
        ("recurring_track_pairs", (7, 3)),
        ("recurring_artist_pairs", (8, 4)),
    ]

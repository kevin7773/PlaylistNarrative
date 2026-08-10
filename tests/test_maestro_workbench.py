from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from playlist_narrative_engine.maestro_workbench.operations import (
    EvidenceStager,
    WorkbenchOperations,
)
from playlist_narrative_engine.maestro_workbench.proposal_builder import (
    build_governed_proposal,
)
from playlist_narrative_engine.maestro_workbench.server import MaestroWorkbenchServer
from playlist_narrative_engine.research_store.service import (
    initialize_research_store,
    open_research_store_service,
)


def _database_url(tmp_path) -> str:
    return f"sqlite:///{(tmp_path / 'research.db').as_posix()}"


def test_evidence_staging_preserves_bytes_filename_and_sha256(tmp_path) -> None:
    content = b"exact screenshot bytes"

    staged = EvidenceStager(tmp_path / "staging").stage("capture.png", content)

    assert staged.original_filename == "capture.png"
    assert staged.size_bytes == len(content)
    assert staged.sha256 == hashlib.sha256(content).hexdigest()
    assert open(staged.local_path, "rb").read() == content


def test_validation_is_read_only_and_uses_governed_schema(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)

        invalid = operations.validate("historical_experiment", {
            "tracklist_completeness": "COMPLETE", "tracks": []
        })
        valid = operations.validate("historical_experiment", {
            "prompt": "Exact prompt",
            "tracklist_completeness": "NOT_OBSERVED",
            "tracks": [],
        })

        assert not invalid["valid"]
        assert invalid["validation_issues"]
        assert valid == {
            "valid": True,
            "validation_issues": [],
            "evidence_valid": True,
            "evidence_issues": [],
        }
        assert service.get_experiment(1) is None


def test_ingestion_is_explicit_single_record_and_returns_projection(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)
        proposal = {
            "prompt": "Exact prompt",
            "tracklist_completeness": "NOT_OBSERVED",
            "tracks": [],
        }

        preview = operations.validate("historical_experiment", proposal)
        assert preview["valid"]
        assert service.get_experiment(1) is None

        result = operations.ingest("historical_experiment", proposal)

        assert result["kind"] == "experiment"
        assert result["record_id"] == 1
        assert result["record"] == service.get_experiment(1)


def test_current_artifact_uses_separate_governed_path(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        result = WorkbenchOperations(service).ingest(
            "current_persisted_artifact",
            {
                "persistence_state": "UNKNOWN",
                "tracklist_completeness": "NOT_OBSERVED",
            },
        )

        assert result["kind"] == "persisted_artifact"
        assert result["record"]["persistence_state"] == "UNKNOWN"


def test_recovery_leads_and_batch_kinds_are_not_supported(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    with open_research_store_service(database_url) as service:
        operations = WorkbenchOperations(service)

        with pytest.raises(ValueError, match="unsupported workbench proposal kind"):
            operations.validate("recovery_lead", {})
        with pytest.raises(ValueError, match="unsupported workbench proposal kind"):
            operations.validate("batch", [])


def test_structured_builder_copies_only_explicit_declarations() -> None:
    proposal = build_governed_proposal(
        "historical_experiment",
        {
            "prompt": "Exact prompt",
            "source_system": "Maestro Beta",
            "tracklist_completeness": "NOT_OBSERVED",
            "evidence_standard": "RECOVERED_HISTORICAL",
            "tracks": [],
            "top_level_evidence": [
                {"source_key": "source_1", "field_name": "prompt", "provenance_type": "DIRECT_OBSERVATION"},
                {"source_key": "source_1", "field_name": "source_system", "provenance_type": "DIRECT_OBSERVATION"},
                {"source_key": "source_1", "field_name": "tracklist_completeness", "provenance_type": "HUMAN_ASSESSMENT"},
            ],
        },
        [{
            "source_type": "SCREENSHOT",
            "source_reference": "Phone capture 1",
            "original_filename": "capture.png",
            "local_path": "staging/capture.png",
            "sha256": "a" * 64,
            "size_bytes": 42,
        }],
    )

    assert proposal["prompt"] == "Exact prompt"
    assert proposal["segments"] == []
    assert proposal["tracks"] == []
    assert proposal["evidence_sources"] == [{
        "source_key": "source_1",
        "source_type": "SCREENSHOT",
        "source_reference": "Phone capture 1",
        "original_filename": "capture.png",
        "local_path": "staging/capture.png",
        "sha256": "a" * 64,
    }]
    assert [link["field_name"] for link in proposal["evidence"]] == [
        "prompt", "source_system", "tracklist_completeness",
    ]


def test_structured_builder_requires_explicit_declarations() -> None:
    with pytest.raises(ValueError, match="tracklist_completeness"):
        build_governed_proposal("historical_experiment", {"tracks": []}, [])

    with pytest.raises(ValueError, match="source_type"):
        build_governed_proposal(
            "historical_experiment",
            {"tracklist_completeness": "NOT_OBSERVED", "tracks": []},
            [{"source_reference": "capture", "original_filename": "x.png", "local_path": "x.png", "sha256": "a" * 64}],
        )

    with pytest.raises(ValueError, match="canonical_identity_established"):
        build_governed_proposal(
            "historical_experiment",
            {
                "tracklist_completeness": "PARTIAL",
                "captures_playlist_start": "UNKNOWN",
                "captures_playlist_end": "UNKNOWN",
                "tracks": [{"title": "Observed title", "artist": "Observed artist"}],
            },
            [],
        )


def test_workbench_python_surface_has_no_direct_repository_access() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "maestro_workbench"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))

    assert "research_store.repository" not in source
    assert "sqlalchemy" not in source
    assert "sqlite3" not in source


def test_local_http_surface_stages_validates_and_explicitly_ingests(tmp_path) -> None:
    database_url = _database_url(tmp_path)
    initialize_research_store(database_url)
    server = MaestroWorkbenchServer(
        ("127.0.0.1", 0),
        database_url=database_url,
        staging_root=tmp_path / "staging",
        access_token="test-token",
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(f"{base_url}/") as response:
            assert b"Collect. Display. Invoke." in response.read()

        unauthorized = Request(
            f"{base_url}/api/validate",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as denied:
            urlopen(unauthorized)
        assert denied.value.code == 403

        evidence_request = Request(
            f"{base_url}/api/stage-evidence",
            data=b"screenshot bytes",
            headers={
                "X-Original-Filename": "capture%20one.png",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(evidence_request) as response:
            staged = json.load(response)
        assert staged["sha256"] == hashlib.sha256(b"screenshot bytes").hexdigest()
        assert staged["original_filename"] == "capture one.png"

        build_request = Request(
            f"{base_url}/api/build-proposal",
            data=json.dumps({
                "kind": "historical_experiment",
                "declarations": {
                    "prompt": "Built prompt",
                    "tracklist_completeness": "NOT_OBSERVED",
                    "tracks": [],
                },
                "staged_evidence": [],
            }).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(build_request) as response:
            built = json.load(response)["proposal"]
        assert built["prompt"] == "Built prompt"
        assert built["tracklist_completeness"] == "NOT_OBSERVED"
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        proposal = {
            "kind": "historical_experiment",
            "proposal": {
                "prompt": "Exact prompt",
                "tracklist_completeness": "NOT_OBSERVED",
                "tracks": [],
            },
        }
        validate_request = Request(
            f"{base_url}/api/validate",
            data=json.dumps(proposal).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(validate_request) as response:
            assert json.load(response)["valid"] is True
        with open_research_store_service(database_url) as service:
            assert service.get_experiment(1) is None

        ingest_request = Request(
            f"{base_url}/api/ingest",
            data=json.dumps(proposal).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Workbench-Token": "test-token",
            },
            method="POST",
        )
        with urlopen(ingest_request) as response:
            inserted = json.load(response)
        assert inserted["record_id"] == 1
        assert inserted["record"]["prompt"] == "Exact prompt"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

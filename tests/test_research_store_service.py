from __future__ import annotations

import hashlib

import pytest

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput,
    PersistedPlaylistArtifactInput,
)
from playlist_narrative_engine.research_store.service import ResearchStoreService


def _service(research_session) -> ResearchStoreService:
    return ResearchStoreService(ResearchRepository(research_session))


def _experiment(**changes) -> dict[str, object]:
    proposal: dict[str, object] = {
        "prompt": "Exact prompt",
        "tracklist_completeness": "NOT_OBSERVED",
        "tracks": [],
    }
    proposal.update(changes)
    return proposal


def _artifact(**changes) -> dict[str, object]:
    proposal: dict[str, object] = {
        "persistence_state": "UNKNOWN",
        "tracklist_completeness": "NOT_OBSERVED",
    }
    proposal.update(changes)
    return proposal


def test_validation_returns_existing_schema_failures_without_writing(research_session) -> None:
    service = _service(research_session)

    result = service.validate_experiment(_experiment(tracklist_completeness="COMPLETE"))

    assert not result.valid
    assert result.value is None
    assert any("COMPLETE requires observed track evidence" in issue.message for issue in result.issues)
    assert service.get_experiment(1) is None


def test_valid_proposals_return_existing_schema_objects_without_writing(research_session) -> None:
    service = _service(research_session)

    experiment = service.validate_experiment(_experiment())
    artifact = service.validate_persisted_artifact(_artifact())

    assert experiment.valid and isinstance(experiment.value, ExperimentInput)
    assert artifact.valid and isinstance(artifact.value, PersistedPlaylistArtifactInput)
    assert service.get_experiment(1) is None
    assert service.get_persisted_artifact(1) is None


def test_evidence_verification_is_read_only_and_reports_exact_failures(
    research_session, tmp_path
) -> None:
    evidence = tmp_path / "capture.png"
    evidence.write_bytes(b"original evidence")
    missing = tmp_path / "missing.png"
    draft = ExperimentInput.model_validate(_experiment(evidence_sources=[
        {
            "source_key": "valid",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 1",
            "local_path": str(evidence),
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        },
        {
            "source_key": "mismatch",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 2",
            "local_path": str(evidence),
            "sha256": "0" * 64,
        },
        {
            "source_key": "missing",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 3",
            "local_path": str(missing),
            "sha256": "1" * 64,
        },
    ]))
    service = _service(research_session)

    result = service.verify_experiment_evidence(draft)

    assert [issue.issue_type for issue in result.issues] == [
        "checksum_mismatch", "file_not_found"
    ]
    assert service.get_experiment(1) is None


def test_single_experiment_ingestion_delegates_and_reads_back(research_session) -> None:
    service = _service(research_session)
    draft = ExperimentInput.model_validate(_experiment())

    inserted = service.ingest_experiment(draft)

    assert inserted.kind == "experiment"
    assert inserted.record_id == 1
    assert inserted.record == service.get_experiment(1)
    assert inserted.record["prompt"] == "Exact prompt"


def test_read_back_does_not_block_next_single_record_transaction(research_session) -> None:
    service = _service(research_session)

    first = service.ingest_experiment(ExperimentInput.model_validate(_experiment()))
    second = service.ingest_experiment(ExperimentInput.model_validate(
        _experiment(prompt="Second")
    ))

    assert first.record_id == 1
    assert second.record_id == 2
    assert second.record["prompt"] == "Second"


def test_single_artifact_ingestion_delegates_and_reads_back(research_session) -> None:
    service = _service(research_session)
    draft = PersistedPlaylistArtifactInput.model_validate(_artifact())

    inserted = service.ingest_persisted_artifact(draft)

    assert inserted.kind == "persisted_artifact"
    assert inserted.record_id == 1
    assert inserted.record == service.get_persisted_artifact(1)
    assert inserted.record["persistence_state"] == "UNKNOWN"


def test_ingestion_rejects_unvalidated_input_before_repository_use(research_session) -> None:
    service = _service(research_session)

    with pytest.raises(TypeError, match="validated ExperimentInput"):
        service.ingest_experiment(_experiment())  # type: ignore[arg-type]

    assert service.get_experiment(1) is None

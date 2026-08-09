from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput, GenerationFailureInput


def load_experiment_documents(path: str | Path) -> list[ExperimentInput]:
    with Path(path).open("r", encoding="utf-8") as handle:
        document: Any = json.load(handle)
    if isinstance(document, dict) and "experiments" in document:
        items = document["experiments"]
    else:
        items = document if isinstance(document, list) else [document]
    return [ExperimentInput.model_validate(_import_shape(item)) for item in items]


def _import_shape(item: dict[str, Any]) -> dict[str, Any]:
    """Remove database identities and compatibility-only export aliases."""
    result = dict(item)
    for key in ("id", "schema_version", "observed_track_count", "created_at"):
        result.pop(key, None)
    for source in result.get("evidence_sources", []):
        source.pop("id", None)
    for link in result.get("evidence", []):
        link.pop("id", None)
        link.pop("evidence_source_id", None)
    for segment in result.get("segments", []):
        segment.pop("id", None)
    for track in result.get("tracks", []):
        track.pop("id", None)
        if "absolute_position" in track:
            track.pop("position", None)
        was_exported = "track_id" in track
        track.pop("track_id", None)
        if was_exported and "canonical_identity_established" not in track:
            track["canonical_identity_established"] = (
                track.get("canonical_title") is not None
                and track.get("canonical_artist") is not None
            )
        for link in track.get("evidence", []):
            link.pop("id", None)
            link.pop("evidence_source_id", None)
    for constraint in result.get("constraints", []):
        constraint.pop("id", None)
    for observation in result.get("observations", []):
        observation.pop("id", None)
        observation.pop("experiment_track_id", None)
    return result


def import_experiment_documents(
    repository: ResearchRepository, path: str | Path
) -> list[int]:
    return [repository.insert_experiment(item) for item in load_experiment_documents(path)]


def import_research_export(repository: ResearchRepository, path: str | Path) -> dict[str, list[int]]:
    """Import a lossless v2 JSON export, including independent failures."""
    with Path(path).open("r", encoding="utf-8") as handle:
        document: Any = json.load(handle)
    experiment_ids = [
        repository.insert_experiment(ExperimentInput.model_validate(_import_shape(item)))
        for item in document.get("experiments", [])
    ]
    failure_ids = [
        repository.record_generation_failure(
            GenerationFailureInput.model_validate(_failure_import_shape(item))
        )
        for item in document.get("generation_failures", [])
    ]
    return {"experiment_ids": experiment_ids, "generation_failure_ids": failure_ids}


def _failure_import_shape(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    for key in ("id", "created_at"):
        result.pop(key, None)
    for source in result.get("evidence_sources", []):
        source.pop("id", None)
    for link in result.get("evidence", []):
        link.pop("id", None)
        link.pop("evidence_source_id", None)
    return result

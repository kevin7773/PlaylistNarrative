from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput, GenerationFailureInput, PersistedArtifactExperimentLinkInput,
    PersistedPlaylistArtifactInput,
)


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
    experiment_items = document.get("experiments", [])
    experiment_ids = [repository.insert_experiment(
        ExperimentInput.model_validate(_import_shape(item))
    ) for item in experiment_items]
    failure_ids = [
        repository.record_generation_failure(
            GenerationFailureInput.model_validate(_failure_import_shape(item))
        )
        for item in document.get("generation_failures", [])
    ]
    artifact_items = document.get("persisted_playlist_artifacts", [])
    artifact_ids = [repository.insert_persisted_artifact(
        PersistedPlaylistArtifactInput.model_validate(_artifact_import_shape(item))
    ) for item in artifact_items]
    experiment_map = {item["id"]: new_id for item, new_id in zip(experiment_items, experiment_ids)}
    artifact_map = {item["id"]: new_id for item, new_id in zip(artifact_items, artifact_ids)}
    correlation_ids = []
    for item in document.get("persisted_artifact_experiment_links", []):
        shaped = _correlation_import_shape(item)
        shaped["experiment_id"] = experiment_map[shaped["experiment_id"]]
        shaped["persisted_artifact_id"] = artifact_map[shaped["persisted_artifact_id"]]
        correlation_ids.append(repository.insert_persisted_artifact_experiment_link(
            PersistedArtifactExperimentLinkInput.model_validate(shaped)
        ))
    return {
        "experiment_ids": experiment_ids,
        "generation_failure_ids": failure_ids,
        "persisted_artifact_ids": artifact_ids,
        "persisted_artifact_experiment_link_ids": correlation_ids,
    }


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


def load_persisted_artifact_documents(path: str | Path) -> list[PersistedPlaylistArtifactInput]:
    with Path(path).open("r", encoding="utf-8") as handle:
        document: Any = json.load(handle)
    if isinstance(document, dict) and "persisted_playlist_artifacts" in document:
        items = document["persisted_playlist_artifacts"]
    else:
        items = document if isinstance(document, list) else [document]
    return [PersistedPlaylistArtifactInput.model_validate(_artifact_import_shape(item)) for item in items]


def import_persisted_artifact_documents(
    repository: ResearchRepository, path: str | Path
) -> list[int]:
    return [repository.insert_persisted_artifact(item) for item in load_persisted_artifact_documents(path)]


def _artifact_import_shape(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    for key in ("id", "schema_version", "observed_track_count"):
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
    return result


def _correlation_import_shape(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    result.pop("id", None)
    for source in result.get("evidence_sources", []):
        source.pop("id", None)
    for link in result.get("evidence", []):
        link.pop("id", None)
        link.pop("evidence_source_id", None)
    return result

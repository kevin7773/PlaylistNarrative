from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from playlist_narrative_engine.research_store.repository import ResearchRepository


def export_json(repository: ResearchRepository, path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "experiments": [
            repository.get_experiment(item) for item in repository.list_experiment_ids()
        ],
        "generation_failures": repository.list_generation_failures(),
        "persisted_playlist_artifacts": [
            repository.get_persisted_artifact(item)
            for item in repository.list_persisted_artifact_ids()
        ],
        "persisted_artifact_experiment_links": (
            repository.list_persisted_artifact_experiment_links()
        ),
    }
    with target.open("w", encoding="utf-8", newline="") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return target


def export_csv_bundle(repository: ResearchRepository, directory: str | Path) -> Path:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    experiments = [
        repository.get_experiment(item) for item in repository.list_experiment_ids()
    ]
    concrete = [item for item in experiments if item is not None]
    _write_csv(target / "experiments.csv", [
        {key: value for key, value in item.items() if key not in {"tracks", "segments", "constraints", "observations", "prompt_labels", "evidence_sources", "evidence"}}
        for item in concrete
    ])
    _write_csv(target / "experiment_tracks.csv", [
        {"experiment_id": item["id"], **{key: value for key, value in track.items() if key != "evidence"}}
        for item in concrete for track in item["tracks"]  # type: ignore[union-attr]
    ])
    _write_csv(target / "tracklist_evidence_segments.csv", [
        {"experiment_id": item["id"], **segment}
        for item in concrete for segment in item["segments"]  # type: ignore[union-attr]
    ])
    _write_csv(target / "evidence_sources.csv", [
        {"experiment_id": item["id"], **source}
        for item in concrete for source in item["evidence_sources"]  # type: ignore[union-attr]
    ])
    _write_csv(target / "evidence_links.csv", [
        {"experiment_id": item["id"], **link}
        for item in concrete for link in item["evidence"]  # type: ignore[union-attr]
    ] + [
        {"experiment_id": item["id"], "experiment_track_id": track["id"], **link}
        for item in concrete for track in item["tracks"] for link in track["evidence"]  # type: ignore[union-attr]
    ])
    constraint_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    for item in concrete:
        for constraint in item["constraints"]:  # type: ignore[union-attr]
            result = constraint["result"]
            constraint_rows.append(
                {"experiment_id": item["id"], **{k: v for k, v in constraint.items() if k != "result"}}
            )
            if result is not None:
                result_rows.append(
                    {"experiment_id": item["id"], "constraint_id": constraint["id"], **result}
                )
    _write_csv(target / "constraints.csv", constraint_rows)
    _write_csv(target / "constraint_results.csv", result_rows)
    _write_csv(target / "observations.csv", [
        {"experiment_id": item["id"], **observation}
        for item in concrete for observation in item["observations"]  # type: ignore[union-attr]
    ])
    _write_csv(target / "experiment_prompt_labels.csv", [
        {"experiment_id": item["id"], "label": label}
        for item in concrete for label in item["prompt_labels"]  # type: ignore[union-attr]
    ])
    failures = repository.list_generation_failures()
    _write_csv(target / "generation_failures.csv", [
        {key: value for key, value in item.items() if key not in {"evidence_sources", "evidence"}}
        for item in failures
    ])
    _write_csv(target / "generation_failure_evidence_sources.csv", [
        {"generation_failure_id": item["id"], **source}
        for item in failures for source in item["evidence_sources"]
    ])
    _write_csv(target / "generation_failure_evidence_links.csv", [
        {"generation_failure_id": item["id"], **link}
        for item in failures for link in item["evidence"]
    ])
    artifacts = [
        repository.get_persisted_artifact(item)
        for item in repository.list_persisted_artifact_ids()
    ]
    artifact_rows = [item for item in artifacts if item is not None]
    _write_csv(target / "persisted_playlist_artifacts.csv", [
        {key: value for key, value in item.items() if key not in {
            "segments", "tracks", "evidence_sources", "evidence"
        }} for item in artifact_rows
    ])
    _write_csv(target / "persisted_artifact_segments.csv", [
        {"persisted_artifact_id": item["id"], **segment}
        for item in artifact_rows for segment in item["segments"]
    ])
    _write_csv(target / "persisted_artifact_tracks.csv", [
        {"persisted_artifact_id": item["id"], **{key: value for key, value in track.items() if key != "evidence"}}
        for item in artifact_rows for track in item["tracks"]
    ])
    _write_csv(target / "persisted_artifact_evidence_sources.csv", [
        {"persisted_artifact_id": item["id"], **source}
        for item in artifact_rows for source in item["evidence_sources"]
    ])
    _write_csv(target / "persisted_artifact_evidence_links.csv", [
        {"persisted_artifact_id": item["id"], **link}
        for item in artifact_rows for link in item["evidence"]
    ] + [
        {"persisted_artifact_id": item["id"], "persisted_artifact_track_id": track["id"], **link}
        for item in artifact_rows for track in item["tracks"] for link in track["evidence"]
    ])
    correlations = repository.list_persisted_artifact_experiment_links()
    _write_csv(target / "persisted_artifact_experiment_links.csv", [
        {key: value for key, value in item.items() if key not in {"evidence_sources", "evidence"}}
        for item in correlations
    ])
    _write_csv(target / "persisted_artifact_correlation_evidence_sources.csv", [
        {"persisted_artifact_experiment_link_id": item["id"], **source}
        for item in correlations for source in item["evidence_sources"]
    ])
    _write_csv(target / "persisted_artifact_correlation_evidence_links.csv", [
        {"persisted_artifact_experiment_link_id": item["id"], **link}
        for item in correlations for link in item["evidence"]
    ])
    return target


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        if fieldnames:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

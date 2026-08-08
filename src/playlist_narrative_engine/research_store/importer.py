from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput


def load_experiment_documents(path: str | Path) -> list[ExperimentInput]:
    with Path(path).open("r", encoding="utf-8") as handle:
        document: Any = json.load(handle)
    items = document if isinstance(document, list) else [document]
    return [ExperimentInput.model_validate(item) for item in items]


def import_experiment_documents(
    repository: ResearchRepository, path: str | Path
) -> list[int]:
    return [repository.insert_experiment(item) for item in load_experiment_documents(path)]

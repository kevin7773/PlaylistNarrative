from __future__ import annotations

from playlist_narrative_engine.research_store.schemas import ExperimentInput


def experiment_input(
    *, prompt: str = "Build a night drive arc", label: str = "night-drive",
    artist: str = "Artist One", title: str = "Song One", assessment: str = "good",
    saved: bool = True,
) -> ExperimentInput:
    return ExperimentInput.model_validate({
        "prompt": prompt,
        "generated_title": "Observed Title",
        "generated_description": "Observed Description",
        "saved": saved,
        "assessment": assessment,
        "tracks": [{"position": 1, "title": title, "artist": artist}],
        "constraints": [],
        "observations": [],
        "prompt_labels": [label],
    })

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.models import Experiment, GenerationFailure, Track
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput, GenerationFailureInput
from tests.research_store_helpers import experiment_input


def test_exact_order_and_raw_display_metadata_are_preserved(research_session) -> None:
    draft = ExperimentInput.model_validate({
        "prompt": "  Keep prompt spacing — exactly.  ",
        "generated_title": "Raw “Title”",
        "generated_description": "Description\nwith line break",
        "saved": True,
        "tracks": [
            {"position": 2, "title": "Song - 2011 Remaster", "artist": "Artist  B", "explicit_flag": None, "version_or_remaster_text": "2011 Remaster", "notes": "shown exactly"},
            {"position": 1, "title": "Song (Live)", "artist": "Artist A", "explicit_flag": True},
        ],
        "constraints": [],
        "observations": [{"observation_type": "display", "observation_text": "  verbatim note  ", "track_position": 2}],
    })
    saved_id = ResearchRepository(research_session).insert_experiment(draft)
    result = ResearchRepository(research_session).get_experiment(saved_id)
    assert result is not None
    assert result["prompt"] == "  Keep prompt spacing — exactly.  "
    assert [item["position"] for item in result["tracks"]] == [1, 2]
    assert result["tracks"][1]["title"] == "Song - 2011 Remaster"
    assert result["tracks"][1]["artist"] == "Artist  B"
    assert result["tracks"][1]["version_or_remaster_text"] == "2011 Remaster"
    assert result["observations"][0]["observation_text"] == "  verbatim note  "
    assert result["observations"][0]["provenance_type"] == "DIRECT_OBSERVATION"


def test_duplicate_track_identity_is_reused_across_experiments(research_session) -> None:
    repository = ResearchRepository(research_session)
    repository.insert_experiment(experiment_input(prompt="First"))
    repository.insert_experiment(experiment_input(prompt="Second", label="workout"))
    assert research_session.scalar(select(func.count()).select_from(Track)) == 1
    assert repository.recurring_tracks()[0]["experiment_count"] == 2


def test_malformed_child_rolls_back_complete_ingestion(research_session) -> None:
    draft = ExperimentInput.model_validate({
        "prompt": "Duplicate placement",
        "generated_title": "Should roll back",
        "generated_description": "Nothing persists",
        "saved": False,
        "tracks": [
            {"position": 1, "title": "A", "artist": "One"},
            {"position": 1, "title": "B", "artist": "Two"},
        ],
    })
    with pytest.raises(IntegrityError):
        ResearchRepository(research_session).insert_experiment(draft)
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == 0
    assert research_session.scalar(select(func.count()).select_from(Track)) == 0


def test_failure_record_requires_no_playlist_or_experiment(research_session) -> None:
    failure_id = ResearchRepository(research_session).record_generation_failure(
        GenerationFailureInput(prompt="Forbidden request", failure_type="REFUSAL", displayed_message="I can’t create that.", notes="Observed verbatim")
    )
    assert research_session.get(GenerationFailure, failure_id) is not None
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == 0

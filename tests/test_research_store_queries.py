from __future__ import annotations

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from tests.research_store_helpers import experiment_input


def test_repeated_artists_and_explicit_cross_label_tracks(research_session) -> None:
    repository = ResearchRepository(research_session)
    repository.insert_experiment(experiment_input(prompt="Night", label="night-drive", artist="Repeat", title="Same"))
    repository.insert_experiment(experiment_input(prompt="Gym", label="workout", artist="Repeat", title="Same"))
    repository.insert_experiment(experiment_input(prompt="Study", label="study", artist="Repeat", title="Different"))
    artist = repository.recurring_artists()[0]
    assert artist == {"canonical_artist": "Repeat", "experiment_count": 3, "appearance_count": 3}
    cross_label = repository.tracks_across_prompt_labels()
    assert len(cross_label) == 1
    assert cross_label[0]["canonical_title"] == "Same"
    assert set(cross_label[0]["labels"].split(",")) == {"night-drive", "workout"}


def test_queries_filter_assessment_saved_and_constraint_result(research_session) -> None:
    repository = ResearchRepository(research_session)
    matching = ExperimentInput.model_validate({
        "prompt": "Prompt", "generated_title": "Title", "generated_description": "Description",
        "saved": True, "assessment": "mixed", "tracks": [{"position": 1, "title": "A", "artist": "B"}],
        "constraints": [{"constraint_type": "artist", "constraint_text": "No repeats", "is_hard_constraint": True,
                         "result": {"status": "PARTIAL", "evidence": "One repeat", "recorded_by": "researcher"}}],
        "observations": [{"observation_type": "interpretation", "observation_text": "Likely fallback",
                          "provenance_type": "HUMAN_ASSESSMENT", "provenance_notes": "Manual review"}],
    })
    matching_id = repository.insert_experiment(matching)
    repository.insert_experiment(experiment_input(assessment="good", saved=False))
    assert [item["id"] for item in repository.query_experiments(assessment="mixed")] == [matching_id]
    assert [item["id"] for item in repository.query_experiments(saved=True)] == [matching_id]
    assert [item["id"] for item in repository.query_experiments(constraint_status="PARTIAL")] == [matching_id]
    complete = repository.get_experiment(matching_id)
    assert complete["constraints"][0]["result"]["provenance_type"] == "HUMAN_ASSESSMENT"
    assert complete["observations"][0]["provenance_notes"] == "Manual review"

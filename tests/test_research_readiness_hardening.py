from __future__ import annotations

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.maestro_workbench.proposal_builder import (
    build_governed_proposal,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentAssessmentOutcome,
    ExperimentInput,
)
from playlist_narrative_engine.research_store.service import ResearchStoreService


def _document(**changes):
    document = {
        "prompt": "Create exactly 12 songs",
        "tracklist_completeness": "NOT_OBSERVED",
        "tracks": [],
        "notes": "PASS appears here but is not an assessment declaration.",
        "assessment": "legacy prose remains independent",
    }
    document.update(changes)
    return document


def test_assessment_outcome_defaults_without_inferring_from_prose() -> None:
    experiment = ExperimentInput.model_validate(_document())
    assert experiment.assessment_outcome == ExperimentAssessmentOutcome.INDETERMINATE
    assert experiment.assessment == "legacy prose remains independent"
    assert experiment.notes == "PASS appears here but is not an assessment declaration."
    assert [item.value for item in ExperimentAssessmentOutcome] == [
        "INDETERMINATE", "PASS", "PARTIAL_PASS", "FAIL",
    ]


def test_assessment_outcome_and_legacy_text_survive_ingestion_unchanged(
    research_session,
) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    validated = service.validate_experiment(_document(
        assessment_outcome="PARTIAL_PASS",
    ))
    assert validated.valid
    record = service.ingest_experiment(validated.value).record
    assert record["assessment_outcome"] == "PARTIAL_PASS"
    assert record["assessment"] == "legacy prose remains independent"


@pytest.mark.parametrize("value", [0, -1, 1.5, "3.5"])
def test_requested_track_count_rejects_nonpositive_or_noninteger_values(value) -> None:
    with pytest.raises(ValidationError):
        ExperimentInput.model_validate(_document(requested_track_count=value))


def test_requested_track_count_is_explicit_optional_and_not_parsed_from_prompt() -> None:
    unknown = ExperimentInput.model_validate(_document())
    known = ExperimentInput.model_validate(_document(requested_track_count=12))
    assert unknown.requested_track_count is None
    assert known.requested_track_count == 12


def test_workbench_builder_preserves_explicit_outcome_and_count_only() -> None:
    proposal = build_governed_proposal("historical_experiment", {
        "tracklist_completeness": "NOT_OBSERVED",
        "assessment_outcome": "FAIL",
        "requested_track_count": 12,
        "notes": "supporting prose",
    }, [])
    assert proposal["assessment_outcome"] == "FAIL"
    assert proposal["requested_track_count"] == 12
    assert proposal["notes"] == "supporting prose"

    no_count = build_governed_proposal("historical_experiment", {
        "tracklist_completeness": "NOT_OBSERVED",
        "assessment_outcome": "INDETERMINATE",
        "prompt": "Create exactly 12 songs",
    }, [])
    assert "requested_track_count" not in no_count


def test_indeterminate_query_is_read_only_and_preserves_legacy_text(
    research_session,
) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    validated = service.validate_experiment(_document())
    service.ingest_experiment(validated.value)
    rows = service.query_experiments(assessment_outcome="INDETERMINATE")
    assert len(rows) == 1
    assert rows[0]["assessment_outcome"] == "INDETERMINATE"
    assert rows[0]["assessment"] == "legacy prose remains independent"

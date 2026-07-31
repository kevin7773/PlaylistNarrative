from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.elicitation import ArtistQuestionnaireSeedGenerator
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.objective_assessment import (
    OBJECTIVE_ASSESSMENT_SCHEMA_VERSION,
    AssessmentOutcome,
    DiscoveryPercentEvidence,
    DurationMinutesEvidence,
    EndingEnergyEvidence,
    EvidenceDimension,
    ListeningContextEvidence,
    Objective,
    ObjectiveAssessment,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
    StartingEnergyEvidence,
    serialize_objective_assessment,
)
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    SequentialPlaylistConstructor,
    TrackScorer,
)


def objective() -> Objective:
    return Objective(
        objective_id="coding-focus",
        statement="Support a focused coding session.",
    )


def complete_evidence() -> tuple[object, ...]:
    return (
        ListeningContextEvidence(
            evidence_id="context",
            dimension="listening_context",
            value="Focused coding",
        ),
        DurationMinutesEvidence(
            evidence_id="duration",
            dimension="duration_minutes",
            value=90,
        ),
        StartingEnergyEvidence(
            evidence_id="start",
            dimension="starting_energy",
            value="medium",
        ),
        EndingEnergyEvidence(
            evidence_id="end",
            dimension="ending_energy",
            value="low",
        ),
        DiscoveryPercentEvidence(
            evidence_id="discovery",
            dimension="discovery_percent",
            value=20,
        ),
    )


def request(evidence: tuple[object, ...]) -> ObjectiveAssessmentRequest:
    return ObjectiveAssessmentRequest(objective=objective(), evidence=evidence)


def test_repeated_and_reordered_runs_are_equal_with_identical_json_bytes() -> None:
    first_request = request(complete_evidence())
    second_request = request(tuple(reversed(complete_evidence())))
    assessor = ObjectiveAssessor()

    first = assessor.assess(first_request)
    repeated = assessor.assess(first_request)
    reordered = assessor.assess(second_request)

    assert first == repeated == reordered
    assert serialize_objective_assessment(first) == serialize_objective_assessment(
        reordered
    )


def test_sufficient_outcome_requires_no_clarification() -> None:
    assessment = ObjectiveAssessor().assess(request(complete_evidence()))

    assert assessment.outcome is AssessmentOutcome.SUFFICIENT
    assert assessment.clarification_required is False
    assert assessment.missing_dimensions == ()
    assert assessment.clarification_questions == ()
    assert assessment.recommendation_claims is False
    assert assessment.playlist_construction_performed is False


def test_missing_evidence_produces_exact_ordered_questions_with_provenance() -> None:
    all_evidence = complete_evidence()
    assessment = ObjectiveAssessor().assess(request((all_evidence[4], all_evidence[2])))

    assert assessment.outcome is AssessmentOutcome.CLARIFICATION_REQUIRED
    assert assessment.clarification_required is True
    assert assessment.present_dimensions == (
        EvidenceDimension.STARTING_ENERGY,
        EvidenceDimension.DISCOVERY_PERCENT,
    )
    assert assessment.missing_dimensions == (
        EvidenceDimension.LISTENING_CONTEXT,
        EvidenceDimension.DURATION_MINUTES,
        EvidenceDimension.ENDING_ENERGY,
    )
    assert tuple(question.ordinal for question in assessment.clarification_questions) == (
        1,
        2,
        3,
    )
    assert tuple(
        question.dimension for question in assessment.clarification_questions
    ) == assessment.missing_dimensions
    assert tuple(
        question.provenance.requirement_code
        for question in assessment.clarification_questions
    ) == ("OA-CTX-001", "OA-DUR-001", "OA-ENE-END-001")
    assert all(
        question.prompt and question.provenance.explanation
        for question in assessment.clarification_questions
    )


@pytest.mark.parametrize(
    ("evidence_payload", "message"),
    (
        (
            {"evidence_id": "x", "dimension": "duration_minutes", "value": 0},
            "greater than or equal to 30",
        ),
        (
            {"evidence_id": "x", "dimension": "duration_minutes", "value": "90"},
            "valid integer",
        ),
        (
            {"evidence_id": "x", "dimension": "discovery_percent", "value": 51},
            "less than or equal to 50",
        ),
        (
            {"evidence_id": "x", "dimension": "starting_energy", "value": "calm"},
            "low",
        ),
        (
            {"evidence_id": "x", "dimension": "listening_context", "value": "   "},
            "nonblank",
        ),
    ),
)
def test_public_value_contracts_reject_invalid_values(
    evidence_payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValidationError, match=message):
        ObjectiveAssessmentRequest.model_validate(
            {"objective": objective().model_dump(), "evidence": [evidence_payload]}
        )


def test_unknown_evidence_dimensions_are_rejected() -> None:
    with pytest.raises(ValidationError, match="union_tag_invalid"):
        ObjectiveAssessmentRequest.model_validate(
            {
                "objective": objective().model_dump(),
                "evidence": [
                    {"evidence_id": "mood", "dimension": "mood", "value": "steady"}
                ],
            }
        )


def test_duplicate_dimensions_and_evidence_ids_are_rejected() -> None:
    first = complete_evidence()[0]
    duplicate_dimension = ListeningContextEvidence(
        evidence_id="other-context",
        dimension="listening_context",
        value="Reading",
    )
    with pytest.raises(ValidationError, match="dimension may appear only once"):
        request((first, duplicate_dimension))

    duplicate_id = DurationMinutesEvidence(
        evidence_id="context",
        dimension="duration_minutes",
        value=60,
    )
    with pytest.raises(ValidationError, match="evidence IDs must be unique"):
        request((first, duplicate_id))


def test_inputs_and_outputs_are_immutable_and_objective_is_not_inferred() -> None:
    assessment_request = request(())
    assessment = ObjectiveAssessor().assess(assessment_request)

    assert len(assessment.missing_dimensions) == 5
    with pytest.raises(ValidationError):
        assessment_request.objective.statement = "Changed"
    with pytest.raises(ValidationError):
        assessment.outcome = AssessmentOutcome.SUFFICIENT


def test_schema_version_and_serialized_field_order_are_explicit() -> None:
    assessment = ObjectiveAssessor().assess(request(complete_evidence()))
    serialized = serialize_objective_assessment(assessment)
    parsed = json.loads(serialized)

    assert assessment.schema_version == OBJECTIVE_ASSESSMENT_SCHEMA_VERSION
    assert tuple(parsed) == (
        "schema_version",
        "artifact_kind",
        "objective",
        "outcome",
        "clarification_required",
        "dimension_ordering_rule",
        "present_dimensions",
        "missing_dimensions",
        "clarification_questions",
        "recommendation_claims",
        "playlist_construction_performed",
    )


def test_response_rejects_unapproved_prompt_or_provenance() -> None:
    assessment = ObjectiveAssessor().assess(request(()))
    tampered = assessment.model_dump(mode="json")
    tampered["clarification_questions"][0]["prompt"] = "Tell me more."

    with pytest.raises(
        ValidationError,
        match="approved clarification contracts",
    ):
        ObjectiveAssessment.model_validate(tampered)


def test_assessment_is_isolated_from_forbidden_layers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> None:
        raise AssertionError("objective assessment called a forbidden layer")

    monkeypatch.setattr(ArtistQuestionnaireSeedGenerator, "generate", unexpected_call)
    monkeypatch.setattr(TrackScorer, "score", unexpected_call)
    monkeypatch.setattr(CandidateSelector, "select", unexpected_call)
    monkeypatch.setattr(SequentialPlaylistConstructor, "construct", unexpected_call)
    monkeypatch.setattr(PlaylistJourneyEvaluator, "evaluate", unexpected_call)

    assessment = ObjectiveAssessor().assess(request(complete_evidence()))

    assert assessment.outcome is AssessmentOutcome.SUFFICIENT

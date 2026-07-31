from __future__ import annotations

import json

from playlist_narrative_engine.objective_assessment.schemas import (
    CLARIFICATION_CONTRACTS,
    AssessmentOutcome,
    ClarificationProvenance,
    ClarificationQuestion,
    ObjectiveAssessment,
    ObjectiveAssessmentRequest,
)

_REQUIREMENTS = CLARIFICATION_CONTRACTS


class ObjectiveAssessor:
    """Observe validated evidence presence without interpreting supplied values."""

    def assess(self, request: ObjectiveAssessmentRequest) -> ObjectiveAssessment:
        present_set = {item.dimension for item in request.evidence}
        present_dimensions = tuple(
            dimension
            for dimension, _, _, _ in _REQUIREMENTS
            if dimension in present_set
        )
        missing_requirements = tuple(
            requirement
            for requirement in _REQUIREMENTS
            if requirement[0] not in present_set
        )
        questions = tuple(
            ClarificationQuestion(
                ordinal=ordinal,
                dimension=requirement[0],
                prompt=requirement[2],
                provenance=ClarificationProvenance(
                    requirement_code=requirement[1],
                    explanation=requirement[3],
                ),
            )
            for ordinal, requirement in enumerate(missing_requirements, start=1)
        )
        clarification_required = bool(missing_requirements)
        return ObjectiveAssessment(
            objective=request.objective,
            outcome=(
                AssessmentOutcome.CLARIFICATION_REQUIRED
                if clarification_required
                else AssessmentOutcome.SUFFICIENT
            ),
            clarification_required=clarification_required,
            present_dimensions=present_dimensions,
            missing_dimensions=tuple(
                requirement[0] for requirement in missing_requirements
            ),
            clarification_questions=questions,
        )


def serialize_objective_assessment(assessment: ObjectiveAssessment) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    serialized = json.dumps(
        assessment.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return serialized.encode("utf-8")

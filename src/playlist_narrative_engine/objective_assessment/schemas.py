from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


OBJECTIVE_ASSESSMENT_SCHEMA_VERSION = "1.0"


class FrozenObjectiveAssessmentModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceDimension(StrEnum):
    LISTENING_CONTEXT = "listening_context"
    DURATION_MINUTES = "duration_minutes"
    STARTING_ENERGY = "starting_energy"
    ENDING_ENERGY = "ending_energy"
    DISCOVERY_PERCENT = "discovery_percent"


class EnergyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AssessmentOutcome(StrEnum):
    SUFFICIENT = "sufficient"
    CLARIFICATION_REQUIRED = "clarification_required"


CLARIFICATION_CONTRACTS = (
    (
        EvidenceDimension.LISTENING_CONTEXT,
        "OA-CTX-001",
        "What listening context should this playlist support?",
        "A listening context is required to state where and why the journey will be used.",
    ),
    (
        EvidenceDimension.DURATION_MINUTES,
        "OA-DUR-001",
        "How many minutes should the listening journey last (30 to 240)?",
        "A duration is required to define the journey's time boundary.",
    ),
    (
        EvidenceDimension.STARTING_ENERGY,
        "OA-ENE-START-001",
        "What energy level should the journey begin with: low, medium, or high?",
        "A starting energy is required to define the beginning of the energy arc.",
    ),
    (
        EvidenceDimension.ENDING_ENERGY,
        "OA-ENE-END-001",
        "What energy level should the journey end with: low, medium, or high?",
        "An ending energy is required to define the destination of the energy arc.",
    ),
    (
        EvidenceDimension.DISCOVERY_PERCENT,
        "OA-DISC-001",
        "What percentage of the journey should be exploratory (0 to 50)?",
        "A discovery percentage is required to define how exploratory the journey may be.",
    ),
)

REQUIRED_DIMENSION_ORDER = tuple(item[0] for item in CLARIFICATION_CONTRACTS)


class Objective(FrozenObjectiveAssessmentModel):
    objective_id: str = Field(min_length=1, max_length=100)
    statement: str = Field(min_length=1, max_length=500)

    @field_validator("objective_id", "statement")
    @classmethod
    def reject_surrounding_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text fields cannot contain surrounding whitespace")
        return value


class EvidenceRecord(FrozenObjectiveAssessmentModel):
    evidence_id: str = Field(min_length=1, max_length=100)

    @field_validator("evidence_id")
    @classmethod
    def reject_surrounding_whitespace(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text fields cannot contain surrounding whitespace")
        return value


class ListeningContextEvidence(EvidenceRecord):
    dimension: Literal[EvidenceDimension.LISTENING_CONTEXT]
    value: str = Field(min_length=1, max_length=200)

    @field_validator("value")
    @classmethod
    def require_explicit_nonblank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("listening context must be nonblank")
        if value != value.strip():
            raise ValueError("listening context cannot contain surrounding whitespace")
        return value


class DurationMinutesEvidence(EvidenceRecord):
    dimension: Literal[EvidenceDimension.DURATION_MINUTES]
    value: int = Field(ge=30, le=240, strict=True)


class StartingEnergyEvidence(EvidenceRecord):
    dimension: Literal[EvidenceDimension.STARTING_ENERGY]
    value: EnergyLevel


class EndingEnergyEvidence(EvidenceRecord):
    dimension: Literal[EvidenceDimension.ENDING_ENERGY]
    value: EnergyLevel


class DiscoveryPercentEvidence(EvidenceRecord):
    dimension: Literal[EvidenceDimension.DISCOVERY_PERCENT]
    value: int = Field(ge=0, le=50, strict=True)


ObjectiveEvidence = Annotated[
    ListeningContextEvidence
    | DurationMinutesEvidence
    | StartingEnergyEvidence
    | EndingEnergyEvidence
    | DiscoveryPercentEvidence,
    Field(discriminator="dimension"),
]


class ObjectiveAssessmentRequest(FrozenObjectiveAssessmentModel):
    schema_version: Literal["1.0"] = OBJECTIVE_ASSESSMENT_SCHEMA_VERSION
    objective: Objective
    evidence: tuple[ObjectiveEvidence, ...]

    @model_validator(mode="after")
    def require_unique_evidence(self) -> ObjectiveAssessmentRequest:
        evidence_ids = tuple(item.evidence_id for item in self.evidence)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        dimensions = tuple(item.dimension for item in self.evidence)
        if len(dimensions) != len(set(dimensions)):
            raise ValueError("each evidence dimension may appear only once")
        return self


class ClarificationProvenance(FrozenObjectiveAssessmentModel):
    requirement_code: str
    explanation: str


class ClarificationQuestion(FrozenObjectiveAssessmentModel):
    ordinal: int = Field(gt=0)
    dimension: EvidenceDimension
    prompt: str
    provenance: ClarificationProvenance


class ObjectiveAssessment(FrozenObjectiveAssessmentModel):
    schema_version: Literal["1.0"] = OBJECTIVE_ASSESSMENT_SCHEMA_VERSION
    artifact_kind: Literal["objective_assessment"] = "objective_assessment"
    objective: Objective
    outcome: AssessmentOutcome
    clarification_required: bool
    dimension_ordering_rule: Literal["documented_readiness_order"] = (
        "documented_readiness_order"
    )
    present_dimensions: tuple[EvidenceDimension, ...]
    missing_dimensions: tuple[EvidenceDimension, ...]
    clarification_questions: tuple[ClarificationQuestion, ...]
    recommendation_claims: Literal[False] = False
    playlist_construction_performed: Literal[False] = False

    @model_validator(mode="after")
    def outcome_matches_missing_evidence(self) -> ObjectiveAssessment:
        expected_ordinals = tuple(range(1, len(self.clarification_questions) + 1))
        if tuple(item.ordinal for item in self.clarification_questions) != expected_ordinals:
            raise ValueError("question ordinals must be contiguous and one-based")
        question_dimensions = tuple(
            item.dimension for item in self.clarification_questions
        )
        if question_dimensions != self.missing_dimensions:
            raise ValueError("questions must correspond exactly to missing dimensions")
        if set(self.present_dimensions) & set(self.missing_dimensions):
            raise ValueError("present and missing dimensions must be disjoint")
        expected_present = tuple(
            dimension
            for dimension in REQUIRED_DIMENSION_ORDER
            if dimension in set(self.present_dimensions)
        )
        expected_missing = tuple(
            dimension
            for dimension in REQUIRED_DIMENSION_ORDER
            if dimension not in set(self.present_dimensions)
        )
        if self.present_dimensions != expected_present:
            raise ValueError("present dimensions must use documented readiness order")
        if self.missing_dimensions != expected_missing:
            raise ValueError("missing dimensions must complete documented readiness order")
        contracts_by_dimension = {
            dimension: (requirement_code, prompt, explanation)
            for dimension, requirement_code, prompt, explanation in CLARIFICATION_CONTRACTS
        }
        for question in self.clarification_questions:
            expected_contract = contracts_by_dimension[question.dimension]
            actual_contract = (
                question.provenance.requirement_code,
                question.prompt,
                question.provenance.explanation,
            )
            if actual_contract != expected_contract:
                raise ValueError("questions must use approved clarification contracts")
        has_missing = bool(self.missing_dimensions)
        expected_outcome = (
            AssessmentOutcome.CLARIFICATION_REQUIRED
            if has_missing
            else AssessmentOutcome.SUFFICIENT
        )
        if self.outcome is not expected_outcome:
            raise ValueError("outcome must match missing evidence")
        if self.clarification_required is not has_missing:
            raise ValueError("clarification flag must match missing evidence")
        return self

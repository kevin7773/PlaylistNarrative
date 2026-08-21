from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from playlist_narrative_engine.sequencing.constructor import ConstructionStatus
from playlist_narrative_engine.sequencing.schemas import TrackRole


EVALUATION_SCHEMA_VERSION = "2.0"


class FrozenEvaluationModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationDisposition(StrEnum):
    COMPLETE_EVALUATED = "complete_evaluated"
    PARTIAL_EVALUATED = "partial_evaluated"
    INCONCLUSIVE = "inconclusive"


class MetricApplicability(StrEnum):
    MEASURED = "measured"
    NOT_APPLICABLE = "not_applicable"
    UNAVAILABLE = "unavailable"


class EvidenceSource(StrEnum):
    DIRECT_FACT = "direct_fact"
    STORED_SCORE_AGGREGATION = "stored_score_aggregation"
    OBJECTIVE_COMPARISON = "objective_comparison"
    UNSUPPORTED = "unsupported"


class EvaluationIssueSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class EvaluationMetric(FrozenEvaluationModel):
    code: str
    applicability: MetricApplicability
    value: float | None = None
    unit: str
    numerator: float | None = None
    denominator: float | None = None
    denominator_description: str
    sample_count: int = Field(ge=0)
    target: float | None = None
    evidence_source: EvidenceSource
    explanation: str
    evidence_positions: tuple[int, ...] = ()
    evidence_phases: tuple[str, ...] = ()

    @model_validator(mode="after")
    def applicability_semantics_are_consistent(self) -> EvaluationMetric:
        if self.applicability is MetricApplicability.MEASURED:
            if self.value is None:
                raise ValueError("measured metrics require a value")
            if self.evidence_source is EvidenceSource.UNSUPPORTED:
                raise ValueError("measured metrics cannot use unsupported evidence")
            return self
        if any(
            value is not None
            for value in (self.value, self.numerator, self.denominator)
        ):
            raise ValueError(
                "non-measured metrics cannot contain observed numeric values"
            )
        if self.sample_count != 0:
            raise ValueError("non-measured metrics require a zero sample count")
        if (
            self.applicability is MetricApplicability.UNAVAILABLE
            and self.evidence_source is not EvidenceSource.UNSUPPORTED
        ):
            raise ValueError("unavailable metrics require unsupported evidence")
        if (
            self.evidence_source is EvidenceSource.UNSUPPORTED
            and self.applicability is not MetricApplicability.UNAVAILABLE
        ):
            raise ValueError("unsupported evidence requires unavailable status")
        return self


class SeriesPoint(FrozenEvaluationModel):
    position: int = Field(gt=0)
    value: float


class PhaseDiagnostic(FrozenEvaluationModel):
    phase_index: int = Field(ge=0)
    phase_name: str
    planned_duration_ratio: float = Field(ge=0.0, le=1.0)
    placed_track_count: int = Field(ge=0)
    placed_duration_seconds: int = Field(ge=0)
    phase_score_sum: float
    phase_score_mean: float | None
    sample_count: int = Field(ge=0)
    evidence_positions: tuple[int, ...]


class RolePositions(FrozenEvaluationModel):
    role: TrackRole
    positions: tuple[int, ...]


class EvaluationIssue(FrozenEvaluationModel):
    code: str
    severity: EvaluationIssueSeverity
    message: str
    evidence_positions: tuple[int, ...] = ()
    evidence_phases: tuple[str, ...] = ()


class EvaluationInputBinding(FrozenEvaluationModel):
    schema_version: Literal["1.0"] = "1.0"
    construction_result_schema_version: str
    construction_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    journey_id: str
    journey_schema_version: str
    journey_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    construction_policy_schema_version: str
    construction_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class EvaluationReport(FrozenEvaluationModel):
    schema_version: Literal["2.0"]
    input_binding: EvaluationInputBinding
    disposition: EvaluationDisposition
    construction_status: ConstructionStatus
    metrics: tuple[EvaluationMetric, ...]
    phase_diagnostics: tuple[PhaseDiagnostic, ...]
    transition_series: tuple[SeriesPoint, ...]
    energy_series: tuple[SeriesPoint, ...]
    lyrical_distraction_series: tuple[SeriesPoint, ...]
    discovery_positions: tuple[int, ...]
    role_positions: tuple[RolePositions, ...]
    issues: tuple[EvaluationIssue, ...]

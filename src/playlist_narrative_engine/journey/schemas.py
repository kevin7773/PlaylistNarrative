from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.objective_assessment import (
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
)
from playlist_narrative_engine.objective_safety import (
    AcceptedObjectiveArtifact,
    ObjectiveSafetyRequest,
    canonical_assessment_sha256,
    canonical_objective_sha256,
    verify_objective_safety_artifact,
    verify_objective_safety_request,
)


JOURNEY_PLAN_SCHEMA_VERSION = "2.0"
JOURNEY_PLANNING_REQUEST_SCHEMA_VERSION = "1.0"
JOURNEY_PLANNING_BINDING_SCHEMA_VERSION = "1.0"


class FrozenJourneyModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class JourneyContext(StrEnum):
    ACTIVE_FOCUS = "Active Focus"


class EnergyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FamiliarityAllocation(FrozenJourneyModel):
    familiar_percent: int = Field(ge=0, le=100)
    discovery_percent: int = Field(ge=0, le=100)

    @model_validator(mode="after")
    def percentages_total_one_hundred(self) -> FamiliarityAllocation:
        if self.familiar_percent + self.discovery_percent != 100:
            raise ValueError("familiar and discovery percentages must total 100")
        return self


class ActiveFocusRequest(FrozenJourneyModel):
    duration_minutes: int = Field(default=90, ge=30, le=240)
    discovery_percent: int = Field(default=20, ge=0, le=50)
    starting_energy: EnergyLevel = EnergyLevel.MEDIUM
    ending_energy: EnergyLevel = EnergyLevel.MEDIUM


class JourneyPhase(FrozenJourneyModel):
    name: str
    purpose: str
    duration_minutes: int = Field(gt=0)
    start_energy: EnergyLevel
    end_energy: EnergyLevel
    familiarity: FamiliarityAllocation


class JourneyPlan(FrozenJourneyModel):
    context: JourneyContext
    duration_minutes: int
    discovery_percent: int
    phases: tuple[JourneyPhase, ...]

    @model_validator(mode="after")
    def allocations_match_plan(self) -> JourneyPlan:
        if sum(phase.duration_minutes for phase in self.phases) != self.duration_minutes:
            raise ValueError("phase durations must equal the journey duration")
        return self


class JourneyPlanningEvidenceReference(FrozenJourneyModel):
    dimension: EvidenceDimension
    evidence_id: str = Field(min_length=1, max_length=100)


class JourneyPlanningInputBinding(FrozenJourneyModel):
    schema_version: Literal["1.0"] = JOURNEY_PLANNING_BINDING_SCHEMA_VERSION
    planning_request_id: str
    planning_request_schema_version: str
    planning_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_id: str
    objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_request_schema_version: str
    assessment_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    assessment_schema_version: str
    assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    safety_request_id: str
    safety_request_schema_version: str
    safety_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: str
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration_id: str
    intent_declaration_schema_version: str
    intent_declaration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    safety_policy_id: str
    safety_policy_version: str
    safety_policy_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    planning_evidence: tuple[JourneyPlanningEvidenceReference, ...]
    planning_parameters: ActiveFocusRequest


class JourneyPlanningRequest(FrozenJourneyModel):
    schema_version: Literal["1.0"] = JOURNEY_PLANNING_REQUEST_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    objective_assessment_request: ObjectiveAssessmentRequest
    objective_assessment_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_assessment: ObjectiveAssessment
    objective_assessment_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_safety_request: ObjectiveSafetyRequest
    objective_safety_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective: AcceptedObjectiveArtifact
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("request_id")
    @classmethod
    def require_exact_request_id(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("journey planning request identity must be nonblank and exact")
        return value

    @model_validator(mode="after")
    def require_complete_authority_chain(self) -> JourneyPlanningRequest:
        assessment_request = self.objective_assessment_request
        assessment = self.objective_assessment
        safety_request = self.objective_safety_request
        accepted = self.accepted_objective
        if self.objective_assessment_request_sha256 != _sha256(assessment_request):
            raise ValueError("assessment-request digest must match exact input evidence")
        if ObjectiveAssessor().assess(assessment_request) != assessment:
            raise ValueError("assessment must be the exact result for its input evidence")
        if self.objective_assessment_sha256 != canonical_assessment_sha256(assessment):
            raise ValueError("assessment digest must match exact assessment authority")
        if safety_request.objective_assessment != assessment:
            raise ValueError("safety request must bind the exact assessment")
        if not verify_objective_safety_request(safety_request):
            raise ValueError("safety request authority must verify exactly")
        if self.objective_safety_request_sha256 != safety_request.canonical_sha256:
            raise ValueError("safety-request digest must match exact authority")
        if self.accepted_objective_sha256 != accepted.canonical_sha256:
            raise ValueError("accepted-objective digest must match exact authority")
        if not verify_objective_safety_artifact(accepted, request=safety_request):
            raise ValueError("accepted objective must verify against the safety request")
        objective = assessment_request.objective
        if (
            assessment.objective != objective
            or safety_request.objective_assessment.objective != objective
            or accepted.objective != objective
        ):
            raise ValueError("all journey authorities must bind the exact objective")
        _derive_active_focus_request(assessment_request)
        _verify_or_set_digest(self)
        return self


class JourneyPlanArtifact(FrozenJourneyModel):
    schema_version: Literal["2.0"] = JOURNEY_PLAN_SCHEMA_VERSION
    artifact_kind: Literal["journey_plan"] = "journey_plan"
    journey_id: str = Field(min_length=1, max_length=200)
    input_binding: JourneyPlanningInputBinding
    objective: Objective
    objective_safety_artifact_id: str = Field(min_length=1, max_length=200)
    plan: JourneyPlan
    candidate_formation_performed: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("journey_id", "objective_safety_artifact_id")
    @classmethod
    def require_exact_identifiers(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("journey artifact identities must be nonblank and exact")
        return value

    @model_validator(mode="after")
    def require_binding_correspondence(self) -> JourneyPlanArtifact:
        binding = self.input_binding
        if (
            binding.objective_id != self.objective.objective_id
            or binding.objective_sha256 != canonical_objective_sha256(self.objective)
            or binding.accepted_objective_artifact_id
            != self.objective_safety_artifact_id
        ):
            raise ValueError("journey artifact authority bindings must match exactly")
        parameters = binding.planning_parameters
        if (
            self.plan.context is not JourneyContext.ACTIVE_FOCUS
            or self.plan.duration_minutes != parameters.duration_minutes
            or self.plan.discovery_percent != parameters.discovery_percent
            or not self.plan.phases
            or self.plan.phases[0].start_energy is not parameters.starting_energy
            or self.plan.phases[-1].end_energy is not parameters.ending_energy
        ):
            raise ValueError("journey plan must preserve authenticated planning parameters")
        _verify_or_set_digest(self)
        return self


def derive_active_focus_request(
    request: JourneyPlanningRequest,
) -> ActiveFocusRequest:
    return _derive_active_focus_request(request.objective_assessment_request)


def create_journey_planning_input_binding(
    request: JourneyPlanningRequest,
) -> JourneyPlanningInputBinding:
    safety_request = request.objective_safety_request
    declaration = safety_request.intent_declaration
    if declaration is None:
        raise ValueError("accepted journey planning requires an intent declaration")
    assessment_request = request.objective_assessment_request
    return JourneyPlanningInputBinding(
        planning_request_id=request.request_id,
        planning_request_schema_version=request.schema_version,
        planning_request_sha256=_required_digest(request.canonical_sha256),
        objective_id=assessment_request.objective.objective_id,
        objective_sha256=canonical_objective_sha256(assessment_request.objective),
        assessment_request_schema_version=assessment_request.schema_version,
        assessment_request_sha256=request.objective_assessment_request_sha256,
        assessment_schema_version=request.objective_assessment.schema_version,
        assessment_sha256=request.objective_assessment_sha256,
        safety_request_id=safety_request.request_id,
        safety_request_schema_version=safety_request.schema_version,
        safety_request_sha256=request.objective_safety_request_sha256,
        accepted_objective_artifact_id=request.accepted_objective.artifact_id,
        accepted_objective_schema_version=request.accepted_objective.schema_version,
        accepted_objective_sha256=request.accepted_objective_sha256,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_schema_version=declaration.schema_version,
        intent_declaration_sha256=_required_digest(declaration.canonical_sha256),
        safety_policy_id=safety_request.safety_policy_id,
        safety_policy_version=safety_request.safety_policy_version,
        safety_policy_sha256=safety_request.safety_policy_sha256,
        planning_evidence=tuple(
            JourneyPlanningEvidenceReference(
                dimension=evidence.dimension,
                evidence_id=evidence.evidence_id,
            )
            for evidence in assessment_request.evidence
        ),
        planning_parameters=_derive_active_focus_request(assessment_request),
    )


def canonical_assessment_request_sha256(
    request: ObjectiveAssessmentRequest,
) -> str:
    return _sha256(request)


def journey_plan_matches_accepted_objective(
    artifact: JourneyPlanArtifact,
    accepted: AcceptedObjectiveArtifact,
) -> bool:
    try:
        validated = JourneyPlanArtifact.model_validate(
            artifact.model_dump(mode="json")
        )
    except (TypeError, ValueError):
        return False
    binding = validated.input_binding
    return (
        validated == artifact
        and validated.objective == accepted.objective
        and validated.objective_safety_artifact_id == accepted.artifact_id
        and binding.accepted_objective_artifact_id == accepted.artifact_id
        and binding.accepted_objective_schema_version == accepted.schema_version
        and binding.accepted_objective_sha256 == accepted.canonical_sha256
        and binding.safety_request_id == accepted.request_id
        and binding.safety_request_sha256 == accepted.input_binding.request_sha256
        and binding.assessment_sha256 == accepted.input_binding.assessment_sha256
        and binding.intent_declaration_id
        == accepted.input_binding.intent_declaration_id
        and binding.intent_declaration_sha256
        == accepted.input_binding.intent_declaration_sha256
        and binding.safety_policy_id == accepted.safety_policy_id
        and binding.safety_policy_version == accepted.safety_policy_version
        and binding.safety_policy_sha256 == accepted.safety_policy_sha256
    )


def _derive_active_focus_request(
    request: ObjectiveAssessmentRequest,
) -> ActiveFocusRequest:
    evidence = {item.dimension: item for item in request.evidence}
    expected = set(EvidenceDimension)
    if set(evidence) != expected:
        raise ValueError("authoritative journey planning requires every evidence dimension")
    context = evidence[EvidenceDimension.LISTENING_CONTEXT]
    duration = evidence[EvidenceDimension.DURATION_MINUTES]
    starting = evidence[EvidenceDimension.STARTING_ENERGY]
    ending = evidence[EvidenceDimension.ENDING_ENERGY]
    discovery = evidence[EvidenceDimension.DISCOVERY_PERCENT]
    if not isinstance(context, ListeningContextEvidence) or (
        context.value != JourneyContext.ACTIVE_FOCUS.value
    ):
        raise ValueError("only exact Active Focus context is supported")
    if not isinstance(duration, DurationMinutesEvidence):
        raise ValueError("duration evidence authority is invalid")
    if not isinstance(starting, StartingEnergyEvidence):
        raise ValueError("starting-energy evidence authority is invalid")
    if not isinstance(ending, EndingEnergyEvidence):
        raise ValueError("ending-energy evidence authority is invalid")
    if not isinstance(discovery, DiscoveryPercentEvidence):
        raise ValueError("discovery evidence authority is invalid")
    return ActiveFocusRequest(
        duration_minutes=duration.value,
        discovery_percent=discovery.value,
        starting_energy=EnergyLevel(starting.value.value),
        ending_energy=EnergyLevel(ending.value.value),
    )


def _canonical_bytes(value: BaseModel) -> bytes:
    return json.dumps(
        value.model_dump(mode="json", exclude={"canonical_sha256"}),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: BaseModel) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _verify_or_set_digest(model: BaseModel) -> None:
    supplied = getattr(model, "canonical_sha256")
    expected = _sha256(model)
    if supplied is not None and supplied != expected:
        raise ValueError("canonical SHA-256 must match journey authority content")
    object.__setattr__(model, "canonical_sha256", expected)


def _required_digest(value: str | None) -> str:
    if value is None:
        raise ValueError("required canonical digest is absent")
    return value

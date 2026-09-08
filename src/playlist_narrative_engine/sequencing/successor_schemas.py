"""Implementation-defined layouts under the frozen construction successor ADR.

These are not historical artifact layouts or a new static authority registry.
Declaration order is the local successor canonical field order.
"""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from playlist_narrative_engine.candidate_formation.integration_schemas import CandidateFormationTrace
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.sequencing.constructor import (
    ConstructionIssue, ConstructionStatus, PlacedTrack,
)

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Natural = Annotated[int, Field(strict=True, ge=0)]
Positive = Annotated[int, Field(strict=True, gt=0)]
Outcome = Literal["MET", "MISSED", "NOT_APPLICABLE"]
Failure = Literal["candidate_pool_exhausted", "duration_target_missed", "required_phase_unrepresented"]


class ClosedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False,
                              revalidate_instances="always")


class ConstructionPolicyV2(ClosedModel):
    schema_version: Literal["2.0"] = "2.0"
    max_tracks_per_artist: Positive = 2
    discovery_familiarity_threshold: float = Field(default=0.35, ge=0, le=1, strict=True)


class CountTarget(ClosedModel):
    mode: Literal["TRACK_COUNT"] = "TRACK_COUNT"
    requested_track_count: Positive


class JourneyTarget(ClosedModel):
    mode: Literal["JOURNEY"] = "JOURNEY"
    minimum_duration_seconds: Positive
    required_phase_indices: tuple[Natural, ...]


class ConstructionTargetArtifact(ClosedModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["construction_target"] = "construction_target"
    journey_id: str
    journey_schema_version: Literal["2.0"] = "2.0"
    journey_artifact_sha256: Digest
    journey_context: JourneyContext
    formation_parent_schema_version: Literal["1.0", "2.0"]
    formation_parent_sha256: Digest
    construction_policy_schema_version: Literal["2.0"] = "2.0"
    construction_policy_sha256: Digest
    requirement: Annotated[CountTarget | JourneyTarget, Field(discriminator="mode")]


class ConstructionInputBindingV2(ClosedModel):
    schema_version: Literal["2.0"] = "2.0"
    journey_id: str
    journey_schema_version: Literal["2.0"] = "2.0"
    journey_artifact_sha256: Digest
    formation_parent_schema_version: Literal["1.0", "2.0"]
    formation_parent_sha256: Digest
    formation_request_id: str
    construction_policy_schema_version: Literal["2.0"] = "2.0"
    construction_policy_sha256: Digest
    target_schema_version: Literal["1.0"] = "1.0"
    target_sha256: Digest
    formed_pool_schema_version: Literal["1.0"] = "1.0"
    formed_pool_sha256: Digest
    ordered_track_ids: tuple[str, ...]
    initial_state_sha256: Digest
    initial_placement_count: Natural


class ResidualFeasibilityFact(ClosedModel):
    """M(r) is null iff capacity is insufficient; zero slots has M(0)=0."""
    prefix_count: Natural
    prefix_duration_seconds: Natural
    remaining_slots: Natural
    remaining_capped_capacity: Natural
    maximum_additional_seconds: Natural | None
    attainable_phase_indices: tuple[Natural, ...]
    failures: tuple[Failure, ...]

    @model_validator(mode="after")
    def consistent_capacity(self):
        enough = self.remaining_capped_capacity >= self.remaining_slots
        if enough != (self.maximum_additional_seconds is not None):
            raise ValueError("M(r) must be defined exactly when capacity covers r")
        if ("candidate_pool_exhausted" in self.failures) == enough:
            raise ValueError("capacity failure must match exact bound")
        if self.remaining_slots == 0 and self.maximum_additional_seconds != 0:
            raise ValueError("M(0) must be zero")
        return self


class HorizonTrial(ClosedModel):
    horizon: Positive
    bound: ResidualFeasibilityFact


class ArtistCapacity(ClosedModel):
    artist_name: str
    available_count: Positive
    capped_count: Positive
    limiting_code: Literal["artist_repetition_limit"] | None


class FeasibilityCertificate(ClosedModel):
    schema_version: Literal["1.0"] = "1.0"
    target_sha256: Digest
    formed_pool_sha256: Digest
    construction_policy_sha256: Digest
    outcome: Literal["FEASIBLE", "INFEASIBLE"]
    planning_horizon: Positive | None
    initial_capped_capacity: Natural
    artist_capacities: tuple[ArtistCapacity, ...]
    horizon_trials: tuple[HorizonTrial, ...]

    @model_validator(mode="after")
    def chosen_trial(self):
        if self.outcome == "FEASIBLE":
            if not self.horizon_trials or self.planning_horizon != self.horizon_trials[-1].horizon:
                raise ValueError("feasible certificate requires chosen horizon")
            if self.horizon_trials[-1].bound.failures:
                raise ValueError("chosen horizon must be feasible")
        if any(not trial.bound.failures for trial in self.horizon_trials[:-1]):
            raise ValueError("cannot skip an earlier feasible horizon")
        if self.outcome == "INFEASIBLE" and any(not t.bound.failures for t in self.horizon_trials):
            raise ValueError("infeasible certificate cannot contain a feasible trial")
        return self


class DecisionFact(ClosedModel):
    position: Positive
    track_id: str
    selector_rank: Positive
    outcome: Literal["SELECTED", "artist_repetition_limit", "global_feasibility_guard"]
    residual: ResidualFeasibilityFact | None

    @model_validator(mode="after")
    def bound_applicability(self):
        if (self.outcome == "artist_repetition_limit") != (self.residual is None):
            raise ValueError("only immediate artist rejection omits residual bound")
        if self.outcome == "global_feasibility_guard" and not self.residual.failures:
            raise ValueError("guard rejection requires a failed hard bound")
        if self.outcome == "SELECTED" and self.residual.failures:
            raise ValueError("selected candidate must preserve hard feasibility")
        return self


class ConstructionPrefix(ClosedModel):
    """Local canonical state helper, not another successor authority/version."""
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["construction_successor_prefix"] = "construction_successor_prefix"
    target_sha256: Digest
    formed_pool_sha256: Digest
    planning_horizon: Positive | None
    tracks: tuple[PlacedTrack, ...]
    decisions: tuple[DecisionFact, ...]


class ArtistCount(ClosedModel):
    artist_name: str
    count: Positive


class HardTargetFacts(ClosedModel):
    achieved_count: Natural
    achieved_duration_seconds: Natural
    count_outcome: Outcome
    duration_outcome: Outcome
    phase_requirement_outcome: Outcome
    represented_phase_indices: tuple[Natural, ...]
    unrepresented_phase_indices: tuple[Natural, ...]
    artist_counts: tuple[ArtistCount, ...]
    artist_cap_satisfied: bool = Field(strict=True)
    hard_target_satisfied: bool = Field(strict=True)


class DiscoveryFacts(ClosedModel):
    requested_percent: Annotated[int, Field(strict=True, ge=0, le=100)]
    requested_ratio: float = Field(ge=0, le=1)
    planning_horizon: Positive | None
    rounded_ranking_target_count: Natural | None
    achieved_count: Natural
    achieved_denominator: Natural
    achieved_ratio: float | None
    exact_target_outcome: Outcome
    structural_outcome: Literal["STRUCTURALLY_INFEASIBLE", "NOT_ESTABLISHED", "NOT_APPLICABLE"]
    structural_reasons: tuple[Literal["NONINTEGRAL_COUNT", "FAMILIAR_CAPACITY", "DISCOVERY_CAPACITY"], ...]
    horizon_target_numerator: Natural | None
    horizon_target_denominator: Literal[100] = 100
    familiar_capped_capacity: Natural
    discovery_capped_capacity: Natural


class ConstructionResultV2(ClosedModel):
    schema_version: Literal["2.0"] = "2.0"
    input_binding: ConstructionInputBindingV2
    formation_trace: CandidateFormationTrace
    target: ConstructionTargetArtifact
    feasibility: FeasibilityCertificate
    tracks: tuple[PlacedTrack, ...]
    decisions: tuple[DecisionFact, ...]
    status: ConstructionStatus
    hard_targets: HardTargetFacts
    discovery: DiscoveryFacts
    residual_feasibility: ResidualFeasibilityFact | None
    stopping_reason: Literal["HARD_TARGET_MET", "global_infeasible", "no_eligible_candidates", "candidate_pool_exhausted"]
    issues: tuple[ConstructionIssue, ...]

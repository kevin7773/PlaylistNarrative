from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from math import floor
from typing import TYPE_CHECKING

from playlist_narrative_engine.journey.schemas import (
    JourneyPlan,
    JourneyPlanArtifact,
)
from playlist_narrative_engine.sequencing.schemas import (
    ScoreBreakdown,
    TrackCandidate,
    TrackRole,
)
from playlist_narrative_engine.sequencing.selector import (
    CandidateSelector,
    RankedCandidate,
)

if TYPE_CHECKING:
    from playlist_narrative_engine.candidate_formation.integration_schemas import (
        CandidateFormationTrace,
        FormedCandidatePoolView,
    )


class ConstructionStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    INFEASIBLE = "infeasible"


CONSTRUCTION_BINDING_SCHEMA_VERSION = "1.0"
CONSTRUCTION_POLICY_SCHEMA_VERSION = "1.0"
CONSTRUCTION_RESULT_SCHEMA_VERSION = "1.0"


class ConstructionIssueSeverity(StrEnum):
    HARD_UNMET = "hard_unmet"
    SOFT_COMPROMISE = "soft_compromise"


@dataclass(frozen=True)
class ConstructionPolicy:
    max_tracks_per_artist: int = 2
    discovery_familiarity_threshold: float = 0.35

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_tracks_per_artist, bool)
            or not isinstance(self.max_tracks_per_artist, int)
            or self.max_tracks_per_artist <= 0
        ):
            raise ValueError("max tracks per artist must be a positive integer")
        if not 0.0 <= self.discovery_familiarity_threshold <= 1.0:
            raise ValueError(
                "discovery familiarity threshold must be between 0.0 and 1.0"
            )


@dataclass(frozen=True)
class ConstructionInputBinding:
    schema_version: str
    journey_id: str
    journey_schema_version: str
    journey_artifact_sha256: str
    formation_parent_schema_version: str
    formation_parent_sha256: str
    formation_request_id: str
    construction_policy_schema_version: str
    construction_policy_sha256: str
    initial_state_sha256: str
    initial_placement_count: int


@dataclass(frozen=True)
class CandidateRejection:
    track_id: str
    selector_rank: int
    code: str
    reason: str


@dataclass(frozen=True)
class PlacedTrack:
    position: int
    candidate: TrackCandidate
    phase_index: int
    phase_name: str
    role: TrackRole
    selector_rank: int
    selection_score: float
    score_breakdown: ScoreBreakdown
    reasons: tuple[str, ...]
    rejected_candidates: tuple[CandidateRejection, ...] = ()
    post_selection_validation: str = "FORMED_HARD_ELIGIBILITY_CONFIRMED"
    refinement_action: str = "NONE"


@dataclass
class ConstructionState:
    """The only mutable domain object during one construction run."""

    placed_tracks: list[PlacedTrack] = field(default_factory=list)
    previous_track: TrackCandidate | None = None
    elapsed_seconds: int = 0
    current_phase_index: int = 0
    used_track_ids: set[str] = field(default_factory=set)
    artist_counts: dict[str, int] = field(default_factory=dict)
    discovery_count: int = 0
    rejections: list[CandidateRejection] = field(default_factory=list)
    formation_trace: CandidateFormationTrace | None = None
    journey_plan_artifact: JourneyPlanArtifact | None = None


@dataclass(frozen=True)
class ConstructionIssue:
    code: str
    message: str
    severity: ConstructionIssueSeverity
    observed_value: int | float | None = None
    requested_value: int | float | None = None


@dataclass(frozen=True)
class ConstructionSummary:
    status: ConstructionStatus
    requested_track_count: int
    achieved_track_count: int
    total_duration_seconds: int
    discovery_count: int
    discovery_ratio: float
    artist_counts: tuple[tuple[str, int], ...]
    phase_track_counts: tuple[tuple[str, int], ...]
    role_counts: tuple[tuple[TrackRole, int], ...]
    rejection_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class ConstructionResult:
    schema_version: str
    input_binding: ConstructionInputBinding
    formation_trace: CandidateFormationTrace
    tracks: tuple[PlacedTrack, ...]
    summary: ConstructionSummary
    issues: tuple[ConstructionIssue, ...]


class SequentialPlaylistConstructor:
    """Place one track at a time using a fresh state-relative ranking."""

    def __init__(
        self,
        selector: CandidateSelector | None = None,
        policy: ConstructionPolicy | None = None,
    ) -> None:
        self.selector = selector or CandidateSelector()
        self.policy = policy or ConstructionPolicy()

    def construct(
        self,
        *,
        journey_plan: JourneyPlanArtifact,
        formed_pool: FormedCandidatePoolView,
        state: ConstructionState,
        requested_track_count: int,
    ) -> ConstructionResult:
        self._validate_request(
            journey_plan,
            formed_pool,
            state,
            requested_track_count,
        )
        from playlist_narrative_engine.sequencing.canonical import (
            create_construction_input_binding,
        )

        input_binding = create_construction_input_binding(
            journey_plan=journey_plan,
            formed_pool=formed_pool,
            construction_policy=self.policy,
            initial_state=state,
        )
        if state.formation_trace is None:
            state.formation_trace = formed_pool.trace
            state.journey_plan_artifact = journey_plan
        plan = journey_plan.plan
        remaining_ids = tuple(
            candidate.track_id
            for candidate in formed_pool.candidates
            if candidate.track_id not in state.used_track_ids
        )
        issues: list[ConstructionIssue] = []

        while (
            len(state.placed_tracks) < requested_track_count and remaining_ids
        ):
            position = len(state.placed_tracks)
            phase_index = self._phase_index_for_position(
                plan,
                position,
                requested_track_count,
            )
            role = self._role_for_position(
                state,
                position,
                phase_index,
                requested_track_count,
            )
            target_discovery_ratio = self._remaining_discovery_ratio(
                plan,
                state,
                requested_track_count,
            )
            ranking = self.selector.select(
                context=plan.context,
                previous_track=state.previous_track,
                phase=plan.phases[phase_index],
                role=role,
                target_discovery_ratio=target_discovery_ratio,
                formed_pool=formed_pool,
                remaining_track_ids=remaining_ids,
                top_n=len(remaining_ids),
            )
            if ranking.formation_trace != formed_pool.trace:
                raise ValueError("ranking envelope formation trace must match pool")
            selected, rejected = self._first_eligible(
                ranking.ranked_candidates, state
            )
            state.rejections.extend(rejected)
            if selected is None:
                issues.append(
                    ConstructionIssue(
                        code="no_eligible_candidates",
                        message=(
                            "Remaining candidates violate active hard constraints"
                        ),
                        severity=ConstructionIssueSeverity.HARD_UNMET,
                        observed_value=len(state.placed_tracks),
                        requested_value=requested_track_count,
                    )
                )
                break

            placement = PlacedTrack(
                position=position + 1,
                candidate=selected.candidate,
                phase_index=phase_index,
                phase_name=plan.phases[phase_index].name,
                role=role,
                selector_rank=selected.rank,
                selection_score=selected.score,
                score_breakdown=selected.score_breakdown,
                reasons=selected.reasons
                + (
                    f"Selected as {role.value} for "
                    f"{plan.phases[phase_index].name}",
                ),
                rejected_candidates=rejected,
            )
            self._place(state, placement)
            remaining_ids = tuple(
                track_id
                for track_id in remaining_ids
                if track_id != selected.candidate.track_id
            )

        if len(state.placed_tracks) < requested_track_count and not issues:
            issues.append(
                ConstructionIssue(
                    code="candidate_pool_exhausted",
                    message="Candidate pool exhausted before requested count",
                    severity=ConstructionIssueSeverity.HARD_UNMET,
                    observed_value=len(state.placed_tracks),
                    requested_value=requested_track_count,
                )
            )
        return self._result(
            state,
            requested_track_count,
            issues,
            input_binding,
        )

    def _validate_request(
        self,
        journey_plan: JourneyPlanArtifact,
        formed_pool: FormedCandidatePoolView,
        state: ConstructionState,
        requested_track_count: int,
    ) -> None:
        if (
            isinstance(requested_track_count, bool)
            or not isinstance(requested_track_count, int)
            or requested_track_count <= 0
        ):
            raise ValueError("requested track count must be a positive integer")
        if len(state.placed_tracks) > requested_track_count:
            raise ValueError(
                "initial state already exceeds requested track count"
            )
        if not journey_plan.plan.phases:
            raise ValueError("journey plan must contain at least one phase")
        trace = formed_pool.trace
        if (
            journey_plan.journey_id != trace.journey_id
            or journey_plan.objective.objective_id != trace.objective_id
            or journey_plan.objective.statement != trace.objective_statement
            or journey_plan.objective_safety_artifact_id
            != trace.accepted_objective_artifact_id
        ):
            raise ValueError(
                "journey artifact must exactly correspond to formation trace"
            )
        self._validate_state(journey_plan, formed_pool, state)

    def _validate_state(
        self,
        journey_plan: JourneyPlanArtifact,
        formed_pool: FormedCandidatePoolView,
        state: ConstructionState,
    ) -> None:
        plan = journey_plan.plan
        if not 0 <= state.current_phase_index < len(plan.phases):
            raise ValueError("construction state has an invalid phase index")
        if (state.formation_trace is None) != (state.journey_plan_artifact is None):
            raise ValueError("construction state lineage must be complete")
        if state.formation_trace is None and (
            state.placed_tracks
            or state.previous_track is not None
            or state.elapsed_seconds
            or state.used_track_ids
            or state.artist_counts
            or state.discovery_count
            or state.rejections
        ):
            raise ValueError(
                "resumed construction state requires immutable formation lineage"
            )
        if state.formation_trace is not None:
            if state.formation_trace != formed_pool.trace:
                raise ValueError("construction state formation identity does not match")
            if state.journey_plan_artifact != journey_plan:
                raise ValueError("construction state journey identity does not match")
        placed_ids = [
            placement.candidate.track_id for placement in state.placed_tracks
        ]
        if len(placed_ids) != len(set(placed_ids)):
            raise ValueError("construction state contains duplicate tracks")
        if set(placed_ids) != state.used_track_ids:
            raise ValueError(
                "construction state used track IDs must exactly match placements"
            )
        formed_by_id = {
            candidate.track_id: candidate for candidate in formed_pool.candidates
        }
        for placement in state.placed_tracks:
            if formed_by_id.get(placement.candidate.track_id) != placement.candidate:
                raise ValueError(
                    "construction state candidate must exactly equal formed candidate"
                )
        expected_positions = list(range(1, len(state.placed_tracks) + 1))
        if [placement.position for placement in state.placed_tracks] != (
            expected_positions
        ):
            raise ValueError(
                "construction state placements are not sequentially positioned"
            )
        if state.placed_tracks:
            if (
                state.previous_track is None
                or state.previous_track != state.placed_tracks[-1].candidate
            ):
                raise ValueError(
                    "construction state previous track is not the last placement"
                )
            if (
                state.current_phase_index
                != state.placed_tracks[-1].phase_index
            ):
                raise ValueError(
                    "construction state phase does not match last placement"
                )
        elif state.previous_track is not None:
            raise ValueError(
                "construction state without placements cannot have previous track"
            )
        expected_duration = sum(
            placement.candidate.duration_seconds
            for placement in state.placed_tracks
        )
        if state.elapsed_seconds != expected_duration:
            raise ValueError(
                "construction state elapsed duration does not match placements"
            )
        expected_artist_counts: dict[str, int] = {}
        for placement in state.placed_tracks:
            artist_key = self._artist_key(placement.candidate.artist_name)
            expected_artist_counts[artist_key] = (
                expected_artist_counts.get(artist_key, 0) + 1
            )
        if state.artist_counts != expected_artist_counts:
            raise ValueError(
                "construction state artist counts do not match placements"
            )
        expected_discovery_count = sum(
            placement.candidate.familiarity
            <= self.policy.discovery_familiarity_threshold
            for placement in state.placed_tracks
        )
        if state.discovery_count != expected_discovery_count:
            raise ValueError(
                "construction state discovery count does not match placements"
            )

    def _first_eligible(
        self,
        ranking: tuple[RankedCandidate, ...],
        state: ConstructionState,
    ) -> tuple[RankedCandidate | None, tuple[CandidateRejection, ...]]:
        rejected: list[CandidateRejection] = []
        for ranked in ranking:
            artist_key = self._artist_key(ranked.candidate.artist_name)
            if (
                state.artist_counts.get(artist_key, 0)
                >= self.policy.max_tracks_per_artist
            ):
                rejected.append(
                    CandidateRejection(
                        track_id=ranked.candidate.track_id,
                        selector_rank=ranked.rank,
                        code="artist_repetition_limit",
                        reason=(
                            f"Artist {ranked.candidate.artist_name!r} reached "
                            f"the limit of {self.policy.max_tracks_per_artist}"
                        ),
                    )
                )
                continue
            return ranked, tuple(rejected)
        return None, tuple(rejected)

    def _place(self, state: ConstructionState, placement: PlacedTrack) -> None:
        candidate = placement.candidate
        state.placed_tracks.append(placement)
        state.previous_track = candidate
        state.elapsed_seconds += candidate.duration_seconds
        state.current_phase_index = placement.phase_index
        state.used_track_ids.add(candidate.track_id)
        artist_key = self._artist_key(candidate.artist_name)
        state.artist_counts[artist_key] = (
            state.artist_counts.get(artist_key, 0) + 1
        )
        if candidate.familiarity <= self.policy.discovery_familiarity_threshold:
            state.discovery_count += 1

    @staticmethod
    def _phase_index_for_position(
        journey_plan: JourneyPlan,
        position: int,
        requested_track_count: int,
    ) -> int:
        slot_midpoint = (position + 0.5) / requested_track_count
        cumulative = 0.0
        for index, phase in enumerate(journey_plan.phases):
            cumulative += phase.duration_minutes / journey_plan.duration_minutes
            if slot_midpoint <= cumulative:
                return index
        return len(journey_plan.phases) - 1

    @staticmethod
    def _role_for_position(
        state: ConstructionState,
        position: int,
        phase_index: int,
        requested_track_count: int,
    ) -> TrackRole:
        if position == 0 and state.previous_track is None:
            return TrackRole.OPENING_ANCHOR
        if position == requested_track_count - 1:
            return TrackRole.CLOSING_TRACK
        if phase_index != state.current_phase_index:
            return TrackRole.PHASE_TRANSITION
        return TrackRole.JOURNEY

    @staticmethod
    def _remaining_discovery_ratio(
        journey_plan: JourneyPlan,
        state: ConstructionState,
        requested_track_count: int,
    ) -> float:
        target_ratio = journey_plan.discovery_percent / 100.0
        target_count = floor(target_ratio * requested_track_count + 0.5)
        remaining_slots = requested_track_count - len(state.placed_tracks)
        remaining_discoveries = target_count - state.discovery_count
        return min(1.0, max(0.0, remaining_discoveries / remaining_slots))

    def _result(
        self,
        state: ConstructionState,
        requested_track_count: int,
        issues: list[ConstructionIssue],
        input_binding: ConstructionInputBinding,
    ) -> ConstructionResult:
        achieved = len(state.placed_tracks)
        if achieved == requested_track_count:
            status = ConstructionStatus.COMPLETE
        elif achieved:
            status = ConstructionStatus.PARTIAL
        else:
            status = ConstructionStatus.INFEASIBLE

        phase_counts: dict[str, int] = {}
        role_counts: dict[TrackRole, int] = {}
        for placement in state.placed_tracks:
            phase_counts[placement.phase_name] = (
                phase_counts.get(placement.phase_name, 0) + 1
            )
            role_counts[placement.role] = role_counts.get(placement.role, 0) + 1
        rejection_counts: dict[str, int] = {}
        for rejection in state.rejections:
            rejection_counts[rejection.code] = (
                rejection_counts.get(rejection.code, 0) + 1
            )

        summary = ConstructionSummary(
            status=status,
            requested_track_count=requested_track_count,
            achieved_track_count=achieved,
            total_duration_seconds=state.elapsed_seconds,
            discovery_count=state.discovery_count,
            discovery_ratio=round(state.discovery_count / achieved, 4)
            if achieved
            else 0.0,
            artist_counts=tuple(sorted(state.artist_counts.items())),
            phase_track_counts=tuple(sorted(phase_counts.items())),
            role_counts=tuple(
                sorted(role_counts.items(), key=lambda item: item[0].value)
            ),
            rejection_counts=tuple(sorted(rejection_counts.items())),
        )
        if state.formation_trace is None:
            raise AssertionError("construction result requires formation trace")
        return ConstructionResult(
            schema_version=CONSTRUCTION_RESULT_SCHEMA_VERSION,
            input_binding=input_binding,
            formation_trace=state.formation_trace,
            tracks=tuple(state.placed_tracks),
            summary=summary,
            issues=tuple(issues),
        )

    @staticmethod
    def _artist_key(artist_name: str) -> str:
        return artist_name

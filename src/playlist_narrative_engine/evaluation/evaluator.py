from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence

from playlist_narrative_engine.evaluation.schemas import (
    EVALUATION_SCHEMA_VERSION,
    EvaluationDisposition,
    EvaluationIssue,
    EvaluationIssueSeverity,
    EvaluationInputBinding,
    EvaluationMetric,
    EvaluationReport,
    EvidenceSource,
    MetricApplicability,
    PhaseDiagnostic,
    RolePositions,
    SeriesPoint,
)
from playlist_narrative_engine.journey.schemas import JourneyPlan, JourneyPlanArtifact
from playlist_narrative_engine.journey.serialization import serialize_journey_plan_artifact
from playlist_narrative_engine.sequencing.canonical import (
    construction_policy_sha256,
    construction_result_matches_evaluation_inputs,
    construction_result_sha256,
)
from playlist_narrative_engine.sequencing.constructor import (
    CONSTRUCTION_POLICY_SCHEMA_VERSION,
    ConstructionIssueSeverity,
    ConstructionPolicy,
    ConstructionResult,
    ConstructionStatus,
    PlacedTrack,
)
from playlist_narrative_engine.sequencing.schemas import TrackRole


class PlaylistJourneyEvaluator:
    """Pure observer over immutable construction evidence."""

    __slots__ = ()

    _UNAVAILABLE_METRICS = (
        (
            "album_repetition_fidelity",
            "Album identity is not present in TrackCandidate.",
        ),
        (
            "vocal_salience",
            "Lyrical-distraction input is not measured vocal salience.",
        ),
        (
            "emotional_continuity",
            "Independent emotional-continuity evidence is not persisted.",
        ),
        (
            "narrative_continuity",
            "Independent narrative-continuity evidence is not persisted.",
        ),
        (
            "phase_energy_contour_fidelity",
            "No public numeric phase-energy target mapping is persisted.",
        ),
        (
            "anchor_spacing_fidelity",
            "No objective anchor-spacing policy is present.",
        ),
    )

    def evaluate(
        self,
        *,
        construction_result: ConstructionResult,
        journey_plan: JourneyPlanArtifact,
        construction_policy: ConstructionPolicy,
    ) -> EvaluationReport:
        if not construction_result_matches_evaluation_inputs(
            construction_result,
            journey_plan=journey_plan,
            construction_policy=construction_policy,
        ):
            raise ValueError(
                "evaluation inputs must match construction-time authority"
            )
        plan = journey_plan.plan
        tracks = construction_result.tracks
        metrics = self._metrics(
            construction_result,
            plan,
            construction_policy,
        )
        phases = self._phase_diagnostics(tracks, plan)
        transition_series = tuple(
            SeriesPoint(
                position=placement.position,
                value=placement.score_breakdown.transition_score,
            )
            for placement in tracks[1:]
        )
        energy_series = tuple(
            SeriesPoint(
                position=placement.position,
                value=placement.candidate.energy,
            )
            for placement in tracks
        )
        lyrical_series = tuple(
            SeriesPoint(
                position=placement.position,
                value=placement.candidate.lyrical_distraction,
            )
            for placement in tracks
        )
        discovery_positions = tuple(
            placement.position
            for placement in tracks
            if placement.candidate.familiarity
            <= construction_policy.discovery_familiarity_threshold
        )
        role_positions = tuple(
            RolePositions(
                role=role,
                positions=tuple(
                    placement.position
                    for placement in tracks
                    if placement.role is role
                ),
            )
            for role in TrackRole
            if any(placement.role is role for placement in tracks)
        )
        issues = self._issues(
            construction_result,
            plan,
            construction_policy,
            discovery_positions,
        )
        return EvaluationReport(
            schema_version=EVALUATION_SCHEMA_VERSION,
            input_binding=EvaluationInputBinding(
                construction_result_schema_version=construction_result.schema_version,
                construction_result_sha256=construction_result_sha256(
                    construction_result
                ),
                journey_id=journey_plan.journey_id,
                journey_schema_version=journey_plan.schema_version,
                journey_artifact_sha256=hashlib.sha256(
                    serialize_journey_plan_artifact(journey_plan)
                ).hexdigest(),
                construction_policy_schema_version=CONSTRUCTION_POLICY_SCHEMA_VERSION,
                construction_policy_sha256=construction_policy_sha256(
                    construction_policy
                ),
            ),
            disposition=self._disposition(construction_result),
            construction_status=construction_result.summary.status,
            metrics=metrics,
            phase_diagnostics=phases,
            transition_series=transition_series,
            energy_series=energy_series,
            lyrical_distraction_series=lyrical_series,
            discovery_positions=discovery_positions,
            role_positions=role_positions,
            issues=issues,
        )

    def _metrics(
        self,
        result: ConstructionResult,
        journey_plan: JourneyPlan,
        policy: ConstructionPolicy,
    ) -> tuple[EvaluationMetric, ...]:
        tracks = result.tracks
        summary = result.summary
        achieved = len(tracks)
        requested = summary.requested_track_count
        track_ids = [placement.candidate.track_id for placement in tracks]
        artist_counts = self._artist_counts(tracks)
        discovery_count = sum(
            placement.candidate.familiarity
            <= policy.discovery_familiarity_threshold
            for placement in tracks
        )
        discovery_ratio = discovery_count / achieved if achieved else 0.0
        represented_phases = {
            placement.phase_index
            for placement in tracks
            if 0 <= placement.phase_index < len(journey_plan.phases)
        }
        metrics = [
            EvaluationMetric(
                code="completion_fidelity",
                applicability=MetricApplicability.MEASURED,
                value=self._rounded(achieved / requested),
                unit="ratio",
                numerator=float(achieved),
                denominator=float(requested),
                denominator_description="requested tracks",
                sample_count=achieved,
                target=1.0,
                evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                explanation=(
                    f"Placed {achieved} of {requested} requested tracks."
                ),
                evidence_positions=tuple(
                    placement.position for placement in tracks
                ),
            ),
            self._direct_metric(
                code="observed_duration_seconds",
                value=sum(
                    placement.candidate.duration_seconds
                    for placement in tracks
                ),
                unit="seconds",
                sample_count=achieved,
                denominator_description="placed tracks",
                explanation=(
                    "Observed duration only; Phase 4B has no duration objective."
                ),
                positions=tuple(placement.position for placement in tracks),
            ),
            self._boolean_metric(
                code="duplicate_track_compliance",
                passed=len(track_ids) == len(set(track_ids)),
                numerator=len(set(track_ids)),
                denominator=achieved,
                denominator_description="placed track IDs",
                explanation="A track ID may appear at most once.",
                positions=tuple(placement.position for placement in tracks),
            ),
            self._boolean_metric(
                code="artist_repetition_compliance",
                passed=all(
                    count <= policy.max_tracks_per_artist
                    for count in artist_counts.values()
                ),
                numerator=max(artist_counts.values(), default=0),
                denominator=policy.max_tracks_per_artist,
                denominator_description="maximum tracks per artist",
                explanation=(
                    "Observed artist counts compared with the construction "
                    "policy maximum."
                ),
                positions=tuple(placement.position for placement in tracks),
            ),
            self._direct_metric(
                code="construction_issue_count",
                value=len(result.issues),
                unit="issues",
                sample_count=len(result.issues),
                denominator_description="construction issues",
                explanation=(
                    "Structured issues emitted by playlist construction."
                ),
            ),
            self._direct_metric(
                code="discovery_count",
                value=discovery_count,
                unit="tracks",
                sample_count=achieved,
                denominator_description="placed tracks",
                explanation=(
                    "Tracks at or below the policy familiarity threshold."
                ),
                positions=tuple(
                    placement.position
                    for placement in tracks
                    if placement.candidate.familiarity
                    <= policy.discovery_familiarity_threshold
                ),
            ),
            *self._discovery_ratio_metrics(
                tracks=tracks,
                discovery_count=discovery_count,
                target_ratio=journey_plan.discovery_percent / 100.0,
                threshold=policy.discovery_familiarity_threshold,
            ),
            EvaluationMetric(
                code="phase_coverage",
                applicability=MetricApplicability.MEASURED,
                value=self._rounded(
                    len(represented_phases) / len(journey_plan.phases)
                ),
                unit="ratio",
                numerator=float(len(represented_phases)),
                denominator=float(len(journey_plan.phases)),
                denominator_description="planned phases",
                sample_count=len(represented_phases),
                target=1.0,
                evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                explanation="Share of planned phases represented by placements.",
                evidence_phases=tuple(
                    journey_plan.phases[index].name
                    for index in sorted(represented_phases)
                ),
            ),
        ]
        metrics.extend(
            (
                self._aggregate_metric(
                    "mean_selection_score",
                    tracks,
                    lambda placement: placement.selection_score,
                    "Mean adjusted selector score over placed tracks.",
                ),
                self._aggregate_metric(
                    "mean_total_scorer_points",
                    tracks,
                    lambda placement: placement.score_breakdown.total_score,
                    "Mean stored TrackScorer total over placed tracks.",
                ),
                self._aggregate_metric(
                    "mean_preference_score",
                    tracks,
                    lambda placement: placement.score_breakdown.preference_score,
                    "Mean stored preference component points.",
                ),
                self._aggregate_metric(
                    "mean_context_score",
                    tracks,
                    lambda placement: placement.score_breakdown.context_score,
                    "Mean stored context component points.",
                ),
                self._aggregate_metric(
                    "mean_phase_score",
                    tracks,
                    lambda placement: placement.score_breakdown.phase_score,
                    "Mean stored phase component points.",
                ),
                self._aggregate_metric(
                    "mean_discovery_score",
                    tracks,
                    lambda placement: placement.score_breakdown.discovery_score,
                    "Mean stored discovery component points.",
                ),
                self._aggregate_metric(
                    "mean_constraint_penalty",
                    tracks,
                    lambda placement: placement.score_breakdown.constraint_penalty,
                    "Mean stored constraint-penalty points.",
                ),
                self._aggregate_metric(
                    "mean_narrative_drift_penalty",
                    tracks,
                    lambda placement: (
                        placement.score_breakdown.narrative_drift_penalty
                    ),
                    "Mean stored narrative-drift-penalty points.",
                ),
                self._aggregate_metric(
                    "mean_transition_score",
                    tracks[1:],
                    lambda placement: placement.score_breakdown.transition_score,
                    "Mean stored transition points; opening track excluded.",
                ),
                self._adjacent_delta_metric(
                    code="mean_absolute_energy_delta",
                    tracks=tracks,
                ),
                self._aggregate_metric(
                    "mean_lyrical_distraction",
                    tracks,
                    lambda placement: placement.candidate.lyrical_distraction,
                    (
                        "Mean supplied lyrical-distraction input; not vocal "
                        "salience."
                    ),
                    unit="input_value",
                    source=EvidenceSource.DIRECT_FACT,
                ),
            )
        )
        metrics.extend(
            self._unavailable_metric(code, explanation)
            for code, explanation in self._UNAVAILABLE_METRICS
        )
        return tuple(metrics)

    def _phase_diagnostics(
        self,
        tracks: tuple[PlacedTrack, ...],
        journey_plan: JourneyPlan,
    ) -> tuple[PhaseDiagnostic, ...]:
        diagnostics: list[PhaseDiagnostic] = []
        for index, phase in enumerate(journey_plan.phases):
            placements = tuple(
                placement
                for placement in tracks
                if placement.phase_index == index
            )
            score_sum = sum(
                placement.score_breakdown.phase_score
                for placement in placements
            )
            diagnostics.append(
                PhaseDiagnostic(
                    phase_index=index,
                    phase_name=phase.name,
                    planned_duration_ratio=self._rounded(
                        phase.duration_minutes / journey_plan.duration_minutes
                    ),
                    placed_track_count=len(placements),
                    placed_duration_seconds=sum(
                        placement.candidate.duration_seconds
                        for placement in placements
                    ),
                    phase_score_sum=self._rounded(score_sum),
                    phase_score_mean=self._rounded(score_sum / len(placements))
                    if placements
                    else None,
                    sample_count=len(placements),
                    evidence_positions=tuple(
                        placement.position for placement in placements
                    ),
                )
            )
        return tuple(diagnostics)

    def _issues(
        self,
        result: ConstructionResult,
        journey_plan: JourneyPlan,
        policy: ConstructionPolicy,
        discovery_positions: tuple[int, ...],
    ) -> tuple[EvaluationIssue, ...]:
        tracks = result.tracks
        summary = result.summary
        issues = self._consistency_issues(result, policy)
        issues.extend(
            EvaluationIssue(
                code=f"construction:{issue.code}",
                severity=(
                    EvaluationIssueSeverity.ERROR
                    if issue.severity is ConstructionIssueSeverity.HARD_UNMET
                    else EvaluationIssueSeverity.WARNING
                ),
                message=issue.message,
            )
            for issue in result.issues
        )
        if summary.status is not ConstructionStatus.COMPLETE:
            issues.append(
                EvaluationIssue(
                    code="partial_objective_coverage",
                    severity=EvaluationIssueSeverity.WARNING,
                    message=(
                        f"Observed {len(tracks)} of "
                        f"{summary.requested_track_count} requested tracks."
                    ),
                    evidence_positions=tuple(
                        placement.position for placement in tracks
                    ),
                )
            )
        for index, phase in enumerate(journey_plan.phases):
            if not any(
                placement.phase_index == index for placement in tracks
            ):
                issues.append(
                    EvaluationIssue(
                        code="planned_phase_unrepresented",
                        severity=EvaluationIssueSeverity.WARNING,
                        message=f"Planned phase {phase.name!r} has no placements.",
                        evidence_phases=(phase.name,),
                    )
                )
        if len(tracks) < 2:
            issues.append(
                EvaluationIssue(
                    code="insufficient_transition_sample",
                    severity=EvaluationIssueSeverity.INFO,
                    message=(
                        "At least two placed tracks are required for an "
                        "incoming-transition sample."
                    ),
                )
            )
        target_discovery_ratio = journey_plan.discovery_percent / 100.0
        observed_discovery_ratio = (
            len(discovery_positions) / len(tracks) if tracks else 0.0
        )
        if tracks and not self._same_number(
            observed_discovery_ratio,
            target_discovery_ratio,
        ):
            issues.append(
                EvaluationIssue(
                    code="discovery_target_missed",
                    severity=EvaluationIssueSeverity.WARNING,
                    message=(
                        f"Observed discovery ratio "
                        f"{observed_discovery_ratio:.4f} differs from target "
                        f"{target_discovery_ratio:.4f}."
                    ),
                    evidence_positions=discovery_positions,
                )
            )
        severe_positions = tuple(
            placement.position
            for placement in tracks[1:]
            if placement.score_breakdown.constraint_penalty > 0
        )
        if severe_positions:
            issues.append(
                EvaluationIssue(
                    code="transition_constraint_penalty_observed",
                    severity=EvaluationIssueSeverity.WARNING,
                    message=(
                        "One or more incoming transitions carry stored "
                        "constraint-penalty points."
                    ),
                    evidence_positions=severe_positions,
                )
            )
        issues.append(
            EvaluationIssue(
                code="metrics_unavailable",
                severity=EvaluationIssueSeverity.INFO,
                message=(
                    "Unsupported metrics are explicitly unavailable: "
                    + ", ".join(
                        code for code, _ in self._UNAVAILABLE_METRICS
                    )
                    + "."
                ),
            )
        )
        return tuple(issues)

    def _consistency_issues(
        self,
        result: ConstructionResult,
        policy: ConstructionPolicy,
    ) -> list[EvaluationIssue]:
        tracks = result.tracks
        summary = result.summary
        checks = (
            (
                summary.achieved_track_count == len(tracks),
                "summary_track_count_mismatch",
                "Summary achieved count does not match placed tracks.",
            ),
            (
                summary.total_duration_seconds
                == sum(
                    placement.candidate.duration_seconds
                    for placement in tracks
                ),
                "summary_duration_mismatch",
                "Summary duration does not match placed tracks.",
            ),
            (
                summary.discovery_count
                == sum(
                    placement.candidate.familiarity
                    <= policy.discovery_familiarity_threshold
                    for placement in tracks
                ),
                "summary_discovery_count_mismatch",
                "Summary discovery count does not match policy classification.",
            ),
            (
                summary.status is not ConstructionStatus.COMPLETE
                or summary.achieved_track_count
                == summary.requested_track_count,
                "summary_completion_status_mismatch",
                "Complete status does not satisfy the requested track count.",
            ),
            (
                [placement.position for placement in tracks]
                == list(range(1, len(tracks) + 1)),
                "placement_position_mismatch",
                "Placement positions are not sequential.",
            ),
        )
        return [
            EvaluationIssue(
                code=code,
                severity=EvaluationIssueSeverity.ERROR,
                message=message,
            )
            for passed, code, message in checks
            if not passed
        ]

    @staticmethod
    def _disposition(result: ConstructionResult) -> EvaluationDisposition:
        if not result.tracks:
            return EvaluationDisposition.INCONCLUSIVE
        if result.summary.status is ConstructionStatus.COMPLETE:
            return EvaluationDisposition.COMPLETE_EVALUATED
        return EvaluationDisposition.PARTIAL_EVALUATED

    @staticmethod
    def _artist_counts(tracks: tuple[PlacedTrack, ...]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for placement in tracks:
            key = placement.candidate.artist_name.casefold()
            counts[key] = counts.get(key, 0) + 1
        return counts

    def _aggregate_metric(
        self,
        code: str,
        tracks: Sequence[PlacedTrack],
        value: Callable[[PlacedTrack], float],
        explanation: str,
        *,
        unit: str = "raw_points",
        source: EvidenceSource = EvidenceSource.STORED_SCORE_AGGREGATION,
    ) -> EvaluationMetric:
        values = tuple(value(placement) for placement in tracks)
        if not values:
            return EvaluationMetric(
                code=code,
                applicability=MetricApplicability.NOT_APPLICABLE,
                unit=unit,
                denominator_description="applicable placements",
                sample_count=0,
                evidence_source=source,
                explanation=explanation,
            )
        total = sum(values)
        return EvaluationMetric(
            code=code,
            applicability=MetricApplicability.MEASURED,
            value=self._rounded(total / len(values)),
            unit=unit,
            numerator=self._rounded(total),
            denominator=float(len(values)),
            denominator_description="applicable placements",
            sample_count=len(values),
            evidence_source=source,
            explanation=explanation,
            evidence_positions=tuple(
                placement.position for placement in tracks
            ),
        )

    def _adjacent_delta_metric(
        self,
        *,
        code: str,
        tracks: tuple[PlacedTrack, ...],
    ) -> EvaluationMetric:
        if len(tracks) < 2:
            return EvaluationMetric(
                code=code,
                applicability=MetricApplicability.NOT_APPLICABLE,
                unit="input_value",
                denominator_description="adjacent transitions",
                sample_count=0,
                evidence_source=EvidenceSource.DIRECT_FACT,
                explanation=(
                    "Mean absolute adjacent energy-input delta; no contour claim."
                ),
            )
        deltas = tuple(
            abs(
                current.candidate.energy
                - previous.candidate.energy
            )
            for previous, current in zip(tracks, tracks[1:])
        )
        return EvaluationMetric(
            code=code,
            applicability=MetricApplicability.MEASURED,
            value=self._rounded(sum(deltas) / len(deltas)),
            unit="input_value",
            numerator=self._rounded(sum(deltas)),
            denominator=float(len(deltas)),
            denominator_description="adjacent transitions",
            sample_count=len(deltas),
            evidence_source=EvidenceSource.DIRECT_FACT,
            explanation=(
                "Mean absolute adjacent energy-input delta; no contour claim."
            ),
            evidence_positions=tuple(
                placement.position for placement in tracks[1:]
            ),
        )

    def _discovery_ratio_metrics(
        self,
        *,
        tracks: tuple[PlacedTrack, ...],
        discovery_count: int,
        target_ratio: float,
        threshold: float,
    ) -> tuple[EvaluationMetric, EvaluationMetric]:
        positions = tuple(
            placement.position
            for placement in tracks
            if placement.candidate.familiarity <= threshold
        )
        if not tracks:
            return (
                EvaluationMetric(
                    code="discovery_ratio",
                    applicability=MetricApplicability.NOT_APPLICABLE,
                    unit="ratio",
                    denominator_description="placed tracks",
                    sample_count=0,
                    target=target_ratio,
                    evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                    explanation=(
                        "Discovery ratio requires at least one placed track."
                    ),
                ),
                EvaluationMetric(
                    code="discovery_ratio_deviation",
                    applicability=MetricApplicability.NOT_APPLICABLE,
                    unit="ratio_points",
                    denominator_description="placed tracks",
                    sample_count=0,
                    target=0.0,
                    evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                    explanation=(
                        "Discovery-ratio deviation requires at least one "
                        "placed track."
                    ),
                ),
            )
        observed_ratio = discovery_count / len(tracks)
        return (
            EvaluationMetric(
                code="discovery_ratio",
                applicability=MetricApplicability.MEASURED,
                value=self._rounded(observed_ratio),
                unit="ratio",
                numerator=float(discovery_count),
                denominator=float(len(tracks)),
                denominator_description="placed tracks",
                sample_count=len(tracks),
                target=target_ratio,
                evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                explanation=(
                    "Observed discovery share compared with the journey target."
                ),
                evidence_positions=positions,
            ),
            EvaluationMetric(
                code="discovery_ratio_deviation",
                applicability=MetricApplicability.MEASURED,
                value=self._rounded(observed_ratio - target_ratio),
                unit="ratio_points",
                numerator=float(discovery_count),
                denominator=float(len(tracks)),
                denominator_description="placed tracks",
                sample_count=len(tracks),
                target=0.0,
                evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
                explanation="Signed observed discovery ratio minus target ratio.",
                evidence_positions=positions,
            ),
        )

    @staticmethod
    def _direct_metric(
        *,
        code: str,
        value: int | float,
        unit: str,
        sample_count: int,
        denominator_description: str,
        explanation: str,
        positions: tuple[int, ...] = (),
    ) -> EvaluationMetric:
        return EvaluationMetric(
            code=code,
            applicability=MetricApplicability.MEASURED,
            value=float(value),
            unit=unit,
            numerator=float(value),
            denominator=None,
            denominator_description=denominator_description,
            sample_count=sample_count,
            evidence_source=EvidenceSource.DIRECT_FACT,
            explanation=explanation,
            evidence_positions=positions,
        )

    @staticmethod
    def _boolean_metric(
        *,
        code: str,
        passed: bool,
        numerator: int,
        denominator: int,
        denominator_description: str,
        explanation: str,
        positions: tuple[int, ...],
    ) -> EvaluationMetric:
        return EvaluationMetric(
            code=code,
            applicability=MetricApplicability.MEASURED,
            value=1.0 if passed else 0.0,
            unit="boolean",
            numerator=float(numerator),
            denominator=float(denominator),
            denominator_description=denominator_description,
            sample_count=len(positions),
            target=1.0,
            evidence_source=EvidenceSource.OBJECTIVE_COMPARISON,
            explanation=explanation,
            evidence_positions=positions,
        )

    @staticmethod
    def _unavailable_metric(
        code: str,
        explanation: str,
    ) -> EvaluationMetric:
        return EvaluationMetric(
            code=code,
            applicability=MetricApplicability.UNAVAILABLE,
            unit="unavailable",
            denominator_description="unsupported by current evidence",
            sample_count=0,
            evidence_source=EvidenceSource.UNSUPPORTED,
            explanation=explanation,
        )

    @staticmethod
    def _rounded(value: float) -> float:
        return round(value, 4)

    @staticmethod
    def _same_number(left: float, right: float) -> bool:
        return abs(left - right) <= 1e-9

"""Independent observation of Result/2.0; no pool search or constructor calls."""
from __future__ import annotations

import hashlib
from collections import Counter
from typing import Literal

from pydantic import model_validator

from playlist_narrative_engine.evaluation.evaluator import PlaylistJourneyEvaluator
from playlist_narrative_engine.evaluation.schemas import (
    EvaluationDisposition, EvaluationInputBinding, EvaluationIssue,
    EvaluationIssueSeverity, EvaluationMetric, EvidenceSource, MetricApplicability,
    PhaseDiagnostic, RolePositions, SeriesPoint,
)
from playlist_narrative_engine.journey import serialize_journey_plan_artifact
from playlist_narrative_engine.sequencing.constructor import ConstructionIssue, ConstructionStatus
from playlist_narrative_engine.sequencing.schemas import TrackRole
from playlist_narrative_engine.sequencing.successor import verify_target_journey
from playlist_narrative_engine.sequencing.successor_canonical import (
    canonical_model_bytes, construction_prefix_sha256, parse_canonical_model,
    serialize_successor, successor_sha256,
)
from playlist_narrative_engine.sequencing.successor_schemas import (
    ArtistCount, ClosedModel, ConstructionResultV2, CountTarget, Digest,
    DiscoveryFacts, HardTargetFacts, JourneyTarget,
)


class EvaluationReportV3(ClosedModel):
    schema_version: Literal["3.0"] = "3.0"
    input_binding: EvaluationInputBinding
    target_sha256: Digest
    disposition: EvaluationDisposition
    construction_status: ConstructionStatus
    hard_targets: HardTargetFacts
    discovery: DiscoveryFacts
    certificate_verification: Literal["BOUND_CONSTRUCTOR_EVIDENCE_NOT_POOL_RECOMPUTED"] = "BOUND_CONSTRUCTOR_EVIDENCE_NOT_POOL_RECOMPUTED"
    construction_issues: tuple[ConstructionIssue, ...]
    metrics: tuple[EvaluationMetric, ...]
    phase_diagnostics: tuple[PhaseDiagnostic, ...]
    transition_series: tuple[SeriesPoint, ...]
    energy_series: tuple[SeriesPoint, ...]
    lyrical_distraction_series: tuple[SeriesPoint, ...]
    discovery_positions: tuple[int, ...]
    role_positions: tuple[RolePositions, ...]
    issues: tuple[EvaluationIssue, ...]

    @model_validator(mode="after")
    def explicit_family_binding(self):
        binding = self.input_binding
        if (binding.construction_result_schema_version, binding.journey_schema_version,
                binding.construction_policy_schema_version) != ("2.0", "2.0", "2.0"):
            raise ValueError("report 3.0 must bind the exact successor family")
        return self


def serialize_evaluation_report_v3(report):
    if type(report) is not EvaluationReportV3:
        raise TypeError("evaluation report 3.0 required")
    return canonical_model_bytes(report)


def evaluation_report_v3_sha256(report):
    return hashlib.sha256(serialize_evaluation_report_v3(report)).hexdigest()


def parse_evaluation_report_v3(data):
    return parse_canonical_model(data, EvaluationReportV3)


def evaluation_report_v3_matches_inputs(report, *, construction_result, journey_plan, construction_policy):
    try:
        reconstructed = PlaylistJourneyEvaluatorV3().evaluate(construction_result=construction_result,
            journey_plan=journey_plan, construction_policy=construction_policy)
        return serialize_evaluation_report_v3(report) == serialize_evaluation_report_v3(reconstructed)
    except (ValueError, TypeError):
        return False


def _positional_phase(plan, index, horizon):
    midpoint = (index + 0.5) / horizon
    cumulative = 0.0
    for phase_index, phase in enumerate(plan.phases):
        cumulative += phase.duration_minutes / plan.duration_minutes
        if midpoint <= cumulative:
            return phase_index
    return len(plan.phases) - 1


def _check_bound(bound, target, horizon, plan):
    if bound.prefix_count + bound.remaining_slots > horizon:
        raise ValueError("bound exceeds original horizon")
    if bound.attainable_phase_indices != tuple(sorted(set(bound.attainable_phase_indices))):
        raise ValueError("noncanonical phase evidence")
    if any(i >= len(plan.phases) for i in bound.attainable_phase_indices):
        raise ValueError("unknown phase in certificate")
    failures = []
    if bound.maximum_additional_seconds is None:
        failures.append("candidate_pool_exhausted")
    if isinstance(target.requirement, JourneyTarget):
        if (bound.maximum_additional_seconds is None
                or bound.prefix_duration_seconds + bound.maximum_additional_seconds < target.requirement.minimum_duration_seconds):
            failures.append("duration_target_missed")
        if not set(target.requirement.required_phase_indices) <= set(bound.attainable_phase_indices):
            failures.append("required_phase_unrepresented")
    if tuple(failures) != bound.failures:
        raise ValueError("certificate arithmetic/failure mismatch")


def _correspondence(result, journey, policy):
    if type(result) is not ConstructionResultV2:
        raise TypeError("result 2.0 required; historical artifacts cannot be relabeled")
    serialize_successor(result)
    target = result.target
    verify_target_journey(target, journey, policy)
    binding, cert, trace = result.input_binding, result.feasibility, result.formation_trace
    journey_hash = hashlib.sha256(serialize_journey_plan_artifact(journey)).hexdigest()
    if (binding.journey_id != journey.journey_id or binding.journey_artifact_sha256 != journey_hash
            or binding.construction_policy_sha256 != successor_sha256(policy)
            or binding.target_sha256 != successor_sha256(target)
            or binding.formation_parent_sha256 != target.formation_parent_sha256
            or binding.formation_parent_schema_version != target.formation_parent_schema_version
            or binding.formation_parent_sha256 != trace.parent_artifact_sha256
            or binding.formation_parent_schema_version != trace.parent_schema_version
            or binding.formation_request_id != trace.parent_request_id
            or trace.journey_id != journey.journey_id
            or trace.objective_id != journey.objective.objective_id
            or trace.objective_statement != journey.objective.statement
            or trace.accepted_objective_artifact_id != journey.objective_safety_artifact_id
            or cert.target_sha256 != binding.target_sha256
            or cert.formed_pool_sha256 != binding.formed_pool_sha256
            or cert.construction_policy_sha256 != binding.construction_policy_sha256):
        raise ValueError("result authority/certificate correspondence mismatch")
    ids = binding.ordered_track_ids
    if ids != tuple(sorted(set(ids), key=lambda x: x.encode("utf-8"))):
        raise ValueError("input order must be unique canonical CF-3 order")
    if binding.initial_placement_count > len(result.tracks):
        raise ValueError("initial prefix exceeds result")
    if binding.initial_state_sha256 != construction_prefix_sha256(target, cert,
            result.tracks[:binding.initial_placement_count], result.decisions):
        raise ValueError("initial prefix binding does not reproduce")
    trials = cert.horizon_trials
    if isinstance(target.requirement, CountTarget):
        if cert.planning_horizon != target.requirement.requested_track_count or len(trials) != 1:
            raise ValueError("count horizon changed")
        expected_horizons = (target.requirement.requested_track_count,)
    else:
        if cert.outcome == "INFEASIBLE" and cert.planning_horizon is not None:
            raise ValueError("infeasible journey has no certified horizon")
        last = cert.planning_horizon if cert.outcome == "FEASIBLE" else cert.initial_capped_capacity
        expected_horizons = tuple(range(1, last + 1))
    if tuple(t.horizon for t in trials) != expected_horizons:
        raise ValueError("missing/reordered horizon evidence")
    if cert.initial_capped_capacity > len(ids):
        raise ValueError("certificate capacity exceeds original pool size")
    capacities = cert.artist_capacities
    if (tuple(c.artist_name for c in capacities) != tuple(sorted({c.artist_name for c in capacities}))
            or sum(c.available_count for c in capacities) != len(ids)
            or sum(c.capped_count for c in capacities) != cert.initial_capped_capacity):
        raise ValueError("artist capacity certificate does not reconcile")
    for c in capacities:
        if (c.capped_count != min(c.available_count, policy.max_tracks_per_artist)
                or c.limiting_code != ("artist_repetition_limit" if c.available_count > policy.max_tracks_per_artist else None)):
            raise ValueError("artist capacity/cause arithmetic mismatch")
    for trial in trials:
        bound = trial.bound
        if (bound.prefix_count != 0 or bound.prefix_duration_seconds != 0
                or bound.remaining_slots != trial.horizon
                or bound.remaining_capped_capacity != cert.initial_capped_capacity
                or bound.attainable_phase_indices != tuple(sorted({_positional_phase(journey.plan, i, trial.horizon) for i in range(trial.horizon)}))):
            raise ValueError("initial certificate is not initial/horizon-scoped")
        _check_bound(bound, target, trial.horizon, journey.plan)


class PlaylistJourneyEvaluatorV3:
    """Reconstructs achieved facts, never asks construction to judge its output."""

    def evaluate(self, *, construction_result, journey_plan, construction_policy):
        result, journey, policy = construction_result, journey_plan, construction_policy
        _correspondence(result, journey, policy)
        target, tracks, cert = result.target, result.tracks, result.feasibility
        k = cert.planning_horizon
        if tracks and (k is None or cert.outcome != "FEASIBLE" or len(tracks) > k):
            raise ValueError("placements lack a feasible original horizon")
        ids = [p.candidate.track_id for p in tracks]
        if len(set(ids)) != len(ids) or not set(ids) <= set(result.input_binding.ordered_track_ids):
            raise ValueError("placements not distinct bound formed identities")
        prior_phase = 0
        for index, placed in enumerate(tracks):
            phase = _positional_phase(journey.plan, index, k)
            role = (TrackRole.OPENING_ANCHOR if index == 0 else TrackRole.CLOSING_TRACK if index == k - 1
                    else TrackRole.PHASE_TRANSITION if phase != prior_phase else TrackRole.JOURNEY)
            if (placed.position != index + 1 or placed.phase_index != phase
                    or placed.phase_name != journey.plan.phases[phase].name or placed.role != role
                    or placed.score_breakdown.role != role
                    or placed.post_selection_validation != "FORMED_HARD_ELIGIBILITY_CONFIRMED"
                    or placed.refinement_action != "NONE"):
                raise ValueError("invalid placement position, phase, role, or formed-validity claim")
            prior_phase = phase
        duration = sum(p.candidate.duration_seconds for p in tracks)
        counts = Counter(p.candidate.artist_name for p in tracks)
        cap_ok = all(n <= policy.max_tracks_per_artist for n in counts.values())
        if not cap_ok:
            raise ValueError("artist cap violated")
        phases = tuple(sorted({p.phase_index for p in tracks}))
        missing = tuple(i for i in range(len(journey.plan.phases)) if i not in phases)
        count_mode = isinstance(target.requirement, CountTarget)
        count_outcome = ("MET" if len(tracks) == target.requirement.requested_track_count else "MISSED") if count_mode else "NOT_APPLICABLE"
        duration_outcome = "NOT_APPLICABLE" if count_mode else ("MET" if duration >= target.requirement.minimum_duration_seconds else "MISSED")
        phase_outcome = "NOT_APPLICABLE" if count_mode else ("MISSED" if missing else "MET")
        hard_met = count_outcome == "MET" if count_mode else duration_outcome == phase_outcome == "MET"
        hard = HardTargetFacts(achieved_count=len(tracks), achieved_duration_seconds=duration,
            count_outcome=count_outcome, duration_outcome=duration_outcome, phase_requirement_outcome=phase_outcome,
            represented_phase_indices=phases, unrepresented_phase_indices=missing,
            artist_counts=tuple(ArtistCount(artist_name=a, count=n) for a, n in sorted(counts.items())),
            artist_cap_satisfied=cap_ok, hard_target_satisfied=hard_met)
        expected_status = ConstructionStatus.COMPLETE if hard_met else ConstructionStatus.PARTIAL if tracks else ConstructionStatus.INFEASIBLE
        if result.hard_targets != hard or result.status != expected_status:
            raise ValueError("claimed hard outcome/status disagrees with independent reconstruction")
        if hard_met:
            if result.stopping_reason != "HARD_TARGET_MET":
                raise ValueError("complete result requires hard stopping fact")
            if not count_mode and any(
                sum(p.candidate.duration_seconds for p in tracks[:n]) >= target.requirement.minimum_duration_seconds
                and set(target.requirement.required_phase_indices) <= {p.phase_index for p in tracks[:n]}
                for n in range(1, len(tracks))):
                raise ValueError("construction continued after hard completion")
        elif tracks:
            if result.stopping_reason not in ("no_eligible_candidates", "candidate_pool_exhausted"):
                raise ValueError("partial result must report residual stopping")
        elif cert.outcome != "INFEASIBLE" or result.stopping_reason != "global_infeasible":
            raise ValueError("empty infeasible result needs initial impossibility certificate")
        residual = result.residual_feasibility
        if (k is None) != (residual is None):
            raise ValueError("residual evidence applicability mismatch")
        if residual is not None:
            _check_bound(residual, target, k, journey.plan)
            slots = 0 if hard_met else k - len(tracks)
            attainable = tuple(sorted(set(phases) | {_positional_phase(journey.plan, i, k) for i in range(len(tracks), len(tracks) + slots)}))
            if (residual.prefix_count != len(tracks) or residual.prefix_duration_seconds != duration
                    or residual.remaining_slots != slots or residual.attainable_phase_indices != attainable
                    or residual.remaining_capped_capacity != cert.initial_capped_capacity - len(tracks)):
                raise ValueError("residual certificate does not bind achieved prefix")
        selected = tuple(d for d in result.decisions if d.outcome == "SELECTED")
        if len(selected) != len(tracks):
            raise ValueError("one selection certificate per placement required")
        for d, p in zip(selected, tracks):
            if (d.position != p.position or d.track_id != p.candidate.track_id
                    or d.selector_rank != p.selector_rank
                    or d.residual.prefix_count != p.position
                    or d.residual.prefix_duration_seconds != sum(t.candidate.duration_seconds for t in tracks[:p.position])):
                raise ValueError("decision certificate/placement mismatch")
            prefix = tracks[:p.position]
            prefix_met = (p.position == target.requirement.requested_track_count if count_mode else
                sum(t.candidate.duration_seconds for t in prefix) >= target.requirement.minimum_duration_seconds
                and set(target.requirement.required_phase_indices) <= {t.phase_index for t in prefix})
            slots = 0 if prefix_met else k - p.position
            attainable = tuple(sorted({t.phase_index for t in prefix} | {_positional_phase(journey.plan, i, k) for i in range(p.position, p.position + slots)}))
            if d.residual.remaining_slots != slots or d.residual.attainable_phase_indices != attainable:
                raise ValueError("selected decision changed original horizon/phase applicability")
        next_position, next_rank = 1, 1
        rejections = []
        for d in result.decisions:
            if (d.track_id not in result.input_binding.ordered_track_ids or d.position > len(tracks) + (not hard_met)
                    or d.position != next_position or d.selector_rank != next_rank):
                raise ValueError("decision outside bound pool/prefix")
            if d.track_id in {p.candidate.track_id for p in tracks[:d.position - 1]}:
                raise ValueError("decision reused an already placed identity")
            if d.residual is not None:
                _check_bound(d.residual, target, k, journey.plan)
                if (d.residual.prefix_count != d.position
                        or d.residual.remaining_capped_capacity != cert.initial_capped_capacity - d.position):
                    raise ValueError("decision capacity is not residual to original artist partition")
            if d.outcome == "SELECTED":
                p = tracks[d.position - 1]
                if [(r.track_id, r.selector_rank, r.code) for r in p.rejected_candidates] != rejections:
                    raise ValueError("placement rejection transcript changed")
                next_position += 1
                next_rank = 1
                rejections = []
            else:
                rejections.append((d.track_id, d.selector_rank, d.outcome))
                next_rank += 1
        percent = journey.plan.discovery_percent
        discovery_positions = tuple(p.position for p in tracks if p.candidate.familiarity <= policy.discovery_familiarity_threshold)
        achieved = len(discovery_positions)
        stored = result.discovery
        reasons = []
        numerator = None if k is None else percent * k
        if k is not None:
            if numerator % 100:
                reasons.append("NONINTEGRAL_COUNT")
            else:
                if k - numerator // 100 > stored.familiar_capped_capacity:
                    reasons.append("FAMILIAR_CAPACITY")
                if numerator // 100 > stored.discovery_capped_capacity:
                    reasons.append("DISCOVERY_CAPACITY")
        if (stored.familiar_capped_capacity > cert.initial_capped_capacity
                or stored.discovery_capped_capacity > cert.initial_capped_capacity
                or not cert.initial_capped_capacity <= stored.familiar_capped_capacity + stored.discovery_capped_capacity <= len(result.input_binding.ordered_track_ids)
                or stored.familiar_capped_capacity < len(tracks) - achieved
                or stored.discovery_capped_capacity < achieved):
            raise ValueError("category certificate incompatible with pool/achieved evidence")
        discovery = DiscoveryFacts(requested_percent=percent, requested_ratio=percent / 100.0,
            planning_horizon=k, rounded_ranking_target_count=None if k is None else (percent * k + 50) // 100,
            achieved_count=achieved, achieved_denominator=len(tracks), achieved_ratio=achieved / len(tracks) if tracks else None,
            exact_target_outcome=("MET" if 100 * achieved == percent * len(tracks) else "MISSED") if tracks else "NOT_APPLICABLE",
            structural_outcome=("STRUCTURALLY_INFEASIBLE" if reasons else "NOT_ESTABLISHED") if k is not None else "NOT_APPLICABLE",
            structural_reasons=tuple(reasons), horizon_target_numerator=numerator,
            familiar_capped_capacity=stored.familiar_capped_capacity, discovery_capped_capacity=stored.discovery_capped_capacity)
        if discovery != stored:
            raise ValueError("discovery facts disagree with exact reconstruction")
        required = []
        if result.stopping_reason != "HARD_TARGET_MET":
            required.append((result.stopping_reason, "hard_unmet"))
        if duration_outcome == "MISSED":
            required.append(("duration_target_missed", "hard_unmet"))
        if phase_outcome == "MISSED":
            required.extend(("required_phase_unrepresented", "hard_unmet") for _ in missing)
        if reasons:
            required.append(("discovery_target_structurally_infeasible", "soft_compromise"))
        if discovery.exact_target_outcome == "MISSED":
            required.append(("discovery_target_missed", "soft_compromise"))
        if [(i.code, i.severity.value) for i in result.issues] != required:
            raise ValueError("missing, reordered, or spurious construction compromises/issues")
        phase_issues = iter(missing)
        for issue in result.issues:
            values = {
                "global_infeasible": (None, None),
                "no_eligible_candidates": (len(tracks), target.requirement.requested_track_count if count_mode else None),
                "candidate_pool_exhausted": (len(tracks), target.requirement.requested_track_count if count_mode else None),
                "duration_target_missed": (duration, target.requirement.minimum_duration_seconds if not count_mode else None),
                "discovery_target_structurally_infeasible": (discovery.familiar_capped_capacity, k),
                "discovery_target_missed": (discovery.achieved_ratio, discovery.requested_ratio),
            }
            expected = (0, next(phase_issues)) if issue.code == "required_phase_unrepresented" else values[issue.code]
            if (issue.observed_value, issue.requested_value) != expected:
                raise ValueError("construction issue arithmetic contradicts reconstructed facts")
        observer = PlaylistJourneyEvaluator()
        # Stored components are measurements, not fresh scoring authority.
        metrics = tuple(EvaluationMetric(code=f"mean_stored_{name}",
            applicability=MetricApplicability.MEASURED if tracks else MetricApplicability.NOT_APPLICABLE,
            value=sum(getattr(p.score_breakdown, name) for p in tracks) / len(tracks) if tracks else None,
            unit="score", denominator_description="placed tracks", sample_count=len(tracks),
            evidence_source=EvidenceSource.STORED_SCORE_AGGREGATION,
            explanation="Arithmetic mean of persisted components; not rescored", evidence_positions=tuple(p.position for p in tracks))
            for name in ("preference_score", "context_score", "phase_score", "transition_score", "discovery_score", "total_score"))
        issues = [EvaluationIssue(code=f"construction:{i.code}",
            severity=EvaluationIssueSeverity.ERROR if i.severity.value == "hard_unmet" else EvaluationIssueSeverity.WARNING,
            message=i.message) for i in result.issues]
        issues.extend(EvaluationIssue(code="planned_phase_unrepresented", severity=EvaluationIssueSeverity.WARNING,
            message="Planned phase has no placement; applicability is recorded in hard-target facts",
            evidence_phases=(journey.plan.phases[i].name,)) for i in missing)
        report = EvaluationReportV3(
            input_binding=EvaluationInputBinding(construction_result_schema_version="2.0", construction_result_sha256=successor_sha256(result),
                journey_id=journey.journey_id, journey_schema_version="2.0",
                journey_artifact_sha256=result.input_binding.journey_artifact_sha256,
                construction_policy_schema_version="2.0", construction_policy_sha256=successor_sha256(policy)),
            target_sha256=successor_sha256(target),
            disposition=EvaluationDisposition.COMPLETE_EVALUATED if hard_met else EvaluationDisposition.PARTIAL_EVALUATED if tracks else EvaluationDisposition.INCONCLUSIVE,
            construction_status=result.status, hard_targets=hard, discovery=discovery, construction_issues=result.issues,
            metrics=metrics, phase_diagnostics=observer._phase_diagnostics(tracks, journey.plan),
            transition_series=tuple(SeriesPoint(position=p.position, value=p.score_breakdown.transition_score) for p in tracks[1:]),
            energy_series=tuple(SeriesPoint(position=p.position, value=p.candidate.energy) for p in tracks),
            lyrical_distraction_series=tuple(SeriesPoint(position=p.position, value=p.candidate.lyrical_distraction) for p in tracks),
            discovery_positions=discovery_positions,
            role_positions=tuple(RolePositions(role=role, positions=tuple(p.position for p in tracks if p.role == role)) for role in TrackRole),
            issues=tuple(issues))
        serialize_evaluation_report_v3(report)
        return report

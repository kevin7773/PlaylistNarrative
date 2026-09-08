"""Governed target construction with an exact partition-capacity guard.

Only this module orchestrates selection. No evaluator participates in decisions.
The CF-3 parent is re-derived through its existing public boundary, not replaced
with caller-provided raw candidates or a reconstructed pool view.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass

from playlist_narrative_engine.candidate_formation.formation_schemas import CandidateFormationArtifact
from playlist_narrative_engine.candidate_formation.integration import (
    derive_formed_candidate_pool, serialize_formed_candidate_pool,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact, serialize_journey_plan_artifact
from playlist_narrative_engine.sequencing.constructor import (
    CandidateRejection, ConstructionIssue, ConstructionIssueSeverity,
    ConstructionState, ConstructionStatus, PlacedTrack, SequentialPlaylistConstructor,
)
from playlist_narrative_engine.sequencing.selector import CandidateSelector
from playlist_narrative_engine.sequencing.schemas import TrackCandidate
from playlist_narrative_engine.sequencing.successor_canonical import (
    construction_prefix_sha256, serialize_successor, successor_sha256,
)
from playlist_narrative_engine.sequencing.successor_schemas import (
    ArtistCapacity, ArtistCount, ConstructionInputBindingV2, ConstructionPolicyV2, ConstructionResultV2,
    ConstructionTargetArtifact, CountTarget, DecisionFact, DiscoveryFacts,
    FeasibilityCertificate, HardTargetFacts, HorizonTrial, JourneyTarget,
    ResidualFeasibilityFact,
)


@dataclass(frozen=True)
class _BoundPlacement:
    candidate: TrackCandidate
    phase_index: int


def _journey_hash(journey):
    return hashlib.sha256(serialize_journey_plan_artifact(journey)).hexdigest()


def _inputs(journey, formation):
    if type(journey) is not JourneyPlanArtifact or type(formation) is not CandidateFormationArtifact:
        raise TypeError("versioned journey and formation parent required")
    validated = JourneyPlanArtifact.model_validate(journey.model_dump(mode="json"))
    if validated != journey:
        raise ValueError("journey requires normalization")
    pool = derive_formed_candidate_pool(formation)
    trace = pool.trace
    if (journey.journey_id != trace.journey_id
            or journey.objective.objective_id != trace.objective_id
            or journey.objective.statement != trace.objective_statement
            or journey.objective_safety_artifact_id != trace.accepted_objective_artifact_id):
        raise ValueError("journey must exactly correspond to CF-3 formation trace")
    return pool


def create_construction_target(*, journey_plan, formation_parent, policy,
                               mode, requested_track_count=None):
    if type(policy) is not ConstructionPolicyV2:
        raise TypeError("policy 2.0 required")
    pool = _inputs(journey_plan, formation_parent)
    if mode == "TRACK_COUNT":
        requirement = CountTarget(requested_track_count=requested_track_count)
    elif mode == "JOURNEY" and requested_track_count is None:
        requirement = JourneyTarget(
            minimum_duration_seconds=60 * journey_plan.plan.duration_minutes,
            required_phase_indices=tuple(range(len(journey_plan.plan.phases))))
    else:
        raise ValueError("unsupported or conflicting hard target")
    return ConstructionTargetArtifact(
        journey_id=journey_plan.journey_id,
        journey_artifact_sha256=_journey_hash(journey_plan),
        journey_context=journey_plan.plan.context,
        formation_parent_schema_version=pool.trace.parent_schema_version,
        formation_parent_sha256=pool.trace.parent_artifact_sha256,
        construction_policy_sha256=successor_sha256(policy), requirement=requirement)


def verify_target_journey(target, journey, policy):
    """Shared correspondence check, not an achieved-output assessment."""
    if type(target) is not ConstructionTargetArtifact or type(policy) is not ConstructionPolicyV2:
        raise TypeError("explicit successor target/policy required")
    serialize_successor(target)
    if type(journey) is not JourneyPlanArtifact:
        raise TypeError("journey 2.0 required")
    JourneyPlanArtifact.model_validate(journey.model_dump(mode="json"))
    if (target.journey_id != journey.journey_id
            or target.journey_artifact_sha256 != _journey_hash(journey)
            or target.journey_context != journey.plan.context
            or target.construction_policy_sha256 != successor_sha256(policy)):
        raise ValueError("target/journey/policy correspondence mismatch")
    if isinstance(target.requirement, JourneyTarget):
        if (target.requirement.minimum_duration_seconds != 60 * journey.plan.duration_minutes
                or target.requirement.required_phase_indices != tuple(range(len(journey.plan.phases)))):
            raise ValueError("journey hard requirements must be exact derivations")


def _retained(candidates, tracks, cap):
    used = {p.candidate.track_id for p in tracks}
    counts = Counter(p.candidate.artist_name for p in tracks)
    groups = {}
    for candidate in candidates:
        if candidate.track_id not in used:
            groups.setdefault(candidate.artist_name, []).append(candidate)
    retained = []
    for artist in sorted(groups, key=lambda x: x.encode("utf-8")):
        ordered = sorted(groups[artist], key=lambda c: (-c.duration_seconds, c.track_id.encode("utf-8")))
        retained.extend(ordered[:max(0, cap - counts[artist])])
    return tuple(sorted(retained, key=lambda c: (-c.duration_seconds, c.track_id.encode("utf-8"))))


def _phase(journey, position, horizon):
    return SequentialPlaylistConstructor._phase_index_for_position(journey.plan, position, horizon)


def _complete(target, tracks):
    if isinstance(target.requirement, CountTarget):
        return len(tracks) == target.requirement.requested_track_count
    return (sum(p.candidate.duration_seconds for p in tracks) >= target.requirement.minimum_duration_seconds
            and set(target.requirement.required_phase_indices) <= {p.phase_index for p in tracks})


def _bound(target, journey, policy, candidates, tracks, horizon):
    # Once all hard targets hold, no unused-slot guarantee is required.
    slots = 0 if _complete(target, tracks) else horizon - len(tracks)
    retained = _retained(candidates, tracks, policy.max_tracks_per_artist)
    maximum = sum(c.duration_seconds for c in retained[:slots]) if len(retained) >= slots else None
    duration = sum(p.candidate.duration_seconds for p in tracks)
    phases = {p.phase_index for p in tracks}
    phases.update(_phase(journey, i, horizon) for i in range(len(tracks), len(tracks) + slots))
    failures = []
    if maximum is None:
        failures.append("candidate_pool_exhausted")
    if isinstance(target.requirement, JourneyTarget):
        if maximum is None or duration + maximum < target.requirement.minimum_duration_seconds:
            failures.append("duration_target_missed")
        if not set(target.requirement.required_phase_indices) <= phases:
            failures.append("required_phase_unrepresented")
    return ResidualFeasibilityFact(
        prefix_count=len(tracks), prefix_duration_seconds=duration, remaining_slots=slots,
        remaining_capped_capacity=len(retained), maximum_additional_seconds=maximum,
        attainable_phase_indices=tuple(sorted(phases)), failures=tuple(failures))


def _certificate(target, journey, policy, pool):
    capacity = len(_retained(pool.candidates, (), policy.max_tracks_per_artist))
    count_mode = isinstance(target.requirement, CountTarget)
    horizons = (target.requirement.requested_track_count,) if count_mode else range(1, capacity + 1)
    trials = []
    chosen = None
    for k in horizons:
        bound = _bound(target, journey, policy, pool.candidates, (), k)
        trials.append(HorizonTrial(horizon=k, bound=bound))
        if not bound.failures:
            chosen = k
            break
    return FeasibilityCertificate(
        target_sha256=successor_sha256(target),
        formed_pool_sha256=hashlib.sha256(serialize_formed_candidate_pool(pool)).hexdigest(),
        construction_policy_sha256=successor_sha256(policy),
        outcome="FEASIBLE" if chosen else "INFEASIBLE",
        planning_horizon=chosen if not count_mode else target.requirement.requested_track_count,
        initial_capped_capacity=capacity,
        artist_capacities=tuple(ArtistCapacity(artist_name=a, available_count=n,
            capped_count=min(n, policy.max_tracks_per_artist),
            limiting_code="artist_repetition_limit" if n > policy.max_tracks_per_artist else None)
            for a, n in sorted(Counter(c.artist_name for c in pool.candidates).items())),
        horizon_trials=tuple(trials))


def _hard_facts(target, journey, policy, tracks):
    duration = sum(p.candidate.duration_seconds for p in tracks)
    phases = tuple(sorted({p.phase_index for p in tracks}))
    missing = tuple(i for i in range(len(journey.plan.phases)) if i not in phases)
    counts = Counter(p.candidate.artist_name for p in tracks)
    cap_ok = all(n <= policy.max_tracks_per_artist for n in counts.values())
    is_count = isinstance(target.requirement, CountTarget)
    return HardTargetFacts(
        achieved_count=len(tracks), achieved_duration_seconds=duration,
        count_outcome=("MET" if _complete(target, tracks) else "MISSED") if is_count else "NOT_APPLICABLE",
        duration_outcome="NOT_APPLICABLE" if is_count else ("MET" if duration >= target.requirement.minimum_duration_seconds else "MISSED"),
        phase_requirement_outcome="NOT_APPLICABLE" if is_count else ("MISSED" if missing else "MET"),
        represented_phase_indices=phases, unrepresented_phase_indices=missing,
        artist_counts=tuple(ArtistCount(artist_name=a, count=n) for a, n in sorted(counts.items())),
        artist_cap_satisfied=cap_ok, hard_target_satisfied=cap_ok and _complete(target, tracks))


def _discovery(journey, policy, candidates, tracks, horizon):
    percent = journey.plan.discovery_percent
    familiar = tuple(c for c in candidates if c.familiarity > policy.discovery_familiarity_threshold)
    discovery = tuple(c for c in candidates if c.familiarity <= policy.discovery_familiarity_threshold)
    familiar_capacity = len(_retained(familiar, (), policy.max_tracks_per_artist))
    discovery_capacity = len(_retained(discovery, (), policy.max_tracks_per_artist))
    reasons = []
    numerator = None if horizon is None else percent * horizon
    if horizon is not None:
        if numerator % 100:
            reasons.append("NONINTEGRAL_COUNT")
        else:
            if horizon - numerator // 100 > familiar_capacity:
                reasons.append("FAMILIAR_CAPACITY")
            if numerator // 100 > discovery_capacity:
                reasons.append("DISCOVERY_CAPACITY")
    achieved = sum(p.candidate.familiarity <= policy.discovery_familiarity_threshold for p in tracks)
    return DiscoveryFacts(
        requested_percent=percent, requested_ratio=percent / 100.0, planning_horizon=horizon,
        rounded_ranking_target_count=None if horizon is None else (percent * horizon + 50) // 100,
        achieved_count=achieved, achieved_denominator=len(tracks),
        achieved_ratio=achieved / len(tracks) if tracks else None,
        exact_target_outcome=("MET" if 100 * achieved == percent * len(tracks) else "MISSED") if tracks else "NOT_APPLICABLE",
        structural_outcome=("STRUCTURALLY_INFEASIBLE" if reasons else "NOT_ESTABLISHED") if horizon is not None else "NOT_APPLICABLE",
        structural_reasons=tuple(reasons), horizon_target_numerator=numerator,
        familiar_capped_capacity=familiar_capacity, discovery_capped_capacity=discovery_capacity)


def _issues(target, hard, discovery, stopping):
    issues = []
    def add(code, message, severity, observed=None, requested=None):
        issues.append(ConstructionIssue(code, message, severity, observed, requested))
    hard_severity = ConstructionIssueSeverity.HARD_UNMET
    soft = ConstructionIssueSeverity.SOFT_COMPROMISE
    if stopping == "global_infeasible":
        add(stopping, "Preconstruction certificate proves the bound hard target infeasible", hard_severity)
    elif stopping != "HARD_TARGET_MET":
        add(stopping, "No continuation; prefix retained, not original-pool infeasibility", hard_severity,
            hard.achieved_count, target.requirement.requested_track_count if isinstance(target.requirement, CountTarget) else None)
    if hard.duration_outcome == "MISSED":
        add("duration_target_missed", "Journey minimum seconds not reached", hard_severity,
            hard.achieved_duration_seconds, target.requirement.minimum_duration_seconds)
    if hard.phase_requirement_outcome == "MISSED":
        for index in hard.unrepresented_phase_indices:
            add("required_phase_unrepresented", f"Required phase index {index} has no placement", hard_severity, 0, index)
    if discovery.structural_outcome == "STRUCTURALLY_INFEASIBLE":
        add("discovery_target_structurally_infeasible", "Exact discovery impossible at certified horizon; soft target does not override hard stopping", soft,
            discovery.familiar_capped_capacity, discovery.planning_horizon)
    if discovery.exact_target_outcome == "MISSED":
        add("discovery_target_missed", "Achieved exact ratio differs; retained because discovery is soft", soft,
            discovery.achieved_ratio, discovery.requested_ratio)
    return tuple(issues)


def _verify_resume(result, target, journey, policy, pool, certificate):
    """Reverify retained evidence against the original pool, never a residual pool."""
    if type(result) is not ConstructionResultV2:
        raise TypeError("only a bound successor result can resume")
    serialize_successor(result)
    b = result.input_binding
    if (result.target != target or result.feasibility != certificate or result.formation_trace != pool.trace
            or b.journey_id != journey.journey_id or b.journey_artifact_sha256 != _journey_hash(journey)
            or b.formation_parent_schema_version != pool.trace.parent_schema_version
            or b.formation_parent_sha256 != pool.trace.parent_artifact_sha256
            or b.formation_request_id != pool.trace.parent_request_id
            or b.construction_policy_sha256 != successor_sha256(policy)
            or b.target_sha256 != successor_sha256(target)
            or b.formed_pool_sha256 != certificate.formed_pool_sha256
            or b.ordered_track_ids != tuple(c.track_id for c in pool.candidates)
            or b.initial_placement_count > len(result.tracks)):
        raise ValueError("resumption must retain original target, horizon, inputs and formation")
    tracks = result.tracks
    by_id = {c.track_id: c for c in pool.candidates}
    ids = [p.candidate.track_id for p in tracks]
    if len(set(ids)) != len(ids) or any(by_id.get(p.candidate.track_id) != p.candidate for p in tracks):
        raise ValueError("resume placements must be distinct exact formed candidates")
    if b.initial_state_sha256 != construction_prefix_sha256(target, certificate, tracks[:b.initial_placement_count], result.decisions):
        raise ValueError("resume initial prefix digest does not reproduce")
    k = certificate.planning_horizon
    if tracks and (k is None or len(tracks) > k or certificate.outcome != "FEASIBLE"):
        raise ValueError("prefix outside original certified horizon")
    hard = _hard_facts(target, journey, policy, tracks)
    discovery = _discovery(journey, policy, pool.candidates, tracks, k)
    status = ConstructionStatus.COMPLETE if hard.hard_target_satisfied else ConstructionStatus.PARTIAL if tracks else ConstructionStatus.INFEASIBLE
    stopping = result.stopping_reason
    if (hard != result.hard_targets or discovery != result.discovery or result.status != status
            or not hard.artist_cap_satisfied
            or (hard.hard_target_satisfied and stopping != "HARD_TARGET_MET")
            or (not hard.hard_target_satisfied and tracks and stopping not in ("candidate_pool_exhausted", "no_eligible_candidates"))
            or (not tracks and (stopping != "global_infeasible" or certificate.outcome != "INFEASIBLE"))
            or result.issues != _issues(target, hard, discovery, stopping)
            or result.residual_feasibility != (_bound(target, journey, policy, pool.candidates, tracks, k) if k is not None else None)):
        raise ValueError("resume facts/status/issues/certificate do not reproduce")
    # All inspected choices, including a failed final attempt, retain typed bounds.
    previous_position, previous_rank = 0, 0
    selected_count = 0
    for d in result.decisions:
        if d.position != previous_position:
            if d.position != previous_position + 1 or d.selector_rank != 1:
                raise ValueError("resume decision order changed")
            previous_position, previous_rank = d.position, 0
        if d.selector_rank != previous_rank + 1 or d.position > len(tracks) + 1:
            raise ValueError("resume decision rank changed")
        previous_rank = d.selector_rank
        prefix = tracks[:d.position - 1]
        candidate = by_id.get(d.track_id)
        if candidate is None or d.track_id in {p.candidate.track_id for p in prefix}:
            raise ValueError("resume decision used a nonremaining identity")
        cap_full = sum(p.candidate.artist_name == candidate.artist_name for p in prefix) >= policy.max_tracks_per_artist
        if cap_full != (d.outcome == "artist_repetition_limit"):
            raise ValueError("resume artist-cap rejection disagrees with prefix")
        if not cap_full:
            # Only identity, seconds and phase enter this residual calculation.
            probe = _BoundPlacement(candidate, _phase(journey, d.position - 1, k))
            expected = _bound(target, journey, policy, pool.candidates, (*prefix, probe), k)
            if d.residual != expected:
                raise ValueError("resume decision residual bound changed")
            if (d.outcome == "global_feasibility_guard") != bool(expected.failures):
                raise ValueError("resume decision outcome changed")
        if d.outcome == "SELECTED":
            if selected_count >= len(tracks) or d.track_id != tracks[selected_count].candidate.track_id or d.position != selected_count + 1:
                raise ValueError("resume selection does not correspond to placement")
            selected_count += 1
    if selected_count != len(tracks):
        raise ValueError("resume selection evidence missing")


class SequentialPlaylistConstructorV2:
    def __init__(self, *, policy=None, selector=None):
        self.policy = policy if policy is not None else ConstructionPolicyV2()
        if type(self.policy) is not ConstructionPolicyV2:
            raise TypeError("constructor successor requires policy 2.0")
        serialize_successor(self.policy)
        self.selector = selector if selector is not None else CandidateSelector()

    def construct(self, *, target, journey_plan, formation_parent, resume_from=None):
        pool = _inputs(journey_plan, formation_parent)
        verify_target_journey(target, journey_plan, self.policy)
        if (target.formation_parent_sha256 != pool.trace.parent_artifact_sha256
                or target.formation_parent_schema_version != pool.trace.parent_schema_version):
            raise ValueError("target formation parent mismatch")
        certificate = _certificate(target, journey_plan, self.policy, pool)
        prefix = ()
        if resume_from is not None:
            _verify_resume(resume_from, target, journey_plan, self.policy, pool, certificate)
            prefix = resume_from.tracks
        binding = ConstructionInputBindingV2(
            journey_id=journey_plan.journey_id, journey_artifact_sha256=_journey_hash(journey_plan),
            formation_parent_schema_version=pool.trace.parent_schema_version,
            formation_parent_sha256=pool.trace.parent_artifact_sha256,
            formation_request_id=pool.trace.parent_request_id,
            construction_policy_sha256=successor_sha256(self.policy), target_sha256=successor_sha256(target),
            formed_pool_sha256=certificate.formed_pool_sha256,
            ordered_track_ids=tuple(c.track_id for c in pool.candidates),
            initial_state_sha256=construction_prefix_sha256(target, certificate, prefix, resume_from.decisions if resume_from else ()),
            initial_placement_count=len(prefix))
        tracks = []
        decisions = []
        state = ConstructionState()
        horizon = certificate.planning_horizon
        stopping = "global_infeasible"
        if certificate.outcome == "FEASIBLE":
            stopping = "candidate_pool_exhausted"
            while len(tracks) < horizon and not _complete(target, tracks):
                position = len(tracks)
                phase_index = _phase(journey_plan, position, horizon)
                role = SequentialPlaylistConstructor._role_for_position(state, position, phase_index, horizon)
                # Exact half-up from the authoritative integer percentage. The
                # historical float helper is intentionally not changed.
                rounded_target = (journey_plan.plan.discovery_percent * horizon + 50) // 100
                demand = min(1.0, max(0.0, (rounded_target - state.discovery_count) / (horizon - position)))
                remaining = tuple(c.track_id for c in pool.candidates if c.track_id not in state.used_track_ids)
                ranking = self.selector.select(
                    context=journey_plan.plan.context, previous_track=state.previous_track,
                    phase=journey_plan.plan.phases[phase_index], role=role, target_discovery_ratio=demand,
                    formed_pool=pool, remaining_track_ids=remaining, top_n=len(remaining))
                if (ranking.formation_trace != pool.trace or ranking.remaining_track_ids != remaining
                        or ranking.context != journey_plan.plan.context or ranking.phase != journey_plan.plan.phases[phase_index]
                        or ranking.role != role or ranking.target_discovery_ratio != demand
                        or ranking.previous_track_id != (state.previous_track.track_id if state.previous_track else None)
                        or ranking.top_n != len(remaining)):
                    raise ValueError("ranking envelope substituted bound inputs")
                by_id = {c.track_id: c for c in pool.candidates}
                ranked_ids = [r.candidate.track_id for r in ranking.ranked_candidates]
                if len(set(ranked_ids)) != len(ranked_ids) or not set(ranked_ids) <= set(remaining):
                    raise ValueError("ranking must contain distinct remaining formed identities")
                if ranked_ids and set(ranked_ids) != set(remaining):
                    raise ValueError("nonempty ranking must cover the requested remaining pool")
                rejected = []
                chosen = None
                for expected_rank, ranked in enumerate(ranking.ranked_candidates, 1):
                    if ranked.candidate != by_id.get(ranked.candidate.track_id) or ranked.rank != expected_rank:
                        raise ValueError("ranked candidate content/rank substituted")
                    if ranked.score_breakdown.role != role:
                        raise ValueError("ranked score breakdown must retain the selected role")
                    candidate = ranked.candidate
                    if state.artist_counts.get(candidate.artist_name, 0) >= self.policy.max_tracks_per_artist:
                        decisions.append(DecisionFact(position=position + 1, track_id=candidate.track_id,
                            selector_rank=ranked.rank, outcome="artist_repetition_limit", residual=None))
                        rejected.append(CandidateRejection(candidate.track_id, ranked.rank, "artist_repetition_limit", "Exact artist cap reached"))
                        continue
                    placed = PlacedTrack(position + 1, candidate, phase_index, journey_plan.plan.phases[phase_index].name,
                        role, ranked.rank, ranked.score, ranked.score_breakdown,
                        ranked.reasons + (f"Selected as {role.value} for {journey_plan.plan.phases[phase_index].name}",), tuple(rejected))
                    residual = _bound(target, journey_plan, self.policy, pool.candidates, (*tracks, placed), horizon)
                    outcome = "global_feasibility_guard" if residual.failures else "SELECTED"
                    decisions.append(DecisionFact(position=position + 1, track_id=candidate.track_id,
                        selector_rank=ranked.rank, outcome=outcome, residual=residual))
                    if residual.failures:
                        rejected.append(CandidateRejection(candidate.track_id, ranked.rank, outcome, "Choice destroys certified residual hard feasibility"))
                        continue
                    chosen = placed
                    break
                if chosen is None:
                    if not tracks:
                        raise ValueError("selector failed before a certified feasible first placement")
                    stopping = "no_eligible_candidates" if remaining else "candidate_pool_exhausted"
                    break
                if position < len(prefix) and chosen != prefix[position]:
                    raise ValueError("resumed prefix does not reproduce exact ranking/placement")
                tracks.append(chosen)
                state.placed_tracks.append(chosen)
                state.previous_track = chosen.candidate
                state.current_phase_index = phase_index
                state.used_track_ids.add(chosen.candidate.track_id)
                state.artist_counts[chosen.candidate.artist_name] = state.artist_counts.get(chosen.candidate.artist_name, 0) + 1
                state.discovery_count += chosen.candidate.familiarity <= self.policy.discovery_familiarity_threshold
                state.elapsed_seconds += chosen.candidate.duration_seconds
            if _complete(target, tracks):
                stopping = "HARD_TARGET_MET"
        if len(prefix) > len(tracks):
            raise ValueError("resume prefix exceeds valid construction")
        hard = _hard_facts(target, journey_plan, self.policy, tracks)
        discovery = _discovery(journey_plan, self.policy, pool.candidates, tracks, horizon)
        result = ConstructionResultV2(
            input_binding=binding, formation_trace=pool.trace, target=target, feasibility=certificate,
            tracks=tuple(tracks), decisions=tuple(decisions),
            status=ConstructionStatus.COMPLETE if hard.hard_target_satisfied else (ConstructionStatus.PARTIAL if tracks else ConstructionStatus.INFEASIBLE),
            hard_targets=hard, discovery=discovery,
            residual_feasibility=_bound(target, journey_plan, self.policy, pool.candidates, tracks, horizon) if horizon is not None else None,
            stopping_reason=stopping, issues=_issues(target, hard, discovery, stopping))
        serialize_successor(result)
        return result

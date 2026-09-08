"""Synthetic conformance replay of the real six-track proof's observed inputs.

This does not mint a new production acquisition/readiness occurrence or claim
that the failed real proof has been rerun successfully.
"""
from dataclasses import replace
import hashlib
import itertools
import json

import pytest

from cf3_test_helpers import OBJECTIVE, formation_artifact
from journey_authority_helpers import journey_authority
from playlist_narrative_engine.candidate_formation import CandidateFormationArtifact, derive_formed_candidate_pool
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.evaluation.successor import (
    EvaluationReportV3, PlaylistJourneyEvaluatorV3, evaluation_report_v3_sha256,
    parse_evaluation_report_v3, serialize_evaluation_report_v3,
)
from playlist_narrative_engine.objective_assessment import EnergyLevel
from playlist_narrative_engine.sequencing import (
    ConstructionPolicy, ConstructionState, ConstructionStatus, SequentialPlaylistConstructor,
    construction_policy_sha256, construction_result_matches_evaluation_inputs,
    construction_result_sha256, serialize_construction_policy,
)
from playlist_narrative_engine.sequencing.schemas import TrackCandidate
from playlist_narrative_engine.sequencing.selector import CandidateSelector
from playlist_narrative_engine.sequencing.successor import (
    SequentialPlaylistConstructorV2, _bound, _certificate, _inputs, _retained,
    create_construction_target,
)
from playlist_narrative_engine.sequencing.successor_canonical import (
    construction_prefix_sha256, parse_successor, serialize_successor, successor_sha256, verify_successor_digest,
)
from playlist_narrative_engine.sequencing.successor_schemas import (
    ConstructionInputBindingV2, ConstructionPolicyV2, ConstructionResultV2,
    ConstructionTargetArtifact,
)


def candidate(identity, seconds=600, artist=None, familiarity=0.5):
    return TrackCandidate(track_id=identity, title=identity, artist_name=artist or identity,
        duration_seconds=seconds, energy=0.5, familiarity=familiarity, preference=0.5,
        context_fit=0.75, instrumentalness=0.75, lyrical_distraction=0.25, groove=0.75)


def six_tracks():
    rows = (
        (33, "Aperture", "Harry Styles", "5D54294A82803CB5", 311, 0, .5, .5, .5, .75, .5, .5),
        (67, "The Great Divide", "Noah Kahan", "251291F66368F1EA", 318, 0, .25, .5, .5, .25, .75, .5),
        (68, "Porch Light", "Noah Kahan", "C0B4C9476E129AE2", 262, 0, .25, .5, .75, .25, .25, .5),
        (98, "This Corrosion", "The Sisters Of Mercy", "EF9D56D007A43122", 655, 1, .75, .75, .25, .75, .75, 1),
        (110, "Lucretia My Reflection", "The Sisters Of Mercy", "411F46A1537ECF15", 524, 1, .75, .75, .25, .75, .75, 1),
        (112, "This Corrosion", "The Sisters Of Mercy", "84761B93D30767F9", 617, 1, .75, .75, .25, .75, .75, 1),
    )
    return tuple(TrackCandidate(track_id=f"itunes-windows-library:9C9E2747D29AB9A8/track:{r[3]}",
        title=r[1], artist_name=r[2], duration_seconds=r[4], familiarity=r[5], energy=r[6],
        instrumentalness=r[7], lyrical_distraction=r[8], groove=r[9], context_fit=r[10], preference=r[11]) for r in rows)


def inputs(candidates=None, *, percent=25):
    journey = journey_authority(OBJECTIVE, duration_minutes=30, discovery_percent=percent,
        starting_energy=EnergyLevel.LOW, ending_energy=EnergyLevel.HIGH)[2]
    parent = formation_artifact(six_tracks() if candidates is None else candidates).model_dump(mode="json")
    parent.update(journey_id=journey.journey_id, accepted_objective_artifact_id=journey.objective_safety_artifact_id)
    return journey, CandidateFormationArtifact.model_validate(parent), ConstructionPolicyV2()


def run(candidates=None, *, mode="JOURNEY", count=None, percent=25, selector=None):
    journey, parent, policy = inputs(candidates, percent=percent)
    target = create_construction_target(journey_plan=journey, formation_parent=parent, policy=policy,
        mode=mode, requested_track_count=count)
    result = SequentialPlaylistConstructorV2(policy=policy, selector=selector).construct(
        target=target, journey_plan=journey, formation_parent=parent)
    report = PlaylistJourneyEvaluatorV3().evaluate(construction_result=result, journey_plan=journey, construction_policy=policy)
    return journey, parent, policy, target, result, report


def test_exact_policy_authorities():
    old, new = ConstructionPolicy(), ConstructionPolicyV2()
    assert len(serialize_construction_policy(old)) == len(serialize_successor(new)) == 89
    assert construction_policy_sha256(old) == "a47bfdd7fc63f1524c38f84c5f3b07e96e292730baa0400e862fb77aeeaeb62c"
    assert successor_sha256(new) == "5d94a0a847d6b13457d64799c46f2832eedfb7d616eb3463a64716f1c59b355b"


def test_real_six_track_regression_and_independent_evaluation():
    journey, parent, policy, target, result, report = run()
    old_policy = ConstructionPolicy()
    old = SequentialPlaylistConstructor(policy=old_policy).construct(journey_plan=journey,
        formed_pool=derive_formed_candidate_pool(parent), state=ConstructionState(), requested_track_count=4)
    assert old.summary.status == "complete"
    assert [p.candidate.duration_seconds for p in old.tracks] == [524, 617, 311, 318]
    assert old.summary.total_duration_seconds == 1770
    assert old.issues == ()
    assert construction_result_matches_evaluation_inputs(old, journey_plan=journey, construction_policy=old_policy)
    assert PlaylistJourneyEvaluator().evaluate(construction_result=old, journey_plan=journey, construction_policy=old_policy).schema_version == "2.0"
    old_again = SequentialPlaylistConstructor(policy=old_policy).construct(journey_plan=journey,
        formed_pool=derive_formed_candidate_pool(parent), state=ConstructionState(), requested_track_count=4)
    assert construction_result_sha256(old_again) == construction_result_sha256(old)
    assert target.requirement.minimum_duration_seconds == 1800
    assert result.feasibility.planning_horizon == 4
    assert result.status == "complete"
    assert [p.candidate.duration_seconds for p in result.tracks] == [524, 655, 311, 318]
    assert result.hard_targets.achieved_duration_seconds == 1808
    assert result.hard_targets.represented_phase_indices == (0, 1, 2)
    assert result.hard_targets.artist_cap_satisfied
    assert result.discovery.achieved_count == 2
    assert result.discovery.achieved_ratio == .5
    assert result.discovery.rounded_ranking_target_count == 1
    assert result.discovery.structural_reasons == ("FAMILIAR_CAPACITY",)
    assert result.discovery.familiar_capped_capacity == 2
    assert [i.code for i in result.issues] == ["discovery_target_structurally_infeasible", "discovery_target_missed"]
    guarded = [d for d in result.decisions if d.outcome == "global_feasibility_guard"]
    assert guarded[0].track_id.endswith("84761B93D30767F9")
    assert guarded[0].residual.prefix_duration_seconds + guarded[0].residual.maximum_additional_seconds == 1770
    assert report.hard_targets == result.hard_targets
    assert report.discovery == result.discovery
    assert report.certificate_verification == "BOUND_CONSTRUCTOR_EVIDENCE_NOT_POOL_RECOMPUTED"
    assert report.construction_issues == result.issues


def test_successor_count_keeps_duration_informational_and_adds_soft_reporting():
    *_, result, report = run(mode="TRACK_COUNT", count=4)
    assert result.status == "complete"
    assert result.hard_targets.achieved_duration_seconds == 1770
    assert result.hard_targets.duration_outcome == "NOT_APPLICABLE"
    assert all(i.code != "duration_target_missed" for i in result.issues)
    assert report.discovery.exact_target_outcome == "MISSED"


@pytest.mark.parametrize("seconds,expected", [(599, "infeasible"), (600, "complete"), (601, "complete")])
def test_zero_tolerance_whole_track_overshoot(seconds, expected):
    *_, result, report = run(tuple(candidate(str(i), seconds) for i in range(3)))
    assert result.status == expected
    if expected == "complete":
        assert result.hard_targets.achieved_duration_seconds == 3 * seconds
    else:
        assert result.tracks == ()
        assert result.feasibility.outcome == "INFEASIBLE"
        assert result.issues[0].code == "global_infeasible"


def test_artist_capacity_count_and_duration_infeasibility():
    tracks = tuple(candidate(str(i), 1000, "same") for i in range(4))
    *_, result, _ = run(tracks)
    assert result.status == "infeasible"  # enough duration, not enough phase slots
    assert result.feasibility.initial_capped_capacity == 2
    assert result.feasibility.horizon_trials[-1].bound.failures == ("required_phase_unrepresented",)
    *_, result, _ = run(tracks, mode="TRACK_COUNT", count=3)
    assert result.status == "infeasible"
    assert result.feasibility.horizon_trials[0].bound.maximum_additional_seconds is None


@pytest.mark.parametrize("count,phases", [(3, [0,1,2]), (4,[0,1,1,2]), (5,[0,1,1,1,2]), (6,[0,1,1,1,1,2])])
def test_unchanged_positional_mapping(count, phases):
    *_, result, _ = run(tuple(candidate(str(i)) for i in range(count)), mode="TRACK_COUNT", count=count)
    assert [p.phase_index for p in result.tracks] == phases


def test_empty_pool_and_no_achieved_ratio():
    *_, result, report = run(())
    assert result.status == "infeasible"
    assert result.feasibility.planning_horizon is None
    assert result.discovery.achieved_ratio is None
    assert result.discovery.exact_target_outcome == "NOT_APPLICABLE"
    assert result.discovery.structural_outcome == "NOT_APPLICABLE"
    assert report.disposition == "inconclusive"


def test_half_up_and_structural_unknown_not_feasibility_claim():
    *_, result, _ = run((candidate("a", familiarity=0), candidate("b")), mode="TRACK_COUNT", count=2)
    assert result.discovery.rounded_ranking_target_count == 1
    assert result.discovery.structural_reasons == ("NONINTEGRAL_COUNT",)
    *_, result, _ = run(tuple(candidate(str(i), familiarity=0 if i == 0 else 1) for i in range(4)), mode="TRACK_COUNT", count=4)
    assert result.discovery.exact_target_outcome == "MET"
    assert result.discovery.structural_outcome == "NOT_ESTABLISHED"
    assert result.issues == ()


def test_distinct_source_tracks_are_not_recording_deduplicated():
    *_, result, _ = run()
    assert len(result.input_binding.ordered_track_ids) == 6
    assert any(i.endswith("EF9D56D007A43122") for i in result.input_binding.ordered_track_ids)
    assert any(i.endswith("84761B93D30767F9") for i in result.input_binding.ordered_track_ids)


def test_replay_canonical_roundtrip_all_successor_artifacts():
    journey, parent, policy, target, result, report = run()
    again = SequentialPlaylistConstructorV2(policy=policy).construct(target=target, journey_plan=journey, formation_parent=parent)
    report_again = PlaylistJourneyEvaluatorV3().evaluate(construction_result=again, journey_plan=journey, construction_policy=policy)
    assert serialize_successor(result) == serialize_successor(again)
    assert serialize_evaluation_report_v3(report) == serialize_evaluation_report_v3(report_again)
    for artifact in (policy, target, result.input_binding, result):
        assert parse_successor(serialize_successor(artifact), type(artifact)) == artifact
        assert verify_successor_digest(artifact, successor_sha256(artifact))
        assert not verify_successor_digest(artifact, successor_sha256(artifact).upper())
    assert parse_evaluation_report_v3(serialize_evaluation_report_v3(report)) == report
    assert (target.schema_version, result.input_binding.schema_version, result.schema_version, report.schema_version) == ("1.0", "2.0", "2.0", "3.0")
    # Implementation-conformance goldens, NOT previously frozen semantic-authority bytes.
    for artifact, size, digest in (
        (target, 682, "80b5d6397806b445850afd81b79f1219dec52d739c34534b24b600e71038c136"),
        (result.input_binding, 1319, "35fe7db3c75b7708295fb989f64ecc713ab07341defe54ecaf17ca7c1db9048f"),
        (result, 12568, "91f73b130eceb759b65207643d08ca635033fa2ae56f22406c674869396e3921"),
    ):
        assert len(serialize_successor(artifact)) == size
        assert successor_sha256(artifact) == digest
    assert len(serialize_evaluation_report_v3(report)) == 6177
    assert evaluation_report_v3_sha256(report) == "e3becfb253435c51e0b006e6f9de79af0d10a583eb0cbf1e5115bf0e08be01c4"


@pytest.mark.parametrize("edit", [
    lambda d: d + b"\n",
    lambda d: d.replace(b'"2.0"', b'"1.0"'),
    lambda d: d.replace(b'"max_tracks_per_artist":2', b'"max_tracks_per_artist":2,"max_tracks_per_artist":2'),
    lambda d: d.replace(b'0.35', b'NaN'),
    lambda d: d.replace(b'0.35', b'Infinity'),
    lambda d: d.replace(b'0.35', b'3.5e-1'),
    lambda d: d.replace(b'"max_tracks_per_artist":2', b'"max_tracks_per_artist":true'),
    lambda d: d.replace(b'}', b',"extra":1}'),
])
def test_noncanonical_or_expanded_policy_rejected(edit):
    with pytest.raises((ValueError, TypeError)):
        parse_successor(edit(serialize_successor(ConstructionPolicyV2())), ConstructionPolicyV2)


@pytest.mark.parametrize("change", [{"minimum_duration_seconds": 1770}, {"required_phase_indices": (0,1)}])
def test_caller_cannot_override_derived_target(change):
    journey, parent, policy, target, *_ = run()
    bad = target.model_copy(update={"requirement": target.requirement.model_copy(update=change)})
    with pytest.raises(ValueError, match="exact derivations"):
        SequentialPlaylistConstructorV2(policy=policy).construct(target=bad, journey_plan=journey, formation_parent=parent)


@pytest.mark.parametrize("mode,count", [("DURATION", None), ("JOURNEY", 4), ("TRACK_COUNT", None), ("TRACK_COUNT", True)])
def test_unknown_and_conflicting_targets_rejected(mode, count):
    journey, parent, policy = inputs()
    with pytest.raises((ValueError, TypeError)):
        create_construction_target(journey_plan=journey, formation_parent=parent, policy=policy, mode=mode, requested_track_count=count)


def test_parent_or_journey_substitution_rejected():
    journey, parent, policy, target, *_ = run()
    _, changed, _ = inputs((candidate("replacement"),))
    with pytest.raises(ValueError, match="formation parent mismatch"):
        SequentialPlaylistConstructorV2(policy=policy).construct(target=target, journey_plan=journey, formation_parent=changed)
    other_journey = inputs(percent=20)[0]
    with pytest.raises(ValueError):
        SequentialPlaylistConstructorV2(policy=policy).construct(target=target, journey_plan=other_journey, formation_parent=parent)


@pytest.mark.parametrize("field,value", [("schema_version", "1.0"), ("status", ConstructionStatus.PARTIAL), ("issues", ())])
def test_evaluator_rejects_relabeling_or_claim_corruption(field, value):
    journey, _, policy, _, result, _ = run()
    with pytest.raises((ValueError, TypeError)):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=result.model_copy(update={field:value}), journey_plan=journey, construction_policy=policy)


def test_evaluator_does_not_trust_complete_or_producer_fact_helpers(monkeypatch):
    journey, _, policy, _, result, _ = run()
    import playlist_narrative_engine.sequencing.successor as producer
    monkeypatch.setattr(producer, "_hard_facts", lambda *args: (_ for _ in ()).throw(AssertionError("producer called")))
    monkeypatch.setattr(producer, "_discovery", lambda *args: (_ for _ in ()).throw(AssertionError("producer called")))
    assert PlaylistJourneyEvaluatorV3().evaluate(construction_result=result, journey_plan=journey, construction_policy=policy)
    bad = result.model_copy(update={"hard_targets": result.hard_targets.model_copy(update={"achieved_duration_seconds":1770})})
    with pytest.raises(ValueError, match="independent reconstruction"):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=bad, journey_plan=journey, construction_policy=policy)


class InterruptedSelector(CandidateSelector):
    def select(self, **kwargs):
        ranking = super().select(**kwargs)
        return replace(ranking, ranked_candidates=()) if kwargs["previous_track"] else ranking


def test_partial_retains_prefix_and_resumes_original_horizon():
    journey, parent, policy, target, partial, _ = run(selector=InterruptedSelector())
    assert partial.status == "partial"
    assert partial.feasibility.outcome == "FEASIBLE"
    assert len(partial.tracks) == 1
    assert partial.stopping_reason == "no_eligible_candidates"
    constructor = SequentialPlaylistConstructorV2(policy=policy)
    resumed = constructor.construct(target=target, journey_plan=journey, formation_parent=parent, resume_from=partial)
    assert resumed.status == "complete"
    assert resumed.feasibility == partial.feasibility
    assert resumed.tracks[:1] == partial.tracks
    assert resumed.input_binding.initial_state_sha256 == construction_prefix_sha256(target, partial.feasibility, partial.tracks, partial.decisions)
    assert resumed.input_binding.initial_placement_count == 1
    assert PlaylistJourneyEvaluatorV3().evaluate(construction_result=resumed, journey_plan=journey, construction_policy=policy)
    tampered = partial.model_copy(update={"tracks": (replace(partial.tracks[0], selection_score=0),)})
    with pytest.raises(ValueError):
        constructor.construct(target=target, journey_plan=journey, formation_parent=parent, resume_from=tampered)


def test_exact_partition_bound_matches_exhaustive_test_oracle():
    # Exhaustive enumeration is test-only, not the runtime mechanism.
    candidates = (candidate("a1", 8, "a"), candidate("a2", 3, "a"), candidate("a3", 9, "a"),
                  candidate("b1", 7, "b"), candidate("b2", 2, "b"), candidate("c1", 4, "c"))
    for cap in (1,2,3):
        retained = _retained(candidates, (), cap)
        for count in range(len(candidates)+1):
            valid = [s for s in itertools.combinations(candidates, count)
                     if all(sum(c.artist_name == a for c in s) <= cap for a in ("a","b","c"))]
            if valid:
                assert sum(c.duration_seconds for c in retained[:count]) == max(sum(c.duration_seconds for c in s) for s in valid)
            else:
                assert len(retained) < count

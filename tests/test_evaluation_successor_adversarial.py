from dataclasses import replace
from types import SimpleNamespace
import itertools
import json

import pytest

from test_construction_successor import (
    InterruptedSelector, candidate, inputs, run, six_tracks,
)
from playlist_narrative_engine.evaluation import PlaylistJourneyEvaluator
from playlist_narrative_engine.evaluation.successor import PlaylistJourneyEvaluatorV3, evaluation_report_v3_matches_inputs
from playlist_narrative_engine.sequencing import ConstructionPolicy, ConstructionState, SequentialPlaylistConstructor
from playlist_narrative_engine.candidate_formation import derive_formed_candidate_pool
from playlist_narrative_engine.sequencing.selector import CandidateSelector
from playlist_narrative_engine.sequencing.successor import SequentialPlaylistConstructorV2, _retained
from playlist_narrative_engine.sequencing.successor_canonical import parse_successor, serialize_successor
from playlist_narrative_engine.sequencing.successor_schemas import ConstructionPolicyV2, ConstructionResultV2


@pytest.mark.parametrize("mutation", [
    lambda r: r.model_copy(update={"input_binding": r.input_binding.model_copy(update={"target_sha256":"0"*64})}),
    lambda r: r.model_copy(update={"input_binding": r.input_binding.model_copy(update={"initial_state_sha256":"0"*64})}),
    lambda r: r.model_copy(update={"input_binding": r.input_binding.model_copy(update={"ordered_track_ids":r.input_binding.ordered_track_ids[::-1]})}),
    lambda r: r.model_copy(update={"input_binding": r.input_binding.model_copy(update={"formed_pool_sha256":"0"*64})}),
    lambda r: r.model_copy(update={"feasibility": r.feasibility.model_copy(update={"horizon_trials":r.feasibility.horizon_trials[1:]})}),
    lambda r: r.model_copy(update={"feasibility": r.feasibility.model_copy(update={"planning_horizon":5})}),
    lambda r: r.model_copy(update={"feasibility": r.feasibility.model_copy(update={"artist_capacities":r.feasibility.artist_capacities[::-1]})}),
    lambda r: r.model_copy(update={"hard_targets": r.hard_targets.model_copy(update={"artist_cap_satisfied":False})}),
    lambda r: r.model_copy(update={"hard_targets": r.hard_targets.model_copy(update={"duration_outcome":"NOT_APPLICABLE"})}),
    lambda r: r.model_copy(update={"discovery": r.discovery.model_copy(update={"exact_target_outcome":"MET"})}),
    lambda r: r.model_copy(update={"discovery": r.discovery.model_copy(update={"achieved_ratio":.25})}),
    lambda r: r.model_copy(update={"discovery": r.discovery.model_copy(update={"rounded_ranking_target_count":2})}),
    lambda r: r.model_copy(update={"discovery": r.discovery.model_copy(update={"structural_reasons":()})}),
    lambda r: r.model_copy(update={"issues":r.issues[::-1]}),
    lambda r: r.model_copy(update={"decisions":tuple(d for d in r.decisions if d.outcome != "global_feasibility_guard")}),
    lambda r: r.model_copy(update={"tracks":r.tracks[::-1]}),
    lambda r: r.model_copy(update={"tracks":(replace(r.tracks[0], phase_index=1), *r.tracks[1:])}),
    lambda r: r.model_copy(update={"tracks":(replace(r.tracks[0], candidate=r.tracks[0].candidate.model_copy(update={"track_id":"not-formed"})), *r.tracks[1:])}),
    lambda r: r.model_copy(update={"tracks":(replace(r.tracks[0], selection_score=float("nan")), *r.tracks[1:])}),
    lambda r: r.model_copy(update={"tracks":(replace(r.tracks[0], score_breakdown=r.tracks[0].score_breakdown.model_copy(update={"total_score":float("inf")})), *r.tracks[1:])}),
])
def test_independent_reconstruction_rejects_corruption(mutation):
    journey, _, policy, _, result, _ = run()
    with pytest.raises((TypeError, ValueError)):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=mutation(result), journey_plan=journey, construction_policy=policy)


@pytest.mark.parametrize("mutation", [
    lambda r: r.model_copy(update={"input_binding":r.input_binding.model_copy(update={"initial_state_sha256":"0"*64})}),
    lambda r: r.model_copy(update={"input_binding":r.input_binding.model_copy(update={"formed_pool_sha256":"0"*64})}),
    lambda r: r.model_copy(update={"hard_targets":r.hard_targets.model_copy(update={"achieved_duration_seconds":0})}),
    lambda r: r.model_copy(update={"issues":()}),
    lambda r: r.model_copy(update={"decisions":()}),
    lambda r: r.model_copy(update={"discovery":r.discovery.model_copy(update={"requested_percent":50})}),
])
def test_resume_reverifies_all_retained_facts(mutation):
    journey, parent, policy, target, partial, _ = run(selector=InterruptedSelector())
    with pytest.raises((TypeError, ValueError)):
        SequentialPlaylistConstructorV2(policy=policy).construct(target=target, journey_plan=journey,
            formation_parent=parent, resume_from=mutation(partial))


def test_historical_successor_dispatch_is_explicit():
    journey, parent, policy, target, result, _ = run()
    with pytest.raises(TypeError):
        SequentialPlaylistConstructor(policy=policy)
    with pytest.raises(TypeError):
        SequentialPlaylistConstructorV2(policy=ConstructionPolicy())
    old = SequentialPlaylistConstructor().construct(journey_plan=journey,
        formed_pool=derive_formed_candidate_pool(parent), state=ConstructionState(), requested_track_count=4)
    with pytest.raises(TypeError):
        PlaylistJourneyEvaluator().evaluate(construction_result=old, journey_plan=journey, construction_policy=policy)
    with pytest.raises(TypeError):
        PlaylistJourneyEvaluator().evaluate(construction_result=result, journey_plan=journey, construction_policy=ConstructionPolicy())
    with pytest.raises(TypeError):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=replace(old, schema_version="2.0"), journey_plan=journey, construction_policy=policy)


def test_successor_canonical_nested_unknown_fields_fail_closed():
    *_, result, _ = run()
    payload = json.loads(serialize_successor(result))
    payload["tracks"][0]["candidate"]["invented_feature"] = 1
    with pytest.raises(ValueError):
        parse_successor(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(), ConstructionResultV2)


def test_version_relabeling_cannot_turn_old_json_into_successor():
    journey, parent, policy, *_ = run()
    old = SequentialPlaylistConstructor().construct(journey_plan=journey,
        formed_pool=derive_formed_candidate_pool(parent), state=ConstructionState(), requested_track_count=4)
    from playlist_narrative_engine.sequencing import serialize_construction_result
    with pytest.raises(ValueError):
        parse_successor(serialize_construction_result(old).replace(b'"schema_version":"1.0"', b'"schema_version":"2.0"'), ConstructionResultV2)


def test_numeric_policy_and_target_expansion_fail_closed():
    for value in (float("nan"), float("inf"), True, "0.35"):
        with pytest.raises(ValueError):
            ConstructionPolicyV2(discovery_familiarity_threshold=value)
    *_, target, result, _ = run()
    expanded = target.model_dump(mode="json")
    expanded["requirement"]["requested_track_count"] = 4
    with pytest.raises(ValueError):
        type(target).model_validate(expanded)


def test_1770_second_achieved_set_cannot_claim_journey_completion():
    journey, _, policy, _, result, _ = run()
    short = six_tracks()[-1]
    changed = result.model_copy(update={"tracks":(result.tracks[0], replace(result.tracks[1], candidate=short), *result.tracks[2:])})
    assert sum(p.candidate.duration_seconds for p in changed.tracks) == 1770
    with pytest.raises(ValueError, match="independent reconstruction"):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=changed, journey_plan=journey, construction_policy=policy)


def test_no_fixture_identity_or_track_count_special_case():
    changed = tuple(c.model_copy(update={"track_id":f"other:{i}", "artist_name":f"renamed:{c.artist_name}", "title":f"renamed:{c.title}"}) for i,c in enumerate(six_tracks()))
    *_, result, _ = run((*changed, candidate("extra", 1, "extra", 0)))
    assert result.status == "complete"
    assert result.hard_targets.achieved_duration_seconds >= 1800
    assert len(result.input_binding.ordered_track_ids) == 7


def test_residual_artist_capacity_bound_against_exhaustive_prefix_oracle():
    candidates = tuple(candidate(str(i), d, a) for i,(d,a) in enumerate(((8,"a"),(3,"a"),(9,"a"),(7,"b"),(2,"b"),(4,"c"))))
    for cap in (1,2):
        for prefix_length in (0,1,2):
            for prefix in itertools.combinations(candidates, prefix_length):
                if any(sum(c.artist_name == a for c in prefix) > cap for a in ("a","b","c")):
                    continue
                placements = tuple(SimpleNamespace(candidate=c) for c in prefix)
                retained = _retained(candidates, placements, cap)
                remaining = tuple(c for c in candidates if c not in prefix)
                for slots in range(len(remaining)+1):
                    valid = [s for s in itertools.combinations(remaining, slots)
                        if all(sum(c.artist_name == a for c in (*prefix,*s)) <= cap for a in ("a","b","c"))]
                    if valid:
                        assert sum(c.duration_seconds for c in retained[:slots]) == max(sum(c.duration_seconds for c in s) for s in valid)
                    else:
                        assert len(retained) < slots


class SubstitutionSelector(CandidateSelector):
    def select(self, **kwargs):
        ranking = super().select(**kwargs)
        first = ranking.ranked_candidates[0]
        changed = replace(first, candidate=first.candidate.model_copy(update={"duration_seconds":999999}))
        return replace(ranking, ranked_candidates=(changed, *ranking.ranked_candidates[1:]))


def test_selector_cannot_substitute_formed_content():
    with pytest.raises(ValueError, match="content/rank substituted"):
        run(selector=SubstitutionSelector())


def test_report_replay_verification_rejects_changed_facts():
    journey, _, policy, _, result, report = run()
    assert evaluation_report_v3_matches_inputs(report, construction_result=result, journey_plan=journey, construction_policy=policy)
    bad = report.model_copy(update={"hard_targets":report.hard_targets.model_copy(update={"achieved_count":0})})
    assert not evaluation_report_v3_matches_inputs(bad, construction_result=result, journey_plan=journey, construction_policy=policy)


def test_issue_numeric_facts_cannot_contradict_typed_outcomes():
    journey, _, policy, _, result, _ = run()
    bad = result.model_copy(update={"issues":(*result.issues[:-1], replace(result.issues[-1], observed_value=.25))})
    with pytest.raises(ValueError, match="issue arithmetic"):
        PlaylistJourneyEvaluatorV3().evaluate(construction_result=bad, journey_plan=journey, construction_policy=policy)


def test_numeric_canonical_zero_and_integral_union_values_have_one_encoding():
    assert serialize_successor(ConstructionPolicyV2(discovery_familiarity_threshold=-0.0)) == serialize_successor(ConstructionPolicyV2(discovery_familiarity_threshold=0.0))
    *_, result, _ = run()
    issue = result.issues[0]
    assert serialize_successor(result) == serialize_successor(result.model_copy(update={"issues":(replace(issue, observed_value=float(issue.observed_value)), *result.issues[1:])}))


def test_exact_artist_identity_not_casefolded():
    tracks = tuple(candidate(str(i), 600, "Artist" if i < 2 else "artist") for i in range(4))
    *_, result, _ = run(tracks)
    assert result.status == "complete"
    assert result.feasibility.initial_capped_capacity == 4
    assert len(result.feasibility.artist_capacities) == 2


def test_category_necessary_bounds_do_not_claim_joint_duration_quota_feasibility():
    tracks = (*tuple(candidate(str(i), 1, familiarity=1) for i in range(4)),
              candidate("novel1", 900, familiarity=0), candidate("novel2", 900, familiarity=0))
    *_, result, _ = run(tracks, percent=0)
    assert result.status == "complete"
    assert result.discovery.structural_outcome == "NOT_ESTABLISHED"
    assert result.discovery.exact_target_outcome == "MISSED"


@pytest.mark.parametrize("seed", range(12))
def test_guard_never_strands_a_certified_bounded_pool(seed):
    import random
    rng = random.Random(seed)
    tracks = tuple(candidate(str(i), rng.randint(50,1200), f"artist:{rng.randrange(4)}", rng.choice((0.,1.))) for i in range(rng.randint(3,9)))
    *_, result, _ = run(tracks)
    assert result.status in ("complete", "infeasible")
    assert (result.status == "complete") == (result.feasibility.outcome == "FEASIBLE")


def test_raw_candidate_or_pool_inputs_are_not_a_constructor_authority_path():
    journey, parent, policy, target, *_ = run()
    constructor = SequentialPlaylistConstructorV2(policy=policy)
    for supplied in (six_tracks(), derive_formed_candidate_pool(parent), b"bytes", "path"):
        with pytest.raises(TypeError):
            constructor.construct(target=target, journey_plan=journey, formation_parent=supplied)


def test_half_up_uses_exact_authoritative_percentage_not_binary_float():
    class DemandSelector(CandidateSelector):
        def __init__(self):
            super().__init__()
            self.demands = []

        def select(self, **kwargs):
            self.demands.append(kwargs["target_discovery_ratio"])
            return super().select(**kwargs)

    selector = DemandSelector()
    *_, result, report = run(tuple(candidate(str(i)) for i in range(50)),
        mode="TRACK_COUNT", count=50, percent=29, selector=selector)
    assert result.discovery.rounded_ranking_target_count == 15
    assert report.discovery.rounded_ranking_target_count == 15
    assert selector.demands[0] == 15 / 50


def test_constructor_rejects_substituted_score_role():
    from playlist_narrative_engine.sequencing.schemas import TrackRole

    class WrongRoleSelector(CandidateSelector):
        def select(self, **kwargs):
            ranking = super().select(**kwargs)
            first = ranking.ranked_candidates[0]
            bad = replace(first, score_breakdown=first.score_breakdown.model_copy(update={"role":TrackRole.ENERGY_RESET}))
            return replace(ranking, ranked_candidates=(bad, *ranking.ranked_candidates[1:]))

    with pytest.raises(ValueError, match="selected role"):
        run(selector=WrongRoleSelector())

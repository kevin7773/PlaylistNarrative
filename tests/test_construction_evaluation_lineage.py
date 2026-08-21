from __future__ import annotations

from dataclasses import replace

import pytest

from cf3_test_helpers import formed_pool, journey_artifact

from playlist_narrative_engine.evaluation import (
    PlaylistJourneyEvaluator,
    evaluation_report_matches_inputs,
)
from playlist_narrative_engine.journey import ActiveFocusRequest, JourneyPlanner
from playlist_narrative_engine.sequencing import (
    ConstructionPolicy,
    ConstructionState,
    SequentialPlaylistConstructor,
    TrackCandidate,
    construction_policy_sha256,
    construction_result_matches_inputs,
    construction_result_sha256,
    serialize_construction_policy,
    serialize_construction_result,
    verify_construction_result_digest,
)


def candidate(track_id: str, *, preference: float = 0.8) -> TrackCandidate:
    return TrackCandidate(
        track_id=track_id,
        title=f"Title {track_id}",
        artist_name=f"Artist {track_id}",
        duration_seconds=180,
        energy=0.6,
        familiarity=0.5,
        preference=preference,
        context_fit=0.7,
        instrumentalness=0.2,
        lyrical_distraction=0.3,
        groove=0.8,
    )


def authority():
    journey = journey_artifact(
        JourneyPlanner().plan_active_focus(ActiveFocusRequest())
    )
    pool = formed_pool((candidate("a", preference=0.9), candidate("b")))
    policy = ConstructionPolicy()
    return journey, pool, policy


def construct(*, requested_count: int = 2):
    journey, pool, policy = authority()
    state = ConstructionState()
    result = SequentialPlaylistConstructor(policy=policy).construct(
        journey_plan=journey,
        formed_pool=pool,
        state=state,
        requested_track_count=requested_count,
    )
    return journey, pool, policy, state, result


def test_construction_emits_exact_input_authority_and_canonical_policy() -> None:
    journey, pool, policy, _, result = construct()
    binding = result.input_binding

    assert binding.journey_id == journey.journey_id
    assert binding.journey_schema_version == journey.schema_version
    assert binding.formation_parent_sha256 == pool.trace.parent_artifact_sha256
    assert binding.formation_request_id == pool.trace.parent_request_id
    assert binding.construction_policy_sha256 == construction_policy_sha256(policy)
    assert serialize_construction_policy(policy) == serialize_construction_policy(
        ConstructionPolicy()
    )
    assert construction_result_matches_inputs(
        result,
        journey_plan=journey,
        formed_pool=pool,
        construction_policy=policy,
    )


def test_construction_binding_detects_policy_journey_and_formation_substitution() -> None:
    journey, pool, policy, _, result = construct()
    different_policy = ConstructionPolicy(max_tracks_per_artist=1)
    different_journey = journey.model_copy(
        update={"journey_id": "different-journey"}
    )
    different_pool = formed_pool((candidate("other"),))

    assert not construction_result_matches_inputs(
        result,
        journey_plan=journey,
        formed_pool=pool,
        construction_policy=different_policy,
    )
    assert not construction_result_matches_inputs(
        result,
        journey_plan=different_journey,
        formed_pool=pool,
        construction_policy=policy,
    )
    assert not construction_result_matches_inputs(
        result,
        journey_plan=journey,
        formed_pool=different_pool,
        construction_policy=policy,
    )


def test_construction_result_digest_is_deterministic_and_detects_governed_changes() -> None:
    _, _, _, state, result = construct()
    digest = construction_result_sha256(result)

    assert serialize_construction_result(result) == serialize_construction_result(result)
    assert digest == construction_result_sha256(result)
    assert verify_construction_result_digest(result, digest)
    assert not verify_construction_result_digest(
        replace(result, tracks=tuple(reversed(result.tracks))),
        digest,
    )
    altered = replace(
        result,
        input_binding=replace(
            result.input_binding,
            construction_policy_sha256="0" * 64,
        ),
    )
    assert construction_result_sha256(altered) != digest

    state.elapsed_seconds += 1
    state.used_track_ids.add("transient-after-result")
    assert construction_result_sha256(result) == digest


def test_resumed_construction_binds_pre_call_state_authority() -> None:
    journey, pool, policy = authority()
    state = ConstructionState()
    constructor = SequentialPlaylistConstructor(policy=policy)
    first = constructor.construct(
        journey_plan=journey,
        formed_pool=pool,
        state=state,
        requested_track_count=1,
    )
    resumed = constructor.construct(
        journey_plan=journey,
        formed_pool=pool,
        state=state,
        requested_track_count=2,
    )

    assert first.input_binding.initial_placement_count == 0
    assert resumed.input_binding.initial_placement_count == 1
    assert (
        first.input_binding.initial_state_sha256
        != resumed.input_binding.initial_state_sha256
    )


def test_evaluation_binds_exact_construction_journey_and_policy() -> None:
    journey, pool, policy, _, result = construct()
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey,
        construction_policy=policy,
    )

    assert report.input_binding.construction_result_sha256 == construction_result_sha256(
        result
    )
    assert report.input_binding.journey_id == journey.journey_id
    assert report.input_binding.construction_policy_sha256 == construction_policy_sha256(
        policy
    )
    assert evaluation_report_matches_inputs(
        report,
        construction_result=result,
        journey_plan=journey,
        construction_policy=policy,
    )
    assert construction_result_matches_inputs(
        result,
        journey_plan=journey,
        formed_pool=pool,
        construction_policy=policy,
    )


def test_evaluation_binding_rejects_substituted_inputs() -> None:
    journey, _, policy, _, result = construct()
    report = PlaylistJourneyEvaluator().evaluate(
        construction_result=result,
        journey_plan=journey,
        construction_policy=policy,
    )
    _, _, _, _, other_result = construct(requested_count=1)

    assert not evaluation_report_matches_inputs(
        report,
        construction_result=other_result,
        journey_plan=journey,
        construction_policy=policy,
    )
    assert not evaluation_report_matches_inputs(
        report,
        construction_result=result,
        journey_plan=journey.model_copy(update={"journey_id": "other"}),
        construction_policy=policy,
    )
    assert not evaluation_report_matches_inputs(
        report,
        construction_result=result,
        journey_plan=journey,
        construction_policy=ConstructionPolicy(max_tracks_per_artist=1),
    )


def test_evaluator_refuses_journey_or_policy_substitution_before_calculation() -> None:
    journey, _, policy, _, result = construct()
    evaluator = PlaylistJourneyEvaluator()

    with pytest.raises(ValueError, match="construction-time authority"):
        evaluator.evaluate(
            construction_result=result,
            journey_plan=journey.model_copy(update={"journey_id": "other"}),
            construction_policy=policy,
        )
    with pytest.raises(ValueError, match="construction-time authority"):
        evaluator.evaluate(
            construction_result=result,
            journey_plan=journey,
            construction_policy=ConstructionPolicy(max_tracks_per_artist=1),
        )

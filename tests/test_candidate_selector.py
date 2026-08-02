from __future__ import annotations

import pytest

from cf3_test_helpers import formed_pool

from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    JourneyPlanner,
)
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    TrackCandidate,
    TrackRole,
    TrackScorer,
)


def candidate(track_id: str, **overrides: object) -> TrackCandidate:
    values: dict[str, object] = {
        "track_id": track_id,
        "title": f"Synthetic {track_id}",
        "artist_name": "Synthetic Artist",
        "duration_seconds": 240,
        "energy": 0.68,
        "familiarity": 0.60,
        "preference": 0.80,
        "context_fit": 0.90,
        "instrumentalness": 0.75,
        "lyrical_distraction": 0.10,
        "groove": 0.80,
    }
    values.update(overrides)
    return TrackCandidate(**values)


@pytest.fixture
def phase():
    return JourneyPlanner().plan_active_focus(ActiveFocusRequest()).phases[1]


def select(
    candidates,
    phase,
    *,
    target_discovery_ratio: float = 0.20,
    top_n: int = 10,
):
    pool = formed_pool(tuple(candidates))
    return CandidateSelector().select(
        context=JourneyContext.ACTIVE_FOCUS,
        previous_track=None,
        phase=phase,
        role=TrackRole.JOURNEY,
        target_discovery_ratio=target_discovery_ratio,
        formed_pool=pool,
        remaining_track_ids=tuple(
            candidate.track_id for candidate in reversed(pool.candidates)
        ),
        top_n=top_n,
    ).ranked_candidates


def test_candidates_are_ranked_by_adjusted_score(phase) -> None:
    results = select(
        [
            candidate("low", preference=0.30),
            candidate("high", preference=0.95),
            candidate("middle", preference=0.65),
        ],
        phase,
    )
    assert [result.candidate.track_id for result in results] == [
        "high",
        "middle",
        "low",
    ]
    assert [result.rank for result in results] == [1, 2, 3]
    assert results[0].score > results[1].score > results[2].score


def test_equal_scores_use_track_identity_not_input_order(phase) -> None:
    alpha = candidate("alpha")
    beta = candidate("beta")
    forward = select([alpha, beta], phase)
    reverse = select([beta, alpha], phase)
    assert [result.candidate.track_id for result in forward] == [
        "alpha",
        "beta",
    ]
    assert [result.candidate.track_id for result in reverse] == [
        "alpha",
        "beta",
    ]
    assert forward == reverse


def test_discovery_target_modifies_novel_and_familiar_tracks(phase) -> None:
    novel = candidate("novel", familiarity=0.10)
    familiar = candidate("familiar", familiarity=0.90)

    low_budget = {
        result.candidate.track_id: result
        for result in select(
            [novel, familiar],
            phase,
            target_discovery_ratio=0.05,
        )
    }
    high_budget = {
        result.candidate.track_id: result
        for result in select(
            [novel, familiar],
            phase,
            target_discovery_ratio=0.30,
        )
    }

    assert high_budget["novel"].score > low_budget["novel"].score
    assert high_budget["familiar"].score < low_budget["familiar"].score
    assert "Discovery budget favors novelty (+0.4000)" in high_budget[
        "novel"
    ].reasons
    assert "Discovery budget favors familiarity (+0.6000)" in low_budget[
        "familiar"
    ].reasons


def test_phase_target_ratio_is_neutral_and_preserves_scorer_result(
    phase,
) -> None:
    track = candidate("neutral", familiarity=0.10)
    direct = TrackScorer().score(
        track,
        phase,
        context=JourneyContext.ACTIVE_FOCUS,
        role=TrackRole.JOURNEY,
    )
    ranked = select([track], phase, target_discovery_ratio=0.20)[0]
    assert ranked.score == direct.total_score
    assert ranked.score_breakdown == direct
    assert ranked.reasons == direct.reasons


def test_score_explanations_are_preserved_with_budget_reason(phase) -> None:
    ranked = select(
        [candidate("explained", familiarity=0.10, preference=0.95)],
        phase,
        target_discovery_ratio=0.30,
    )[0]
    assert ranked.reasons[: len(ranked.score_breakdown.reasons)] == (
        ranked.score_breakdown.reasons
    )
    assert ranked.reasons[-1].startswith("Discovery budget favors novelty")


def test_top_n_truncates_after_full_ranking(phase) -> None:
    candidates = [
        candidate(f"track-{index:02}", preference=index / 20)
        for index in range(12)
    ]
    results = select(candidates, phase, top_n=3)
    assert len(results) == 3
    assert [result.rank for result in results] == [1, 2, 3]
    assert [result.candidate.track_id for result in results] == [
        "track-11",
        "track-10",
        "track-09",
    ]


def test_default_top_n_is_ten(phase) -> None:
    results = select(
        [candidate(f"track-{index:02}") for index in range(12)],
        phase,
    )
    assert len(results) == 10


def test_empty_candidates_return_empty_ranking(phase) -> None:
    assert select([], phase) == ()


@pytest.mark.parametrize("ratio", [-0.01, 1.01])
def test_discovery_ratio_bounds_are_validated(phase, ratio: float) -> None:
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        select([candidate("track")], phase, target_discovery_ratio=ratio)


@pytest.mark.parametrize("top_n", [0, -1, 1.5, True])
def test_top_n_must_be_a_positive_integer(phase, top_n) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        select([candidate("track")], phase, top_n=top_n)


def test_previous_track_is_used_for_transition_scoring(phase) -> None:
    next_track = candidate("next", energy=0.70, groove=0.82)
    previous = candidate("previous", energy=0.69, groove=0.80)
    result = CandidateSelector().select(
        context=JourneyContext.ACTIVE_FOCUS,
        previous_track=previous,
        phase=phase,
        role=TrackRole.JOURNEY,
        target_discovery_ratio=0.20,
        formed_pool=formed_pool((previous, next_track)),
        remaining_track_ids=(next_track.track_id,),
    ).ranked_candidates[0]
    assert "Smooth groove and energy transition" in result.reasons

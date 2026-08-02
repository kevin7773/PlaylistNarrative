from __future__ import annotations

import pytest

from cf3_test_helpers import formed_pool, journey_artifact

from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    JourneyPlanner,
)
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    ConstructionPolicy,
    ConstructionState,
    ConstructionStatus,
    SequentialPlaylistConstructor,
    TrackCandidate,
)


def candidate(track_id: str, **overrides: object) -> TrackCandidate:
    values: dict[str, object] = {
        "track_id": track_id,
        "title": f"Synthetic {track_id}",
        "artist_name": f"Artist {track_id}",
        "duration_seconds": 210,
        "energy": 0.65,
        "familiarity": 0.70,
        "preference": 0.80,
        "context_fit": 0.90,
        "instrumentalness": 0.70,
        "lyrical_distraction": 0.10,
        "groove": 0.80,
    }
    values.update(overrides)
    return TrackCandidate(**values)


@pytest.fixture
def journey_plan():
    return journey_artifact(
        JourneyPlanner().plan_active_focus(ActiveFocusRequest())
    )


class RecordingSelector(CandidateSelector):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str | None, tuple[str, ...]]] = []

    def select(self, **kwargs):
        previous = kwargs["previous_track"]
        remaining_track_ids = tuple(kwargs["remaining_track_ids"])
        self.calls.append(
            (
                previous.track_id if previous else None,
                remaining_track_ids,
            )
        )
        return super().select(**kwargs)


class BudgetRecordingSelector(CandidateSelector):
    def __init__(self) -> None:
        super().__init__()
        self.target_ratios: list[float] = []

    def select(self, **kwargs):
        self.target_ratios.append(kwargs["target_discovery_ratio"])
        return super().select(**kwargs)


def test_constructor_reranks_after_every_placement(journey_plan) -> None:
    selector = RecordingSelector()
    pool = (
        candidate("a", preference=0.95, familiarity=0.95),
        candidate("b", preference=0.85),
        candidate("c", preference=0.75),
    )
    result = SequentialPlaylistConstructor(selector=selector).construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=ConstructionState(),
        requested_track_count=3,
    )

    assert result.summary.status is ConstructionStatus.COMPLETE
    assert len(selector.calls) == 3
    assert selector.calls[0][0] is None
    assert selector.calls[1][0] == result.tracks[0].candidate.track_id
    assert selector.calls[2][0] == result.tracks[1].candidate.track_id
    assert [len(call[1]) for call in selector.calls] == [3, 2, 1]


def test_transition_changes_the_later_selection(journey_plan) -> None:
    anchor = candidate(
        "anchor",
        energy=0.65,
        groove=0.80,
        preference=0.98,
        familiarity=0.95,
    )
    smooth = candidate(
        "smooth",
        energy=0.66,
        groove=0.82,
        preference=0.75,
    )
    isolated_winner = candidate(
        "isolated-winner",
        energy=0.68,
        groove=0.05,
        preference=0.90,
    )
    selector = CandidateSelector()
    phase = journey_plan.plan.phases[1]
    before_anchor = selector.select(
        context=journey_plan.plan.context,
        previous_track=None,
        phase=phase,
        role="journey",
        target_discovery_ratio=0.20,
        formed_pool=formed_pool((smooth, isolated_winner)),
        remaining_track_ids=(smooth.track_id, isolated_winner.track_id),
        top_n=2,
    )
    assert (
        before_anchor.ranked_candidates[0].candidate.track_id
        == "isolated-winner"
    )

    result = SequentialPlaylistConstructor(selector=selector).construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool((anchor, smooth, isolated_winner)),
        state=ConstructionState(),
        requested_track_count=3,
    )
    assert [track.candidate.track_id for track in result.tracks[:2]] == [
        "anchor",
        "smooth",
    ]
    assert "Smooth groove and energy transition" in result.tracks[1].reasons


def test_construction_is_deterministic_and_pool_order_independent(
    journey_plan,
) -> None:
    pool = tuple(candidate(f"track-{index}") for index in range(5))
    forward = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=ConstructionState(),
        requested_track_count=4,
    )
    reverse = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(tuple(reversed(pool))),
        state=ConstructionState(),
        requested_track_count=4,
    )
    assert forward == reverse
    assert repr(forward).encode("utf-8") == repr(reverse).encode("utf-8")


def test_constructor_and_selector_accumulate_no_hidden_state(
    journey_plan,
) -> None:
    selector = CandidateSelector()
    constructor = SequentialPlaylistConstructor(selector=selector)
    selector_snapshot = dict(selector.__dict__)
    constructor_snapshot = dict(constructor.__dict__)
    plan_snapshot = journey_plan.model_dump_json()
    pool = (candidate("a"), candidate("b"))

    constructor.construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=ConstructionState(),
        requested_track_count=2,
    )

    assert selector.__dict__ == selector_snapshot
    assert constructor.__dict__ == constructor_snapshot
    assert journey_plan.model_dump_json() == plan_snapshot
    assert pool == (candidate("a"), candidate("b"))


def test_tracks_are_never_selected_twice(journey_plan) -> None:
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(
            [candidate(f"track-{index}") for index in range(4)]
        ),
        state=ConstructionState(),
        requested_track_count=4,
    )
    track_ids = [track.candidate.track_id for track in result.tracks]
    assert len(track_ids) == len(set(track_ids)) == 4


def test_caller_candidate_pool_is_unchanged(journey_plan) -> None:
    pool = [
        candidate("a", preference=0.90),
        candidate("b", preference=0.80),
        candidate("c", preference=0.70),
    ]
    original = list(pool)
    SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=ConstructionState(),
        requested_track_count=2,
    )
    assert pool == original
    assert [id(track) for track in pool] == [id(track) for track in original]


def test_candidate_pool_exhaustion_returns_partial_result(journey_plan) -> None:
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool((candidate("a"), candidate("b"))),
        state=ConstructionState(),
        requested_track_count=4,
    )
    assert result.summary.status is ConstructionStatus.PARTIAL
    assert result.summary.achieved_track_count == 2
    assert result.issues[0].code == "candidate_pool_exhausted"
    assert result.issues[0].observed_value == 2
    assert result.issues[0].requested_value == 4


def test_empty_pool_is_gracefully_infeasible(journey_plan) -> None:
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(()),
        state=ConstructionState(),
        requested_track_count=2,
    )
    assert result.tracks == ()
    assert result.summary.status is ConstructionStatus.INFEASIBLE
    assert result.issues[0].code == "candidate_pool_exhausted"


def test_single_track_pool_completes_single_track_request(journey_plan) -> None:
    only = candidate("only")
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool((only,)),
        state=ConstructionState(),
        requested_track_count=1,
    )
    assert result.summary.status is ConstructionStatus.COMPLETE
    assert result.tracks[0].candidate == only
    assert result.tracks[0].position == 1


def test_requested_count_is_enforced(journey_plan) -> None:
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(
            tuple(candidate(f"track-{index}") for index in range(8))
        ),
        state=ConstructionState(),
        requested_track_count=3,
    )
    assert len(result.tracks) == 3
    assert result.summary.requested_track_count == 3
    assert result.summary.achieved_track_count == 3
    assert result.summary.status is ConstructionStatus.COMPLETE


def test_requested_count_is_final_total_when_resuming_state(
    journey_plan,
) -> None:
    pool = tuple(candidate(f"track-{index}") for index in range(4))
    state = ConstructionState()
    constructor = SequentialPlaylistConstructor()
    constructor.construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=state,
        requested_track_count=2,
    )
    resumed = constructor.construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=state,
        requested_track_count=3,
    )
    assert len(resumed.tracks) == 3
    assert resumed.summary.achieved_track_count == 3
    assert len({track.candidate.track_id for track in resumed.tracks}) == 3


def test_exhausted_discovery_demand_reranks_with_zero_target(
    journey_plan,
) -> None:
    discovery = candidate("discovery", familiarity=0.10, preference=1.0)
    familiar_pool = (
        discovery,
        candidate("familiar-a", familiarity=0.90, preference=0.1),
        candidate("familiar-b", familiarity=0.85, preference=0.1),
        candidate("familiar-c", familiarity=0.80, preference=0.1),
        candidate("familiar-d", familiarity=0.75, preference=0.1),
    )
    pool = formed_pool(familiar_pool)
    state = ConstructionState()
    SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=pool,
        state=state,
        requested_track_count=1,
    )
    assert state.discovery_count == 1

    selector = BudgetRecordingSelector()
    SequentialPlaylistConstructor(selector=selector).construct(
        journey_plan=journey_plan,
        formed_pool=pool,
        state=state,
        requested_track_count=5,
    )
    assert selector.target_ratios
    assert set(selector.target_ratios) == {0.0}
    assert state.discovery_count == 1


def test_invalid_resumed_state_is_rejected(journey_plan) -> None:
    pool = (candidate("a"), candidate("b"))
    state = ConstructionState()
    SequentialPlaylistConstructor().construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=state,
        requested_track_count=1,
    )
    state.previous_track = candidate("not-the-last-placement")

    with pytest.raises(
        ValueError,
        match="previous track is not the last placement",
    ):
        SequentialPlaylistConstructor().construct(
            journey_plan=journey_plan,
            formed_pool=formed_pool(pool),
            state=state,
            requested_track_count=2,
        )


def test_highest_ranked_ineligible_artist_is_rejected_visibly(
    journey_plan,
) -> None:
    first = candidate(
        "first",
        artist_name="Repeated Artist",
        preference=0.99,
        familiarity=0.95,
    )
    repeated = candidate(
        "repeated",
        artist_name="Repeated Artist",
        preference=0.98,
    )
    eligible = candidate(
        "eligible",
        artist_name="Other Artist",
        preference=0.70,
    )
    result = SequentialPlaylistConstructor(
        policy=ConstructionPolicy(max_tracks_per_artist=1)
    ).construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool((first, repeated, eligible)),
        state=ConstructionState(),
        requested_track_count=2,
    )
    assert [track.candidate.track_id for track in result.tracks] == [
        "first",
        "eligible",
    ]
    rejection = result.tracks[1].rejected_candidates[0]
    assert rejection.track_id == "repeated"
    assert rejection.code == "artist_repetition_limit"


def test_artist_limit_exhaustion_stops_without_violation(journey_plan) -> None:
    pool = (
        candidate("a", artist_name="One Artist"),
        candidate("b", artist_name="One Artist"),
    )
    result = SequentialPlaylistConstructor(
        policy=ConstructionPolicy(max_tracks_per_artist=1)
    ).construct(
        journey_plan=journey_plan,
        formed_pool=formed_pool(pool),
        state=ConstructionState(),
        requested_track_count=2,
    )
    assert result.summary.status is ConstructionStatus.PARTIAL
    assert result.summary.achieved_track_count == 1
    assert result.issues[0].code == "no_eligible_candidates"
    assert result.summary.artist_counts == (("One Artist", 1),)


@pytest.mark.parametrize("requested_count", [0, -1, 1.5, True])
def test_requested_count_must_be_a_positive_integer(
    journey_plan,
    requested_count,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        SequentialPlaylistConstructor().construct(
            journey_plan=journey_plan,
            formed_pool=formed_pool((candidate("a"),)),
            state=ConstructionState(),
            requested_track_count=requested_count,
        )

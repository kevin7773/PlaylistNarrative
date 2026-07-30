from __future__ import annotations

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.journey import (
    ActiveFocusRequest,
    JourneyPlanner,
)
from playlist_narrative_engine.sequencing import (
    TrackCandidate,
    TrackRole,
    TrackScorer,
    TransitionProfile,
)


def candidate(**overrides: object) -> TrackCandidate:
    values: dict[str, object] = {
        "track_id": "track-1",
        "title": "Synthetic Focus Track",
        "artist_name": "Test Artist",
        "duration_seconds": 240,
        "energy": 0.68,
        "familiarity": 0.90,
        "preference": 0.95,
        "context_fit": 0.95,
        "instrumentalness": 0.80,
        "lyrical_distraction": 0.05,
        "groove": 0.85,
    }
    values.update(overrides)
    return TrackCandidate(**values)


@pytest.fixture
def sustained_phase():
    return JourneyPlanner().plan_active_focus(ActiveFocusRequest()).phases[1]


def test_familiar_preferred_context_track_scores_high(sustained_phase) -> None:
    result = TrackScorer().score(
        candidate(), sustained_phase, role=TrackRole.OPENING_ANCHOR
    )
    assert result.total_score >= 90
    assert "Strong listener preference" in result.reasons
    assert "Strong Active Focus context fit" in result.reasons
    assert "Familiar opening anchor" in result.reasons


def test_lyrical_distraction_reduces_active_focus_score(sustained_phase) -> None:
    scorer = TrackScorer()
    quiet = scorer.score(candidate(lyrical_distraction=0.0), sustained_phase)
    distracting = scorer.score(
        candidate(lyrical_distraction=1.0), sustained_phase
    )
    assert distracting.context_score <= quiet.context_score - 9.5
    assert distracting.total_score < quiet.total_score
    assert "High lyrical distraction for Active Focus" in distracting.reasons


def test_smooth_cross_genre_transition_can_score_well(sustained_phase) -> None:
    previous = candidate(track_id="previous", energy=0.66, groove=0.82)
    profile = TransitionProfile(
        energy_continuity=0.95,
        groove_continuity=0.92,
        emotional_continuity=0.82,
        narrative_continuity=0.88,
        intentional_contrast=0.15,
    )
    result = TrackScorer().score(
        candidate(familiarity=0.55),
        sustained_phase,
        previous_track=previous,
        transition_profile=profile,
    )
    assert result.transition_score >= 18
    assert result.total_score >= 85
    assert "Smooth groove and energy transition" in result.reasons


def test_disjointed_transition_gets_meaningful_penalty(sustained_phase) -> None:
    result = TrackScorer().score(
        candidate(),
        sustained_phase,
        previous_track=candidate(track_id="previous"),
        transition_profile=TransitionProfile(
            energy_continuity=0.10,
            groove_continuity=0.15,
            emotional_continuity=0.20,
            narrative_continuity=0.20,
            intentional_contrast=0.0,
        ),
    )
    assert result.constraint_penalty >= 6
    assert result.narrative_drift_penalty == 0
    assert result.transition_score < 5
    assert "Abrupt transition without intentional contrast" in result.reasons


def test_intentional_contrast_reduces_abrupt_transition_penalty(
    sustained_phase,
) -> None:
    scorer = TrackScorer()
    previous = candidate(track_id="previous")
    abrupt = dict(
        energy_continuity=0.10,
        groove_continuity=0.15,
        emotional_continuity=0.35,
        narrative_continuity=0.40,
    )
    unsupported = scorer.score(
        candidate(),
        sustained_phase,
        previous_track=previous,
        transition_profile=TransitionProfile(
            **abrupt, intentional_contrast=0.0
        ),
    )
    intentional = scorer.score(
        candidate(),
        sustained_phase,
        previous_track=previous,
        transition_profile=TransitionProfile(
            **abrupt, intentional_contrast=0.9
        ),
    )
    assert intentional.constraint_penalty < unsupported.constraint_penalty
    assert intentional.transition_score > unsupported.transition_score
    assert intentional.total_score > unsupported.total_score
    assert (
        "Intentional contrast supports an abrupt transition"
        in intentional.reasons
    )


def test_discovery_does_not_rescue_bad_fit(sustained_phase) -> None:
    result = TrackScorer().score(
        candidate(
            familiarity=0.0,
            preference=0.15,
            context_fit=0.05,
            instrumentalness=0.0,
            lyrical_distraction=1.0,
            energy=0.0,
            groove=0.05,
        ),
        sustained_phase,
        role=TrackRole.DISCOVERY_SPOTLIGHT,
    )
    assert result.discovery_score == 0
    assert result.total_score < 15
    assert (
        "Discovery value withheld because fit thresholds fail"
        in result.reasons
    )


def test_roles_distinguish_controlled_opener_and_qualified_discovery(
    sustained_phase,
) -> None:
    controlled_opener = candidate(
        track_id="controlled-opener",
        energy=0.65,
        familiarity=0.95,
        preference=0.95,
        context_fit=0.90,
        instrumentalness=0.40,
        lyrical_distraction=0.25,
        groove=0.85,
    )
    qualified_discovery = candidate(
        track_id="qualified-discovery",
        energy=0.72,
        familiarity=0.15,
        preference=0.65,
        context_fit=0.72,
        instrumentalness=0.35,
        lyrical_distraction=0.50,
        groove=0.90,
    )
    scorer = TrackScorer()

    opener_as_anchor = scorer.score(
        controlled_opener,
        sustained_phase,
        role=TrackRole.OPENING_ANCHOR,
    )
    discovery_as_anchor = scorer.score(
        qualified_discovery,
        sustained_phase,
        role=TrackRole.OPENING_ANCHOR,
    )
    opener_as_spotlight = scorer.score(
        controlled_opener,
        sustained_phase,
        role=TrackRole.DISCOVERY_SPOTLIGHT,
    )
    discovery_as_spotlight = scorer.score(
        qualified_discovery,
        sustained_phase,
        role=TrackRole.DISCOVERY_SPOTLIGHT,
    )

    assert opener_as_anchor.total_score > discovery_as_anchor.total_score + 20
    assert "Familiar opening anchor" in opener_as_anchor.reasons
    assert "High novelty weakens opening anchor" in discovery_as_anchor.reasons
    assert (
        "Qualified novelty supports discovery spotlight"
        in discovery_as_spotlight.reasons
    )
    anchor_gap = opener_as_anchor.total_score - discovery_as_anchor.total_score
    spotlight_gap = (
        opener_as_spotlight.total_score - discovery_as_spotlight.total_score
    )
    assert spotlight_gap < anchor_gap / 3


def test_scores_and_explanations_are_deterministic(sustained_phase) -> None:
    scorer = TrackScorer()
    track = candidate(familiarity=0.25)
    first = scorer.score(track, sustained_phase)
    second = scorer.score(track, sustained_phase)
    assert first == second
    assert first.model_dump_json() == second.model_dump_json()


def test_explicit_penalties_remain_separate_and_reduce_total(
    sustained_phase,
) -> None:
    scorer = TrackScorer()
    baseline = scorer.score(candidate(), sustained_phase)
    penalized = scorer.score(
        candidate(),
        sustained_phase,
        constraint_penalty=4.0,
        narrative_drift_penalty=7.5,
    )
    assert penalized.constraint_penalty == 4.0
    assert penalized.narrative_drift_penalty == 7.5
    assert penalized.total_score == pytest.approx(
        baseline.total_score - 11.5, abs=0.0001
    )


def test_all_required_track_roles_are_available() -> None:
    assert set(TrackRole) == {
        TrackRole.OPENING_ANCHOR,
        TrackRole.JOURNEY,
        TrackRole.DISCOVERY_SPOTLIGHT,
        TrackRole.ENERGY_RESET,
        TrackRole.PHASE_TRANSITION,
        TrackRole.EPIC_EVENT,
        TrackRole.CLOSING_TRACK,
    }


@pytest.mark.parametrize(
    "field",
    [
        "energy",
        "familiarity",
        "preference",
        "context_fit",
        "instrumentalness",
        "lyrical_distraction",
        "groove",
    ],
)
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_track_candidate_unit_float_bounds(field: str, value: float) -> None:
    with pytest.raises(ValidationError):
        candidate(**{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "energy_continuity",
        "groove_continuity",
        "emotional_continuity",
        "narrative_continuity",
        "intentional_contrast",
    ],
)
@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_transition_profile_unit_float_bounds(field: str, value: float) -> None:
    values = {
        "energy_continuity": 0.5,
        "groove_continuity": 0.5,
        "emotional_continuity": 0.5,
        "narrative_continuity": 0.5,
        "intentional_contrast": 0.5,
    }
    values[field] = value
    with pytest.raises(ValidationError):
        TransitionProfile(**values)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("duration_seconds", 0),
        ("duration_seconds", -1),
        ("track_id", ""),
        ("title", ""),
        ("artist_name", ""),
    ],
)
def test_track_identity_and_duration_are_validated(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        candidate(**{field: value})


def test_transition_profile_requires_previous_track(sustained_phase) -> None:
    with pytest.raises(ValueError, match="requires a previous track"):
        TrackScorer().score(
            candidate(),
            sustained_phase,
            transition_profile=TransitionProfile(
                energy_continuity=1.0,
                groove_continuity=1.0,
                emotional_continuity=1.0,
                narrative_continuity=1.0,
                intentional_contrast=0.0,
            ),
        )

from __future__ import annotations

import ast
from dataclasses import replace
import hashlib
import inspect
from pathlib import Path

import pytest

from cf3_test_helpers import formation_artifact, formed_pool, journey_artifact
from playlist_narrative_engine.candidate_formation import (
    FormedCandidatePoolView,
    derive_formed_candidate_pool,
    serialize_candidate_formation,
    serialize_formed_candidate_pool,
)
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.sequencing import (
    CandidateSelector,
    ConstructionState,
    SequentialPlaylistConstructor,
    TrackCandidate,
    TrackRole,
    serialize_ranking_result,
)


def candidate(track_id: str, **overrides: object) -> TrackCandidate:
    values: dict[str, object] = {
        "track_id": track_id,
        "title": f"Title {track_id}",
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


def test_view_projects_exact_formed_entries_and_canonical_parent_digest() -> None:
    artifact = formation_artifact((candidate("b"), candidate("a")))

    view = derive_formed_candidate_pool(artifact)

    assert view.formed_entries == artifact.formed
    assert view.candidates == tuple(entry.candidate for entry in artifact.formed)
    assert tuple(item.track_id for item in view.candidates) == ("a", "b")
    assert not hasattr(view, "withheld")
    assert not hasattr(view, "withholding_reasons")
    assert view.trace.parent_artifact_sha256 == hashlib.sha256(
        serialize_candidate_formation(artifact)
    ).hexdigest()


def test_view_cannot_be_constructed_from_caller_supplied_candidates() -> None:
    pool = formed_pool((candidate("a"),))

    with pytest.raises(TypeError, match="must be derived"):
        FormedCandidatePoolView(
            trace=pool.trace,
            formed_entries=pool.formed_entries,
        )
    with pytest.raises(TypeError, match="cannot be rewritten"):
        pool.model_copy(update={"formed_entries": ()})


def test_equivalent_parent_artifacts_produce_equal_canonical_views() -> None:
    first = derive_formed_candidate_pool(
        formation_artifact((candidate("b"), candidate("a")))
    )
    second = derive_formed_candidate_pool(
        formation_artifact((candidate("a"), candidate("b")))
    )

    assert first == second
    assert serialize_formed_candidate_pool(first) == serialize_formed_candidate_pool(
        second
    )


def test_remaining_id_order_is_membership_only_and_resolves_canonically() -> None:
    pool = formed_pool((candidate("c"), candidate("a"), candidate("b")))
    phase = journey_artifact().plan.phases[1]
    selector = CandidateSelector()

    forward = selector.select(
        context=JourneyContext.ACTIVE_FOCUS,
        previous_track=None,
        phase=phase,
        role=TrackRole.JOURNEY,
        target_discovery_ratio=0.20,
        formed_pool=pool,
        remaining_track_ids=("a", "c"),
    )
    reverse = selector.select(
        context=JourneyContext.ACTIVE_FOCUS,
        previous_track=None,
        phase=phase,
        role=TrackRole.JOURNEY,
        target_discovery_ratio=0.20,
        formed_pool=pool,
        remaining_track_ids=("c", "a"),
    )

    assert forward == reverse
    assert serialize_ranking_result(forward) == serialize_ranking_result(reverse)
    assert forward.remaining_track_ids == ("a", "c")
    assert forward.formation_trace == pool.trace
    assert all(
        not hasattr(ranked, "formation_trace")
        for ranked in forward.ranked_candidates
    )


@pytest.mark.parametrize("track_ids", (("a", "a"), ("A",), ("a ",), ("á",)))
def test_remaining_ids_reject_duplicates_and_near_matches(
    track_ids: tuple[str, ...],
) -> None:
    pool = formed_pool((candidate("a"),))

    with pytest.raises(ValueError):
        pool.resolve_remaining(track_ids)


def test_previous_track_must_exactly_equal_formed_candidate() -> None:
    original = candidate("a")
    pool = formed_pool((original, candidate("b")))

    with pytest.raises(ValueError, match="previous track must exactly equal"):
        CandidateSelector().select(
            context=JourneyContext.ACTIVE_FOCUS,
            previous_track=original.model_copy(update={"energy": 0.1}),
            phase=journey_artifact().plan.phases[1],
            role=TrackRole.JOURNEY,
            target_discovery_ratio=0.20,
            formed_pool=pool,
            remaining_track_ids=("b",),
        )


def test_construction_preserves_trace_and_rejects_wrong_journey() -> None:
    pool = formed_pool((candidate("a"),))
    journey = journey_artifact()
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey,
        formed_pool=pool,
        state=ConstructionState(),
        requested_track_count=1,
    )

    assert result.formation_trace == pool.trace
    wrong = journey.model_copy(update={"journey_id": "other"})
    with pytest.raises(ValueError, match="exactly correspond"):
        SequentialPlaylistConstructor().construct(
            journey_plan=wrong,
            formed_pool=pool,
            state=ConstructionState(),
            requested_track_count=1,
        )


def test_construction_does_not_normalize_artist_identity() -> None:
    pool = formed_pool(
        (
            candidate("a", artist_name="Artist", preference=0.9),
            candidate("b", artist_name="artist", preference=0.8),
        )
    )
    result = SequentialPlaylistConstructor().construct(
        journey_plan=journey_artifact(),
        formed_pool=pool,
        state=ConstructionState(),
        requested_track_count=2,
    )

    assert tuple(track.candidate.artist_name for track in result.tracks) == (
        "Artist",
        "artist",
    )


def test_resume_requires_exact_formation_journey_and_typed_candidate() -> None:
    first = candidate("a", preference=0.9)
    second = candidate("b", preference=0.8)
    pool = formed_pool((first, second))
    journey = journey_artifact()
    state = ConstructionState()
    constructor = SequentialPlaylistConstructor()
    constructor.construct(
        journey_plan=journey,
        formed_pool=pool,
        state=state,
        requested_track_count=1,
    )

    with pytest.raises(ValueError, match="formation identity"):
        constructor.construct(
            journey_plan=journey,
            formed_pool=formed_pool((first, second, candidate("c"))),
            state=state,
            requested_track_count=2,
        )

    changed = state.placed_tracks[0].candidate.model_copy(update={"energy": 0.1})
    state.placed_tracks[0] = replace(state.placed_tracks[0], candidate=changed)
    state.previous_track = changed
    with pytest.raises(ValueError, match="exactly equal formed candidate"):
        constructor.construct(
            journey_plan=journey,
            formed_pool=pool,
            state=state,
            requested_track_count=2,
        )


def test_resume_cannot_adopt_lineage_after_state_already_exists() -> None:
    pool = formed_pool((candidate("a"), candidate("b")))
    journey = journey_artifact()
    state = ConstructionState()
    SequentialPlaylistConstructor().construct(
        journey_plan=journey,
        formed_pool=pool,
        state=state,
        requested_track_count=1,
    )
    state.formation_trace = None
    state.journey_plan_artifact = None

    with pytest.raises(ValueError, match="requires immutable formation lineage"):
        SequentialPlaylistConstructor().construct(
            journey_plan=journey,
            formed_pool=pool,
            state=state,
            requested_track_count=2,
        )

def test_production_entry_points_have_no_raw_candidate_parameters() -> None:
    selector_parameters = inspect.signature(CandidateSelector.select).parameters
    constructor_parameters = inspect.signature(
        SequentialPlaylistConstructor.construct
    ).parameters

    assert "candidates" not in selector_parameters
    assert "candidate_pool" not in constructor_parameters
    assert "formed_pool" in selector_parameters
    assert "formed_pool" in constructor_parameters
    with pytest.raises(TypeError):
        CandidateSelector().select(candidates=(candidate("a"),))
    with pytest.raises(TypeError):
        SequentialPlaylistConstructor().construct(
            journey_plan=journey_artifact(),
            candidate_pool=(candidate("a"),),
            state=ConstructionState(),
            requested_track_count=1,
        )


def test_sequencing_source_has_no_candidate_construction_or_withheld_access() -> None:
    source_root = (
        Path(__file__).parents[1]
        / "src"
        / "playlist_narrative_engine"
        / "sequencing"
    )
    for filename in ("selector.py", "constructor.py"):
        source = (source_root / filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "TrackCandidate" not in calls
        assert "withheld" not in source
        assert "CandidateFormationArtifact" not in source


def test_only_candidate_formation_constructs_production_track_candidates() -> None:
    source_root = (
        Path(__file__).parents[1] / "src" / "playlist_narrative_engine"
    )
    constructors: list[str] = []
    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "TrackCandidate"
            for node in ast.walk(tree)
        ):
            constructors.append(path.relative_to(source_root).as_posix())

    assert constructors == ["candidate_formation/former.py"]

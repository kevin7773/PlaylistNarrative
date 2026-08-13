from __future__ import annotations

import statistics

import hashlib

import pytest

from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput,
    PersistedPlaylistArtifactInput,
)
from playlist_narrative_engine.research_store.service import (
    ResearchStoreService,
    _position_summary,
)
from sqlalchemy import event
from tests.research_store_helpers import experiment_input


def _profile_experiment(
    *, length: int, generated_title: str, canonical: dict[int, tuple[str, str]]
) -> ExperimentInput:
    tracks = []
    for position in range(1, length + 1):
        if position in canonical:
            title, artist = canonical[position]
            tracks.append({"position": position, "title": title, "artist": artist})
        else:
            tracks.append({
                "position": position,
                "title": f"Unresolved {position}",
                "artist": "Unknown",
                "canonical_identity_established": False,
            })
    return ExperimentInput.model_validate({
        "prompt": f"Prompt for {generated_title}",
        "prompt_title": f"Prompt {generated_title}",
        "generated_title": generated_title,
        "generated_track_count": length,
        "tracks": tracks,
    })


def _unknown_position_experiment() -> ExperimentInput:
    return ExperimentInput.model_validate({
        "prompt": "Unknown placement",
        "prompt_title": "Unknown position prompt",
        "generated_title": "Unknown position playlist",
        "generated_track_count": 10,
        "tracklist_completeness": "PARTIAL",
        "segments": [{
            "segment_ordinal": 1,
            "relationship_to_previous": "FIRST",
            "captures_playlist_start": "YES",
            "captures_playlist_end": "UNKNOWN",
        }],
        "tracks": [
            {
                "observed_ordinal": 1, "evidence_segment": 1,
                "segment_ordinal": 1, "absolute_position": 3,
                "title": "Source", "artist": "Source Artist",
            },
            {
                "observed_ordinal": 2, "evidence_segment": 1,
                "segment_ordinal": 2, "absolute_position": None,
                "title": "Strong", "artist": "Candidate Artist",
            },
        ],
    })


def test_position_summary_quartile_boundaries_and_empty_statistics() -> None:
    forty = [
        {"absolute_position": position, "tracklist_length": 40}
        for position in (1, 10, 11, 20, 21, 30, 31, 40)
    ]
    thirty = [
        {"absolute_position": position, "tracklist_length": 30}
        for position in (1, 8, 9, 15, 16, 23, 24, 30)
    ]
    missing = [{"absolute_position": None, "tracklist_length": 40}]

    for rows in (forty, thirty):
        summary = _position_summary(rows)
        assert [summary[key] for key in (
            "first_quartile_count", "second_quartile_count",
            "third_quartile_count", "fourth_quartile_count",
        )] == [2, 2, 2, 2]

    empty = _position_summary(missing)
    assert empty["absolute_positions"] == []
    assert empty["minimum_position"] is None
    assert empty["maximum_position"] is None
    assert empty["mean_position"] is None
    assert empty["median_position"] is None
    assert empty["position_standard_deviation"] is None
    assert empty["unknown_position_count"] == 1
    assert _position_summary([{"absolute_position": 7, "tracklist_length": 10}])[
        "position_standard_deviation"
    ] == 0.0


def _service(research_session) -> ResearchStoreService:
    return ResearchStoreService(ResearchRepository(research_session))


def test_query_surface_delegates_read_only_projections_without_leaking_persistence(
    research_session,
) -> None:
    service = _service(research_session)
    first = service.ingest_experiment(experiment_input(prompt="One", artist="Repeat", title="Same"))
    second = service.ingest_experiment(experiment_input(prompt="Two", artist="Repeat", title="Same"))
    track_id = service.recurring_tracks()[0]["id"]
    writes: list[str] = []

    def record_write(_connection, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(research_session.bind, "before_cursor_execute", record_write)
    try:
        tracks = service.recurring_tracks()
        artists = service.recurring_artists()
        track_occurrences = service.track_occurrences(track_id)
        artist_occurrences = service.artist_occurrences("Repeat")
        track_profile = service.track_profile(track_id)
        artist_profile = service.artist_profile("Repeat")
        recurring_track_profiles = service.recurring_track_profiles()
        recurring_artist_profiles = service.recurring_artist_profiles()
        comparison = service.compare_experiments(first.record_id, second.record_id)
        track_cooccurrences = service.track_cooccurrences(track_id)
        artist_cooccurrences = service.artist_cooccurrences("Repeat")
        track_pair_occurrences = service.track_pair_occurrences(track_id, 999_999)
        artist_pair_occurrences = service.artist_pair_occurrences("Repeat", "Absent")
        track_pairs = service.recurring_track_pairs()
        artist_pairs = service.recurring_artist_pairs()
    finally:
        event.remove(research_session.bind, "before_cursor_execute", record_write)

    assert tracks[0]["experiment_count"] == 2
    assert artists[0]["experiment_count"] == 2
    assert len(track_occurrences) == 2
    assert len(artist_occurrences) == 2
    assert track_profile is not None
    assert artist_profile is not None
    assert recurring_track_profiles
    assert recurring_artist_profiles
    assert comparison is not None
    assert track_cooccurrences == []
    assert artist_cooccurrences == []
    assert track_pair_occurrences == []
    assert artist_pair_occurrences == []
    assert track_pairs == []
    assert artist_pairs == []
    assert writes == []
    assert all(isinstance(item, dict) for item in track_occurrences)
    assert not any(
        isinstance(value, ResearchRepository)
        for item in (tracks + artists + track_occurrences + artist_occurrences)
        for value in item.values()
    )


def test_recurrence_profiles_use_relative_quartiles_and_population_statistics(
    research_session,
) -> None:
    service = _service(research_session)
    first = service.ingest_experiment(_profile_experiment(
        length=40,
        generated_title="Forty A",
        canonical={10: ("Same", "Repeat"), 31: ("Other", "Repeat")},
    ))
    second = service.ingest_experiment(_profile_experiment(
        length=30,
        generated_title="Thirty",
        canonical={8: ("Same", "Repeat")},
    ))
    third = service.ingest_experiment(_profile_experiment(
        length=40,
        generated_title="Forty B",
        canonical={11: ("Same", "Repeat")},
    ))
    track_id = next(
        item["id"] for item in service.recurring_tracks()
        if item["canonical_title"] == "Same"
    )

    track = service.track_profile(track_id)
    artist = service.artist_profile("Repeat")

    assert track is not None
    assert track["experiment_count"] == 3
    assert track["appearance_count"] == 3
    assert track["absolute_positions"] == [10, 8, 11]
    assert track["minimum_position"] == 8
    assert track["maximum_position"] == 11
    assert track["mean_position"] == 29 / 3
    assert track["median_position"] == 10
    assert track["position_standard_deviation"] == statistics.pstdev([10, 8, 11])
    assert track["first_quartile_count"] == 2
    assert track["second_quartile_count"] == 1
    assert track["third_quartile_count"] == 0
    assert track["fourth_quartile_count"] == 0
    assert [item["tracklist_length"] for item in track["occurrences"]] == [40, 30, 40]
    assert [item["experiment_id"] for item in track["occurrences"]] == [
        first.record_id, second.record_id, third.record_id,
    ]

    assert artist is not None
    assert artist["experiment_count"] == 3
    assert artist["appearance_count"] == 4
    assert artist["positions"] == [10, 31, 8, 11]
    assert artist["first_quartile_count"] == 2
    assert artist["second_quartile_count"] == 1
    assert artist["fourth_quartile_count"] == 1
    assert service.artist_profile("repeat") is None
    assert service.track_profile(999_999) is None


def test_profile_rankings_and_pairwise_overlap_use_only_canonical_identity(
    research_session,
) -> None:
    service = _service(research_session)
    first = service.ingest_experiment(_profile_experiment(
        length=4,
        generated_title="First",
        canonical={1: ("Shared", "Repeat"), 4: ("Only A", "Repeat")},
    ))
    second = service.ingest_experiment(_profile_experiment(
        length=3,
        generated_title="Second",
        canonical={2: ("Shared", "Repeat")},
    ))

    track_profiles = service.recurring_track_profiles(10)
    artist_profiles = service.recurring_artist_profiles(10)
    comparison = service.compare_experiments(first.record_id, second.record_id)

    assert track_profiles[0]["canonical_title"] == "Shared"
    assert track_profiles[0]["experiment_count"] == 2
    assert artist_profiles[0]["canonical_artist"] == "Repeat"
    assert artist_profiles[0]["appearance_count"] == 3
    assert comparison == {
        "experiment_id_a": first.record_id,
        "experiment_id_b": second.record_id,
        "generated_title_a": "First",
        "generated_title_b": "Second",
        "track_count_a": 4,
        "track_count_b": 3,
        "shared_canonical_track_ids": [track_profiles[0]["canonical_track_id"]],
        "shared_canonical_track_count": 1,
        "track_overlap_ratio_a": 0.5,
        "track_overlap_ratio_b": 1.0,
        "shared_canonical_artists": ["Repeat"],
        "shared_canonical_artist_count": 1,
        "artist_overlap_ratio_a": 1.0,
        "artist_overlap_ratio_b": 1.0,
    }
    assert service.compare_experiments(first.record_id, 999_999) is None


def test_q3_track_and_artist_cooccurrence_counts_support_and_positions(
    research_session,
) -> None:
    service = _service(research_session)
    first = service.ingest_experiment(_profile_experiment(
        length=8,
        generated_title="First pair",
        canonical={
            1: ("Source", "Source Artist"),
            3: ("Strong", "Candidate Artist"),
            4: ("Another", "Candidate Artist"),
            8: ("Weak", "Weak Artist"),
        },
    ))
    second = service.ingest_experiment(_profile_experiment(
        length=6,
        generated_title="Second pair",
        canonical={
            2: ("Source", "Source Artist"),
            5: ("Strong", "Candidate Artist"),
            6: ("Another", "Candidate Artist"),
        },
    ))
    third = service.ingest_experiment(_unknown_position_experiment())
    recurring = service.recurring_tracks(20)
    source_id = next(item["id"] for item in recurring if item["canonical_title"] == "Source")
    strong_id = next(item["id"] for item in recurring if item["canonical_title"] == "Strong")

    track_rows = service.track_cooccurrences(source_id, 20)
    artist_rows = service.artist_cooccurrences("Source Artist", 20)
    pair_rows = service.track_pair_occurrences(source_id, strong_id)
    artist_pair_rows = service.artist_pair_occurrences("Source Artist", "Candidate Artist")

    assert track_rows[0] == {
        "canonical_track_id": strong_id,
        "canonical_title": "Strong",
        "canonical_artist": "Candidate Artist",
        "experiment_count_together": 3,
        "appearance_count_together": 3,
        "source_track_experiment_count": 3,
        "candidate_track_experiment_count": 3,
        "shared_experiment_ids": [first.record_id, second.record_id, third.record_id],
        "shared_experiment_count": 3,
        "source_support_ratio": 1.0,
        "candidate_support_ratio": 1.0,
    }
    assert track_rows[-1]["canonical_title"] == "Weak"
    assert track_rows[-1]["shared_experiment_count"] == 1
    assert service.track_cooccurrences(source_id, 1) == track_rows[:1]
    assert service.artist_cooccurrences("source artist") == []
    assert artist_rows[0]["canonical_artist"] == "Candidate Artist"
    assert artist_rows[0]["experiment_count_together"] == 3
    assert artist_rows[0]["shared_experiment_count"] == 3

    assert [item["experiment_id"] for item in pair_rows] == [
        first.record_id, second.record_id, third.record_id,
    ]
    assert pair_rows[0]["track_a_absolute_position"] == 1
    assert pair_rows[0]["track_b_absolute_position"] == 3
    assert pair_rows[0]["absolute_position_distance"] == 2
    assert pair_rows[0]["track_a_normalized_position"] == 1 / 8
    assert pair_rows[0]["track_b_normalized_position"] == 3 / 8
    assert pair_rows[0]["normalized_distance"] == 2 / 8
    assert pair_rows[2]["track_a_absolute_position"] == 3
    assert pair_rows[2]["track_b_absolute_position"] is None
    assert pair_rows[2]["track_b_absolute_positions"] == []
    assert pair_rows[2]["absolute_position_distance"] is None
    assert pair_rows[2]["normalized_distance"] is None

    assert len(artist_pair_rows[0]["artist_b_placements"]) == 2
    assert len(artist_pair_rows[1]["artist_b_placements"]) == 2
    assert len(artist_pair_rows[2]["artist_b_placements"]) == 1
    assert service.artist_pair_occurrences("source artist", "Candidate Artist") == []


def test_q3_recurring_pairs_are_unique_filtered_and_deterministic(
    research_session,
) -> None:
    service = _service(research_session)
    for number in range(3):
        canonical = {
            1: ("Source", "Source Artist"),
            2: ("Strong", "Candidate Artist"),
        }
        if number < 2:
            canonical[3] = ("Medium", "Medium Artist")
        if number == 0:
            canonical[4] = ("Weak", "Weak Artist")
        service.ingest_experiment(_profile_experiment(
            length=5,
            generated_title=f"Pair {number}",
            canonical=canonical,
        ))

    track_pairs = service.recurring_track_pairs(20, 2)
    artist_pairs = service.recurring_artist_pairs(20, 2)

    assert all(
        item["track_a_canonical_id"] < item["track_b_canonical_id"]
        for item in track_pairs
    )
    assert len({
        (item["track_a_canonical_id"], item["track_b_canonical_id"])
        for item in track_pairs
    }) == len(track_pairs)
    assert [item["shared_experiment_count"] for item in track_pairs] == sorted(
        [item["shared_experiment_count"] for item in track_pairs], reverse=True
    )
    assert all(item["shared_experiment_count"] >= 2 for item in track_pairs)
    assert service.recurring_track_pairs(1, 2) == track_pairs[:1]
    assert all(item["artist_a"] < item["artist_b"] for item in artist_pairs)
    assert all(item["shared_experiment_count"] >= 2 for item in artist_pairs)
    strongest = track_pairs[0]
    assert strongest["shared_experiment_count"] == 3
    assert strongest["track_a_support_ratio"] == 1.0
    assert strongest["track_b_support_ratio"] == 1.0


def _experiment(**changes) -> dict[str, object]:
    proposal: dict[str, object] = {
        "prompt": "Exact prompt",
        "tracklist_completeness": "NOT_OBSERVED",
        "tracks": [],
    }
    proposal.update(changes)
    return proposal


def _artifact(**changes) -> dict[str, object]:
    proposal: dict[str, object] = {
        "persistence_state": "UNKNOWN",
        "tracklist_completeness": "NOT_OBSERVED",
    }
    proposal.update(changes)
    return proposal


def test_validation_returns_existing_schema_failures_without_writing(research_session) -> None:
    service = _service(research_session)

    result = service.validate_experiment(_experiment(tracklist_completeness="COMPLETE"))

    assert not result.valid
    assert result.value is None
    assert any("COMPLETE requires observed track evidence" in issue.message for issue in result.issues)
    assert service.get_experiment(1) is None


def test_valid_proposals_return_existing_schema_objects_without_writing(research_session) -> None:
    service = _service(research_session)

    experiment = service.validate_experiment(_experiment())
    artifact = service.validate_persisted_artifact(_artifact())

    assert experiment.valid and isinstance(experiment.value, ExperimentInput)
    assert artifact.valid and isinstance(artifact.value, PersistedPlaylistArtifactInput)
    assert service.get_experiment(1) is None
    assert service.get_persisted_artifact(1) is None


def test_evidence_verification_is_read_only_and_reports_exact_failures(
    research_session, tmp_path
) -> None:
    evidence = tmp_path / "capture.png"
    evidence.write_bytes(b"original evidence")
    missing = tmp_path / "missing.png"
    draft = ExperimentInput.model_validate(_experiment(evidence_sources=[
        {
            "source_key": "valid",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 1",
            "local_path": str(evidence),
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        },
        {
            "source_key": "mismatch",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 2",
            "local_path": str(evidence),
            "sha256": "0" * 64,
        },
        {
            "source_key": "missing",
            "source_type": "SCREENSHOT",
            "source_reference": "capture 3",
            "local_path": str(missing),
            "sha256": "1" * 64,
        },
    ]))
    service = _service(research_session)

    result = service.verify_experiment_evidence(draft)

    assert [issue.issue_type for issue in result.issues] == [
        "checksum_mismatch", "file_not_found"
    ]
    assert service.get_experiment(1) is None


def test_single_experiment_ingestion_delegates_and_reads_back(research_session) -> None:
    service = _service(research_session)
    draft = ExperimentInput.model_validate(_experiment())

    inserted = service.ingest_experiment(draft)

    assert inserted.kind == "experiment"
    assert inserted.record_id == 1
    assert inserted.record == service.get_experiment(1)
    assert inserted.record["prompt"] == "Exact prompt"


def test_read_back_does_not_block_next_single_record_transaction(research_session) -> None:
    service = _service(research_session)

    first = service.ingest_experiment(ExperimentInput.model_validate(_experiment()))
    second = service.ingest_experiment(ExperimentInput.model_validate(
        _experiment(prompt="Second")
    ))

    assert first.record_id == 1
    assert second.record_id == 2
    assert second.record["prompt"] == "Second"


def test_single_artifact_ingestion_delegates_and_reads_back(research_session) -> None:
    service = _service(research_session)
    draft = PersistedPlaylistArtifactInput.model_validate(_artifact())

    inserted = service.ingest_persisted_artifact(draft)

    assert inserted.kind == "persisted_artifact"
    assert inserted.record_id == 1
    assert inserted.record == service.get_persisted_artifact(1)
    assert inserted.record["persistence_state"] == "UNKNOWN"


def test_ingestion_rejects_unvalidated_input_before_repository_use(research_session) -> None:
    service = _service(research_session)

    with pytest.raises(TypeError, match="validated ExperimentInput"):
        service.ingest_experiment(_experiment())  # type: ignore[arg-type]

    assert service.get_experiment(1) is None

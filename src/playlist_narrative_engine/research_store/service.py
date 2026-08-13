from __future__ import annotations

import hashlib
import itertools
import statistics
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Iterator, Literal, TypeVar

from pydantic import ValidationError

from playlist_narrative_engine.research_store.database import (
    make_research_engine,
    make_research_session_factory,
)
from playlist_narrative_engine.research_store.migrations import migrate_research_database
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.study_repository import StudyRepository
from playlist_narrative_engine.research_store.schemas import (
    EvidenceSourceInput,
    ExperimentInput,
    GenerationFailureInput,
    PersistedPlaylistArtifactInput,
)
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyProtocolAmendmentInput,
    StudyRegistrationInput,
    StudyRunDisposition,
)


ValidatedValue = TypeVar("ValidatedValue")
QueryValue = TypeVar("QueryValue")
RecordKind = Literal["experiment", "persisted_artifact"]


@dataclass(frozen=True)
class ValidationIssue:
    location: tuple[str | int, ...]
    message: str
    issue_type: str


@dataclass(frozen=True)
class ValidationResult(Generic[ValidatedValue]):
    value: ValidatedValue | None
    issues: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return self.value is not None and not self.issues


@dataclass(frozen=True)
class EvidenceVerificationIssue:
    source_key: str
    local_path: str
    issue_type: Literal["file_not_found", "checksum_mismatch"]
    message: str


@dataclass(frozen=True)
class EvidenceVerificationResult:
    issues: tuple[EvidenceVerificationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class IngestedRecord:
    kind: RecordKind
    record_id: int
    record: dict[str, object]


class ResearchStoreService:
    """Orchestrate existing research-store operations without adding semantics."""

    def __init__(self, repository: ResearchRepository) -> None:
        self._repository = repository
        self._studies = StudyRepository(repository.session)

    @staticmethod
    def validate_experiment(proposal: object) -> ValidationResult[ExperimentInput]:
        return _validate(ExperimentInput, proposal)

    @staticmethod
    def validate_persisted_artifact(
        proposal: object,
    ) -> ValidationResult[PersistedPlaylistArtifactInput]:
        return _validate(PersistedPlaylistArtifactInput, proposal)

    @staticmethod
    def validate_study_protocol(
        proposal: object,
    ) -> ValidationResult[StudyRegistrationInput]:
        return _validate(StudyRegistrationInput, proposal)

    @staticmethod
    def validate_study_protocol_amendment(
        proposal: object,
    ) -> ValidationResult[StudyProtocolAmendmentInput]:
        return _validate(StudyProtocolAmendmentInput, proposal)

    def register_study(self, proposal: StudyRegistrationInput) -> dict[str, object]:
        _require_type(proposal, StudyRegistrationInput)
        return self._studies.register_study(proposal)

    def register_protocol_amendment(
        self, study_id: int, proposal: StudyProtocolAmendmentInput
    ) -> dict[str, object]:
        _require_type(proposal, StudyProtocolAmendmentInput)
        return self._studies.register_protocol_amendment(study_id, proposal)

    def get_study(self, study_id_or_key: int | str) -> dict[str, object] | None:
        return self._read_projection(self._studies.get_study, study_id_or_key)

    def get_protocol_version(
        self, study_id_or_key: int | str, version: int
    ) -> dict[str, object] | None:
        return self._read_query(
            self._studies.get_protocol_version, study_id_or_key, version
        )

    def list_studies(self) -> list[dict[str, object]]:
        return self._read_query(self._studies.list_studies)

    def record_study_operational_attempt(
        self, planned_run_id: int, proposal: StudyOperationalAttemptInput
    ) -> dict[str, object]:
        _require_type(proposal, StudyOperationalAttemptInput)
        return self._studies.record_operational_attempt(planned_run_id, proposal)

    def ingest_planned_experiment(
        self, planned_run_id: int, proposal: ExperimentInput
    ) -> dict[str, object]:
        _require_type(proposal, ExperimentInput)
        return self._studies.realize_experiment(planned_run_id, proposal)

    def record_planned_generation_failure(
        self,
        planned_run_id: int,
        proposal: GenerationFailureInput,
        disposition: StudyRunDisposition,
    ) -> dict[str, object]:
        _require_type(proposal, GenerationFailureInput)
        return self._studies.realize_generation_failure(
            planned_run_id, proposal, disposition
        )

    @staticmethod
    def verify_experiment_evidence(
        proposal: ExperimentInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    @staticmethod
    def verify_persisted_artifact_evidence(
        proposal: PersistedPlaylistArtifactInput,
    ) -> EvidenceVerificationResult:
        return _verify_sources(proposal.evidence_sources)

    def ingest_experiment(self, proposal: ExperimentInput) -> IngestedRecord:
        _require_type(proposal, ExperimentInput)
        record_id = self._repository.insert_experiment(proposal)
        record = self._read_experiment(record_id)
        if record is None:
            raise RuntimeError("inserted experiment could not be read back")
        return IngestedRecord("experiment", record_id, record)

    def ingest_persisted_artifact(
        self, proposal: PersistedPlaylistArtifactInput
    ) -> IngestedRecord:
        _require_type(proposal, PersistedPlaylistArtifactInput)
        record_id = self._repository.insert_persisted_artifact(proposal)
        record = self._read_persisted_artifact(record_id)
        if record is None:
            raise RuntimeError("inserted persisted artifact could not be read back")
        return IngestedRecord("persisted_artifact", record_id, record)

    def get_experiment(self, record_id: int) -> dict[str, object] | None:
        return self._read_experiment(record_id)

    def get_persisted_artifact(self, record_id: int) -> dict[str, object] | None:
        return self._read_persisted_artifact(record_id)

    def query_experiments(
        self, *, assessment: str | None = None,
        assessment_outcome: str | None = None,
        constraint_status: str | None = None,
        saved: bool | None = None,
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.query_experiments,
            assessment=assessment,
            assessment_outcome=assessment_outcome,
            constraint_status=constraint_status,
            saved=saved,
        )

    def recurring_tracks(self, limit: int = 20) -> list[dict[str, object]]:
        return self._read_query(self._repository.recurring_tracks, limit)

    def recurring_artists(self, limit: int = 20) -> list[dict[str, object]]:
        return self._read_query(self._repository.recurring_artists, limit)

    def track_occurrences(
        self, canonical_track_id: int
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.track_occurrences, canonical_track_id
        )

    def artist_occurrences(
        self, canonical_artist: str
    ) -> list[dict[str, object]]:
        return self._read_query(
            self._repository.artist_occurrences, canonical_artist
        )

    def track_profile(
        self, canonical_track_id: int
    ) -> dict[str, object] | None:
        occurrences = self.track_occurrences(canonical_track_id)
        if not occurrences:
            return None
        summary = _position_summary(occurrences)
        first = occurrences[0]
        return {
            "canonical_track_id": canonical_track_id,
            "canonical_title": first["canonical_title"],
            "canonical_artist": first["canonical_artist"],
            "experiment_count": len({item["experiment_id"] for item in occurrences}),
            "appearance_count": len(occurrences),
            **summary,
            "occurrences": occurrences,
        }

    def artist_profile(
        self, canonical_artist: str
    ) -> dict[str, object] | None:
        occurrences = self.artist_occurrences(canonical_artist)
        if not occurrences:
            return None
        summary = _position_summary(occurrences, position_key="positions")
        return {
            "canonical_artist": canonical_artist,
            "experiment_count": len({item["experiment_id"] for item in occurrences}),
            "appearance_count": len(occurrences),
            **summary,
            "occurrences": occurrences,
        }

    def recurring_track_profiles(self, limit: int = 20) -> list[dict[str, object]]:
        profiles: list[dict[str, object]] = []
        for item in self.recurring_tracks(limit):
            profile = self.track_profile(int(item["id"]))
            if profile is not None:
                profiles.append(profile)
        return profiles

    def recurring_artist_profiles(self, limit: int = 20) -> list[dict[str, object]]:
        profiles: list[dict[str, object]] = []
        for item in self.recurring_artists(limit):
            profile = self.artist_profile(str(item["canonical_artist"]))
            if profile is not None:
                profiles.append(profile)
        return profiles

    def compare_experiments(
        self, experiment_id_a: int, experiment_id_b: int
    ) -> dict[str, object] | None:
        experiment_a = self.get_experiment(experiment_id_a)
        experiment_b = self.get_experiment(experiment_id_b)
        if experiment_a is None or experiment_b is None:
            return None
        tracks_a = {
            int(item["track_id"])
            for item in experiment_a["tracks"]
            if item["track_id"] is not None
        }
        tracks_b = {
            int(item["track_id"])
            for item in experiment_b["tracks"]
            if item["track_id"] is not None
        }
        artists_a = {
            str(item["canonical_artist"])
            for item in experiment_a["tracks"]
            if item["track_id"] is not None
        }
        artists_b = {
            str(item["canonical_artist"])
            for item in experiment_b["tracks"]
            if item["track_id"] is not None
        }
        shared_tracks = sorted(tracks_a & tracks_b)
        shared_artists = sorted(artists_a & artists_b)
        return {
            "experiment_id_a": experiment_id_a,
            "experiment_id_b": experiment_id_b,
            "generated_title_a": experiment_a["generated_title"],
            "generated_title_b": experiment_b["generated_title"],
            "track_count_a": len(experiment_a["tracks"]),
            "track_count_b": len(experiment_b["tracks"]),
            "shared_canonical_track_ids": shared_tracks,
            "shared_canonical_track_count": len(shared_tracks),
            "track_overlap_ratio_a": _ratio(len(shared_tracks), len(tracks_a)),
            "track_overlap_ratio_b": _ratio(len(shared_tracks), len(tracks_b)),
            "shared_canonical_artists": shared_artists,
            "shared_canonical_artist_count": len(shared_artists),
            "artist_overlap_ratio_a": _ratio(len(shared_artists), len(artists_a)),
            "artist_overlap_ratio_b": _ratio(len(shared_artists), len(artists_b)),
        }

    def track_cooccurrences(
        self, canonical_track_id: int, limit: int = 20
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        track_sets, track_appearances, catalog = _track_corpus(experiments)
        source_experiments = track_sets.get(canonical_track_id, set())
        results: list[dict[str, object]] = []
        for candidate_id, candidate_experiments in track_sets.items():
            if candidate_id == canonical_track_id:
                continue
            shared = sorted(source_experiments & candidate_experiments)
            if not shared:
                continue
            candidate = catalog[candidate_id]
            results.append({
                "canonical_track_id": candidate_id,
                "canonical_title": candidate["canonical_title"],
                "canonical_artist": candidate["canonical_artist"],
                "experiment_count_together": len(shared),
                "appearance_count_together": sum(
                    track_appearances[(experiment_id, candidate_id)]
                    for experiment_id in shared
                ),
                "source_track_experiment_count": len(source_experiments),
                "candidate_track_experiment_count": len(candidate_experiments),
                "shared_experiment_ids": shared,
                "shared_experiment_count": len(shared),
                "source_support_ratio": _ratio(len(shared), len(source_experiments)),
                "candidate_support_ratio": _ratio(len(shared), len(candidate_experiments)),
            })
        return sorted(
            results,
            key=lambda item: (-int(item["shared_experiment_count"]), int(item["canonical_track_id"])),
        )[:limit]

    def artist_cooccurrences(
        self, canonical_artist: str, limit: int = 20
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        artist_sets = _artist_experiment_sets(experiments)
        source_experiments = artist_sets.get(canonical_artist, set())
        results: list[dict[str, object]] = []
        for candidate, candidate_experiments in artist_sets.items():
            if candidate == canonical_artist:
                continue
            shared = sorted(source_experiments & candidate_experiments)
            if not shared:
                continue
            results.append({
                "canonical_artist": candidate,
                "experiment_count_together": len(shared),
                "source_artist_experiment_count": len(source_experiments),
                "candidate_artist_experiment_count": len(candidate_experiments),
                "shared_experiment_ids": shared,
                "shared_experiment_count": len(shared),
                "source_support_ratio": _ratio(len(shared), len(source_experiments)),
                "candidate_support_ratio": _ratio(len(shared), len(candidate_experiments)),
            })
        return sorted(
            results,
            key=lambda item: (-int(item["shared_experiment_count"]), str(item["canonical_artist"])),
        )[:limit]

    def track_pair_occurrences(
        self, canonical_track_id_a: int, canonical_track_id_b: int
    ) -> list[dict[str, object]]:
        if canonical_track_id_a == canonical_track_id_b:
            return []
        results: list[dict[str, object]] = []
        for experiment in self._all_experiments():
            placements_a = [
                item for item in experiment["tracks"]
                if item["track_id"] == canonical_track_id_a
            ]
            placements_b = [
                item for item in experiment["tracks"]
                if item["track_id"] == canonical_track_id_b
            ]
            if not placements_a or not placements_b:
                continue
            length = _experiment_tracklist_length(experiment)
            position_a = _single_position(placements_a)
            position_b = _single_position(placements_b)
            normalized_a = _normalized_position(position_a, length)
            normalized_b = _normalized_position(position_b, length)
            results.append({
                "experiment_id": experiment["id"],
                "generated_title": experiment["generated_title"],
                "prompt_title": experiment["prompt_title"],
                "tracklist_length": length,
                "track_a_absolute_position": position_a,
                "track_b_absolute_position": position_b,
                "track_a_absolute_positions": _known_positions(placements_a),
                "track_b_absolute_positions": _known_positions(placements_b),
                "absolute_position_distance": (
                    abs(position_a - position_b)
                    if position_a is not None and position_b is not None else None
                ),
                "track_a_normalized_position": normalized_a,
                "track_b_normalized_position": normalized_b,
                "normalized_distance": (
                    abs(normalized_a - normalized_b)
                    if normalized_a is not None and normalized_b is not None else None
                ),
            })
        return results

    def artist_pair_occurrences(
        self, canonical_artist_a: str, canonical_artist_b: str
    ) -> list[dict[str, object]]:
        if canonical_artist_a == canonical_artist_b:
            return []
        results: list[dict[str, object]] = []
        for experiment in self._all_experiments():
            placements_a = _artist_placements(experiment, canonical_artist_a)
            placements_b = _artist_placements(experiment, canonical_artist_b)
            if not placements_a or not placements_b:
                continue
            results.append({
                "experiment_id": experiment["id"],
                "generated_title": experiment["generated_title"],
                "prompt_title": experiment["prompt_title"],
                "tracklist_length": _experiment_tracklist_length(experiment),
                "artist_a_placements": placements_a,
                "artist_b_placements": placements_b,
            })
        return results

    def recurring_track_pairs(
        self, limit: int = 20, minimum_shared_experiments: int = 2
    ) -> list[dict[str, object]]:
        experiments = self._all_experiments()
        track_sets, _appearances, catalog = _track_corpus(experiments)
        results: list[dict[str, object]] = []
        for track_a, track_b in itertools.combinations(sorted(track_sets), 2):
            shared = sorted(track_sets[track_a] & track_sets[track_b])
            if len(shared) < minimum_shared_experiments:
                continue
            item_a = catalog[track_a]
            item_b = catalog[track_b]
            results.append({
                "track_a_canonical_id": track_a,
                "track_a_canonical_title": item_a["canonical_title"],
                "track_a_canonical_artist": item_a["canonical_artist"],
                "track_b_canonical_id": track_b,
                "track_b_canonical_title": item_b["canonical_title"],
                "track_b_canonical_artist": item_b["canonical_artist"],
                "shared_experiment_count": len(shared),
                "shared_experiment_ids": shared,
                "track_a_experiment_count": len(track_sets[track_a]),
                "track_b_experiment_count": len(track_sets[track_b]),
                "track_a_support_ratio": _ratio(len(shared), len(track_sets[track_a])),
                "track_b_support_ratio": _ratio(len(shared), len(track_sets[track_b])),
            })
        return sorted(results, key=lambda item: (
            -int(item["shared_experiment_count"]),
            int(item["track_a_canonical_id"]),
            int(item["track_b_canonical_id"]),
        ))[:limit]

    def recurring_artist_pairs(
        self, limit: int = 20, minimum_shared_experiments: int = 2
    ) -> list[dict[str, object]]:
        artist_sets = _artist_experiment_sets(self._all_experiments())
        results: list[dict[str, object]] = []
        for artist_a, artist_b in itertools.combinations(sorted(artist_sets), 2):
            shared = sorted(artist_sets[artist_a] & artist_sets[artist_b])
            if len(shared) < minimum_shared_experiments:
                continue
            results.append({
                "artist_a": artist_a,
                "artist_b": artist_b,
                "shared_experiment_count": len(shared),
                "shared_experiment_ids": shared,
                "artist_a_experiment_count": len(artist_sets[artist_a]),
                "artist_b_experiment_count": len(artist_sets[artist_b]),
                "artist_a_support_ratio": _ratio(len(shared), len(artist_sets[artist_a])),
                "artist_b_support_ratio": _ratio(len(shared), len(artist_sets[artist_b])),
            })
        return sorted(results, key=lambda item: (
            -int(item["shared_experiment_count"]),
            str(item["artist_a"]),
            str(item["artist_b"]),
        ))[:limit]

    def _all_experiments(self) -> list[dict[str, object]]:
        record_ids = self._read_query(self._repository.list_experiment_ids)
        return [
            experiment
            for record_id in record_ids
            if (experiment := self.get_experiment(int(record_id))) is not None
        ]

    def _read_experiment(self, record_id: int) -> dict[str, object] | None:
        return self._read_projection(self._repository.get_experiment, record_id)

    def _read_persisted_artifact(self, record_id: int) -> dict[str, object] | None:
        return self._read_projection(self._repository.get_persisted_artifact, record_id)

    def _read_projection(
        self,
        reader: Callable[[int], dict[str, object] | None],
        record_id: int,
    ) -> dict[str, object] | None:
        session = self._repository.session
        transaction_already_active = session.in_transaction()
        try:
            return reader(record_id)
        finally:
            if not transaction_already_active and session.in_transaction():
                session.rollback()

    def _read_query(
        self,
        reader: Callable[..., QueryValue],
        *args: Any,
        **kwargs: Any,
    ) -> QueryValue:
        session = self._repository.session
        transaction_already_active = session.in_transaction()
        try:
            return reader(*args, **kwargs)
        finally:
            if not transaction_already_active and session.in_transaction():
                session.rollback()


def initialize_research_store(database_url: str | None = None) -> int:
    """Prepare the isolated research store without exposing its persistence objects."""
    return migrate_research_database(make_research_engine(database_url))


@contextmanager
def open_research_store_service(
    database_url: str | None = None,
) -> Iterator[ResearchStoreService]:
    """Open one service scope while keeping repository and session wiring private."""
    engine = make_research_engine(database_url)
    sessions = make_research_session_factory(engine)
    with sessions() as session:
        yield ResearchStoreService(ResearchRepository(session))


def _validate(model_type: type[ValidatedValue], proposal: object) -> ValidationResult[ValidatedValue]:
    try:
        value = model_type.model_validate(proposal)  # type: ignore[attr-defined]
    except ValidationError as exc:
        issues = tuple(
            ValidationIssue(
                location=tuple(item["loc"]),
                message=item["msg"],
                issue_type=item["type"],
            )
            for item in exc.errors()
        )
        return ValidationResult(value=None, issues=issues)
    return ValidationResult(value=value)


def _verify_sources(sources: list[EvidenceSourceInput]) -> EvidenceVerificationResult:
    issues: list[EvidenceVerificationIssue] = []
    for source in sources:
        if source.local_path is None:
            continue
        path = Path(source.local_path)
        if not path.is_file():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="file_not_found",
                message=f"local evidence file not found: {path}",
            ))
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.lower() != source.sha256.lower():
            issues.append(EvidenceVerificationIssue(
                source_key=source.source_key,
                local_path=source.local_path,
                issue_type="checksum_mismatch",
                message=f"evidence checksum mismatch: {path}",
            ))
    return EvidenceVerificationResult(tuple(issues))


def _require_type(value: object, expected: type[object]) -> None:
    if not isinstance(value, expected):
        raise TypeError(f"ingestion requires a validated {expected.__name__}")


def _position_summary(
    occurrences: list[dict[str, object]], *, position_key: str = "absolute_positions"
) -> dict[str, object]:
    positions = [
        int(item["absolute_position"])
        for item in occurrences
        if item["absolute_position"] is not None
    ]
    quartiles = [0, 0, 0, 0]
    for item in occurrences:
        position = item["absolute_position"]
        length = item["tracklist_length"]
        if position is None or length is None or int(length) <= 0:
            continue
        quartile = min(4, ((int(position) - 1) * 4 // int(length)) + 1)
        quartiles[quartile - 1] += 1
    return {
        position_key: positions,
        "minimum_position": min(positions) if positions else None,
        "maximum_position": max(positions) if positions else None,
        "mean_position": statistics.fmean(positions) if positions else None,
        "median_position": statistics.median(positions) if positions else None,
        "position_standard_deviation": statistics.pstdev(positions) if positions else None,
        "first_quartile_count": quartiles[0],
        "second_quartile_count": quartiles[1],
        "third_quartile_count": quartiles[2],
        "fourth_quartile_count": quartiles[3],
        "unknown_position_count": len(occurrences) - len(positions),
    }


def _ratio(shared_count: int, total_count: int) -> float:
    return shared_count / total_count if total_count else 0.0


def _track_corpus(
    experiments: list[dict[str, object]],
) -> tuple[
    dict[int, set[int]],
    dict[tuple[int, int], int],
    dict[int, dict[str, object]],
]:
    experiment_sets: dict[int, set[int]] = {}
    appearances: dict[tuple[int, int], int] = {}
    catalog: dict[int, dict[str, object]] = {}
    for experiment in experiments:
        experiment_id = int(experiment["id"])
        for placement in experiment["tracks"]:
            track_id = placement["track_id"]
            if track_id is None:
                continue
            canonical_track_id = int(track_id)
            experiment_sets.setdefault(canonical_track_id, set()).add(experiment_id)
            key = (experiment_id, canonical_track_id)
            appearances[key] = appearances.get(key, 0) + 1
            catalog[canonical_track_id] = {
                "canonical_title": placement["canonical_title"],
                "canonical_artist": placement["canonical_artist"],
            }
    return experiment_sets, appearances, catalog


def _artist_experiment_sets(
    experiments: list[dict[str, object]],
) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for experiment in experiments:
        experiment_id = int(experiment["id"])
        for placement in experiment["tracks"]:
            if placement["track_id"] is None:
                continue
            artist = str(placement["canonical_artist"])
            result.setdefault(artist, set()).add(experiment_id)
    return result


def _experiment_tracklist_length(experiment: dict[str, object]) -> int:
    generated = experiment["generated_track_count"]
    return int(generated) if generated is not None else len(experiment["tracks"])


def _known_positions(placements: list[dict[str, object]]) -> list[int]:
    return [
        int(item["absolute_position"])
        for item in placements
        if item["absolute_position"] is not None
    ]


def _single_position(placements: list[dict[str, object]]) -> int | None:
    positions = _known_positions(placements)
    return positions[0] if len(placements) == 1 and len(positions) == 1 else None


def _normalized_position(position: int | None, tracklist_length: int) -> float | None:
    if position is None or tracklist_length <= 0:
        return None
    return position / tracklist_length


def _artist_placements(
    experiment: dict[str, object], canonical_artist: str
) -> list[dict[str, object]]:
    return [
        {
            "canonical_track_id": item["track_id"],
            "canonical_title": item["canonical_title"],
            "canonical_artist": item["canonical_artist"],
            "display_title": item["title"],
            "display_artist": item["artist"],
            "observed_ordinal": item["observed_ordinal"],
            "absolute_position": item["absolute_position"],
        }
        for item in experiment["tracks"]
        if item["track_id"] is not None
        and item["canonical_artist"] == canonical_artist
    ]

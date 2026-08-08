from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session

from playlist_narrative_engine.research_store.models import (
    Constraint,
    ConstraintResult,
    Experiment,
    ExperimentPromptLabel,
    ExperimentTrack,
    GenerationFailure,
    Observation,
    Track,
)
from playlist_narrative_engine.research_store.schemas import (
    ConstraintStatus,
    ExperimentInput,
    GenerationFailureInput,
)


class ResearchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_experiment(self, draft: ExperimentInput) -> int:
        """Insert an experiment and every child row in one transaction."""
        with self.session.begin():
            experiment_values = dict(
                prompt_text=draft.prompt,
                prompt_title=draft.prompt_title,
                source_system=draft.source_system,
                generated_playlist_title=draft.generated_title,
                generated_playlist_description=draft.generated_description,
                requested_track_count=draft.requested_track_count,
                observed_track_count=len(draft.tracks),
                saved_by_user=draft.saved,
                overall_assessment=draft.assessment,
                notes=draft.notes,
            )
            if draft.created_at is not None:
                experiment_values["created_at"] = draft.created_at
            experiment = Experiment(**experiment_values)
            self.session.add(experiment)
            self.session.flush()

            for item in draft.tracks:
                canonical_title = (
                    item.canonical_title if item.canonical_title is not None else item.title
                )
                canonical_artist = (
                    item.canonical_artist if item.canonical_artist is not None else item.artist
                )
                track = self.session.scalar(
                    select(Track).where(
                        Track.canonical_title == canonical_title,
                        Track.canonical_artist == canonical_artist,
                    )
                )
                if track is None:
                    track = Track(
                        canonical_title=canonical_title,
                        canonical_artist=canonical_artist,
                        normalized_title=item.normalized_title,
                        normalized_artist=item.normalized_artist,
                    )
                    self.session.add(track)
                    self.session.flush()
                self.session.add(
                    ExperimentTrack(
                        experiment_id=experiment.id,
                        track_id=track.id,
                        position=item.position,
                        display_title=item.title,
                        display_artist=item.artist,
                        explicit_flag=item.explicit_flag,
                        version_or_remaster_text=item.version_or_remaster_text,
                        notes=item.notes,
                    )
                )

            for item in draft.constraints:
                constraint = Constraint(
                    experiment_id=experiment.id,
                    constraint_type=item.constraint_type,
                    constraint_text=item.constraint_text,
                    is_hard_constraint=item.is_hard_constraint,
                )
                self.session.add(constraint)
                self.session.flush()
                if item.result is not None:
                    self.session.add(
                        ConstraintResult(
                            experiment_id=experiment.id,
                            constraint_id=constraint.id,
                            status=item.result.status.value,
                            evidence=item.result.evidence,
                            provenance_type=item.result.provenance_type.value,
                            recorded_by=item.result.recorded_by,
                            provenance_notes=item.result.provenance_notes,
                        )
                    )

            self.session.add_all(
                Observation(
                    experiment_id=experiment.id,
                    observation_type=item.observation_type,
                    observation_text=item.observation_text,
                    severity=item.severity,
                    track_position=item.track_position,
                    provenance_type=item.provenance_type.value,
                    recorded_by=item.recorded_by,
                    provenance_notes=item.provenance_notes,
                )
                for item in draft.observations
            )
            self.session.add_all(
                ExperimentPromptLabel(experiment_id=experiment.id, label=label)
                for label in draft.prompt_labels
            )
            self.session.flush()
            experiment_id = experiment.id
        return experiment_id

    def record_generation_failure(self, draft: GenerationFailureInput) -> int:
        with self.session.begin():
            failure_values = dict(
                prompt_text=draft.prompt,
                source_system=draft.source_system,
                failure_type=draft.failure_type,
                displayed_message=draft.displayed_message,
                notes=draft.notes,
            )
            if draft.created_at is not None:
                failure_values["created_at"] = draft.created_at
            failure = GenerationFailure(**failure_values)
            self.session.add(failure)
            self.session.flush()
            failure_id = failure.id
        return failure_id

    def get_experiment(self, experiment_id: int) -> dict[str, object] | None:
        experiment = self.session.get(Experiment, experiment_id)
        if experiment is None:
            return None
        placements = list(
            self.session.scalars(
                select(ExperimentTrack)
                .where(ExperimentTrack.experiment_id == experiment_id)
                .order_by(ExperimentTrack.position)
            )
        )
        constraints = list(
            self.session.scalars(
                select(Constraint)
                .where(Constraint.experiment_id == experiment_id)
                .order_by(Constraint.id)
            )
        )
        observations = list(
            self.session.scalars(
                select(Observation)
                .where(Observation.experiment_id == experiment_id)
                .order_by(Observation.id)
            )
        )
        labels = list(
            self.session.scalars(
                select(ExperimentPromptLabel.label)
                .where(ExperimentPromptLabel.experiment_id == experiment_id)
                .order_by(ExperimentPromptLabel.label)
            )
        )
        return {
            "id": experiment.id,
            "created_at": experiment.created_at.isoformat(),
            "prompt": experiment.prompt_text,
            "prompt_title": experiment.prompt_title,
            "source_system": experiment.source_system,
            "generated_title": experiment.generated_playlist_title,
            "generated_description": experiment.generated_playlist_description,
            "requested_track_count": experiment.requested_track_count,
            "observed_track_count": experiment.observed_track_count,
            "saved": experiment.saved_by_user,
            "assessment": experiment.overall_assessment,
            "notes": experiment.notes,
            "prompt_labels": labels,
            "tracks": [self._placement_dict(item) for item in placements],
            "constraints": [self._constraint_dict(item) for item in constraints],
            "observations": [self._observation_dict(item) for item in observations],
        }

    def list_generation_failures(self) -> list[dict[str, object]]:
        failures = self.session.scalars(
            select(GenerationFailure).order_by(GenerationFailure.created_at, GenerationFailure.id)
        )
        return [
            {
                "id": item.id,
                "created_at": item.created_at.isoformat(),
                "prompt": item.prompt_text,
                "source_system": item.source_system,
                "failure_type": item.failure_type,
                "displayed_message": item.displayed_message,
                "notes": item.notes,
            }
            for item in failures
        ]

    def recurring_tracks(self, limit: int = 20) -> list[dict[str, object]]:
        statement = (
            select(
                Track.id,
                Track.canonical_title,
                Track.canonical_artist,
                func.count(distinct(ExperimentTrack.experiment_id)).label("experiment_count"),
            )
            .join(ExperimentTrack)
            .group_by(Track.id)
            .order_by(func.count(distinct(ExperimentTrack.experiment_id)).desc(), Track.id)
            .limit(limit)
        )
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def recurring_artists(self, limit: int = 20) -> list[dict[str, object]]:
        statement = (
            select(
                Track.canonical_artist,
                func.count(distinct(ExperimentTrack.experiment_id)).label("experiment_count"),
                func.count(ExperimentTrack.track_id).label("appearance_count"),
            )
            .join(ExperimentTrack)
            .group_by(Track.canonical_artist)
            .order_by(
                func.count(distinct(ExperimentTrack.experiment_id)).desc(),
                Track.canonical_artist,
            )
            .limit(limit)
        )
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def tracks_across_prompt_labels(
        self, *, minimum_distinct_labels: int = 2
    ) -> list[dict[str, object]]:
        """Find tracks spanning explicit human-assigned labels; infer nothing."""
        statement = (
            select(
                Track.id,
                Track.canonical_title,
                Track.canonical_artist,
                func.count(distinct(ExperimentPromptLabel.label)).label("label_count"),
                func.group_concat(distinct(ExperimentPromptLabel.label)).label("labels"),
            )
            .join(ExperimentTrack, ExperimentTrack.track_id == Track.id)
            .join(
                ExperimentPromptLabel,
                ExperimentPromptLabel.experiment_id == ExperimentTrack.experiment_id,
            )
            .group_by(Track.id)
            .having(func.count(distinct(ExperimentPromptLabel.label)) >= minimum_distinct_labels)
            .order_by(func.count(distinct(ExperimentPromptLabel.label)).desc(), Track.id)
        )
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def query_experiments(
        self,
        *,
        assessment: str | None = None,
        constraint_status: ConstraintStatus | str | None = None,
        saved: bool | None = None,
    ) -> list[dict[str, object]]:
        statement: Select[tuple[Experiment]] = select(Experiment)
        if constraint_status is not None:
            value = (
                constraint_status.value
                if isinstance(constraint_status, ConstraintStatus)
                else constraint_status
            )
            statement = statement.join(ConstraintResult).where(ConstraintResult.status == value)
        if assessment is not None:
            statement = statement.where(Experiment.overall_assessment == assessment)
        if saved is not None:
            statement = statement.where(Experiment.saved_by_user.is_(saved))
        statement = statement.distinct().order_by(Experiment.created_at, Experiment.id)
        return [self._experiment_summary(item) for item in self.session.scalars(statement)]

    def list_experiment_ids(self) -> Sequence[int]:
        return list(self.session.scalars(select(Experiment.id).order_by(Experiment.id)))

    def _placement_dict(self, item: ExperimentTrack) -> dict[str, object]:
        track = item.track
        return {
            "position": item.position,
            "track_id": track.id,
            "canonical_title": track.canonical_title,
            "canonical_artist": track.canonical_artist,
            "normalized_title": track.normalized_title,
            "normalized_artist": track.normalized_artist,
            "title": item.display_title,
            "artist": item.display_artist,
            "explicit_flag": item.explicit_flag,
            "version_or_remaster_text": item.version_or_remaster_text,
            "notes": item.notes,
        }

    @staticmethod
    def _constraint_dict(item: Constraint) -> dict[str, object]:
        result = item.result
        return {
            "id": item.id,
            "constraint_type": item.constraint_type,
            "constraint_text": item.constraint_text,
            "is_hard_constraint": item.is_hard_constraint,
            "result": None
            if result is None
            else {
                "status": result.status,
                "evidence": result.evidence,
                "provenance_type": result.provenance_type,
                "recorded_by": result.recorded_by,
                "provenance_notes": result.provenance_notes,
            },
        }

    @staticmethod
    def _observation_dict(item: Observation) -> dict[str, object]:
        return {
            "id": item.id,
            "observation_type": item.observation_type,
            "observation_text": item.observation_text,
            "severity": item.severity,
            "track_position": item.track_position,
            "provenance_type": item.provenance_type,
            "recorded_by": item.recorded_by,
            "provenance_notes": item.provenance_notes,
        }

    @staticmethod
    def _experiment_summary(item: Experiment) -> dict[str, object]:
        return {
            "id": item.id,
            "created_at": item.created_at.isoformat(),
            "prompt": item.prompt_text,
            "generated_title": item.generated_playlist_title,
            "assessment": item.overall_assessment,
            "saved": item.saved_by_user,
            "observed_track_count": item.observed_track_count,
        }

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from contextlib import nullcontext
from pathlib import Path

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session

from playlist_narrative_engine.research_store.models import (
    Constraint, ConstraintResult, EvidenceLink, EvidenceSource, Experiment,
    ExperimentPromptLabel, ExperimentTrack, GenerationFailure, Observation,
    PersistedArtifactExperimentLink, PersistedArtifactSegment,
    PersistedArtifactTrack, PersistedPlaylistArtifact, Track,
    TracklistEvidenceSegment,
)
from playlist_narrative_engine.research_store.schemas import (
    ConstraintStatus, ExperimentInput, FieldEvidenceInput, GenerationFailureInput,
    PersistedArtifactExperimentLinkInput, PersistedPlaylistArtifactInput,
)


class ResearchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert_experiment(self, draft: ExperimentInput) -> int:
        """Insert an experiment and every evidence-bearing child in one transaction."""
        transaction = nullcontext() if self.session.in_transaction() else self.session.begin()
        with transaction:
            values = dict(
                generated_at=draft.generated_at, prompt_text=draft.prompt,
                prompt_title=draft.prompt_title, source_system=draft.source_system,
                generated_playlist_title=draft.generated_title,
                generated_playlist_description=draft.generated_description,
                requested_track_count=draft.requested_track_count,
                generated_track_count=draft.generated_track_count,
                observed_track_count=len(draft.tracks),
                tracklist_completeness=draft.tracklist_completeness.value,
                saved_by_user=draft.saved, evidence_standard=draft.evidence_standard.value,
                assessment_outcome=draft.assessment_outcome.value,
                overall_assessment=draft.assessment, notes=draft.notes,
            )
            if draft.recorded_at is not None:
                values["recorded_at"] = draft.recorded_at
            experiment = Experiment(**values)
            self.session.add(experiment)
            self.session.flush()

            sources = self._insert_sources(experiment.id, None, draft.evidence_sources)
            self._insert_links(sources, draft.evidence, experiment_id=experiment.id)

            segments: dict[int, TracklistEvidenceSegment] = {}
            for item in draft.segments:
                segment = TracklistEvidenceSegment(
                    experiment_id=experiment.id, segment_ordinal=item.segment_ordinal,
                    relationship_to_previous=item.relationship_to_previous.value,
                    captures_playlist_start=item.captures_playlist_start.value,
                    captures_playlist_end=item.captures_playlist_end.value, notes=item.notes,
                )
                self.session.add(segment)
                self.session.flush()
                segments[item.segment_ordinal] = segment
                prefixed = [link.model_copy(update={"field_name": f"segment.{item.segment_ordinal}.{link.field_name}"}) for link in item.evidence]
                self._insert_links(sources, prefixed, experiment_id=experiment.id)

            placements_by_observed: dict[int, ExperimentTrack] = {}
            for item in draft.tracks:
                track = self._canonical_track(item)
                placement = ExperimentTrack(
                    experiment_id=experiment.id,
                    track_id=None if track is None else track.id,
                    evidence_segment_id=segments[item.evidence_segment].id,
                    observed_ordinal=item.observed_ordinal,
                    segment_ordinal=item.segment_ordinal,
                    absolute_position=item.absolute_position,
                    display_title=item.title, display_artist=item.artist,
                    explicit_flag=item.explicit_flag,
                    version_or_remaster_text=item.version_or_remaster_text,
                    notes=item.notes,
                )
                self.session.add(placement)
                self.session.flush()
                placements_by_observed[item.observed_ordinal] = placement
                self._insert_links(sources, item.evidence, experiment_track_id=placement.id)

            for item in draft.constraints:
                constraint = Constraint(
                    experiment_id=experiment.id, constraint_type=item.constraint_type,
                    constraint_text=item.constraint_text, is_hard_constraint=item.is_hard_constraint,
                    study_constraint_definition_id=item.study_constraint_definition_id,
                )
                self.session.add(constraint)
                self.session.flush()
                if item.result is not None:
                    self.session.add(ConstraintResult(
                        experiment_id=experiment.id, constraint_id=constraint.id,
                        status=item.result.status.value, evidence=item.result.evidence,
                        provenance_type=item.result.provenance_type.value,
                        recorded_by=item.result.recorded_by,
                        provenance_notes=item.result.provenance_notes,
                    ))

            for item in draft.observations:
                placement_id = None
                if item.track_observed_ordinal is not None:
                    placement_id = placements_by_observed[item.track_observed_ordinal].id
                self.session.add(Observation(
                    experiment_id=experiment.id, experiment_track_id=placement_id,
                    observation_type=item.observation_type,
                    observation_text=item.observation_text, severity=item.severity,
                    track_position=item.track_position,
                    provenance_type=item.provenance_type.value,
                    recorded_by=item.recorded_by, provenance_notes=item.provenance_notes,
                ))
            self.session.add_all(ExperimentPromptLabel(experiment_id=experiment.id, label=label) for label in draft.prompt_labels)
            self.session.flush()
            return experiment.id

    def _canonical_track(self, item) -> Track | None:
        if not item.canonical_identity_established:
            return None
        title = item.canonical_title if item.canonical_title is not None else item.title
        artist = item.canonical_artist if item.canonical_artist is not None else item.artist
        if title is None or artist is None:
            return None
        track = self.session.scalar(select(Track).where(Track.canonical_title == title, Track.canonical_artist == artist))
        if track is None:
            track = Track(canonical_title=title, canonical_artist=artist,
                          normalized_title=item.normalized_title, normalized_artist=item.normalized_artist)
            self.session.add(track)
            self.session.flush()
        return track

    def _insert_sources(
        self, experiment_id, failure_id, items, *, persisted_artifact_id=None,
        persisted_artifact_experiment_link_id=None,
    ) -> dict[str, EvidenceSource]:
        result = {}
        for item in items:
            if item.local_path is not None:
                path = Path(item.local_path)
                if not path.is_file():
                    raise ValueError(f"local evidence file not found: {path}")
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual.lower() != item.sha256.lower():
                    raise ValueError(f"evidence checksum mismatch: {path}")
            source = EvidenceSource(
                experiment_id=experiment_id, generation_failure_id=failure_id,
                persisted_artifact_id=persisted_artifact_id,
                persisted_artifact_experiment_link_id=persisted_artifact_experiment_link_id,
                source_key=item.source_key, source_type=item.source_type,
                source_reference=item.source_reference, original_filename=item.original_filename,
                local_path=item.local_path, sha256=None if item.sha256 is None else item.sha256.lower(),
                source_timestamp=item.source_timestamp, notes=item.notes,
            )
            self.session.add(source)
            self.session.flush()
            result[item.source_key] = source
        return result

    def _insert_links(self, sources: dict[str, EvidenceSource], items: list[FieldEvidenceInput], **target) -> None:
        for item in items:
            source = sources[item.source_key]
            if target.get("experiment_id") is not None or target.get("experiment_track_id") is not None:
                valid_domain = source.experiment_id is not None
            elif target.get("generation_failure_id") is not None:
                valid_domain = source.generation_failure_id is not None
            elif target.get("persisted_artifact_id") is not None or target.get("persisted_artifact_track_id") is not None:
                valid_domain = source.persisted_artifact_id is not None
            elif target.get("persisted_artifact_experiment_link_id") is not None:
                valid_domain = source.persisted_artifact_experiment_link_id is not None
            else:
                valid_domain = False
            if not valid_domain:
                raise ValueError("evidence source ownership domain does not match claim target")
            self.session.add(EvidenceLink(
                evidence_source_id=source.id,
                experiment_id=target.get("experiment_id"),
                experiment_track_id=target.get("experiment_track_id"),
                generation_failure_id=target.get("generation_failure_id"),
                persisted_artifact_id=target.get("persisted_artifact_id"),
                persisted_artifact_track_id=target.get("persisted_artifact_track_id"),
                persisted_artifact_experiment_link_id=target.get("persisted_artifact_experiment_link_id"),
                field_name=item.field_name, provenance_type=item.provenance_type.value,
                support_status=item.support_status.value, notes=item.notes,
            ))

    def record_generation_failure(self, draft: GenerationFailureInput) -> int:
        transaction = nullcontext() if self.session.in_transaction() else self.session.begin()
        with transaction:
            values = dict(generated_at=draft.generated_at, prompt_text=draft.prompt,
                          source_system=draft.source_system, failure_type=draft.failure_type,
                          displayed_message=draft.displayed_message,
                          evidence_standard=draft.evidence_standard.value, notes=draft.notes)
            if draft.recorded_at is not None:
                values["recorded_at"] = draft.recorded_at
            failure = GenerationFailure(**values)
            self.session.add(failure)
            self.session.flush()
            sources = self._insert_sources(None, failure.id, draft.evidence_sources)
            self._insert_links(sources, draft.evidence, generation_failure_id=failure.id)
            return failure.id

    def insert_persisted_artifact(self, draft: PersistedPlaylistArtifactInput) -> int:
        """Insert current persisted-artifact evidence without touching experiments."""
        with self.session.begin():
            values = dict(
                observed_at=draft.observed_at, source_system=draft.source_system,
                display_title=draft.display_title,
                display_description=draft.display_description,
                visibility_text=draft.visibility_text,
                persistence_state=draft.persistence_state.value,
                displayed_track_count=draft.displayed_track_count,
                displayed_duration_text=draft.displayed_duration_text,
                observed_track_count=len(draft.tracks),
                tracklist_completeness=draft.tracklist_completeness.value,
                evidence_standard=draft.evidence_standard.value, notes=draft.notes,
            )
            if draft.recorded_at is not None:
                values["recorded_at"] = draft.recorded_at
            artifact = PersistedPlaylistArtifact(**values)
            self.session.add(artifact)
            self.session.flush()
            sources = self._insert_sources(
                None, None, draft.evidence_sources, persisted_artifact_id=artifact.id
            )
            self._insert_links(sources, draft.evidence, persisted_artifact_id=artifact.id)
            segments: dict[int, PersistedArtifactSegment] = {}
            for item in draft.segments:
                segment = PersistedArtifactSegment(
                    persisted_artifact_id=artifact.id,
                    segment_ordinal=item.segment_ordinal,
                    relationship_to_previous=item.relationship_to_previous.value,
                    captures_playlist_start=item.captures_playlist_start.value,
                    captures_playlist_end=item.captures_playlist_end.value,
                    notes=item.notes,
                )
                self.session.add(segment)
                self.session.flush()
                segments[item.segment_ordinal] = segment
                prefixed = [
                    link.model_copy(update={
                        "field_name": f"segment.{item.segment_ordinal}.{link.field_name}"
                    }) for link in item.evidence
                ]
                self._insert_links(sources, prefixed, persisted_artifact_id=artifact.id)
            for item in draft.tracks:
                track = self._canonical_track(item)
                placement = PersistedArtifactTrack(
                    persisted_artifact_id=artifact.id,
                    track_id=None if track is None else track.id,
                    artifact_segment_id=segments[item.evidence_segment].id,
                    observed_ordinal=item.observed_ordinal,
                    segment_ordinal=item.segment_ordinal,
                    absolute_position=item.absolute_position,
                    display_title=item.title, display_artist=item.artist,
                    explicit_flag=item.explicit_flag,
                    version_or_remaster_text=item.version_or_remaster_text,
                    notes=item.notes,
                )
                self.session.add(placement)
                self.session.flush()
                self._insert_links(
                    sources, item.evidence, persisted_artifact_track_id=placement.id
                )
            self.session.flush()
            return artifact.id

    def insert_persisted_artifact_experiment_link(
        self, draft: PersistedArtifactExperimentLinkInput
    ) -> int:
        """Insert relationship evidence without mutating either endpoint."""
        with self.session.begin():
            if self.session.get(PersistedPlaylistArtifact, draft.persisted_artifact_id) is None:
                raise ValueError("persisted artifact does not exist")
            if self.session.get(Experiment, draft.experiment_id) is None:
                raise ValueError("experiment does not exist")
            link = PersistedArtifactExperimentLink(
                persisted_artifact_id=draft.persisted_artifact_id,
                experiment_id=draft.experiment_id,
                relationship_type=draft.relationship_type.value,
                unchanged_since_generation=draft.unchanged_since_generation.value,
                notes=draft.notes,
            )
            self.session.add(link)
            self.session.flush()
            sources = self._insert_sources(
                None, None, draft.evidence_sources,
                persisted_artifact_experiment_link_id=link.id,
            )
            self._insert_links(
                sources, draft.evidence,
                persisted_artifact_experiment_link_id=link.id,
            )
            self.session.flush()
            return link.id

    def get_experiment(self, experiment_id: int) -> dict[str, object] | None:
        experiment = self.session.get(Experiment, experiment_id)
        if experiment is None:
            return None
        segments = list(self.session.scalars(select(TracklistEvidenceSegment).where(TracklistEvidenceSegment.experiment_id == experiment_id).order_by(TracklistEvidenceSegment.segment_ordinal)))
        placements = list(self.session.scalars(select(ExperimentTrack).where(ExperimentTrack.experiment_id == experiment_id).order_by(ExperimentTrack.observed_ordinal)))
        constraints = list(self.session.scalars(select(Constraint).where(Constraint.experiment_id == experiment_id).order_by(Constraint.id)))
        observations = list(self.session.scalars(select(Observation).where(Observation.experiment_id == experiment_id).order_by(Observation.id)))
        labels = list(self.session.scalars(select(ExperimentPromptLabel.label).where(ExperimentPromptLabel.experiment_id == experiment_id).order_by(ExperimentPromptLabel.label)))
        sources = list(self.session.scalars(select(EvidenceSource).where(EvidenceSource.experiment_id == experiment_id).order_by(EvidenceSource.id)))
        links = list(self.session.scalars(select(EvidenceLink).where((EvidenceLink.experiment_id == experiment_id) | (EvidenceLink.experiment_track_id.in_([p.id for p in placements] or [-1]))).order_by(EvidenceLink.id)))
        recorded = experiment.recorded_at.isoformat()
        return {
            "id": experiment.id, "schema_version": 3, "recorded_at": recorded,
            "created_at": recorded, "generated_at": None if experiment.generated_at is None else experiment.generated_at.isoformat(),
            "prompt": experiment.prompt_text, "prompt_title": experiment.prompt_title,
            "source_system": experiment.source_system,
            "generated_title": experiment.generated_playlist_title,
            "generated_description": experiment.generated_playlist_description,
            "requested_track_count": experiment.requested_track_count,
            "generated_track_count": experiment.generated_track_count,
            "observed_track_count": experiment.observed_track_count,
            "tracklist_completeness": experiment.tracklist_completeness,
            "saved": experiment.saved_by_user, "evidence_standard": experiment.evidence_standard,
            "assessment_outcome": experiment.assessment_outcome,
            "assessment": experiment.overall_assessment, "notes": experiment.notes,
            "prompt_labels": labels,
            "segments": [self._segment_dict(item) for item in segments],
            "tracks": [self._placement_dict(item) for item in placements],
            "evidence_sources": [self._source_dict(item) for item in sources],
            "evidence": [self._link_dict(item) for item in links if item.experiment_id is not None],
            "constraints": [self._constraint_dict(item) for item in constraints],
            "observations": [self._observation_dict(item) for item in observations],
        }

    def list_generation_failures(self) -> list[dict[str, object]]:
        items = self.session.scalars(select(GenerationFailure).order_by(GenerationFailure.recorded_at, GenerationFailure.id))
        return [{"id": item.id, "recorded_at": item.recorded_at.isoformat(), "created_at": item.recorded_at.isoformat(),
                 "generated_at": None if item.generated_at is None else item.generated_at.isoformat(),
                 "prompt": item.prompt_text, "source_system": item.source_system,
                 "failure_type": item.failure_type, "displayed_message": item.displayed_message,
                 "evidence_standard": item.evidence_standard,
                 "evidence_sources": [self._source_dict(source) for source in self.session.scalars(select(EvidenceSource).where(EvidenceSource.generation_failure_id == item.id).order_by(EvidenceSource.id))],
                 "evidence": [self._link_dict(link) for link in self.session.scalars(select(EvidenceLink).where(EvidenceLink.generation_failure_id == item.id).order_by(EvidenceLink.id))],
                 "notes": item.notes} for item in items]

    def get_persisted_artifact(self, artifact_id: int) -> dict[str, object] | None:
        artifact = self.session.get(PersistedPlaylistArtifact, artifact_id)
        if artifact is None:
            return None
        segments = list(self.session.scalars(
            select(PersistedArtifactSegment)
            .where(PersistedArtifactSegment.persisted_artifact_id == artifact_id)
            .order_by(PersistedArtifactSegment.segment_ordinal)
        ))
        placements = list(self.session.scalars(
            select(PersistedArtifactTrack)
            .where(PersistedArtifactTrack.persisted_artifact_id == artifact_id)
            .order_by(PersistedArtifactTrack.observed_ordinal)
        ))
        sources = list(self.session.scalars(
            select(EvidenceSource)
            .where(EvidenceSource.persisted_artifact_id == artifact_id)
            .order_by(EvidenceSource.id)
        ))
        links = list(self.session.scalars(
            select(EvidenceLink).where(
                (EvidenceLink.persisted_artifact_id == artifact_id)
                | (EvidenceLink.persisted_artifact_track_id.in_(
                    [placement.id for placement in placements] or [-1]
                ))
            ).order_by(EvidenceLink.id)
        ))
        return {
            "id": artifact.id, "schema_version": 3,
            "recorded_at": artifact.recorded_at.isoformat(),
            "observed_at": None if artifact.observed_at is None else artifact.observed_at.isoformat(),
            "source_system": artifact.source_system,
            "display_title": artifact.display_title,
            "display_description": artifact.display_description,
            "visibility_text": artifact.visibility_text,
            "persistence_state": artifact.persistence_state,
            "displayed_track_count": artifact.displayed_track_count,
            "displayed_duration_text": artifact.displayed_duration_text,
            "observed_track_count": artifact.observed_track_count,
            "tracklist_completeness": artifact.tracklist_completeness,
            "evidence_standard": artifact.evidence_standard,
            "notes": artifact.notes,
            "segments": [self._artifact_segment_dict(item) for item in segments],
            "tracks": [self._artifact_placement_dict(item) for item in placements],
            "evidence_sources": [self._source_dict(item) for item in sources],
            "evidence": [self._link_dict(item) for item in links if item.persisted_artifact_id is not None],
        }

    def list_persisted_artifact_ids(self) -> Sequence[int]:
        return list(self.session.scalars(
            select(PersistedPlaylistArtifact.id).order_by(PersistedPlaylistArtifact.id)
        ))

    def list_persisted_artifact_experiment_links(self) -> list[dict[str, object]]:
        rows = self.session.scalars(
            select(PersistedArtifactExperimentLink).order_by(PersistedArtifactExperimentLink.id)
        )
        result = []
        for item in rows:
            sources = list(self.session.scalars(
                select(EvidenceSource)
                .where(EvidenceSource.persisted_artifact_experiment_link_id == item.id)
                .order_by(EvidenceSource.id)
            ))
            links = list(self.session.scalars(
                select(EvidenceLink)
                .where(EvidenceLink.persisted_artifact_experiment_link_id == item.id)
                .order_by(EvidenceLink.id)
            ))
            result.append({
                "id": item.id,
                "persisted_artifact_id": item.persisted_artifact_id,
                "experiment_id": item.experiment_id,
                "relationship_type": item.relationship_type,
                "unchanged_since_generation": item.unchanged_since_generation,
                "notes": item.notes,
                "evidence_sources": [self._source_dict(source) for source in sources],
                "evidence": [self._link_dict(link) for link in links],
            })
        return result

    def recurring_tracks(self, limit: int = 20) -> list[dict[str, object]]:
        statement = (select(Track.id, Track.canonical_title, Track.canonical_artist,
                    func.count(distinct(ExperimentTrack.experiment_id)).label("experiment_count"))
                    .join(ExperimentTrack).group_by(Track.id)
                    .order_by(func.count(distinct(ExperimentTrack.experiment_id)).desc(), Track.id).limit(limit))
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def recurring_artists(self, limit: int = 20) -> list[dict[str, object]]:
        statement = (select(Track.canonical_artist,
                    func.count(distinct(ExperimentTrack.experiment_id)).label("experiment_count"),
                    func.count(ExperimentTrack.track_id).label("appearance_count"))
                    .join(ExperimentTrack).group_by(Track.canonical_artist)
                    .order_by(func.count(distinct(ExperimentTrack.experiment_id)).desc(), Track.canonical_artist).limit(limit))
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def track_occurrences(self, canonical_track_id: int) -> list[dict[str, object]]:
        statement = (
            select(
                Experiment.id.label("experiment_id"),
                Experiment.prompt_title,
                Experiment.generated_playlist_title.label("generated_title"),
                func.coalesce(
                    Experiment.generated_track_count,
                    Experiment.observed_track_count,
                ).label("tracklist_length"),
                Track.id.label("canonical_track_id"),
                Track.canonical_title,
                Track.canonical_artist,
                ExperimentTrack.display_title,
                ExperimentTrack.display_artist,
                ExperimentTrack.observed_ordinal,
                ExperimentTrack.absolute_position,
            )
            .join(ExperimentTrack, ExperimentTrack.experiment_id == Experiment.id)
            .join(Track, Track.id == ExperimentTrack.track_id)
            .where(Track.id == canonical_track_id)
            .order_by(
                Experiment.id,
                ExperimentTrack.absolute_position.is_(None),
                ExperimentTrack.absolute_position,
                ExperimentTrack.observed_ordinal,
            )
        )
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def artist_occurrences(self, canonical_artist: str) -> list[dict[str, object]]:
        statement = (
            select(
                Experiment.id.label("experiment_id"),
                Experiment.prompt_title,
                Experiment.generated_playlist_title.label("generated_title"),
                func.coalesce(
                    Experiment.generated_track_count,
                    Experiment.observed_track_count,
                ).label("tracklist_length"),
                Track.id.label("canonical_track_id"),
                Track.canonical_title,
                Track.canonical_artist,
                ExperimentTrack.display_title,
                ExperimentTrack.display_artist,
                ExperimentTrack.observed_ordinal,
                ExperimentTrack.absolute_position,
            )
            .join(ExperimentTrack, ExperimentTrack.experiment_id == Experiment.id)
            .join(Track, Track.id == ExperimentTrack.track_id)
            .where(Track.canonical_artist == canonical_artist)
            .order_by(
                Experiment.id,
                ExperimentTrack.absolute_position.is_(None),
                ExperimentTrack.absolute_position,
                ExperimentTrack.observed_ordinal,
            )
        )
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def tracks_across_prompt_labels(self, *, minimum_distinct_labels: int = 2) -> list[dict[str, object]]:
        statement = (select(Track.id, Track.canonical_title, Track.canonical_artist,
                    func.count(distinct(ExperimentPromptLabel.label)).label("label_count"),
                    func.group_concat(distinct(ExperimentPromptLabel.label)).label("labels"))
                    .join(ExperimentTrack, ExperimentTrack.track_id == Track.id)
                    .join(ExperimentPromptLabel, ExperimentPromptLabel.experiment_id == ExperimentTrack.experiment_id)
                    .group_by(Track.id).having(func.count(distinct(ExperimentPromptLabel.label)) >= minimum_distinct_labels)
                    .order_by(func.count(distinct(ExperimentPromptLabel.label)).desc(), Track.id))
        return [dict(row._mapping) for row in self.session.execute(statement)]

    def query_experiments(
        self, *, assessment=None, assessment_outcome=None,
        constraint_status=None, saved=None,
    ) -> list[dict[str, object]]:
        statement: Select[tuple[Experiment]] = select(Experiment)
        if constraint_status is not None:
            value = constraint_status.value if isinstance(constraint_status, ConstraintStatus) else constraint_status
            statement = statement.join(ConstraintResult).where(ConstraintResult.status == value)
        if assessment is not None:
            statement = statement.where(Experiment.overall_assessment == assessment)
        if assessment_outcome is not None:
            value = getattr(assessment_outcome, "value", assessment_outcome)
            statement = statement.where(Experiment.assessment_outcome == value)
        if saved is not None:
            statement = statement.where(Experiment.saved_by_user.is_(saved))
        statement = statement.distinct().order_by(Experiment.recorded_at, Experiment.id)
        return [self._experiment_summary(item) for item in self.session.scalars(statement)]

    def list_experiment_ids(self) -> Sequence[int]:
        return list(self.session.scalars(select(Experiment.id).order_by(Experiment.id)))

    def _placement_dict(self, item):
        links = list(self.session.scalars(select(EvidenceLink).where(EvidenceLink.experiment_track_id == item.id).order_by(EvidenceLink.id)))
        track = item.track
        return {"id": item.id, "observed_ordinal": item.observed_ordinal,
                "evidence_segment": item.segment.segment_ordinal, "segment_ordinal": item.segment_ordinal,
                "absolute_position": item.absolute_position, "position": item.absolute_position,
                "track_id": None if track is None else track.id,
                "canonical_title": None if track is None else track.canonical_title,
                "canonical_artist": None if track is None else track.canonical_artist,
                "normalized_title": None if track is None else track.normalized_title,
                "normalized_artist": None if track is None else track.normalized_artist,
                "title": item.display_title, "artist": item.display_artist,
                "explicit_flag": item.explicit_flag,
                "version_or_remaster_text": item.version_or_remaster_text, "notes": item.notes,
                "evidence": [self._link_dict(link) for link in links]}

    def _artifact_placement_dict(self, item):
        links = list(self.session.scalars(
            select(EvidenceLink)
            .where(EvidenceLink.persisted_artifact_track_id == item.id)
            .order_by(EvidenceLink.id)
        ))
        track = item.track
        return {
            "id": item.id, "observed_ordinal": item.observed_ordinal,
            "evidence_segment": item.segment.segment_ordinal,
            "segment_ordinal": item.segment_ordinal,
            "absolute_position": item.absolute_position,
            "track_id": None if track is None else track.id,
            "canonical_title": None if track is None else track.canonical_title,
            "canonical_artist": None if track is None else track.canonical_artist,
            "normalized_title": None if track is None else track.normalized_title,
            "normalized_artist": None if track is None else track.normalized_artist,
            "title": item.display_title, "artist": item.display_artist,
            "explicit_flag": item.explicit_flag,
            "version_or_remaster_text": item.version_or_remaster_text,
            "notes": item.notes,
            "evidence": [self._link_dict(link) for link in links],
        }

    @staticmethod
    def _segment_dict(item):
        return {"id": item.id, "segment_ordinal": item.segment_ordinal,
                "relationship_to_previous": item.relationship_to_previous,
                "captures_playlist_start": item.captures_playlist_start,
                "captures_playlist_end": item.captures_playlist_end, "notes": item.notes}

    @staticmethod
    def _artifact_segment_dict(item):
        return {
            "id": item.id, "segment_ordinal": item.segment_ordinal,
            "relationship_to_previous": item.relationship_to_previous,
            "captures_playlist_start": item.captures_playlist_start,
            "captures_playlist_end": item.captures_playlist_end,
            "notes": item.notes,
        }

    @staticmethod
    def _source_dict(item):
        return {"id": item.id, "source_key": item.source_key, "source_type": item.source_type,
                "source_reference": item.source_reference, "original_filename": item.original_filename,
                "local_path": item.local_path, "sha256": item.sha256,
                "source_timestamp": None if item.source_timestamp is None else item.source_timestamp.isoformat(),
                "notes": item.notes}

    def _link_dict(self, item):
        return {"id": item.id, "evidence_source_id": item.evidence_source_id,
                "source_key": item.source.source_key,
                "field_name": item.field_name, "provenance_type": item.provenance_type,
                "support_status": item.support_status, "notes": item.notes}

    @staticmethod
    def _constraint_dict(item):
        result = item.result
        return {"id": item.id, "constraint_type": item.constraint_type,
                "constraint_text": item.constraint_text, "is_hard_constraint": item.is_hard_constraint,
                "study_constraint_definition_id": item.study_constraint_definition_id,
                "result": None if result is None else {"status": result.status, "evidence": result.evidence,
                "provenance_type": result.provenance_type, "recorded_by": result.recorded_by,
                "provenance_notes": result.provenance_notes}}

    def _observation_dict(self, item):
        placement = None if item.experiment_track_id is None else self.session.get(ExperimentTrack, item.experiment_track_id)
        return {"id": item.id, "observation_type": item.observation_type,
                "observation_text": item.observation_text, "severity": item.severity,
                "experiment_track_id": item.experiment_track_id,
                "track_observed_ordinal": None if placement is None else placement.observed_ordinal,
                "track_position": item.track_position,
                "provenance_type": item.provenance_type, "recorded_by": item.recorded_by,
                "provenance_notes": item.provenance_notes}

    @staticmethod
    def _experiment_summary(item):
        return {"id": item.id, "recorded_at": item.recorded_at.isoformat(),
                "created_at": item.recorded_at.isoformat(),
                "generated_at": None if item.generated_at is None else item.generated_at.isoformat(),
                "prompt": item.prompt_text, "generated_title": item.generated_playlist_title,
                "assessment_outcome": item.assessment_outcome,
                "assessment": item.overall_assessment, "saved": item.saved_by_user,
                "observed_track_count": item.observed_track_count,
                "tracklist_completeness": item.tracklist_completeness}

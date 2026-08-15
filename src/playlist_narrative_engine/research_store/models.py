from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from playlist_narrative_engine.research_store.database import ResearchBase


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


_TYPED_PARAMETER_CHECK = (
    "(value_type='BOOLEAN' AND boolean_value IS NOT NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
    "(value_type='INTEGER' AND boolean_value IS NULL AND integer_value IS NOT NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
    "(value_type='DECIMAL' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NOT NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
    "(value_type='TEXT' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NOT NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
    "(value_type='DATE' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NOT NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
    "(value_type='VOCABULARY_TERM' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NOT NULL AND vocabulary_term_key IS NOT NULL)"
)


class SchemaVersion(ResearchBase):
    __tablename__ = "schema_version"

    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class Experiment(ResearchBase):
    __tablename__ = "experiments"
    __table_args__ = (
        CheckConstraint("requested_track_count IS NULL OR requested_track_count > 0"),
        CheckConstraint("generated_track_count IS NULL OR generated_track_count >= 0"),
        CheckConstraint("observed_track_count >= 0"),
        CheckConstraint("tracklist_completeness IN ('COMPLETE', 'PARTIAL', 'NOT_OBSERVED')"),
        CheckConstraint("evidence_standard IN ('LEGACY_V1', 'CONTEMPORARY_MANUAL', 'RECOVERED_HISTORICAL', 'CURRENT_PRIMARY_EVIDENCE')"),
        CheckConstraint("assessment_outcome IN ('INDETERMINATE', 'PASS', 'PARTIAL_PASS', 'FAIL')"),
        Index("ix_experiments_recorded_at", "recorded_at"),
        Index("ix_experiments_generated_at", "generated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    prompt_title: Mapped[str | None] = mapped_column(Text)
    source_system: Mapped[str | None] = mapped_column(Text)
    generated_playlist_title: Mapped[str | None] = mapped_column(Text)
    generated_playlist_description: Mapped[str | None] = mapped_column(Text)
    requested_track_count: Mapped[int | None] = mapped_column(Integer)
    generated_track_count: Mapped[int | None] = mapped_column(Integer)
    observed_track_count: Mapped[int] = mapped_column(Integer)
    tracklist_completeness: Mapped[str] = mapped_column(String(20))
    saved_by_user: Mapped[bool | None] = mapped_column(Boolean)
    evidence_standard: Mapped[str] = mapped_column(String(30))
    assessment_outcome: Mapped[str] = mapped_column(
        String(20), nullable=False, default="INDETERMINATE"
    )
    overall_assessment: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    segments: Mapped[list[TracklistEvidenceSegment]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    placements: Mapped[list[ExperimentTrack]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    constraints: Mapped[list[Constraint]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    observations: Mapped[list[Observation]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    prompt_labels: Mapped[list[ExperimentPromptLabel]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )
    evidence_sources: Mapped[list[EvidenceSource]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class Track(ResearchBase):
    __tablename__ = "tracks"
    __table_args__ = (
        UniqueConstraint("canonical_title", "canonical_artist", name="uq_track_raw_identity"),
        Index("ix_tracks_canonical_identity", "canonical_title", "canonical_artist"),
        Index("ix_tracks_canonical_artist", "canonical_artist"),
        Index("ix_tracks_normalized_identity", "normalized_title", "normalized_artist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_title: Mapped[str] = mapped_column(Text)
    canonical_artist: Mapped[str] = mapped_column(Text)
    normalized_title: Mapped[str | None] = mapped_column(Text)
    normalized_artist: Mapped[str | None] = mapped_column(Text)


class TracklistEvidenceSegment(ResearchBase):
    __tablename__ = "tracklist_evidence_segments"
    __table_args__ = (
        UniqueConstraint("experiment_id", "segment_ordinal", name="uq_segment_ordinal"),
        CheckConstraint("segment_ordinal > 0"),
        CheckConstraint("relationship_to_previous IN ('FIRST', 'CONTIGUOUS', 'GAP_UNKNOWN_SIZE')"),
        CheckConstraint("captures_playlist_start IN ('YES', 'NO', 'UNKNOWN')"),
        CheckConstraint("captures_playlist_end IN ('YES', 'NO', 'UNKNOWN')"),
        Index("ix_segments_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    segment_ordinal: Mapped[int] = mapped_column(Integer)
    relationship_to_previous: Mapped[str] = mapped_column(String(30))
    captures_playlist_start: Mapped[str] = mapped_column(String(10))
    captures_playlist_end: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment] = relationship(back_populates="segments")
    placements: Mapped[list[ExperimentTrack]] = relationship(back_populates="segment")


class ExperimentTrack(ResearchBase):
    __tablename__ = "experiment_tracks"
    __table_args__ = (
        UniqueConstraint("experiment_id", "observed_ordinal", name="uq_observed_ordinal"),
        UniqueConstraint("evidence_segment_id", "segment_ordinal", name="uq_segment_track_ordinal"),
        UniqueConstraint("experiment_id", "absolute_position", name="uq_absolute_position"),
        CheckConstraint("observed_ordinal > 0"),
        CheckConstraint("segment_ordinal > 0"),
        CheckConstraint("absolute_position IS NULL OR absolute_position > 0"),
        Index("ix_experiment_tracks_experiment", "experiment_id"),
        Index("ix_experiment_tracks_track", "track_id"),
        Index("ix_experiment_tracks_segment", "evidence_segment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"))
    evidence_segment_id: Mapped[int] = mapped_column(
        ForeignKey("tracklist_evidence_segments.id", ondelete="CASCADE")
    )
    observed_ordinal: Mapped[int] = mapped_column(Integer)
    segment_ordinal: Mapped[int] = mapped_column(Integer)
    absolute_position: Mapped[int | None] = mapped_column(Integer)
    display_title: Mapped[str | None] = mapped_column(Text)
    display_artist: Mapped[str | None] = mapped_column(Text)
    explicit_flag: Mapped[bool | None] = mapped_column(Boolean)
    version_or_remaster_text: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment] = relationship(back_populates="placements")
    segment: Mapped[TracklistEvidenceSegment] = relationship(back_populates="placements")
    track: Mapped[Track | None] = relationship()


class Constraint(ResearchBase):
    __tablename__ = "constraints"
    __table_args__ = (Index("ix_constraints_experiment", "experiment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    constraint_type: Mapped[str] = mapped_column(Text)
    constraint_text: Mapped[str] = mapped_column(Text)
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean)
    study_constraint_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_constraint_definitions.id")
    )

    experiment: Mapped[Experiment] = relationship(back_populates="constraints")
    result: Mapped[ConstraintResult | None] = relationship(
        back_populates="constraint", cascade="all, delete-orphan", uselist=False
    )


class ConstraintResult(ResearchBase):
    __tablename__ = "constraint_results"
    __table_args__ = (
        CheckConstraint("status IN ('PASS', 'PARTIAL', 'FAIL', 'UNKNOWN')"),
        CheckConstraint("provenance_type IN ('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"),
    )

    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True)
    constraint_id: Mapped[int] = mapped_column(ForeignKey("constraints.id", ondelete="CASCADE"), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    evidence: Mapped[str | None] = mapped_column(Text)
    provenance_type: Mapped[str] = mapped_column(String(30))
    recorded_by: Mapped[str | None] = mapped_column(Text)
    provenance_notes: Mapped[str | None] = mapped_column(Text)

    constraint: Mapped[Constraint] = relationship(back_populates="result")


class Observation(ResearchBase):
    __tablename__ = "observations"
    __table_args__ = (
        CheckConstraint("track_position IS NULL OR track_position > 0"),
        CheckConstraint("provenance_type IN ('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"),
        Index("ix_observations_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    experiment_track_id: Mapped[int | None] = mapped_column(ForeignKey("experiment_tracks.id", ondelete="SET NULL"))
    observation_type: Mapped[str] = mapped_column(Text)
    observation_text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(Text)
    track_position: Mapped[int | None] = mapped_column(Integer)
    provenance_type: Mapped[str] = mapped_column(String(30))
    recorded_by: Mapped[str | None] = mapped_column(Text)
    provenance_notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment] = relationship(back_populates="observations")


class ExperimentPromptLabel(ResearchBase):
    __tablename__ = "experiment_prompt_labels"
    __table_args__ = (
        UniqueConstraint("experiment_id", "label", name="uq_experiment_prompt_label"),
        Index("ix_prompt_labels_label", "label"),
    )

    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True)
    label: Mapped[str] = mapped_column(Text, primary_key=True)
    experiment: Mapped[Experiment] = relationship(back_populates="prompt_labels")


class GenerationFailure(ResearchBase):
    __tablename__ = "generation_failures"
    __table_args__ = (
        Index("ix_generation_failures_recorded_at", "recorded_at"),
        Index("ix_generation_failures_generated_at", "generated_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime)
    prompt_text: Mapped[str | None] = mapped_column(Text)
    source_system: Mapped[str | None] = mapped_column(Text)
    failure_type: Mapped[str] = mapped_column(Text)
    displayed_message: Mapped[str | None] = mapped_column(Text)
    evidence_standard: Mapped[str] = mapped_column(String(30), default="CONTEMPORARY_MANUAL")
    notes: Mapped[str | None] = mapped_column(Text)


class PersistedPlaylistArtifact(ResearchBase):
    __tablename__ = "persisted_playlist_artifacts"
    __table_args__ = (
        CheckConstraint("displayed_track_count IS NULL OR displayed_track_count >= 0"),
        CheckConstraint("observed_track_count >= 0"),
        CheckConstraint("persistence_state IN ('PRESENT', 'ABSENT', 'UNKNOWN')"),
        CheckConstraint("tracklist_completeness IN ('COMPLETE', 'PARTIAL', 'NOT_OBSERVED')"),
        CheckConstraint("evidence_standard IN ('LEGACY_V1', 'CONTEMPORARY_MANUAL', 'RECOVERED_HISTORICAL', 'CURRENT_PRIMARY_EVIDENCE')"),
        Index("ix_persisted_artifacts_recorded_at", "recorded_at"),
        Index("ix_persisted_artifacts_observed_at", "observed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime)
    source_system: Mapped[str | None] = mapped_column(Text)
    display_title: Mapped[str | None] = mapped_column(Text)
    display_description: Mapped[str | None] = mapped_column(Text)
    visibility_text: Mapped[str | None] = mapped_column(Text)
    persistence_state: Mapped[str] = mapped_column(String(10))
    displayed_track_count: Mapped[int | None] = mapped_column(Integer)
    displayed_duration_text: Mapped[str | None] = mapped_column(Text)
    observed_track_count: Mapped[int] = mapped_column(Integer)
    tracklist_completeness: Mapped[str] = mapped_column(String(20))
    evidence_standard: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text)

    segments: Mapped[list[PersistedArtifactSegment]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    placements: Mapped[list[PersistedArtifactTrack]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    experiment_links: Mapped[list[PersistedArtifactExperimentLink]] = relationship(
        back_populates="artifact", cascade="all, delete-orphan"
    )
    evidence_sources: Mapped[list[EvidenceSource]] = relationship(
        back_populates="persisted_artifact", cascade="all, delete-orphan"
    )


class PersistedArtifactSegment(ResearchBase):
    __tablename__ = "persisted_artifact_segments"
    __table_args__ = (
        UniqueConstraint("persisted_artifact_id", "segment_ordinal", name="uq_artifact_segment_ordinal"),
        CheckConstraint("segment_ordinal > 0"),
        CheckConstraint("relationship_to_previous IN ('FIRST', 'CONTIGUOUS', 'GAP_UNKNOWN_SIZE')"),
        CheckConstraint("captures_playlist_start IN ('YES', 'NO', 'UNKNOWN')"),
        CheckConstraint("captures_playlist_end IN ('YES', 'NO', 'UNKNOWN')"),
        Index("ix_artifact_segments_artifact", "persisted_artifact_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    persisted_artifact_id: Mapped[int] = mapped_column(
        ForeignKey("persisted_playlist_artifacts.id", ondelete="CASCADE")
    )
    segment_ordinal: Mapped[int] = mapped_column(Integer)
    relationship_to_previous: Mapped[str] = mapped_column(String(30))
    captures_playlist_start: Mapped[str] = mapped_column(String(10))
    captures_playlist_end: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)

    artifact: Mapped[PersistedPlaylistArtifact] = relationship(back_populates="segments")
    placements: Mapped[list[PersistedArtifactTrack]] = relationship(back_populates="segment")


class PersistedArtifactTrack(ResearchBase):
    __tablename__ = "persisted_artifact_tracks"
    __table_args__ = (
        UniqueConstraint("persisted_artifact_id", "observed_ordinal", name="uq_artifact_observed_ordinal"),
        UniqueConstraint("artifact_segment_id", "segment_ordinal", name="uq_artifact_segment_track_ordinal"),
        UniqueConstraint("persisted_artifact_id", "absolute_position", name="uq_artifact_absolute_position"),
        CheckConstraint("observed_ordinal > 0"),
        CheckConstraint("segment_ordinal > 0"),
        CheckConstraint("absolute_position IS NULL OR absolute_position > 0"),
        Index("ix_artifact_tracks_artifact", "persisted_artifact_id"),
        Index("ix_artifact_tracks_track", "track_id"),
        Index("ix_artifact_tracks_segment", "artifact_segment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    persisted_artifact_id: Mapped[int] = mapped_column(
        ForeignKey("persisted_playlist_artifacts.id", ondelete="CASCADE")
    )
    track_id: Mapped[int | None] = mapped_column(ForeignKey("tracks.id"))
    artifact_segment_id: Mapped[int] = mapped_column(
        ForeignKey("persisted_artifact_segments.id", ondelete="CASCADE")
    )
    observed_ordinal: Mapped[int] = mapped_column(Integer)
    segment_ordinal: Mapped[int] = mapped_column(Integer)
    absolute_position: Mapped[int | None] = mapped_column(Integer)
    display_title: Mapped[str | None] = mapped_column(Text)
    display_artist: Mapped[str | None] = mapped_column(Text)
    explicit_flag: Mapped[bool | None] = mapped_column(Boolean)
    version_or_remaster_text: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    artifact: Mapped[PersistedPlaylistArtifact] = relationship(back_populates="placements")
    segment: Mapped[PersistedArtifactSegment] = relationship(back_populates="placements")
    track: Mapped[Track | None] = relationship()


class PersistedArtifactExperimentLink(ResearchBase):
    __tablename__ = "persisted_artifact_experiment_links"
    __table_args__ = (
        UniqueConstraint("persisted_artifact_id", "experiment_id", name="uq_artifact_experiment_link"),
        CheckConstraint("relationship_type = 'USER_ATTESTED_CORRELATION'"),
        CheckConstraint("unchanged_since_generation IN ('YES', 'NO', 'UNKNOWN')"),
        Index("ix_artifact_experiment_links_artifact", "persisted_artifact_id"),
        Index("ix_artifact_experiment_links_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    persisted_artifact_id: Mapped[int] = mapped_column(
        ForeignKey("persisted_playlist_artifacts.id", ondelete="CASCADE")
    )
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    relationship_type: Mapped[str] = mapped_column(String(40))
    unchanged_since_generation: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)

    artifact: Mapped[PersistedPlaylistArtifact] = relationship(back_populates="experiment_links")


class EvidenceSource(ResearchBase):
    __tablename__ = "evidence_sources"
    __table_args__ = (
        UniqueConstraint("experiment_id", "source_key", name="uq_experiment_source_key"),
        UniqueConstraint("generation_failure_id", "source_key", name="uq_failure_source_key"),
        UniqueConstraint("persisted_artifact_id", "source_key", name="uq_artifact_source_key"),
        UniqueConstraint("persisted_artifact_experiment_link_id", "source_key", name="uq_artifact_link_source_key"),
        CheckConstraint("local_path IS NULL OR sha256 IS NOT NULL"),
        CheckConstraint("(experiment_id IS NOT NULL) + (generation_failure_id IS NOT NULL) + (persisted_artifact_id IS NOT NULL) + (persisted_artifact_experiment_link_id IS NOT NULL) = 1"),
        Index("ix_evidence_sources_experiment", "experiment_id"),
        Index("ix_evidence_sources_artifact", "persisted_artifact_id"),
        Index("ix_evidence_sources_artifact_link", "persisted_artifact_experiment_link_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    generation_failure_id: Mapped[int | None] = mapped_column(ForeignKey("generation_failures.id", ondelete="CASCADE"))
    persisted_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("persisted_playlist_artifacts.id", ondelete="CASCADE")
    )
    persisted_artifact_experiment_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("persisted_artifact_experiment_links.id", ondelete="CASCADE")
    )
    source_key: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment | None] = relationship(back_populates="evidence_sources")
    persisted_artifact: Mapped[PersistedPlaylistArtifact | None] = relationship(
        back_populates="evidence_sources"
    )


class EvidenceLink(ResearchBase):
    __tablename__ = "evidence_links"
    __table_args__ = (
        CheckConstraint("provenance_type IN ('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"),
        CheckConstraint("support_status IN ('FULL', 'PARTIAL')"),
        CheckConstraint("(experiment_id IS NOT NULL) + (experiment_track_id IS NOT NULL) + (generation_failure_id IS NOT NULL) + (persisted_artifact_id IS NOT NULL) + (persisted_artifact_track_id IS NOT NULL) + (persisted_artifact_experiment_link_id IS NOT NULL) = 1"),
        Index("ix_evidence_links_source", "evidence_source_id"),
        Index("ix_evidence_links_experiment", "experiment_id"),
        Index("ix_evidence_links_track", "experiment_track_id"),
        Index("ix_evidence_links_artifact", "persisted_artifact_id"),
        Index("ix_evidence_links_artifact_track", "persisted_artifact_track_id"),
        Index("ix_evidence_links_artifact_link", "persisted_artifact_experiment_link_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_source_id: Mapped[int] = mapped_column(ForeignKey("evidence_sources.id", ondelete="CASCADE"))
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    experiment_track_id: Mapped[int | None] = mapped_column(ForeignKey("experiment_tracks.id", ondelete="CASCADE"))
    generation_failure_id: Mapped[int | None] = mapped_column(ForeignKey("generation_failures.id", ondelete="CASCADE"))
    persisted_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("persisted_playlist_artifacts.id", ondelete="CASCADE")
    )
    persisted_artifact_track_id: Mapped[int | None] = mapped_column(
        ForeignKey("persisted_artifact_tracks.id", ondelete="CASCADE")
    )
    persisted_artifact_experiment_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("persisted_artifact_experiment_links.id", ondelete="CASCADE")
    )
    field_name: Mapped[str] = mapped_column(Text)
    provenance_type: Mapped[str] = mapped_column(String(30))
    support_status: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)

    source: Mapped[EvidenceSource] = relationship()


class Study(ResearchBase):
    __tablename__ = "studies"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_key: Mapped[str] = mapped_column(Text, unique=True)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class StudyProtocolVersion(ResearchBase):
    __tablename__ = "study_protocol_versions"
    __table_args__ = (
        UniqueConstraint("study_id", "version_number", name="uq_study_protocol_version"),
        UniqueConstraint("predecessor_version_id", name="uq_study_protocol_predecessor"),
        CheckConstraint("version_number > 0"),
        CheckConstraint(
            "(registered_at IS NULL AND registration_hash IS NULL) OR "
            "(registered_at IS NOT NULL AND registration_hash IS NOT NULL)"
        ),
        Index("ix_study_protocol_study", "study_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id", ondelete="RESTRICT"))
    version_number: Mapped[int] = mapped_column(Integer)
    predecessor_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    registered_at: Mapped[datetime | None] = mapped_column(DateTime)
    registration_hash: Mapped[str | None] = mapped_column(String(64))
    amendment_reason: Mapped[str | None] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    primary_hypothesis: Mapped[str] = mapped_column(Text)
    null_hypothesis: Mapped[str] = mapped_column(Text)
    design_summary: Mapped[str] = mapped_column(Text)
    planned_sample_size: Mapped[int] = mapped_column(Integer)
    randomization_method: Mapped[str] = mapped_column(Text)
    randomization_seed: Mapped[str] = mapped_column(Text)
    operational_failure_policy: Mapped[str] = mapped_column(Text)
    operational_failure_consumes_run: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    refusal_policy: Mapped[str] = mapped_column(Text)
    missing_result_policy: Mapped[str] = mapped_column(Text)


class StudyCondition(ResearchBase):
    __tablename__ = "study_conditions"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "condition_key", name="uq_study_condition_key"),
        CheckConstraint("role IN ('CONTROL', 'TREATMENT')"),
        Index("ix_study_conditions_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    condition_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    exact_factor_definition: Mapped[str] = mapped_column(Text)


class StudyBlock(ResearchBase):
    __tablename__ = "study_blocks"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "block_key", name="uq_study_block_key"),
        Index("ix_study_blocks_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    block_key: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    block_definition: Mapped[str] = mapped_column(Text)


class StudyConstraintDefinition(ResearchBase):
    __tablename__ = "study_constraint_definitions"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "constraint_key", name="uq_study_constraint_key"),
        CheckConstraint(
            "permitted_result_provenance IN "
            "('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"
        ),
        Index("ix_study_constraints_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    constraint_key: Mapped[str] = mapped_column(Text)
    constraint_type: Mapped[str] = mapped_column(Text)
    constraint_text: Mapped[str] = mapped_column(Text)
    is_hard_constraint: Mapped[bool] = mapped_column(Boolean)
    evaluation_rule: Mapped[str] = mapped_column(Text)
    permitted_result_provenance: Mapped[str] = mapped_column(String(30))
    unknown_handling: Mapped[str] = mapped_column(Text)


class StudyConstraintEvaluationPlan(ResearchBase):
    __tablename__ = "study_constraint_evaluation_plans"
    __table_args__ = (
        UniqueConstraint("constraint_definition_id", name="uq_study_constraint_evaluation_plan"),
        CheckConstraint("subject_kind IN ('RUN', 'EXPERIMENT_PLACEMENT', 'PLACEMENT_FIELD')"),
        CheckConstraint(
            "(subject_kind = 'PLACEMENT_FIELD' AND subject_field IS NOT NULL) OR "
            "(subject_kind != 'PLACEMENT_FIELD' AND subject_field IS NULL)"
        ),
        CheckConstraint(
            "subject_field IS NULL OR subject_field IN "
            "('display_title', 'display_artist', 'explicit_flag', 'version_or_remaster_text')"
        ),
        Index("ix_study_evaluation_plans_definition", "constraint_definition_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    constraint_definition_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_definitions.id", ondelete="RESTRICT")
    )
    instrumentation_version: Mapped[str] = mapped_column(Text)
    subject_kind: Mapped[str] = mapped_column(String(30))
    subject_field: Mapped[str | None] = mapped_column(String(40))
    subject_selector_key: Mapped[str] = mapped_column(Text)
    subject_selector_version: Mapped[str] = mapped_column(Text)
    subject_evaluator_key: Mapped[str] = mapped_column(Text)
    subject_evaluator_version: Mapped[str] = mapped_column(Text)
    aggregate_evaluator_key: Mapped[str] = mapped_column(Text)
    aggregate_evaluator_version: Mapped[str] = mapped_column(Text)
    require_complete_subject_set: Mapped[bool] = mapped_column(Boolean, nullable=False)
    allow_partial_subject_status: Mapped[bool] = mapped_column(Boolean, nullable=False)


class StudyConstraintMeasurementDefinition(ResearchBase):
    __tablename__ = "study_constraint_measurement_definitions"
    __table_args__ = (
        UniqueConstraint("evaluation_plan_id", "measurement_key", name="uq_study_measurement_key"),
        CheckConstraint(
            "authority IN ('DIRECT_OBSERVATION', 'STRUCTURAL_DERIVATION', "
            "'EXTERNAL_FACT_VERIFICATION', 'HUMAN_ASSESSMENT')"
        ),
        CheckConstraint("value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'TEXT', 'DATE', 'VOCABULARY_TERM')"),
        CheckConstraint(
            "(value_type = 'VOCABULARY_TERM' AND vocabulary_key IS NOT NULL) OR "
            "(value_type != 'VOCABULARY_TERM' AND vocabulary_key IS NULL)"
        ),
        CheckConstraint(
            "(derivation_key IS NULL AND derivation_version IS NULL) OR "
            "(derivation_key IS NOT NULL AND derivation_version IS NOT NULL)"
        ),
        CheckConstraint(
            "unavailable_policy IS NULL OR unavailable_policy IN "
            "('MUST_HAVE_VALUE', 'MAY_BE_UNAVAILABLE')"
        ),
        Index("ix_study_measurements_plan", "evaluation_plan_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_evaluation_plans.id", ondelete="RESTRICT")
    )
    measurement_key: Mapped[str] = mapped_column(Text)
    authority: Mapped[str] = mapped_column(String(40))
    value_type: Mapped[str] = mapped_column(String(30))
    unit_key: Mapped[str | None] = mapped_column(Text)
    vocabulary_key: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_required: Mapped[bool] = mapped_column(Boolean, nullable=False)
    derivation_key: Mapped[str | None] = mapped_column(Text)
    derivation_version: Mapped[str | None] = mapped_column(Text)
    unavailable_policy: Mapped[str | None] = mapped_column(String(30))


class StudyConstraintEvaluationParameter(ResearchBase):
    __tablename__ = "study_constraint_evaluation_parameters"
    __table_args__ = (
        UniqueConstraint("evaluation_plan_id", "parameter_key", name="uq_study_evaluation_parameter"),
        CheckConstraint("value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'TEXT', 'DATE', 'VOCABULARY_TERM')"),
        CheckConstraint(
            "(value_type = 'BOOLEAN' AND boolean_value IS NOT NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
            "(value_type = 'INTEGER' AND boolean_value IS NULL AND integer_value IS NOT NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
            "(value_type = 'DECIMAL' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NOT NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
            "(value_type = 'TEXT' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NOT NULL AND date_value IS NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
            "(value_type = 'DATE' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NOT NULL AND vocabulary_key IS NULL AND vocabulary_term_key IS NULL) OR "
            "(value_type = 'VOCABULARY_TERM' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_key IS NOT NULL AND vocabulary_term_key IS NOT NULL)"
        ),
        Index("ix_study_evaluation_parameters_plan", "evaluation_plan_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_evaluation_plans.id", ondelete="RESTRICT")
    )
    parameter_key: Mapped[str] = mapped_column(Text)
    value_type: Mapped[str] = mapped_column(String(30))
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    integer_value: Mapped[int | None] = mapped_column(Integer)
    decimal_value: Mapped[str | None] = mapped_column(Text)
    text_value: Mapped[str | None] = mapped_column(Text)
    date_value: Mapped[date | None] = mapped_column(Date)
    vocabulary_key: Mapped[str | None] = mapped_column(Text)
    vocabulary_term_key: Mapped[str | None] = mapped_column(Text)


class StudyConstraintEvaluationVocabularyTerm(ResearchBase):
    __tablename__ = "study_constraint_evaluation_vocabulary_terms"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_plan_id", "vocabulary_key", "term_key",
            name="uq_study_evaluation_vocabulary_term",
        ),
        Index("ix_study_evaluation_vocabulary_plan", "evaluation_plan_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_evaluation_plans.id", ondelete="RESTRICT")
    )
    vocabulary_key: Mapped[str] = mapped_column(Text)
    term_key: Mapped[str] = mapped_column(Text)
    term_definition: Mapped[str] = mapped_column(Text)


class ConstraintEvaluationSubject(ResearchBase):
    __tablename__ = "constraint_evaluation_subjects"
    __table_args__ = (
        CheckConstraint("subject_kind IN ('RUN', 'EXPERIMENT_PLACEMENT', 'PLACEMENT_FIELD')"),
        CheckConstraint("enumeration_ordinal > 0"),
        CheckConstraint(
            "(subject_kind = 'RUN' AND experiment_track_id IS NULL AND governed_field IS NULL) OR "
            "(subject_kind = 'EXPERIMENT_PLACEMENT' AND experiment_track_id IS NOT NULL AND governed_field IS NULL) OR "
            "(subject_kind = 'PLACEMENT_FIELD' AND experiment_track_id IS NOT NULL AND governed_field IS NOT NULL)"
        ),
        CheckConstraint(
            "governed_field IS NULL OR governed_field IN "
            "('display_title', 'display_artist', 'explicit_flag', 'version_or_remaster_text')"
        ),
        UniqueConstraint(
            "constraint_id", "subject_kind", "experiment_track_id", "governed_field",
            name="uq_constraint_evaluation_subject_identity",
        ),
        UniqueConstraint(
            "constraint_id", "enumeration_ordinal",
            name="uq_constraint_evaluation_subject_ordinal",
        ),
        Index("ix_constraint_evaluation_subjects_experiment", "experiment_id"),
        Index("ix_constraint_evaluation_subjects_constraint", "constraint_id"),
        Index("ix_constraint_evaluation_subjects_track", "experiment_track_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="RESTRICT"))
    constraint_id: Mapped[int] = mapped_column(ForeignKey("constraints.id", ondelete="RESTRICT"))
    subject_kind: Mapped[str] = mapped_column(String(30))
    experiment_track_id: Mapped[int | None] = mapped_column(
        ForeignKey("experiment_tracks.id", ondelete="RESTRICT")
    )
    governed_field: Mapped[str | None] = mapped_column(String(40))
    enumeration_ordinal: Mapped[int] = mapped_column(Integer)


class ConstraintEvaluationMeasurement(ResearchBase):
    __tablename__ = "constraint_evaluation_measurements"
    __table_args__ = (
        UniqueConstraint(
            "subject_id", "measurement_definition_id",
            name="uq_constraint_evaluation_measurement",
        ),
        CheckConstraint(
            "authority_kind IN ('DIRECT_OBSERVATION', 'STRUCTURAL_DERIVATION', "
            "'EXTERNAL_FACT_VERIFICATION', 'HUMAN_ASSESSMENT')"
        ),
        CheckConstraint(
            "value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'TEXT', 'DATE', "
            "'VOCABULARY_TERM', 'UNAVAILABLE')"
        ),
        CheckConstraint(
            "(value_type = 'BOOLEAN' AND boolean_value IS NOT NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'INTEGER' AND boolean_value IS NULL AND integer_value IS NOT NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'DECIMAL' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NOT NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'TEXT' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NOT NULL AND date_value IS NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'DATE' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NOT NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'VOCABULARY_TERM' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_term_key IS NOT NULL AND unavailable_reason IS NULL) OR "
            "(value_type = 'UNAVAILABLE' AND boolean_value IS NULL AND integer_value IS NULL AND decimal_value IS NULL AND text_value IS NULL AND date_value IS NULL AND vocabulary_term_key IS NULL AND unavailable_reason IS NOT NULL)"
        ),
        Index("ix_constraint_evaluation_measurements_subject", "subject_id"),
        Index("ix_constraint_evaluation_measurements_definition", "measurement_definition_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("constraint_evaluation_subjects.id", ondelete="RESTRICT")
    )
    measurement_definition_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_measurement_definitions.id", ondelete="RESTRICT")
    )
    authority_kind: Mapped[str] = mapped_column(String(40))
    value_type: Mapped[str] = mapped_column(String(30))
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    integer_value: Mapped[int | None] = mapped_column(Integer)
    decimal_value: Mapped[str | None] = mapped_column(Text)
    text_value: Mapped[str | None] = mapped_column(Text)
    date_value: Mapped[date | None] = mapped_column(Date)
    vocabulary_term_key: Mapped[str | None] = mapped_column(Text)
    unavailable_reason: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ConstraintEvaluationMeasurementEvidence(ResearchBase):
    __tablename__ = "constraint_evaluation_measurement_evidence"
    __table_args__ = (
        UniqueConstraint(
            "measurement_id", "evidence_source_id", "evidence_link_id", "evidence_role",
            name="uq_constraint_evaluation_measurement_evidence",
        ),
        CheckConstraint(
            "evidence_role IN ('SUBJECT_IDENTITY', 'OBSERVED_VALUE', 'EXTERNAL_FACT', "
            "'CORRESPONDENCE', 'OPERATOR_JUDGMENT')"
        ),
        CheckConstraint(
            "provenance_type IN ('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', "
            "'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"
        ),
        CheckConstraint("support_status IN ('FULL', 'PARTIAL')"),
        Index("ix_constraint_evaluation_evidence_measurement", "measurement_id"),
        Index("ix_constraint_evaluation_evidence_source", "evidence_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    measurement_id: Mapped[int] = mapped_column(
        ForeignKey("constraint_evaluation_measurements.id", ondelete="RESTRICT")
    )
    evidence_source_id: Mapped[int] = mapped_column(
        ForeignKey("evidence_sources.id", ondelete="RESTRICT")
    )
    evidence_link_id: Mapped[int | None] = mapped_column(
        ForeignKey("evidence_links.id", ondelete="RESTRICT")
    )
    evidence_role: Mapped[str] = mapped_column(String(30))
    provenance_type: Mapped[str] = mapped_column(String(30))
    support_status: Mapped[str] = mapped_column(String(10))
    field_or_segment_reference: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class ConstraintSubjectResult(ResearchBase):
    __tablename__ = "constraint_subject_results"
    __table_args__ = (
        UniqueConstraint("subject_id", name="uq_constraint_subject_result"),
        CheckConstraint("status IN ('PASS', 'PARTIAL', 'FAIL', 'UNKNOWN')"),
        Index("ix_constraint_subject_results_subject", "subject_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("constraint_evaluation_subjects.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(20))
    evaluator_key: Mapped[str] = mapped_column(Text)
    evaluator_version: Mapped[str] = mapped_column(Text)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    reason_code: Mapped[str] = mapped_column(Text)


class StudyOutcomeDefinition(ResearchBase):
    __tablename__ = "study_outcome_definitions"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "outcome_key", name="uq_study_outcome_key"),
        CheckConstraint("role IN ('PRIMARY', 'SECONDARY', 'EXPLORATORY')"),
        Index("ix_study_outcomes_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    outcome_key: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20))
    unit_of_analysis: Mapped[str] = mapped_column(Text)
    outcome_definition: Mapped[str] = mapped_column(Text)
    computation_rule: Mapped[str] = mapped_column(Text)
    missing_data_rule: Mapped[str] = mapped_column(Text)
    refusal_handling: Mapped[str] = mapped_column(Text)
    operational_failure_handling: Mapped[str] = mapped_column(Text)


class StudyAnalysisDefinition(ResearchBase):
    __tablename__ = "study_analysis_definitions"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "analysis_key", name="uq_study_analysis_key"),
        Index("ix_study_analyses_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    outcome_definition_id: Mapped[int] = mapped_column(
        ForeignKey("study_outcome_definitions.id", ondelete="RESTRICT")
    )
    analysis_key: Mapped[str] = mapped_column(Text)
    analysis_population: Mapped[str] = mapped_column(Text)
    comparison_definition: Mapped[str] = mapped_column(Text)
    aggregation_rule: Mapped[str] = mapped_column(Text)
    exclusion_rule: Mapped[str] = mapped_column(Text)
    reporting_rule: Mapped[str] = mapped_column(Text)


class StudyExecutionContract(ResearchBase):
    __tablename__ = "study_execution_contracts"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", name="uq_study_execution_contract_protocol"),
        Index("ix_study_execution_contracts_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    contract_version: Mapped[str] = mapped_column(Text)


class StudyOutcomeCalculationPlan(ResearchBase):
    __tablename__ = "study_outcome_calculation_plans"
    __table_args__ = (
        UniqueConstraint("execution_contract_id", "outcome_definition_id", name="uq_study_outcome_calculation_plan"),
        CheckConstraint("input_kind IN ('CONSTRAINT_RESULTS', 'STRUCTURED_SUBJECT_RESULTS', 'STRUCTURED_MEASUREMENTS', 'REALIZATION_DISPOSITION')"),
        CheckConstraint("output_value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'VOCABULARY_TERM', 'DISPOSITION')"),
        CheckConstraint("subject_interpretation IS NULL OR subject_interpretation IN ('FIELD_PREDICATE', 'PLACEMENT_EVENT')"),
        CheckConstraint("(output_value_type='VOCABULARY_TERM' AND output_vocabulary_key IS NOT NULL) OR (output_value_type!='VOCABULARY_TERM' AND output_vocabulary_key IS NULL)"),
        Index("ix_study_outcome_calculation_contract", "execution_contract_id"),
        Index("ix_study_outcome_calculation_outcome", "outcome_definition_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_contract_id: Mapped[int] = mapped_column(ForeignKey("study_execution_contracts.id", ondelete="RESTRICT"))
    outcome_definition_id: Mapped[int] = mapped_column(ForeignKey("study_outcome_definitions.id", ondelete="RESTRICT"))
    calculator_key: Mapped[str] = mapped_column(Text)
    calculator_version: Mapped[str] = mapped_column(Text)
    input_kind: Mapped[str] = mapped_column(String(40))
    output_value_type: Mapped[str] = mapped_column(String(30))
    output_vocabulary_key: Mapped[str | None] = mapped_column(Text)
    subject_interpretation: Mapped[str | None] = mapped_column(String(30))


class StudyOutcomeDispositionPolicy(ResearchBase):
    __tablename__ = "study_outcome_disposition_policies"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "population_state", name="uq_study_outcome_disposition_policy"),
        CheckConstraint("population_state IN ('EXPERIMENT_RECORDED', 'MAESTRO_REFUSAL_RECORDED', 'MAESTRO_FAILURE_RECORDED', 'PENDING')"),
        CheckConstraint("treatment IN ('CALCULATE', 'MISSING', 'NOT_CALCULABLE')"),
        Index("ix_study_outcome_disposition_plan", "calculation_plan_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_outcome_calculation_plans.id", ondelete="RESTRICT")
    )
    population_state: Mapped[str] = mapped_column(String(40))
    treatment: Mapped[str] = mapped_column(String(30))


class StudyOutcomeConstraintBinding(ResearchBase):
    __tablename__ = "study_outcome_constraint_bindings"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "ordinal", name="uq_study_outcome_binding_ordinal"),
        UniqueConstraint("calculation_plan_id", "binding_role", "constraint_definition_id", name="uq_study_outcome_binding_identity"),
        CheckConstraint("ordinal > 0"),
        Index("ix_study_outcome_bindings_plan", "calculation_plan_id"),
        Index("ix_study_outcome_bindings_constraint", "constraint_definition_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_outcome_calculation_plans.id", ondelete="RESTRICT"))
    constraint_definition_id: Mapped[int] = mapped_column(ForeignKey("study_constraint_definitions.id", ondelete="RESTRICT"))
    binding_role: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)


class StudyOutcomeSubjectKind(ResearchBase):
    __tablename__ = "study_outcome_subject_kinds"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "subject_kind", name="uq_study_outcome_subject_kind"),
        CheckConstraint("subject_kind IN ('RUN', 'EXPERIMENT_PLACEMENT', 'PLACEMENT_FIELD')"),
        Index("ix_study_outcome_subject_kinds_plan", "calculation_plan_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_outcome_calculation_plans.id", ondelete="RESTRICT"))
    subject_kind: Mapped[str] = mapped_column(String(30))


class StudyOutcomeCalculationParameter(ResearchBase):
    __tablename__ = "study_outcome_calculation_parameters"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "parameter_key", "ordinal", name="uq_study_outcome_parameter"),
        CheckConstraint("ordinal > 0"),
        CheckConstraint("value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'TEXT', 'DATE', 'VOCABULARY_TERM')"),
        CheckConstraint(_TYPED_PARAMETER_CHECK),
        Index("ix_study_outcome_parameters_plan", "calculation_plan_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_outcome_calculation_plans.id", ondelete="RESTRICT"))
    parameter_key: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    value_type: Mapped[str] = mapped_column(String(30))
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    integer_value: Mapped[int | None] = mapped_column(Integer)
    decimal_value: Mapped[str | None] = mapped_column(Text)
    text_value: Mapped[str | None] = mapped_column(Text)
    date_value: Mapped[date | None] = mapped_column(Date)
    vocabulary_key: Mapped[str | None] = mapped_column(Text)
    vocabulary_term_key: Mapped[str | None] = mapped_column(Text)


class StudyOutcomeCalculationVocabularyTerm(ResearchBase):
    __tablename__ = "study_outcome_calculation_vocabulary_terms"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "vocabulary_key", "term_key", name="uq_study_outcome_vocabulary_term"),
        Index("ix_study_outcome_vocabulary_plan", "calculation_plan_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_outcome_calculation_plans.id", ondelete="RESTRICT"))
    vocabulary_key: Mapped[str] = mapped_column(Text)
    term_key: Mapped[str] = mapped_column(Text)
    term_definition: Mapped[str] = mapped_column(Text)


class StudyAnalysisCalculationPlan(ResearchBase):
    __tablename__ = "study_analysis_calculation_plans"
    __table_args__ = (
        UniqueConstraint("execution_contract_id", "analysis_definition_id", name="uq_study_analysis_calculation_plan"),
        CheckConstraint("population_scope='ALL_REGISTERED_PLANNED_RUNS'"),
        Index("ix_study_analysis_calculation_contract", "execution_contract_id"),
        Index("ix_study_analysis_calculation_analysis", "analysis_definition_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    execution_contract_id: Mapped[int] = mapped_column(ForeignKey("study_execution_contracts.id", ondelete="RESTRICT"))
    analysis_definition_id: Mapped[int] = mapped_column(ForeignKey("study_analysis_definitions.id", ondelete="RESTRICT"))
    calculator_key: Mapped[str] = mapped_column(Text)
    calculator_version: Mapped[str] = mapped_column(Text)
    population_scope: Mapped[str] = mapped_column(String(50))
    output_shape_key: Mapped[str] = mapped_column(Text)
    output_shape_version: Mapped[str] = mapped_column(Text)


class StudyAnalysisDimension(ResearchBase):
    __tablename__ = "study_analysis_dimensions"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "ordinal", name="uq_study_analysis_dimension_ordinal"),
        UniqueConstraint("calculation_plan_id", "dimension_role", "dimension_key", name="uq_study_analysis_dimension_identity"),
        CheckConstraint("ordinal > 0"),
        CheckConstraint("dimension_role IN ('GROUP', 'MATCH')"),
        CheckConstraint("dimension_key IN ('CONDITION', 'BLOCK', 'REPLICATE')"),
        Index("ix_study_analysis_dimensions_plan", "calculation_plan_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_analysis_calculation_plans.id", ondelete="RESTRICT"))
    dimension_role: Mapped[str] = mapped_column(String(20))
    dimension_key: Mapped[str] = mapped_column(String(20))
    ordinal: Mapped[int] = mapped_column(Integer)


class StudyAnalysisConditionBinding(ResearchBase):
    __tablename__ = "study_analysis_condition_bindings"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "comparison_role", name="uq_study_analysis_condition_role"),
        CheckConstraint("comparison_role IN ('LEFT', 'RIGHT')"),
        Index("ix_study_analysis_condition_plan", "calculation_plan_id"),
        Index("ix_study_analysis_condition_condition", "condition_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_analysis_calculation_plans.id", ondelete="RESTRICT"))
    condition_id: Mapped[int] = mapped_column(ForeignKey("study_conditions.id", ondelete="RESTRICT"))
    comparison_role: Mapped[str] = mapped_column(String(20))


class StudyAnalysisCalculationParameter(ResearchBase):
    __tablename__ = "study_analysis_calculation_parameters"
    __table_args__ = (
        UniqueConstraint("calculation_plan_id", "parameter_key", "ordinal", name="uq_study_analysis_parameter"),
        CheckConstraint("ordinal > 0"),
        CheckConstraint("value_type IN ('BOOLEAN', 'INTEGER', 'DECIMAL', 'TEXT', 'DATE', 'VOCABULARY_TERM')"),
        CheckConstraint(_TYPED_PARAMETER_CHECK),
        Index("ix_study_analysis_parameters_plan", "calculation_plan_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    calculation_plan_id: Mapped[int] = mapped_column(ForeignKey("study_analysis_calculation_plans.id", ondelete="RESTRICT"))
    parameter_key: Mapped[str] = mapped_column(Text)
    ordinal: Mapped[int] = mapped_column(Integer)
    value_type: Mapped[str] = mapped_column(String(30))
    boolean_value: Mapped[bool | None] = mapped_column(Boolean)
    integer_value: Mapped[int | None] = mapped_column(Integer)
    decimal_value: Mapped[str | None] = mapped_column(Text)
    text_value: Mapped[str | None] = mapped_column(Text)
    date_value: Mapped[date | None] = mapped_column(Date)
    vocabulary_key: Mapped[str | None] = mapped_column(Text)
    vocabulary_term_key: Mapped[str | None] = mapped_column(Text)


class StudyPlannedRun(ResearchBase):
    __tablename__ = "study_planned_runs"
    __table_args__ = (
        UniqueConstraint("protocol_version_id", "run_key", name="uq_study_run_key"),
        UniqueConstraint("protocol_version_id", "randomized_ordinal", name="uq_study_run_order"),
        UniqueConstraint(
            "block_id", "condition_id", "replicate_number",
            name="uq_study_run_replicate",
        ),
        CheckConstraint("replicate_number > 0"),
        CheckConstraint("randomized_ordinal > 0"),
        Index("ix_study_runs_protocol", "protocol_version_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    protocol_version_id: Mapped[int] = mapped_column(
        ForeignKey("study_protocol_versions.id", ondelete="RESTRICT")
    )
    condition_id: Mapped[int] = mapped_column(ForeignKey("study_conditions.id", ondelete="RESTRICT"))
    block_id: Mapped[int] = mapped_column(ForeignKey("study_blocks.id", ondelete="RESTRICT"))
    run_key: Mapped[str] = mapped_column(Text)
    replicate_number: Mapped[int] = mapped_column(Integer)
    randomized_ordinal: Mapped[int] = mapped_column(Integer)
    planned_prompt_text: Mapped[str] = mapped_column(Text)
    planned_source_system: Mapped[str | None] = mapped_column(Text)
    replacement_for_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_planned_runs.id", ondelete="RESTRICT")
    )


class StudyPlannedRunConstraint(ResearchBase):
    __tablename__ = "study_planned_run_constraints"

    planned_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_planned_runs.id", ondelete="RESTRICT"), primary_key=True
    )
    constraint_definition_id: Mapped[int] = mapped_column(
        ForeignKey("study_constraint_definitions.id", ondelete="RESTRICT"), primary_key=True
    )


class StudyRunAttempt(ResearchBase):
    __tablename__ = "study_run_attempts"
    __table_args__ = (
        UniqueConstraint("planned_run_id", "attempt_number", name="uq_study_run_attempt"),
        CheckConstraint("attempt_number > 0"),
        CheckConstraint("attempt_type = 'OPERATIONAL_FAILURE'"),
        Index("ix_study_attempts_run", "planned_run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    planned_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_planned_runs.id", ondelete="RESTRICT")
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    attempt_type: Mapped[str] = mapped_column(String(30), default="OPERATIONAL_FAILURE")
    consumes_planned_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failure_code: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text)


class StudyRunRealization(ResearchBase):
    __tablename__ = "study_run_realizations"
    __table_args__ = (
        UniqueConstraint("planned_run_id", name="uq_study_run_realization"),
        UniqueConstraint("experiment_id", name="uq_study_realization_experiment"),
        UniqueConstraint("generation_failure_id", name="uq_study_realization_failure"),
        CheckConstraint(
            "disposition IN ('EXPERIMENT_RECORDED', 'MAESTRO_REFUSAL_RECORDED', "
            "'MAESTRO_FAILURE_RECORDED')"
        ),
        CheckConstraint(
            "(disposition = 'EXPERIMENT_RECORDED' AND experiment_id IS NOT NULL "
            "AND generation_failure_id IS NULL) OR "
            "(disposition IN ('MAESTRO_REFUSAL_RECORDED', 'MAESTRO_FAILURE_RECORDED') "
            "AND experiment_id IS NULL AND generation_failure_id IS NOT NULL)"
        ),
        Index("ix_study_realizations_run", "planned_run_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    planned_run_id: Mapped[int] = mapped_column(
        ForeignKey("study_planned_runs.id", ondelete="RESTRICT")
    )
    disposition: Mapped[str] = mapped_column(String(40))
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id", ondelete="RESTRICT"))
    generation_failure_id: Mapped[int | None] = mapped_column(
        ForeignKey("generation_failures.id", ondelete="RESTRICT")
    )
    realized_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

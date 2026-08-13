from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

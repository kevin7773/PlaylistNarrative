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
        CheckConstraint("requested_track_count IS NULL OR requested_track_count >= 0"),
        CheckConstraint("generated_track_count IS NULL OR generated_track_count >= 0"),
        CheckConstraint("observed_track_count >= 0"),
        CheckConstraint("tracklist_completeness IN ('COMPLETE', 'PARTIAL', 'NOT_OBSERVED')"),
        CheckConstraint("evidence_standard IN ('LEGACY_V1', 'CONTEMPORARY_MANUAL', 'RECOVERED_HISTORICAL')"),
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


class EvidenceSource(ResearchBase):
    __tablename__ = "evidence_sources"
    __table_args__ = (
        UniqueConstraint("experiment_id", "source_key", name="uq_experiment_source_key"),
        UniqueConstraint("generation_failure_id", "source_key", name="uq_failure_source_key"),
        CheckConstraint("local_path IS NULL OR sha256 IS NOT NULL"),
        CheckConstraint("(experiment_id IS NOT NULL) + (generation_failure_id IS NOT NULL) = 1"),
        Index("ix_evidence_sources_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    generation_failure_id: Mapped[int | None] = mapped_column(ForeignKey("generation_failures.id", ondelete="CASCADE"))
    source_key: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    source_reference: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(Text)
    local_path: Mapped[str | None] = mapped_column(Text)
    sha256: Mapped[str | None] = mapped_column(String(64))
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment | None] = relationship(back_populates="evidence_sources")


class EvidenceLink(ResearchBase):
    __tablename__ = "evidence_links"
    __table_args__ = (
        CheckConstraint("provenance_type IN ('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT', 'MIGRATION_DERIVATION')"),
        CheckConstraint("support_status IN ('FULL', 'PARTIAL')"),
        CheckConstraint("(experiment_id IS NOT NULL) + (experiment_track_id IS NOT NULL) + (generation_failure_id IS NOT NULL) = 1"),
        Index("ix_evidence_links_source", "evidence_source_id"),
        Index("ix_evidence_links_experiment", "experiment_id"),
        Index("ix_evidence_links_track", "experiment_track_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_source_id: Mapped[int] = mapped_column(ForeignKey("evidence_sources.id", ondelete="CASCADE"))
    experiment_id: Mapped[int | None] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    experiment_track_id: Mapped[int | None] = mapped_column(ForeignKey("experiment_tracks.id", ondelete="CASCADE"))
    generation_failure_id: Mapped[int | None] = mapped_column(ForeignKey("generation_failures.id", ondelete="CASCADE"))
    field_name: Mapped[str] = mapped_column(Text)
    provenance_type: Mapped[str] = mapped_column(String(30))
    support_status: Mapped[str] = mapped_column(String(10))
    notes: Mapped[str | None] = mapped_column(Text)

    source: Mapped[EvidenceSource] = relationship()

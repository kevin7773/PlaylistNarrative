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
        CheckConstraint("observed_track_count >= 0"),
        Index("ix_experiments_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    prompt_text: Mapped[str] = mapped_column(Text)
    prompt_title: Mapped[str | None] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(Text, default="Maestro Beta")
    generated_playlist_title: Mapped[str] = mapped_column(Text)
    generated_playlist_description: Mapped[str] = mapped_column(Text)
    requested_track_count: Mapped[int | None] = mapped_column(Integer)
    observed_track_count: Mapped[int] = mapped_column(Integer)
    saved_by_user: Mapped[bool] = mapped_column(Boolean)
    overall_assessment: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

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


class ExperimentTrack(ResearchBase):
    __tablename__ = "experiment_tracks"
    __table_args__ = (
        UniqueConstraint("experiment_id", "position", name="uq_experiment_track_position"),
        CheckConstraint("position > 0"),
        Index("ix_experiment_tracks_experiment", "experiment_id"),
        Index("ix_experiment_tracks_track", "track_id"),
    )

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True
    )
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id"))
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_title: Mapped[str] = mapped_column(Text)
    display_artist: Mapped[str] = mapped_column(Text)
    explicit_flag: Mapped[bool | None] = mapped_column(Boolean)
    version_or_remaster_text: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    experiment: Mapped[Experiment] = relationship(back_populates="placements")
    track: Mapped[Track] = relationship()


class Constraint(ResearchBase):
    __tablename__ = "constraints"
    __table_args__ = (Index("ix_constraints_experiment", "experiment_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE")
    )
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
        CheckConstraint(
            "provenance_type IN "
            "('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT')"
        ),
    )

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True
    )
    constraint_id: Mapped[int] = mapped_column(
        ForeignKey("constraints.id", ondelete="CASCADE"), primary_key=True
    )
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
        CheckConstraint(
            "provenance_type IN "
            "('DIRECT_OBSERVATION', 'HUMAN_ASSESSMENT', 'DERIVED_QUERY_RESULT')"
        ),
        Index("ix_observations_experiment", "experiment_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE")
    )
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

    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), primary_key=True
    )
    label: Mapped[str] = mapped_column(Text, primary_key=True)

    experiment: Mapped[Experiment] = relationship(back_populates="prompt_labels")


class GenerationFailure(ResearchBase):
    __tablename__ = "generation_failures"
    __table_args__ = (Index("ix_generation_failures_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    prompt_text: Mapped[str] = mapped_column(Text)
    source_system: Mapped[str] = mapped_column(Text, default="Maestro Beta")
    failure_type: Mapped[str] = mapped_column(Text)
    displayed_message: Mapped[str] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

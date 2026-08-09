from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, MetaData, Table, inspect, select

from playlist_narrative_engine.research_store.database import ResearchBase
from playlist_narrative_engine.research_store.models import (
    Constraint, ConstraintResult, EvidenceLink, EvidenceSource, Experiment,
    ExperimentPromptLabel, ExperimentTrack, GenerationFailure, Observation,
    SchemaVersion, Track, TracklistEvidenceSegment,
)

CURRENT_SCHEMA_VERSION = 3


def get_schema_version(engine: Engine) -> int:
    if "schema_version" not in inspect(engine).get_table_names():
        return 0
    with engine.connect() as connection:
        versions = list(connection.scalars(select(SchemaVersion.version)))
    return max(versions, default=0)


def _rows(connection, table_name: str) -> list[dict]:
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=connection)
    return [dict(row._mapping) for row in connection.execute(table.select())]


def _migrate_v1_to_v2(engine: Engine) -> None:
    """Rebuild schema-v1 records under the complete-ingestion v2 contract."""
    table_names = set(inspect(engine).get_table_names())
    names = [
        "experiments", "tracks", "experiment_tracks", "constraints",
        "constraint_results", "observations", "experiment_prompt_labels",
        "generation_failures",
    ]
    with engine.connect() as connection:
        snapshot = {name: _rows(connection, name) if name in table_names else [] for name in names}
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        with connection.begin():
            old = MetaData()
            old.reflect(bind=connection)
            old.drop_all(bind=connection)
            ResearchBase.metadata.create_all(bind=connection)
            if snapshot["tracks"]:
                connection.execute(Track.__table__.insert(), snapshot["tracks"])
            for row in snapshot["experiments"]:
                connection.execute(Experiment.__table__.insert().values(
                    id=row["id"], recorded_at=row["created_at"], generated_at=None,
                    prompt_text=row["prompt_text"], prompt_title=row["prompt_title"],
                    source_system=row["source_system"],
                    generated_playlist_title=row["generated_playlist_title"],
                    generated_playlist_description=row["generated_playlist_description"],
                    requested_track_count=row["requested_track_count"],
                    generated_track_count=row["observed_track_count"],
                    observed_track_count=row["observed_track_count"],
                    tracklist_completeness="COMPLETE", saved_by_user=row["saved_by_user"],
                    evidence_standard="LEGACY_V1", overall_assessment=row["overall_assessment"],
                    notes=row["notes"],
                ))
                segment_id = connection.execute(TracklistEvidenceSegment.__table__.insert().values(
                    experiment_id=row["id"], segment_ordinal=1,
                    relationship_to_previous="FIRST", captures_playlist_start="YES",
                    captures_playlist_end="YES",
                    notes="Derived from the schema-v1 complete-ingestion contract.",
                )).inserted_primary_key[0]
                migration_source_id = connection.execute(EvidenceSource.__table__.insert().values(
                    experiment_id=row["id"], generation_failure_id=None,
                    persisted_artifact_id=None, persisted_artifact_experiment_link_id=None,
                    source_key="schema_v1_contract", source_type="SCHEMA_MIGRATION_CONTRACT",
                    source_reference="research-store schema version 1 complete-ingestion contract",
                    original_filename=None, local_path=None, sha256=None, source_timestamp=None,
                    notes="Structured provenance for facts deterministically created by migration 1 to 2.",
                )).inserted_primary_key[0]
                for field_name in (
                    "generated_track_count", "tracklist_completeness",
                    "segment.1.relationship_to_previous",
                    "segment.1.captures_playlist_start", "segment.1.captures_playlist_end",
                ):
                    connection.execute(EvidenceLink.__table__.insert().values(
                        evidence_source_id=migration_source_id, experiment_id=row["id"],
                        experiment_track_id=None, generation_failure_id=None,
                        persisted_artifact_id=None, persisted_artifact_track_id=None,
                        persisted_artifact_experiment_link_id=None,
                        field_name=field_name, provenance_type="MIGRATION_DERIVATION",
                        support_status="FULL", notes=None,
                    ))
                for placement in sorted(
                    (item for item in snapshot["experiment_tracks"] if item["experiment_id"] == row["id"]),
                    key=lambda item: item["position"],
                ):
                    connection.execute(ExperimentTrack.__table__.insert().values(
                        experiment_id=placement["experiment_id"], track_id=placement["track_id"],
                        evidence_segment_id=segment_id, observed_ordinal=placement["position"],
                        segment_ordinal=placement["position"], absolute_position=placement["position"],
                        display_title=placement["display_title"], display_artist=placement["display_artist"],
                        explicit_flag=placement["explicit_flag"],
                        version_or_remaster_text=placement["version_or_remaster_text"], notes=placement["notes"],
                    ))
            for row in snapshot["constraints"]:
                connection.execute(Constraint.__table__.insert().values(**row))
            for row in snapshot["constraint_results"]:
                connection.execute(ConstraintResult.__table__.insert().values(**row))
            placement_ids = {
                (row.experiment_id, row.absolute_position): row.id
                for row in connection.execute(select(ExperimentTrack)).all()
            }
            for row in snapshot["observations"]:
                connection.execute(Observation.__table__.insert().values(
                    id=row["id"], experiment_id=row["experiment_id"],
                    experiment_track_id=placement_ids.get((row["experiment_id"], row["track_position"])),
                    observation_type=row["observation_type"], observation_text=row["observation_text"],
                    severity=row["severity"], track_position=row["track_position"],
                    provenance_type=row["provenance_type"], recorded_by=row["recorded_by"],
                    provenance_notes=row["provenance_notes"],
                ))
            for row in snapshot["experiment_prompt_labels"]:
                connection.execute(ExperimentPromptLabel.__table__.insert().values(**row))
            for row in snapshot["generation_failures"]:
                connection.execute(GenerationFailure.__table__.insert().values(
                    id=row["id"], recorded_at=row["created_at"], generated_at=None,
                    prompt_text=row["prompt_text"], source_system=row["source_system"],
                    failure_type=row["failure_type"], displayed_message=row["displayed_message"],
                    notes=row["notes"], evidence_standard="LEGACY_V1",
                ))
            connection.execute(SchemaVersion.__table__.insert().values(
                version=2, applied_at=datetime.now(timezone.utc)
            ))
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()


def _migrate_v2_to_v3(engine: Engine) -> None:
    """Add persisted-artifact entities while preserving every v2 evidence ID."""
    with engine.connect() as connection:
        source_rows = _rows(connection, "evidence_sources")
        link_rows = _rows(connection, "evidence_links")
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
        with connection.begin():
            old = MetaData()
            old.reflect(bind=connection, only=["evidence_links", "evidence_sources"])
            old.tables["evidence_links"].drop(bind=connection)
            old.tables["evidence_sources"].drop(bind=connection)
            ResearchBase.metadata.create_all(bind=connection)
            for row in source_rows:
                row.update(persisted_artifact_id=None, persisted_artifact_experiment_link_id=None)
            for row in link_rows:
                row.update(
                    persisted_artifact_id=None,
                    persisted_artifact_track_id=None,
                    persisted_artifact_experiment_link_id=None,
                )
            if source_rows:
                connection.execute(EvidenceSource.__table__.insert(), source_rows)
            if link_rows:
                connection.execute(EvidenceLink.__table__.insert(), link_rows)
            connection.execute(SchemaVersion.__table__.insert().values(
                version=3, applied_at=datetime.now(timezone.utc)
            ))
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        connection.commit()


def migrate_research_database(engine: Engine) -> int:
    current = get_schema_version(engine)
    if current > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Research database schema {current} is newer than supported schema {CURRENT_SCHEMA_VERSION}"
        )
    if current == 0:
        ResearchBase.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(SchemaVersion.__table__.insert().values(
                version=3, applied_at=datetime.now(timezone.utc)
            ))
        return 3
    if current == 1:
        _migrate_v1_to_v2(engine)
        current = 2
    if current == 2:
        _migrate_v2_to_v3(engine)
        return 3
    return current

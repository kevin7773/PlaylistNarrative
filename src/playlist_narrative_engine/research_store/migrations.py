from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Engine, MetaData, Table, inspect, select

from playlist_narrative_engine.research_store.database import ResearchBase
from playlist_narrative_engine.research_store.models import (
    Constraint, ConstraintResult, EvidenceLink, EvidenceSource, Experiment,
    ExperimentPromptLabel, ExperimentTrack, GenerationFailure, Observation,
    SchemaVersion, Track, TracklistEvidenceSegment,
)

CURRENT_SCHEMA_VERSION = 8


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
                    assessment_outcome="INDETERMINATE",
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


def _migrate_v3_to_v4(engine: Engine) -> None:
    """Add an explicit assessment outcome without interpreting legacy prose."""
    with engine.begin() as connection:
        columns = {item["name"] for item in inspect(connection).get_columns("experiments")}
        if "assessment_outcome" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE experiments ADD COLUMN assessment_outcome VARCHAR(20) "
                "NOT NULL DEFAULT 'INDETERMINATE' "
                "CHECK (assessment_outcome IN "
                "('INDETERMINATE', 'PASS', 'PARTIAL_PASS', 'FAIL'))"
            )
        connection.execute(SchemaVersion.__table__.insert().values(
            version=4, applied_at=datetime.now(timezone.utc)
        ))


_PROTOCOL_CHILD_TABLES = {
    "study_conditions": "protocol_version_id",
    "study_blocks": "protocol_version_id",
    "study_constraint_definitions": "protocol_version_id",
    "study_outcome_definitions": "protocol_version_id",
    "study_analysis_definitions": "protocol_version_id",
    "study_planned_runs": "protocol_version_id",
}


def _create_study_immutability_triggers(connection) -> None:
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_identity_no_update "
        "BEFORE UPDATE ON studies BEGIN SELECT RAISE(ABORT, 'registered study identity is immutable'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_identity_no_delete "
        "BEFORE DELETE ON studies BEGIN SELECT RAISE(ABORT, 'registered study identity is immutable'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_protocol_no_update_after_registration "
        "BEFORE UPDATE ON study_protocol_versions WHEN OLD.registered_at IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'registered protocol is immutable'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_protocol_no_delete_after_registration "
        "BEFORE DELETE ON study_protocol_versions WHEN OLD.registered_at IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'registered protocol is immutable'); END"
    )
    for table, column in _PROTOCOL_CHILD_TABLES.items():
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_insert_after_registration "
            f"BEFORE INSERT ON {table} WHEN "
            f"(SELECT registered_at FROM study_protocol_versions WHERE id=NEW.{column}) IS NOT NULL "
            "BEGIN SELECT RAISE(ABORT, 'registered protocol children are immutable'); END"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update_after_registration "
            f"BEFORE UPDATE ON {table} WHEN "
            f"(SELECT registered_at FROM study_protocol_versions WHERE id=OLD.{column}) IS NOT NULL "
            "BEGIN SELECT RAISE(ABORT, 'registered protocol children are immutable'); END"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete_after_registration "
            f"BEFORE DELETE ON {table} WHEN "
            f"(SELECT registered_at FROM study_protocol_versions WHERE id=OLD.{column}) IS NOT NULL "
            "BEGIN SELECT RAISE(ABORT, 'registered protocol children are immutable'); END"
        )
    for table in ("study_planned_run_constraints",):
        parent = (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_planned_runs pr ON pr.protocol_version_id=pv.id "
            f"WHERE pr.id={{alias}}.planned_run_id"
        )
        for action, alias in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}_after_registration "
                f"BEFORE {action} ON {table} WHEN ({parent.format(alias=alias)}) IS NOT NULL "
                "BEGIN SELECT RAISE(ABORT, 'registered protocol applicability is immutable'); END"
            )
    p7_parents = {
        "study_constraint_evaluation_plans": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_constraint_definitions cd ON cd.protocol_version_id=pv.id "
            "WHERE cd.id={alias}.constraint_definition_id"
        ),
        "study_constraint_measurement_definitions": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_constraint_definitions cd ON cd.protocol_version_id=pv.id "
            "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=cd.id "
            "WHERE ep.id={alias}.evaluation_plan_id"
        ),
        "study_constraint_evaluation_parameters": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_constraint_definitions cd ON cd.protocol_version_id=pv.id "
            "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=cd.id "
            "WHERE ep.id={alias}.evaluation_plan_id"
        ),
        "study_constraint_evaluation_vocabulary_terms": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_constraint_definitions cd ON cd.protocol_version_id=pv.id "
            "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=cd.id "
            "WHERE ep.id={alias}.evaluation_plan_id"
        ),
    }
    for table, parent in p7_parents.items():
        for action, alias in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}_after_registration "
                f"BEFORE {action} ON {table} WHEN ({parent.format(alias=alias)}) IS NOT NULL "
                "BEGIN SELECT RAISE(ABORT, 'registered structured-evaluation plan is immutable'); END"
            )
    execution_parents = {
        "study_execution_contracts": (
            "SELECT registered_at FROM study_protocol_versions "
            "WHERE id={alias}.protocol_version_id"
        ),
        "study_outcome_calculation_plans": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "WHERE ec.id={alias}.execution_contract_id"
        ),
        "study_outcome_disposition_policies": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_outcome_calculation_plans op ON op.execution_contract_id=ec.id "
            "WHERE op.id={alias}.calculation_plan_id"
        ),
        "study_outcome_constraint_bindings": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_outcome_calculation_plans op ON op.execution_contract_id=ec.id "
            "WHERE op.id={alias}.calculation_plan_id"
        ),
        "study_outcome_subject_kinds": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_outcome_calculation_plans op ON op.execution_contract_id=ec.id "
            "WHERE op.id={alias}.calculation_plan_id"
        ),
        "study_outcome_calculation_parameters": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_outcome_calculation_plans op ON op.execution_contract_id=ec.id "
            "WHERE op.id={alias}.calculation_plan_id"
        ),
        "study_outcome_calculation_vocabulary_terms": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_outcome_calculation_plans op ON op.execution_contract_id=ec.id "
            "WHERE op.id={alias}.calculation_plan_id"
        ),
        "study_analysis_calculation_plans": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "WHERE ec.id={alias}.execution_contract_id"
        ),
        "study_analysis_dimensions": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_analysis_calculation_plans ap ON ap.execution_contract_id=ec.id "
            "WHERE ap.id={alias}.calculation_plan_id"
        ),
        "study_analysis_condition_bindings": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_analysis_calculation_plans ap ON ap.execution_contract_id=ec.id "
            "WHERE ap.id={alias}.calculation_plan_id"
        ),
        "study_analysis_calculation_parameters": (
            "SELECT pv.registered_at FROM study_protocol_versions pv "
            "JOIN study_execution_contracts ec ON ec.protocol_version_id=pv.id "
            "JOIN study_analysis_calculation_plans ap ON ap.execution_contract_id=ec.id "
            "WHERE ap.id={alias}.calculation_plan_id"
        ),
    }
    for table, parent in execution_parents.items():
        for action, alias in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
            connection.exec_driver_sql(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}_after_registration "
                f"BEFORE {action} ON {table} WHEN ({parent.format(alias=alias)}) IS NOT NULL "
                "BEGIN SELECT RAISE(ABORT, 'registered execution contract is immutable'); END"
            )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_outcome_binding_same_protocol "
        "BEFORE INSERT ON study_outcome_constraint_bindings BEGIN "
        "SELECT CASE WHEN (SELECT cd.protocol_version_id FROM study_constraint_definitions cd WHERE cd.id=NEW.constraint_definition_id) != "
        "(SELECT ec.protocol_version_id FROM study_outcome_calculation_plans op JOIN study_execution_contracts ec ON ec.id=op.execution_contract_id WHERE op.id=NEW.calculation_plan_id) "
        "THEN RAISE(ABORT, 'outcome constraint binding crosses protocol versions') END; END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_analysis_condition_same_protocol "
        "BEFORE INSERT ON study_analysis_condition_bindings BEGIN "
        "SELECT CASE WHEN (SELECT c.protocol_version_id FROM study_conditions c WHERE c.id=NEW.condition_id) != "
        "(SELECT ec.protocol_version_id FROM study_analysis_calculation_plans ap JOIN study_execution_contracts ec ON ec.id=ap.execution_contract_id WHERE ap.id=NEW.calculation_plan_id) "
        "THEN RAISE(ABORT, 'analysis condition binding crosses protocol versions') END; END"
    )
    for table in ("study_run_attempts", "study_run_realizations"):
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update "
            f"BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'study run history is append-only'); END"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete "
            f"BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'study run history is append-only'); END"
        )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_realization_no_predating_experiment "
        "BEFORE INSERT ON study_run_realizations "
        "WHEN NEW.experiment_id IS NOT NULL AND "
        "(SELECT e.recorded_at FROM experiments e WHERE e.id=NEW.experiment_id) < "
        "(SELECT pv.registered_at FROM study_protocol_versions pv "
        "JOIN study_planned_runs pr ON pr.protocol_version_id=pv.id "
        "WHERE pr.id=NEW.planned_run_id) "
        "BEGIN SELECT RAISE(ABORT, 'experiment predates protocol registration'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_realization_no_predating_failure "
        "BEFORE INSERT ON study_run_realizations "
        "WHEN NEW.generation_failure_id IS NOT NULL AND "
        "(SELECT gf.recorded_at FROM generation_failures gf WHERE gf.id=NEW.generation_failure_id) < "
        "(SELECT pv.registered_at FROM study_protocol_versions pv "
        "JOIN study_planned_runs pr ON pr.protocol_version_id=pv.id "
        "WHERE pr.id=NEW.planned_run_id) "
        "BEGIN SELECT RAISE(ABORT, 'generation failure predates protocol registration'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_linked_constraint_no_update "
        "BEFORE UPDATE ON constraints WHEN OLD.study_constraint_definition_id IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'study-attributed constraint snapshots are immutable'); END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_linked_constraint_no_delete "
        "BEFORE DELETE ON constraints WHEN OLD.study_constraint_definition_id IS NOT NULL "
        "BEGIN SELECT RAISE(ABORT, 'study-attributed constraint snapshots are immutable'); END"
    )


def _create_p7_runtime_triggers(connection) -> None:
    runtime_tables = (
        "constraint_evaluation_subjects",
        "constraint_evaluation_measurements",
        "constraint_evaluation_measurement_evidence",
        "constraint_subject_results",
    )
    for table in runtime_tables:
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'structured evaluation runtime is immutable'); END"
        )
    for action in ("UPDATE", "DELETE"):
        alias = "OLD"
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS structured_constraint_result_no_{action.lower()} "
            f"BEFORE {action} ON constraint_results WHEN EXISTS ("
            "SELECT 1 FROM constraints c JOIN study_constraint_evaluation_plans ep "
            "ON ep.constraint_definition_id=c.study_constraint_definition_id "
            f"WHERE c.id={alias}.constraint_id) "
            "BEGIN SELECT RAISE(ABORT, 'structured aggregate ConstraintResult is immutable'); END"
        )
        connection.exec_driver_sql(
            f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
            "BEGIN SELECT RAISE(ABORT, 'structured evaluation runtime is immutable'); END"
        )

    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS constraint_evaluation_subject_validate_insert "
        "BEFORE INSERT ON constraint_evaluation_subjects BEGIN "
        "SELECT CASE WHEN (SELECT experiment_id FROM constraints WHERE id=NEW.constraint_id) != NEW.experiment_id "
        "THEN RAISE(ABORT, 'evaluation subject constraint belongs to another experiment') END; "
        "SELECT CASE WHEN NEW.experiment_track_id IS NOT NULL AND "
        "(SELECT experiment_id FROM experiment_tracks WHERE id=NEW.experiment_track_id) != NEW.experiment_id "
        "THEN RAISE(ABORT, 'evaluation subject placement belongs to another experiment') END; "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraints c "
        "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=c.study_constraint_definition_id "
        "WHERE c.id=NEW.constraint_id) "
        "THEN RAISE(ABORT, 'constraint has no registered structured-evaluation plan') END; "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraints c "
        "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=c.study_constraint_definition_id "
        "WHERE c.id=NEW.constraint_id AND ep.subject_kind=NEW.subject_kind "
        "AND COALESCE(ep.subject_field,'')=COALESCE(NEW.governed_field,'')) "
        "THEN RAISE(ABORT, 'evaluation subject differs from registered plan') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_subjects existing "
        "WHERE existing.constraint_id=NEW.constraint_id AND existing.subject_kind=NEW.subject_kind "
        "AND COALESCE(existing.experiment_track_id,-1)=COALESCE(NEW.experiment_track_id,-1) "
        "AND COALESCE(existing.governed_field,'')=COALESCE(NEW.governed_field,'')) "
        "THEN RAISE(ABORT, 'duplicate evaluation subject') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM study_run_realizations WHERE experiment_id=NEW.experiment_id) "
        "THEN RAISE(ABORT, 'cannot attach structured evaluation after realization') END; "
        "END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS constraint_evaluation_measurement_validate_insert "
        "BEFORE INSERT ON constraint_evaluation_measurements BEGIN "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraint_evaluation_subjects s "
        "JOIN constraints c ON c.id=s.constraint_id "
        "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=c.study_constraint_definition_id "
        "JOIN study_constraint_measurement_definitions md ON md.evaluation_plan_id=ep.id "
        "WHERE s.id=NEW.subject_id AND md.id=NEW.measurement_definition_id) "
        "THEN RAISE(ABORT, 'measurement definition does not govern subject constraint') END; "
        "SELECT CASE WHEN (SELECT authority FROM study_constraint_measurement_definitions WHERE id=NEW.measurement_definition_id) != NEW.authority_kind "
        "THEN RAISE(ABORT, 'measurement authority differs from registered definition') END; "
        "SELECT CASE WHEN NEW.value_type != 'UNAVAILABLE' AND "
        "(SELECT value_type FROM study_constraint_measurement_definitions WHERE id=NEW.measurement_definition_id) != NEW.value_type "
        "THEN RAISE(ABORT, 'measurement value type differs from registered definition') END; "
        "SELECT CASE WHEN NEW.value_type='VOCABULARY_TERM' AND NOT EXISTS ("
        "SELECT 1 FROM study_constraint_measurement_definitions md "
        "JOIN study_constraint_evaluation_vocabulary_terms vt "
        "ON vt.evaluation_plan_id=md.evaluation_plan_id AND vt.vocabulary_key=md.vocabulary_key "
        "WHERE md.id=NEW.measurement_definition_id AND vt.term_key=NEW.vocabulary_term_key) "
        "THEN RAISE(ABORT, 'measurement vocabulary term is not registered') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_subjects s "
        "JOIN study_run_realizations r ON r.experiment_id=s.experiment_id WHERE s.id=NEW.subject_id) "
        "THEN RAISE(ABORT, 'cannot attach structured evaluation after realization') END; "
        "END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS constraint_evaluation_evidence_validate_insert "
        "BEFORE INSERT ON constraint_evaluation_measurement_evidence BEGIN "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraint_evaluation_measurements m "
        "JOIN constraint_evaluation_subjects s ON s.id=m.subject_id "
        "JOIN evidence_sources es ON es.id=NEW.evidence_source_id "
        "WHERE m.id=NEW.measurement_id AND es.experiment_id=s.experiment_id) "
        "THEN RAISE(ABORT, 'evaluation evidence belongs to another experiment') END; "
        "SELECT CASE WHEN NEW.evidence_link_id IS NOT NULL AND NOT EXISTS ("
        "SELECT 1 FROM constraint_evaluation_measurements m "
        "JOIN constraint_evaluation_subjects s ON s.id=m.subject_id "
        "JOIN evidence_links el ON el.id=NEW.evidence_link_id "
        "JOIN evidence_sources es ON es.id=el.evidence_source_id "
        "WHERE m.id=NEW.measurement_id AND el.evidence_source_id=NEW.evidence_source_id "
        "AND es.experiment_id=s.experiment_id) "
        "THEN RAISE(ABORT, 'evaluation evidence link belongs to another experiment or source') END; "
        "SELECT CASE WHEN NEW.evidence_link_id IS NOT NULL AND EXISTS ("
        "SELECT 1 FROM constraint_evaluation_measurements m "
        "JOIN constraint_evaluation_subjects s ON s.id=m.subject_id "
        "JOIN evidence_links el ON el.id=NEW.evidence_link_id "
        "WHERE m.id=NEW.measurement_id AND s.subject_kind='PLACEMENT_FIELD' AND "
        "(el.experiment_track_id IS NULL OR el.experiment_track_id != s.experiment_track_id OR "
        "NOT ((s.governed_field='display_title' AND el.field_name='title') OR "
        "(s.governed_field='display_artist' AND el.field_name='artist') OR "
        "(s.governed_field=el.field_name)))) "
        "THEN RAISE(ABORT, 'field evidence link does not match evaluation subject') END; "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraint_evaluation_measurements m "
        "JOIN study_constraint_measurement_definitions md ON md.id=m.measurement_definition_id "
        "WHERE m.id=NEW.measurement_id AND ((md.authority='DIRECT_OBSERVATION' AND NEW.evidence_role IN ('SUBJECT_IDENTITY','OBSERVED_VALUE')) OR "
        "(md.authority='STRUCTURAL_DERIVATION' AND NEW.evidence_role='SUBJECT_IDENTITY') OR "
        "(md.authority='EXTERNAL_FACT_VERIFICATION' AND NEW.evidence_role IN ('SUBJECT_IDENTITY','EXTERNAL_FACT','CORRESPONDENCE')) OR "
        "(md.authority='HUMAN_ASSESSMENT' AND NEW.evidence_role IN ('SUBJECT_IDENTITY','OPERATOR_JUDGMENT')))) "
        "THEN RAISE(ABORT, 'evidence role is not permitted for measurement authority') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_measurement_evidence existing "
        "WHERE existing.measurement_id=NEW.measurement_id "
        "AND existing.evidence_source_id=NEW.evidence_source_id "
        "AND COALESCE(existing.evidence_link_id,-1)=COALESCE(NEW.evidence_link_id,-1) "
        "AND existing.evidence_role=NEW.evidence_role) "
        "THEN RAISE(ABORT, 'duplicate evaluation measurement evidence') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_measurements m "
        "JOIN constraint_evaluation_subjects s ON s.id=m.subject_id "
        "JOIN study_run_realizations r ON r.experiment_id=s.experiment_id WHERE m.id=NEW.measurement_id) "
        "THEN RAISE(ABORT, 'cannot attach structured evaluation after realization') END; "
        "END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS constraint_subject_result_validate_insert "
        "BEFORE INSERT ON constraint_subject_results BEGIN "
        "SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM constraint_evaluation_subjects s "
        "JOIN constraints c ON c.id=s.constraint_id "
        "JOIN study_constraint_evaluation_plans ep ON ep.constraint_definition_id=c.study_constraint_definition_id "
        "WHERE s.id=NEW.subject_id AND ep.subject_evaluator_key=NEW.evaluator_key "
        "AND ep.subject_evaluator_version=NEW.evaluator_version) "
        "THEN RAISE(ABORT, 'subject result evaluator differs from registered plan') END; "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_subjects s "
        "JOIN study_run_realizations r ON r.experiment_id=s.experiment_id WHERE s.id=NEW.subject_id) "
        "THEN RAISE(ABORT, 'cannot attach structured evaluation after realization') END; "
        "END"
    )
    connection.exec_driver_sql(
        "CREATE TRIGGER IF NOT EXISTS study_realization_structured_protocol_match "
        "BEFORE INSERT ON study_run_realizations WHEN NEW.experiment_id IS NOT NULL BEGIN "
        "SELECT CASE WHEN EXISTS (SELECT 1 FROM constraint_evaluation_subjects s "
        "JOIN constraints c ON c.id=s.constraint_id "
        "JOIN study_constraint_definitions cd ON cd.id=c.study_constraint_definition_id "
        "JOIN study_planned_runs pr ON pr.id=NEW.planned_run_id "
        "WHERE s.experiment_id=NEW.experiment_id AND cd.protocol_version_id != pr.protocol_version_id) "
        "THEN RAISE(ABORT, 'structured evaluation protocol does not match planned run') END; "
        "END"
    )


def _migrate_v4_to_v5(engine: Engine) -> None:
    """Add prospective study registration without reinterpreting experiments."""
    with engine.begin() as connection:
        ResearchBase.metadata.create_all(bind=connection)
        columns = {item["name"] for item in inspect(connection).get_columns("constraints")}
        if "study_constraint_definition_id" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE constraints ADD COLUMN study_constraint_definition_id INTEGER "
                "REFERENCES study_constraint_definitions(id)"
            )
        _create_study_immutability_triggers(connection)
        connection.execute(SchemaVersion.__table__.insert().values(
            version=5, applied_at=datetime.now(timezone.utc)
        ))


def _migrate_v5_to_v6(engine: Engine) -> None:
    """Add prospective structured-evaluation protocol and runtime storage."""
    with engine.begin() as connection:
        ResearchBase.metadata.create_all(bind=connection)
        _create_study_immutability_triggers(connection)
        _create_p7_runtime_triggers(connection)
        connection.execute(SchemaVersion.__table__.insert().values(
            version=6, applied_at=datetime.now(timezone.utc)
        ))


def _migrate_v6_to_v7(engine: Engine) -> None:
    """Add prospective Study execution-contract declarations without runtime results."""
    with engine.begin() as connection:
        ResearchBase.metadata.create_all(bind=connection)
        _create_study_immutability_triggers(connection)
        _create_p7_runtime_triggers(connection)
        connection.execute(SchemaVersion.__table__.insert().values(
            version=7, applied_at=datetime.now(timezone.utc)
        ))


def _migrate_v7_to_v8(engine: Engine) -> None:
    """Add prospective outcome disposition authority without runtime results."""
    with engine.begin() as connection:
        ResearchBase.metadata.create_all(bind=connection)
        _create_study_immutability_triggers(connection)
        _create_p7_runtime_triggers(connection)
        connection.execute(SchemaVersion.__table__.insert().values(
            version=8, applied_at=datetime.now(timezone.utc)
        ))


def migrate_research_database(engine: Engine) -> int:
    current = get_schema_version(engine)
    if current > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"Research database schema {current} is newer than supported schema {CURRENT_SCHEMA_VERSION}"
        )
    if current == 0:
        ResearchBase.metadata.create_all(engine)
        with engine.begin() as connection:
            _create_study_immutability_triggers(connection)
            _create_p7_runtime_triggers(connection)
            connection.execute(SchemaVersion.__table__.insert().values(
                version=8, applied_at=datetime.now(timezone.utc)
            ))
        return 8
    if current == 1:
        _migrate_v1_to_v2(engine)
        current = 2
    if current == 2:
        _migrate_v2_to_v3(engine)
        current = 3
    if current == 3:
        _migrate_v3_to_v4(engine)
        current = 4
    if current == 4:
        _migrate_v4_to_v5(engine)
        current = 5
    if current == 5:
        _migrate_v5_to_v6(engine)
        current = 6
    if current == 6:
        _migrate_v6_to_v7(engine)
        current = 7
    if current == 7:
        _migrate_v7_to_v8(engine)
        return 8
    return current

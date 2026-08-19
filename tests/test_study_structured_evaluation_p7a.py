from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, select, text
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.database import (
    make_research_engine,
    make_research_session_factory,
)
from playlist_narrative_engine.research_store.migrations import (
    get_schema_version,
    migrate_research_database,
)
from playlist_narrative_engine.research_store.models import (
    StudyConstraintEvaluationParameter,
    StudyConstraintEvaluationPlan,
    StudyConstraintEvaluationVocabularyTerm,
    StudyConstraintMeasurementDefinition,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_evaluator_registry import (
    EvaluatorIdentity,
    EvaluatorRole,
    StudyEvaluatorRegistry,
)
from playlist_narrative_engine.research_store.study_protocol import (
    canonical_protocol_bytes,
    legacy_canonical_protocol_bytes,
    protocol_registration_hash,
)
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput


def _document(*, structured: bool) -> dict[str, object]:
    constraint = {
        "constraint_key": "generic-constraint",
        "constraint_type": "prospective_generic",
        "constraint_text": "Apply the frozen generic predicate.",
        "is_hard_constraint": True,
        "evaluation_rule": "Use the frozen structured evaluator plan.",
        "permitted_result_provenance": (
            "DERIVED_QUERY_RESULT" if structured else "DIRECT_OBSERVATION"
        ),
        "unknown_handling": "UNKNOWN remains missing and is never converted to FAIL.",
    }
    if structured:
        constraint["structured_evaluation_plan"] = {
            "instrumentation_version": "1",
            "subject_kind": "PLACEMENT_FIELD",
            "subject_field": "display_title",
            "subject_selector": {
                "evaluator_key": "selector.generic",
                "evaluator_version": "1",
            },
            "subject_evaluator": {
                "evaluator_key": "subject.generic",
                "evaluator_version": "1",
            },
            "aggregate_evaluator": {
                "evaluator_key": "aggregate.generic",
                "evaluator_version": "1",
            },
            "require_complete_subject_set": True,
            "allow_partial_subject_status": False,
            "measurement_definitions": [{
                "measurement_key": "displayed-value",
                "authority": "DIRECT_OBSERVATION",
                "value_type": "VOCABULARY_TERM",
                "vocabulary_key": "observed-status",
                "required": True,
                "evidence_required": True,
                "unavailable_policy": "MAY_BE_UNAVAILABLE",
            }],
            "parameters": [{
                "parameter_key": "expected-term",
                "value_type": "VOCABULARY_TERM",
                "vocabulary_key": "observed-status",
                "vocabulary_term_key": "present",
            }],
            "vocabulary_terms": [{
                "vocabulary_key": "observed-status",
                "term_key": "present",
                "term_definition": "The exact displayed value is present.",
            }],
        }
    return {
        "study_key": "P7A-SYNTHETIC",
        "title": "Prospective structured evaluation",
        "protocol": {
            "version_number": 1,
            "objective": "Test protocol-time structured evaluation registration.",
            "primary_hypothesis": "The registered condition changes compliance.",
            "null_hypothesis": "The registered condition does not change compliance.",
            "design_summary": "One synthetic prospective run.",
            "planned_sample_size": 1,
            "randomization_method": "One frozen ordinal.",
            "randomization_seed": "p7a-seed",
            "operational_failure_policy": "Operational failures do not consume the run.",
            "refusal_policy": "Refusals terminally realize the run.",
            "missing_result_policy": "UNKNOWN is not imputed.",
            "conditions": [{
                "condition_key": "control", "label": "Control", "role": "CONTROL",
                "exact_factor_definition": "No treatment factor.",
            }],
            "blocks": [{
                "block_key": "block-1", "label": "Block 1",
                "block_definition": "Synthetic registration block.",
            }],
            "constraint_definitions": [constraint],
            "outcome_definitions": [{
                "outcome_key": "primary", "role": "PRIMARY",
                "unit_of_analysis": "planned run", "outcome_definition": "Aggregate status.",
                "computation_rule": "Use the aggregate ConstraintResult.",
                "missing_data_rule": "UNKNOWN is missing.",
                "refusal_handling": "Report separately.",
                "operational_failure_handling": "Exclude.",
            }],
            "analysis_definitions": [{
                "analysis_key": "primary", "outcome_key": "primary",
                "analysis_population": "Terminal scientific runs.",
                "comparison_definition": "Report the registered result.",
                "aggregation_rule": "Descriptive only.",
                "exclusion_rule": "Exclude operational failures.",
                "reporting_rule": "Report UNKNOWN separately.",
            }],
            "planned_runs": [{
                "run_key": "run-1", "condition_key": "control", "block_key": "block-1",
                "replicate_number": 1, "randomized_ordinal": 1,
                "planned_prompt_text": "Return one governed output.",
                "planned_source_system": "Maestro Beta",
                "applicable_constraint_keys": ["generic-constraint"],
            }],
        },
    }


def _registry() -> StudyEvaluatorRegistry:
    return StudyEvaluatorRegistry({
        EvaluatorIdentity(EvaluatorRole.SUBJECT_SELECTOR, "selector.generic", "1"),
        EvaluatorIdentity(EvaluatorRole.SUBJECT_EVALUATOR, "subject.generic", "1"),
        EvaluatorIdentity(EvaluatorRole.AGGREGATE_EVALUATOR, "aggregate.generic", "1"),
    })


def _proposal(*, structured: bool) -> StudyRegistrationInput:
    return StudyRegistrationInput.model_validate(_document(structured=structured))


def test_legacy_protocol_canonical_bytes_and_hash_are_exactly_stable() -> None:
    legacy = _proposal(structured=False)
    current = canonical_protocol_bytes(legacy.study_key, legacy.title, legacy.protocol)
    historical = legacy_canonical_protocol_bytes(
        legacy.study_key, legacy.title, legacy.protocol
    )
    assert current == historical
    assert b"structured_evaluation_plan" not in current
    assert protocol_registration_hash(
        legacy.study_key, legacy.title, legacy.protocol
    ) == protocol_registration_hash(legacy.study_key, legacy.title, legacy.protocol)


@pytest.mark.parametrize("mutation", [
    "subject_evaluator_version", "measurement_definition", "parameter", "vocabulary",
])
def test_every_governed_plan_element_changes_future_protocol_hash(mutation: str) -> None:
    baseline = _document(structured=True)
    changed = deepcopy(baseline)
    plan = changed["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]
    if mutation == "subject_evaluator_version":
        plan["subject_evaluator"]["evaluator_version"] = "2"
    elif mutation == "measurement_definition":
        plan["measurement_definitions"][0]["evidence_required"] = False
    elif mutation == "parameter":
        plan["parameters"][0]["vocabulary_term_key"] = "absent"
        plan["vocabulary_terms"].append({
            "vocabulary_key": "observed-status", "term_key": "absent",
            "term_definition": "The exact displayed value is absent.",
        })
    else:
        plan["vocabulary_terms"][0]["term_definition"] = "Changed governed meaning."
    left = StudyRegistrationInput.model_validate(baseline)
    right = StudyRegistrationInput.model_validate(changed)
    assert protocol_registration_hash(left.study_key, left.title, left.protocol) != protocol_registration_hash(
        right.study_key, right.title, right.protocol
    )


def test_legacy_canonicalizer_refuses_to_discard_a_future_plan() -> None:
    proposal = _proposal(structured=True)
    with pytest.raises(ValueError, match="cannot omit"):
        legacy_canonical_protocol_bytes(proposal.study_key, proposal.title, proposal.protocol)


def test_registration_rejects_unsupported_evaluator_identity(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    with pytest.raises(ValueError, match="unsupported structured-evaluation evaluator identity"):
        service.register_study(_proposal(structured=True))
    assert service.list_studies() == []


def test_supported_plan_is_persisted_and_immutable_after_registration(research_session) -> None:
    service = ResearchStoreService(
        ResearchRepository(research_session), evaluator_registry=_registry()
    )
    proposal = _proposal(structured=True)
    study = service.register_study(proposal)
    protocol = service.get_protocol_version(study["id"], 1)
    plan = protocol["constraint_definitions"][0]["structured_evaluation_plan"]
    assert plan["subject_evaluator"] == {
        "evaluator_key": "subject.generic", "evaluator_version": "1"
    }
    assert len(plan["measurement_definitions"]) == 1
    assert len(plan["parameters"]) == 1
    assert len(plan["vocabulary_terms"]) == 1
    with pytest.raises(IntegrityError, match="structured-evaluation plan is immutable"):
        research_session.execute(text(
            "UPDATE study_constraint_evaluation_plans "
            "SET instrumentation_version='changed' WHERE id=:id"
        ), {"id": plan["id"]})
        research_session.commit()
    research_session.rollback()


def test_legacy_registration_has_no_implicit_or_default_plan(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    proposal = _proposal(structured=False)
    stored = service.register_study(proposal)
    protocol = service.get_protocol_version(stored["id"], 1)
    assert "structured_evaluation_plan" not in protocol["constraint_definitions"][0]
    assert research_session.scalar(select(func.count()).select_from(StudyConstraintEvaluationPlan)) == 0
    assert research_session.scalar(select(func.count()).select_from(StudyConstraintMeasurementDefinition)) == 0
    assert research_session.scalar(select(func.count()).select_from(StudyConstraintEvaluationParameter)) == 0
    assert research_session.scalar(select(func.count()).select_from(StudyConstraintEvaluationVocabularyTerm)) == 0


def test_v5_to_latest_is_additive_and_preserves_existing_governed_rows(tmp_path) -> None:
    engine = make_research_engine(f"sqlite:///{(tmp_path / 'representative-v5.db').as_posix()}")
    assert migrate_research_database(engine) == 9
    factory = make_research_session_factory(engine)
    with factory() as session:
        service = ResearchStoreService(ResearchRepository(session))
        study = service.register_study(_proposal(structured=False))
        protocol = service.get_protocol_version(study["id"], 1)
        definition = protocol["constraint_definitions"][0]
        service.ingest_planned_experiment(
            protocol["planned_runs"][0]["id"],
            ExperimentInput.model_validate({
                "prompt": "Return one governed output.",
                "source_system": "Maestro Beta",
                "generated_title": "Observed",
                "tracks": [{
                    "position": 1, "title": "Track", "artist": "Artist",
                    "evidence": [{"source_key": "source-1", "field_name": "title"}],
                }],
                "evidence_sources": [{
                    "source_key": "source-1", "source_type": "SCREENSHOT",
                    "source_reference": "synthetic governed source",
                }],
                "constraints": [{
                    "study_constraint_definition_id": definition["id"],
                    "constraint_type": definition["constraint_type"],
                    "constraint_text": definition["constraint_text"],
                    "is_hard_constraint": definition["is_hard_constraint"],
                    "result": {
                        "status": "PASS", "provenance_type": "DIRECT_OBSERVATION",
                    },
                }],
            }),
        )
    governed_tables = (
        "experiments", "constraint_results", "study_run_realizations",
        "evidence_sources", "evidence_links",
    )
    with engine.begin() as connection:
        before = {
            table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in governed_tables
        }
        stored_hashes = list(connection.scalars(text(
            "SELECT registration_hash FROM study_protocol_versions ORDER BY id"
        )))
        for table in (
            "study_constraint_evaluation_vocabulary_terms",
            "study_constraint_evaluation_parameters",
            "study_constraint_measurement_definitions",
            "study_constraint_evaluation_plans",
        ):
            connection.exec_driver_sql(f"DROP TABLE {table}")
            connection.execute(text("DELETE FROM schema_version WHERE version IN (6, 7, 8, 9)"))
        connection.execute(text(
            "INSERT OR IGNORE INTO schema_version(version, applied_at) VALUES (5, CURRENT_TIMESTAMP)"
        ))
    assert get_schema_version(engine) == 5
    assert migrate_research_database(engine) == 9
    with engine.connect() as connection:
        after = {
            table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in governed_tables
        }
        after_hashes = list(connection.scalars(text(
            "SELECT registration_hash FROM study_protocol_versions ORDER BY id"
        )))
        p7_counts = {
            table: connection.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            for table in (
                "study_constraint_evaluation_plans",
                "study_constraint_measurement_definitions",
                "study_constraint_evaluation_parameters",
                "study_constraint_evaluation_vocabulary_terms",
                "constraint_evaluation_subjects",
                "constraint_evaluation_measurements",
                "constraint_evaluation_measurement_evidence",
                "constraint_subject_results",
            )
        }
    assert before == after
    assert stored_hashes == after_hashes
    assert set(p7_counts.values()) == {0}
    measurement_columns = {
        item["name"] for item in inspect(engine).get_columns("study_constraint_measurement_definitions")
    }
    assert {"derivation_key", "derivation_version", "unavailable_policy"} <= measurement_columns

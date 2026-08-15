from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.models import (
    Constraint,
    ConstraintEvaluationMeasurement,
    ConstraintEvaluationMeasurementEvidence,
    ConstraintEvaluationSubject,
    ConstraintSubjectResult,
    EvidenceLink,
    EvidenceSource,
    ExperimentTrack,
    StudyConstraintMeasurementDefinition,
    StudyRunRealization,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_schemas import StudyRegistrationInput
from test_study_structured_evaluation_p7a import _document, _registry


def _registration() -> StudyRegistrationInput:
    document = _document(structured=True)
    base = document["protocol"]["constraint_definitions"][0]
    field = deepcopy(base)
    field["constraint_key"] = "field-constraint"
    field["structured_evaluation_plan"]["measurement_definitions"] = [
        {"measurement_key": "observed", "authority": "DIRECT_OBSERVATION", "value_type": "TEXT", "required": True, "evidence_required": True, "unavailable_policy": "MAY_BE_UNAVAILABLE"},
        {"measurement_key": "external", "authority": "EXTERNAL_FACT_VERIFICATION", "value_type": "DATE", "required": False, "evidence_required": True, "unavailable_policy": "MAY_BE_UNAVAILABLE"},
        {"measurement_key": "judgment", "authority": "HUMAN_ASSESSMENT", "value_type": "TEXT", "required": False, "evidence_required": True, "unavailable_policy": "MAY_BE_UNAVAILABLE"},
        {"measurement_key": "vocabulary", "authority": "DIRECT_OBSERVATION", "value_type": "VOCABULARY_TERM", "vocabulary_key": "observed-status", "required": False, "evidence_required": True, "unavailable_policy": "MAY_BE_UNAVAILABLE"},
    ]
    placement = deepcopy(base)
    placement["constraint_key"] = "placement-constraint"
    placement["structured_evaluation_plan"]["subject_kind"] = "EXPERIMENT_PLACEMENT"
    placement["structured_evaluation_plan"]["subject_field"] = None
    run = deepcopy(base)
    run["constraint_key"] = "run-constraint"
    run["structured_evaluation_plan"]["subject_kind"] = "RUN"
    run["structured_evaluation_plan"]["subject_field"] = None
    run["structured_evaluation_plan"]["measurement_definitions"] = [
        {"measurement_key": "count", "authority": "STRUCTURAL_DERIVATION", "value_type": "INTEGER", "required": True, "evidence_required": False, "derivation_key": "structural.placement_count", "derivation_version": "1", "unavailable_policy": "MUST_HAVE_VALUE"},
    ]
    document["protocol"]["constraint_definitions"] = [field, placement, run]
    document["protocol"]["planned_runs"][0]["applicable_constraint_keys"] = [
        "field-constraint", "placement-constraint", "run-constraint"
    ]
    return StudyRegistrationInput.model_validate(document)


def _setup(research_session):
    service = ResearchStoreService(
        ResearchRepository(research_session), evaluator_registry=_registry()
    )
    study = service.register_study(_registration())
    protocol = service.get_protocol_version(study["id"], 1)
    definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
    proposal = ExperimentInput.model_validate({
        "prompt": "Return one governed output.",
        "source_system": "Maestro Beta",
        "generated_title": "Observed",
        "tracks": [{
            "position": 1, "title": "Track", "artist": "Artist",
            "evidence": [
                {"source_key": "screenshot", "field_name": "title"},
                {"source_key": "screenshot", "field_name": "artist"},
            ],
        }, {"position": 2, "title": "Second", "artist": "Artist Two"}],
        "evidence_sources": [
            {"source_key": "screenshot", "source_type": "SCREENSHOT", "source_reference": "screen"},
            {"source_key": "external", "source_type": "AUTHORITATIVE_REFERENCE", "source_reference": "catalog"},
            {"source_key": "operator", "source_type": "CONVERSATION_USER_STATEMENT", "source_reference": "operator statement"},
        ],
        "constraints": [{
            "study_constraint_definition_id": definition["id"],
            "constraint_type": definition["constraint_type"],
            "constraint_text": definition["constraint_text"],
            "is_hard_constraint": definition["is_hard_constraint"],
        } for definition in definitions.values()],
    })
    experiment_id = service.ingest_experiment(proposal).record_id
    constraints = {
        row.study_constraint_definition_id: row
        for row in research_session.scalars(select(Constraint).where(Constraint.experiment_id == experiment_id))
    }
    by_key = {key: constraints[value["id"]] for key, value in definitions.items()}
    track = research_session.scalar(select(ExperimentTrack).where(ExperimentTrack.experiment_id == experiment_id))
    sources = {row.source_key: row for row in research_session.scalars(select(EvidenceSource).where(EvidenceSource.experiment_id == experiment_id))}
    links = list(research_session.scalars(select(EvidenceLink).where(EvidenceLink.experiment_track_id == track.id)))
    definitions_by_key = {}
    for key, definition in definitions.items():
        plan_id = definition["structured_evaluation_plan"]["id"]
        definitions_by_key[key] = {
            row.measurement_key: row for row in research_session.scalars(
                select(StudyConstraintMeasurementDefinition).where(
                    StudyConstraintMeasurementDefinition.evaluation_plan_id == plan_id
                )
            )
        }
    return service, protocol, experiment_id, by_key, track, sources, links, definitions_by_key


def _subject(session, *, experiment_id, constraint, kind, track_id=None, field=None, ordinal=1):
    row = ConstraintEvaluationSubject(
        experiment_id=experiment_id, constraint_id=constraint.id,
        subject_kind=kind, experiment_track_id=track_id,
        governed_field=field, enumeration_ordinal=ordinal,
    )
    session.add(row)
    session.commit()
    return row


def _measurement(session, subject, definition, *, authority=None, value_type=None, **values):
    row = ConstraintEvaluationMeasurement(
        subject_id=subject.id, measurement_definition_id=definition.id,
        authority_kind=authority or definition.authority,
        value_type=value_type or definition.value_type,
        recorded_by="test fixture", **values,
    )
    session.add(row)
    session.commit()
    return row


def test_subject_shapes_use_track_identity_not_absolute_position(research_session) -> None:
    _, _, experiment_id, constraints, track, *_ = _setup(research_session)
    run = _subject(research_session, experiment_id=experiment_id, constraint=constraints["run-constraint"], kind="RUN")
    placement = _subject(research_session, experiment_id=experiment_id, constraint=constraints["placement-constraint"], kind="EXPERIMENT_PLACEMENT", track_id=track.id)
    field = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    assert [run.experiment_track_id, placement.experiment_track_id, field.governed_field] == [None, track.id, "display_title"]
    assert not hasattr(field, "absolute_position")


@pytest.mark.parametrize("kind,track_id,field", [
    ("RUN", "TRACK", None),
    ("EXPERIMENT_PLACEMENT", None, None),
    ("PLACEMENT_FIELD", "TRACK", None),
    ("PLACEMENT_FIELD", "TRACK", "not_governed"),
])
def test_invalid_subject_discriminators_are_rejected(research_session, kind, track_id, field) -> None:
    _, _, experiment_id, constraints, track, *_ = _setup(research_session)
    research_session.add(ConstraintEvaluationSubject(
        experiment_id=experiment_id, constraint_id=constraints["field-constraint"].id,
        subject_kind=kind, experiment_track_id=track.id if track_id else None,
        governed_field=field, enumeration_ordinal=1,
    ))
    with pytest.raises(IntegrityError):
        research_session.commit()
    research_session.rollback()


def test_duplicate_and_cross_experiment_subjects_are_rejected(research_session) -> None:
    service, _, experiment_id, constraints, track, *_ = _setup(research_session)
    _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    research_session.add(ConstraintEvaluationSubject(
        experiment_id=experiment_id, constraint_id=constraints["field-constraint"].id,
        subject_kind="PLACEMENT_FIELD", experiment_track_id=track.id,
        governed_field="display_title", enumeration_ordinal=2,
    ))
    with pytest.raises(IntegrityError, match="duplicate evaluation subject"):
        research_session.commit()
    research_session.rollback()
    other_id = service.ingest_experiment(ExperimentInput.model_validate({
        "source_system": "Maestro Beta", "tracks": [{"position": 1, "title": "Other", "artist": "Other"}],
    })).record_id
    other_track = research_session.scalar(select(ExperimentTrack).where(ExperimentTrack.experiment_id == other_id))
    research_session.add(ConstraintEvaluationSubject(
        experiment_id=experiment_id, constraint_id=constraints["placement-constraint"].id,
        subject_kind="EXPERIMENT_PLACEMENT", experiment_track_id=other_track.id,
        enumeration_ordinal=1,
    ))
    with pytest.raises(IntegrityError, match="placement belongs to another experiment"):
        research_session.commit()
    research_session.rollback()


def test_typed_measurements_unknown_vocabulary_and_definition_enforcement(research_session) -> None:
    _, _, experiment_id, constraints, track, _, _, definitions = _setup(research_session)
    subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    observed = definitions["field-constraint"]["observed"]
    measurement = _measurement(research_session, subject, observed, text_value="Track")
    assert measurement.text_value == "Track"
    second_track = research_session.scalar(select(ExperimentTrack).where(
        ExperimentTrack.experiment_id == experiment_id, ExperimentTrack.id != track.id
    ))
    unavailable_subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=second_track.id, field="display_title", ordinal=2)
    unavailable = _measurement(research_session, unavailable_subject, observed, value_type="UNAVAILABLE", unavailable_reason="source unavailable")
    assert unavailable.unavailable_reason == "source unavailable"
    research_session.add(ConstraintEvaluationMeasurement(
        subject_id=unavailable_subject.id,
        measurement_definition_id=definitions["field-constraint"]["vocabulary"].id,
        authority_kind="DIRECT_OBSERVATION", value_type="VOCABULARY_TERM",
        vocabulary_term_key="not-registered", recorded_by="test fixture",
    ))
    with pytest.raises(IntegrityError, match="vocabulary term is not registered"):
        research_session.commit()
    research_session.rollback()


@pytest.mark.parametrize("value_type,values", [
    ("UNAVAILABLE", {}),
    ("UNAVAILABLE", {"unavailable_reason": "unknown", "text_value": "fabricated"}),
    ("TEXT", {}),
])
def test_measurement_value_discriminator_rejects_invalid_shapes(
    research_session, value_type, values
) -> None:
    _, _, experiment_id, constraints, _, _, _, definitions = _setup(research_session)
    subject = _subject(
        research_session, experiment_id=experiment_id,
        constraint=constraints["run-constraint"], kind="RUN"
    )
    research_session.add(ConstraintEvaluationMeasurement(
        subject_id=subject.id,
        measurement_definition_id=definitions["run-constraint"]["count"].id,
        authority_kind="STRUCTURAL_DERIVATION", value_type=value_type,
        recorded_by="test fixture", **values,
    ))
    with pytest.raises(IntegrityError):
        research_session.commit()
    research_session.rollback()


def test_measurement_plan_authority_type_and_duplicate_are_enforced(research_session) -> None:
    _, _, experiment_id, constraints, track, _, _, definitions = _setup(research_session)
    run_subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["run-constraint"], kind="RUN")
    research_session.add(ConstraintEvaluationMeasurement(
        subject_id=run_subject.id,
        measurement_definition_id=definitions["field-constraint"]["observed"].id,
        authority_kind="DIRECT_OBSERVATION", value_type="TEXT",
        text_value="wrong plan", recorded_by="test fixture",
    ))
    with pytest.raises(IntegrityError, match="does not govern"):
        research_session.commit()
    research_session.rollback()
    field_subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    observed = definitions["field-constraint"]["observed"]
    research_session.add(ConstraintEvaluationMeasurement(
        subject_id=field_subject.id, measurement_definition_id=observed.id,
        authority_kind="HUMAN_ASSESSMENT", value_type="TEXT",
        text_value="wrong authority", recorded_by="test fixture",
    ))
    with pytest.raises(IntegrityError, match="authority differs"):
        research_session.commit()
    research_session.rollback()
    _measurement(research_session, field_subject, observed, text_value="Track")
    research_session.add(ConstraintEvaluationMeasurement(
        subject_id=field_subject.id, measurement_definition_id=observed.id,
        authority_kind="DIRECT_OBSERVATION", value_type="TEXT",
        text_value="duplicate", recorded_by="test fixture",
    ))
    with pytest.raises(IntegrityError):
        research_session.commit()
    research_session.rollback()


def test_evidence_roles_and_field_linkage_remain_distinct(research_session) -> None:
    service, _, experiment_id, constraints, track, sources, links, definitions = _setup(research_session)
    title_link = next(link for link in links if link.field_name == "title")
    subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    observed = _measurement(research_session, subject, definitions["field-constraint"]["observed"], text_value="Track")
    direct = ConstraintEvaluationMeasurementEvidence(
        measurement_id=observed.id, evidence_source_id=sources["screenshot"].id,
        evidence_link_id=title_link.id, evidence_role="OBSERVED_VALUE",
        provenance_type="DIRECT_OBSERVATION", support_status="FULL",
    )
    research_session.add(direct)
    research_session.commit()
    external = _measurement(research_session, subject, definitions["field-constraint"]["external"], date_value=date(2020, 1, 1))
    research_session.add_all([
        ConstraintEvaluationMeasurementEvidence(
            measurement_id=external.id, evidence_source_id=sources["external"].id,
            evidence_role="EXTERNAL_FACT", provenance_type="DIRECT_OBSERVATION", support_status="FULL",
        ),
        ConstraintEvaluationMeasurementEvidence(
            measurement_id=external.id, evidence_source_id=sources["screenshot"].id,
            evidence_role="CORRESPONDENCE", provenance_type="HUMAN_ASSESSMENT", support_status="FULL",
        ),
    ])
    research_session.commit()
    judgment = _measurement(research_session, subject, definitions["field-constraint"]["judgment"], text_value="correspondence established")
    research_session.add(ConstraintEvaluationMeasurementEvidence(
        measurement_id=judgment.id, evidence_source_id=sources["operator"].id,
        evidence_role="OPERATOR_JUDGMENT", provenance_type="HUMAN_ASSESSMENT", support_status="FULL",
    ))
    research_session.commit()
    projection = service.get_evaluation_provenance(constraints["field-constraint"].id)
    assert {row["evidence_role"] for row in projection["evidence"]} == {
        "OBSERVED_VALUE", "EXTERNAL_FACT", "CORRESPONDENCE", "OPERATOR_JUDGMENT"
    }


def test_mismatched_field_link_and_other_experiment_evidence_are_rejected(research_session) -> None:
    service, _, experiment_id, constraints, track, sources, links, definitions = _setup(research_session)
    artist_link = next(link for link in links if link.field_name == "artist")
    subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    observed = _measurement(research_session, subject, definitions["field-constraint"]["observed"], text_value="Track")
    research_session.add(ConstraintEvaluationMeasurementEvidence(
        measurement_id=observed.id, evidence_source_id=sources["screenshot"].id,
        evidence_link_id=artist_link.id, evidence_role="OBSERVED_VALUE",
        provenance_type="DIRECT_OBSERVATION", support_status="FULL",
    ))
    with pytest.raises(IntegrityError, match="does not match evaluation subject"):
        research_session.commit()
    research_session.rollback()
    other_id = service.ingest_experiment(ExperimentInput.model_validate({
        "source_system": "Maestro Beta", "tracks": [],
        "evidence_sources": [{"source_key": "other", "source_type": "SCREENSHOT", "source_reference": "other"}],
    })).record_id
    other_source = research_session.scalar(select(EvidenceSource).where(EvidenceSource.experiment_id == other_id))
    research_session.add(ConstraintEvaluationMeasurementEvidence(
        measurement_id=observed.id, evidence_source_id=other_source.id,
        evidence_role="OBSERVED_VALUE", provenance_type="DIRECT_OBSERVATION", support_status="FULL",
    ))
    with pytest.raises(IntegrityError, match="belongs to another experiment"):
        research_session.commit()
    research_session.rollback()


def test_subject_result_storage_is_exact_immutable_and_readable(research_session) -> None:
    service, _, experiment_id, constraints, track, *_ = _setup(research_session)
    subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=track.id, field="display_title")
    second_track = research_session.scalar(select(ExperimentTrack).where(
        ExperimentTrack.experiment_id == experiment_id,
        ExperimentTrack.id != track.id,
    ))
    for status in ("PASS", "PARTIAL", "FAIL", "UNKNOWN"):
        if status == "PARTIAL":
            subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["field-constraint"], kind="PLACEMENT_FIELD", track_id=second_track.id, field="display_title", ordinal=2)
        elif status == "FAIL":
            subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["placement-constraint"], kind="EXPERIMENT_PLACEMENT", track_id=track.id)
        elif status == "UNKNOWN":
            subject = _subject(research_session, experiment_id=experiment_id, constraint=constraints["placement-constraint"], kind="EXPERIMENT_PLACEMENT", track_id=second_track.id, ordinal=2)
        research_session.add(ConstraintSubjectResult(
            subject_id=subject.id, status=status,
            evaluator_key="subject.generic", evaluator_version="1",
            reason_code=f"fixture-{status.lower()}",
        ))
        research_session.commit()
    projection = service.get_structured_constraint_evaluation(constraints["field-constraint"].id)
    assert {row["result"]["status"] for row in projection["subjects"]} == {"PASS", "PARTIAL"}
    result_id = projection["subjects"][0]["result"]["id"]
    first_subject_id = projection["subjects"][0]["id"]
    research_session.add(ConstraintSubjectResult(
        subject_id=first_subject_id, status="PASS", evaluator_key="subject.generic",
        evaluator_version="1", reason_code="duplicate",
    ))
    with pytest.raises(IntegrityError):
        research_session.commit()
    research_session.rollback()
    with pytest.raises(IntegrityError, match="structured evaluation runtime is immutable"):
        research_session.execute(text("UPDATE constraint_subject_results SET status='FAIL' WHERE id=:id"), {"id": result_id})
        research_session.commit()
    research_session.rollback()


def test_post_realization_and_legacy_insertion_are_rejected(research_session) -> None:
    service, protocol, experiment_id, constraints, track, *_ = _setup(research_session)
    run_id = protocol["planned_runs"][0]["id"]
    research_session.add(StudyRunRealization(
        planned_run_id=run_id, disposition="EXPERIMENT_RECORDED", experiment_id=experiment_id
    ))
    research_session.commit()
    research_session.add(ConstraintEvaluationSubject(
        experiment_id=experiment_id, constraint_id=constraints["field-constraint"].id,
        subject_kind="PLACEMENT_FIELD", experiment_track_id=track.id,
        governed_field="display_title", enumeration_ordinal=1,
    ))
    with pytest.raises(IntegrityError, match="after realization"):
        research_session.commit()
    research_session.rollback()
    legacy_document = _document(structured=False)
    legacy_document["study_key"] = "P7B-LEGACY"
    legacy_study = service.register_study(StudyRegistrationInput.model_validate(legacy_document))
    legacy_protocol = service.get_protocol_version(legacy_study["id"], 1)
    legacy_definition = legacy_protocol["constraint_definitions"][0]
    legacy_id = service.ingest_experiment(ExperimentInput.model_validate({
        "source_system": "Maestro Beta", "tracks": [], "constraints": [{
            "study_constraint_definition_id": legacy_definition["id"],
            "constraint_type": legacy_definition["constraint_type"],
            "constraint_text": legacy_definition["constraint_text"],
            "is_hard_constraint": True,
        }],
    })).record_id
    legacy_constraint = research_session.scalar(select(Constraint).where(Constraint.experiment_id == legacy_id))
    research_session.add(ConstraintEvaluationSubject(
        experiment_id=legacy_id, constraint_id=legacy_constraint.id,
        subject_kind="RUN", enumeration_ordinal=1,
    ))
    with pytest.raises(IntegrityError, match="no registered structured-evaluation plan"):
        research_session.commit()
    research_session.rollback()
    assert service.classify_evaluation_instrumentation(legacy_constraint.id)["instrumentation_classification"] == "LEGACY_AGGREGATE_ONLY"

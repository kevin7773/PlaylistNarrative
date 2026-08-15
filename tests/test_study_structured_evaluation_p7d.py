from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.models import (
    Constraint,
    ConstraintEvaluationMeasurement,
    ConstraintEvaluationMeasurementEvidence,
    ConstraintEvaluationSubject,
    ConstraintResult,
    ConstraintSubjectResult,
    Experiment,
    StudyRunRealization,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.schemas import GenerationFailureInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_schemas import (
    StudyRunDisposition,
    StructuredStudyEvaluationInput,
    StudyRegistrationInput,
)
from test_study_structured_evaluation_p7a import _document


def _ref(key):
    return {"evaluator_key": key, "evaluator_version": "1"}


def _study(kind="RUN", field=None, evaluator="subject.integer_equals", value_type="INTEGER", *, evidence_required=False, aggregate="aggregate.single_subject", parameters=None, legacy=False):
    doc = _document(structured=False)
    doc["study_key"] = f"P7D-{kind}-{field or 'run'}-{legacy}"
    definition = doc["protocol"]["constraint_definitions"][0]
    definition.update(constraint_key="structured", permitted_result_provenance="DERIVED_QUERY_RESULT")
    definition["structured_evaluation_plan"] = {
        "instrumentation_version": "1", "subject_kind": kind,
        "subject_field": field,
        "subject_selector": _ref("selector.run" if kind == "RUN" else "selector.all_placements"),
        "subject_evaluator": _ref(evaluator), "aggregate_evaluator": _ref(aggregate),
        "require_complete_subject_set": True, "allow_partial_subject_status": False,
        "measurement_definitions": [{
            "measurement_key": "observed", "authority": (
                "STRUCTURAL_DERIVATION" if kind == "RUN" and value_type == "INTEGER" else
                "EXTERNAL_FACT_VERIFICATION" if value_type == "DATE" else "DIRECT_OBSERVATION"
            ), "value_type": value_type, "required": True,
            "evidence_required": evidence_required,
            "unavailable_policy": "MUST_HAVE_VALUE",
            **({"derivation_key": "structural.placement_count", "derivation_version": "1"} if kind == "RUN" and value_type == "INTEGER" else {}),
        }],
        "parameters": parameters or [{"parameter_key": "expected", "value_type": value_type, f"{value_type.lower()}_value": 10}],
    }
    if value_type == "VOCABULARY_TERM":
        definition["structured_evaluation_plan"]["measurement_definitions"][0]["vocabulary_key"] = "terms"
        definition["structured_evaluation_plan"]["vocabulary_terms"] = [{
            "vocabulary_key": "terms", "term_key": "allowed", "term_definition": "Allowed."
        }]
    if legacy:
        legacy_definition = deepcopy(definition)
        legacy_definition.pop("structured_evaluation_plan")
        legacy_definition.update(
            constraint_key="legacy", constraint_type="legacy",
            constraint_text="Legacy aggregate constraint.",
            permitted_result_provenance="HUMAN_ASSESSMENT",
        )
        doc["protocol"]["constraint_definitions"].append(legacy_definition)
        doc["protocol"]["planned_runs"][0]["applicable_constraint_keys"] = ["structured", "legacy"]
    else:
        doc["protocol"]["planned_runs"][0]["applicable_constraint_keys"] = ["structured"]
    return StudyRegistrationInput.model_validate(doc)


def _register(service, proposal):
    study = service.register_study(proposal)
    protocol = service.get_protocol_version(study["id"], 1)
    return protocol, {item["constraint_key"]: item for item in protocol["constraint_definitions"]}


def _experiment(protocol, definitions, *, count=10, explicit=None, evidence=False, legacy=False):
    tracks = []
    sources = []
    if evidence:
        sources = [{"source_key": "screen", "source_type": "SCREENSHOT", "source_reference": "screen"}]
    for position in range(1, count + 1):
        track = {"position": position, "title": f"Night Track {position}", "artist": f"Artist {position}"}
        if explicit is not None:
            track["explicit_flag"] = explicit[position - 1]
        if evidence:
            field = "explicit_flag" if explicit is not None else "title"
            track["evidence"] = [{"source_key": "screen", "field_name": field}]
        tracks.append(track)
    constraints = [{
        "study_constraint_definition_id": definitions["structured"]["id"],
        "constraint_type": definitions["structured"]["constraint_type"],
        "constraint_text": definitions["structured"]["constraint_text"],
        "is_hard_constraint": True,
    }]
    if legacy:
        constraints.append({
            "study_constraint_definition_id": definitions["legacy"]["id"],
            "constraint_type": definitions["legacy"]["constraint_type"],
            "constraint_text": definitions["legacy"]["constraint_text"],
            "is_hard_constraint": True,
            "result": {"status": "PASS", "provenance_type": "HUMAN_ASSESSMENT"},
        })
    return ExperimentInput.model_validate({
        "prompt": protocol["planned_runs"][0]["planned_prompt_text"],
        "source_system": protocol["planned_runs"][0]["planned_source_system"],
        "tracks": tracks, "evidence_sources": sources, "constraints": constraints,
    })


def _run_payload(definition_id, value=10, *, assertion=None):
    return StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definition_id,
        "asserted_aggregate_status": assertion,
        "subjects": [{"subject_kind": "RUN", "enumeration_ordinal": 1, "measurements": []}],
    }]})


def _counts(session):
    models = (Experiment, Constraint, ConstraintResult, ConstraintEvaluationSubject, ConstraintEvaluationMeasurement, ConstraintEvaluationMeasurementEvidence, ConstraintSubjectResult, StudyRunRealization)
    return [session.scalar(select(func.count()).select_from(model)) for model in models]


def test_atomic_structured_cardinality_realization_and_readback(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    realization = service.realize_structured_study_experiment(
        protocol["planned_runs"][0]["id"],
        _experiment(protocol, definitions),
        _run_payload(definitions["structured"]["id"]),
    )
    experiment = service.get_experiment(realization["experiment_id"])
    constraint = experiment["constraints"][0]
    structured = service.get_structured_constraint_evaluation(constraint["id"])
    assert constraint["result"]["status"] == "PASS"
    assert structured["instrumentation_classification"] == "STRUCTURED_DERIVABLE"
    assert len(structured["subjects"]) == 1
    assert structured["subjects"][0]["subject_kind"] == "RUN"
    assert structured["subjects"][0]["measurements"][0]["integer_value"] == 10
    assert structured["subjects"][0]["result"]["status"] == "PASS"


def test_legacy_path_cannot_bypass_structured_required(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    with pytest.raises(ValueError, match="STRUCTURED_REQUIRED"):
        service.ingest_planned_experiment(protocol["planned_runs"][0]["id"], _experiment(protocol, definitions))
    research_session.rollback()
    assert _counts(research_session)[:3] == [0, 0, 0]


@pytest.mark.parametrize("mutation,match", [
    ("override", "incomplete"),
    ("authority", "incomplete"),
    ("type", "incomplete"),
    ("assertion", "contradicts"),
    ("subject", "exact enumeration"),
])
def test_every_structured_failure_rolls_back_all_rows(research_session, mutation, match) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    experiment = _experiment(protocol, definitions)
    payload = _run_payload(definitions["structured"]["id"])
    raw = payload.model_dump(mode="python")
    if mutation in {"override", "authority", "type"}:
        raw["constraints"][0]["subjects"][0]["measurements"] = [{
            "measurement_key": "observed", "authority_kind": "STRUCTURAL_DERIVATION",
            "value_type": "INTEGER", "integer_value": 10, "recorded_by": "operator", "evidence": [],
        }]
    measurement = raw["constraints"][0]["subjects"][0]["measurements"][0] if raw["constraints"][0]["subjects"][0]["measurements"] else None
    if mutation == "authority": measurement["authority_kind"] = "DIRECT_OBSERVATION"
    elif mutation == "type": measurement.update(value_type="TEXT", integer_value=None, text_value="10")
    elif mutation == "assertion": raw["constraints"][0]["asserted_aggregate_status"] = "FAIL"
    elif mutation == "subject": raw["constraints"][0]["subjects"][0]["enumeration_ordinal"] = 2
    bad = StructuredStudyEvaluationInput.model_validate(raw)
    before = _counts(research_session)
    research_session.rollback()
    with pytest.raises(ValueError, match=match):
        service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], experiment, bad)
    research_session.rollback()
    assert _counts(research_session) == before


def test_lexical_mixed_aggregate_persists_exact_subject_results(research_session) -> None:
    params = [
        {"parameter_key": "token", "value_type": "TEXT", "text_value": "night"},
        {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study("PLACEMENT_FIELD", "display_title", "subject.lexical_standalone_token", "TEXT", aggregate="aggregate.all_subjects_required", parameters=params))
    experiment = _experiment(protocol, definitions, count=2)
    experiment = experiment.model_copy(update={"tracks": [experiment.tracks[0], experiment.tracks[1].model_copy(update={"title": "Daylight"})]})
    subjects = [{"subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": index, "track_observed_ordinal": index, "governed_field": "display_title", "measurements": [{"measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION", "value_type": "TEXT", "text_value": track.title, "recorded_by": "fixture"}]} for index, track in enumerate(experiment.tracks, 1)]
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{"study_constraint_definition_id": definitions["structured"]["id"], "subjects": subjects}]})
    realization = service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], experiment, payload)
    constraint = service.get_experiment(realization["experiment_id"])["constraints"][0]
    projection = service.get_structured_constraint_evaluation(constraint["id"])
    assert [row["result"]["status"] for row in projection["subjects"]] == ["PASS", "FAIL"]
    assert constraint["result"]["status"] == "PARTIAL"


def test_boolean_field_evidence_and_mixed_legacy_are_atomic(research_session) -> None:
    params = [
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study("PLACEMENT_FIELD", "explicit_flag", "subject.boolean_equals", "BOOLEAN", evidence_required=True, aggregate="aggregate.all_subjects_required", parameters=params, legacy=True))
    experiment = _experiment(protocol, definitions, count=2, explicit=[False, True], evidence=True, legacy=True)
    subjects = [{"subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": i, "track_observed_ordinal": i, "governed_field": "explicit_flag", "measurements": [{"measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION", "value_type": "BOOLEAN", "boolean_value": value, "recorded_by": "fixture", "evidence": [{"source_key": "screen", "evidence_link_field": "explicit_flag", "evidence_role": "OBSERVED_VALUE", "provenance_type": "DIRECT_OBSERVATION", "support_status": "FULL"}]}]} for i, value in enumerate([False, True], 1)]
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{"study_constraint_definition_id": definitions["structured"]["id"], "subjects": subjects}]})
    realization = service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], experiment, payload)
    constraints = service.get_experiment(realization["experiment_id"])["constraints"]
    assert {row["result"]["status"] for row in constraints} == {"PASS", "PARTIAL"}
    structured_constraint = next(row for row in constraints if row["study_constraint_definition_id"] == definitions["structured"]["id"])
    provenance = service.get_evaluation_provenance(structured_constraint["id"])
    assert len(provenance["evidence"]) == 2


def test_structured_runtime_and_aggregate_are_immutable_after_realization(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    realization = service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], _experiment(protocol, definitions), _run_payload(definitions["structured"]["id"]))
    constraint = research_session.scalar(select(Constraint).where(Constraint.experiment_id == realization["experiment_id"]))
    with pytest.raises(IntegrityError, match="structured aggregate"):
        research_session.execute(text("UPDATE constraint_results SET status='FAIL' WHERE constraint_id=:id"), {"id": constraint.id}); research_session.commit()
    research_session.rollback()


def test_external_fact_and_correspondence_evidence_are_distinct(research_session) -> None:
    params = [
        {"parameter_key": "start_date", "value_type": "DATE", "date_value": "2020-01-01"},
        {"parameter_key": "end_date", "value_type": "DATE", "date_value": "2020-12-31"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "EXPERIMENT_PLACEMENT", None, "subject.date_inclusive_window", "DATE",
        evidence_required=True, parameters=params,
    ))
    experiment = _experiment(protocol, definitions, count=1, evidence=True)
    experiment_doc = experiment.model_dump(mode="python")
    experiment_doc["evidence_sources"].append(
        {"source_key": "external", "source_type": "AUTHORITATIVE_REFERENCE", "source_reference": "catalog"}
    )
    experiment = ExperimentInput.model_validate(experiment_doc)
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"],
        "subjects": [{
            "subject_kind": "EXPERIMENT_PLACEMENT", "enumeration_ordinal": 1,
            "track_observed_ordinal": 1,
            "measurements": [{
                "measurement_key": "observed",
                "authority_kind": "EXTERNAL_FACT_VERIFICATION",
                "value_type": "DATE", "date_value": "2020-06-01",
                "recorded_by": "fixture",
                "evidence": [
                    {"source_key": "external", "evidence_role": "EXTERNAL_FACT", "provenance_type": "DIRECT_OBSERVATION", "support_status": "FULL"},
                    {"source_key": "screen", "evidence_link_field": "title", "evidence_role": "CORRESPONDENCE", "provenance_type": "HUMAN_ASSESSMENT", "support_status": "FULL"},
                ],
            }],
        }],
    }]})
    realization = service.realize_structured_study_experiment(
        protocol["planned_runs"][0]["id"], experiment, payload
    )
    constraint = service.get_experiment(realization["experiment_id"])["constraints"][0]
    provenance = service.get_evaluation_provenance(constraint["id"])
    assert {row["evidence_role"] for row in provenance["evidence"]} == {
        "EXTERNAL_FACT", "CORRESPONDENCE"
    }


def test_missing_external_evidence_rolls_back_experiment(research_session) -> None:
    params = [
        {"parameter_key": "start_date", "value_type": "DATE", "date_value": "2020-01-01"},
        {"parameter_key": "end_date", "value_type": "DATE", "date_value": "2020-12-31"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "EXPERIMENT_PLACEMENT", None, "subject.date_inclusive_window", "DATE",
        evidence_required=True, parameters=params,
    ))
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"],
        "subjects": [{"subject_kind": "EXPERIMENT_PLACEMENT", "enumeration_ordinal": 1, "track_observed_ordinal": 1, "measurements": [{
            "measurement_key": "observed", "authority_kind": "EXTERNAL_FACT_VERIFICATION",
            "value_type": "DATE", "date_value": "2020-06-01", "recorded_by": "fixture",
        }]}],
    }]})
    before = _counts(research_session); research_session.rollback()
    with pytest.raises(ValueError, match="EVIDENCE_REQUIRED"):
        service.realize_structured_study_experiment(
            protocol["planned_runs"][0]["id"], _experiment(protocol, definitions, count=1), payload
        )
    research_session.rollback()
    assert _counts(research_session) == before


def test_refusal_for_structured_run_creates_no_p7_rows(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, _ = _register(service, _study())
    service.record_planned_generation_failure(
        protocol["planned_runs"][0]["id"],
        GenerationFailureInput.model_validate({
            "prompt": protocol["planned_runs"][0]["planned_prompt_text"],
            "source_system": protocol["planned_runs"][0]["planned_source_system"],
            "failure_type": "MAESTRO_REFUSAL", "displayed_message": "Cannot comply.",
        }),
        StudyRunDisposition.MAESTRO_REFUSAL_RECORDED,
    )
    assert _counts(research_session)[3:7] == [0, 0, 0, 0]


def test_realization_insert_failure_rolls_back_every_structured_row(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    before = _counts(research_session); research_session.rollback()
    def fail_realization(*_args, **_kwargs):
        raise RuntimeError("induced realization failure")
    event.listen(StudyRunRealization, "before_insert", fail_realization)
    try:
        with pytest.raises(RuntimeError, match="induced realization failure"):
            service.realize_structured_study_experiment(
                protocol["planned_runs"][0]["id"],
                _experiment(protocol, definitions),
                _run_payload(definitions["structured"]["id"]),
            )
    finally:
        event.remove(StudyRunRealization, "before_insert", fail_realization)
        research_session.rollback()
    assert _counts(research_session) == before


def test_experiment_insert_and_constraint_snapshot_failures_leave_no_rows(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    before = _counts(research_session); research_session.rollback()
    invalid_file = _experiment(protocol, definitions).model_dump(mode="python")
    invalid_file["evidence_sources"] = [{
        "source_key": "missing", "source_type": "SCREENSHOT", "source_reference": "missing",
        "local_path": "definitely-not-present.png", "sha256": "0" * 64,
    }]
    with pytest.raises(ValueError, match="not found"):
        service.realize_structured_study_experiment(
            protocol["planned_runs"][0]["id"],
            ExperimentInput.model_validate(invalid_file),
            _run_payload(definitions["structured"]["id"]),
        )
    research_session.rollback(); assert _counts(research_session) == before
    research_session.rollback()
    bad_snapshot = _experiment(protocol, definitions).model_dump(mode="python")
    bad_snapshot["constraints"][0]["constraint_text"] = "mutated snapshot"
    with pytest.raises(ValueError, match="exactly match"):
        service.realize_structured_study_experiment(
            protocol["planned_runs"][0]["id"],
            ExperimentInput.model_validate(bad_snapshot),
            _run_payload(definitions["structured"]["id"]),
        )
    research_session.rollback(); assert _counts(research_session) == before


def test_invalid_vocabulary_rolls_back_all_rows(research_session) -> None:
    proposal = _study(
        "RUN", None, "subject.vocabulary_allowed", "VOCABULARY_TERM",
        parameters=[{
            "parameter_key": "allowed_term", "value_type": "VOCABULARY_TERM",
            "vocabulary_key": "terms", "vocabulary_term_key": "allowed",
        }],
    )
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, proposal)
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"],
        "subjects": [{"subject_kind": "RUN", "enumeration_ordinal": 1, "measurements": [{
            "measurement_key": "observed", "authority_kind": "STRUCTURAL_DERIVATION",
            "value_type": "VOCABULARY_TERM", "vocabulary_term_key": "invented",
            "recorded_by": "fixture",
        }]}],
    }]})
    before = _counts(research_session); research_session.rollback()
    with pytest.raises(ValueError, match="VOCABULARY_TERM_UNREGISTERED"):
        service.realize_structured_study_experiment(
            protocol["planned_runs"][0]["id"], _experiment(protocol, definitions), payload
        )
    research_session.rollback(); assert _counts(research_session) == before


def test_evaluator_failure_rolls_back_empty_placement_run(research_session) -> None:
    params = [
        {"parameter_key": "token", "value_type": "TEXT", "text_value": "night"},
        {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": False},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "PLACEMENT_FIELD", "display_title", "subject.lexical_standalone_token", "TEXT",
        parameters=params,
    ))
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"], "subjects": [],
    }]})
    before = _counts(research_session); research_session.rollback()
    with pytest.raises(ValueError, match="exactly one subject"):
        service.realize_structured_study_experiment(
            protocol["planned_runs"][0]["id"], _experiment(protocol, definitions, count=0), payload
        )
    research_session.rollback(); assert _counts(research_session) == before

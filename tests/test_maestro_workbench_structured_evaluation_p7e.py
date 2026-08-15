from __future__ import annotations

from copy import deepcopy

from sqlalchemy import func, select

from playlist_narrative_engine.research_store.models import EvidenceLink, Experiment
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import ExperimentInput
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_schemas import (
    StudyRegistrationInput,
    StructuredStudyEvaluationInput,
)
from test_maestro_workbench_studies_p2 import RunningWorkbench
from test_study_structured_evaluation_p7d import _experiment, _register, _run_payload, _study


def test_structured_worksheet_enumerates_read_only_subjects_and_previews(research_session):
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    experiment = _experiment(protocol, definitions)
    counts_before = research_session.scalar(select(func.count()).select_from(Experiment))

    worksheet = service.prepare_structured_evaluation_worksheet(
        protocol["planned_runs"][0]["id"], experiment
    )
    assert worksheet["constraints"][0]["subjects"][0]["subject_kind"] == "RUN"
    assert worksheet["constraints"][0]["definition"]["structured_evaluation_plan"]
    assert worksheet["constraints"][0]["derived_measurements"][0]["integer_value"] == 10
    preview = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment,
        _run_payload(definitions["structured"]["id"]),
    )
    assert preview["complete"]
    assert preview["constraints"][0]["subject_results"][0]["status"] == "PASS"
    assert preview["constraints"][0]["aggregate_constraint_result"]["status"] == "PASS"
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == counts_before


def test_incomplete_or_tampered_preview_is_blocked_without_writes(research_session):
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study())
    experiment = _experiment(protocol, definitions)
    raw = _run_payload(definitions["structured"]["id"]).model_dump(mode="python")
    raw["constraints"][0]["subjects"][0]["measurements"] = [{
        "measurement_key": "observed", "authority_kind": "STRUCTURAL_DERIVATION",
        "value_type": "INTEGER", "integer_value": 10, "recorded_by": "operator",
    }]
    from playlist_narrative_engine.research_store.study_schemas import StructuredStudyEvaluationInput
    preview = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment,
        StructuredStudyEvaluationInput.model_validate(raw),
    )
    assert not preview["complete"]
    assert preview["constraints"][0]["issues"][0]["code"] == "DERIVED_VALUE_SUPPLIED"
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == 0


def test_http_worksheet_preview_and_atomic_structured_realization(tmp_path):
    app = RunningWorkbench(tmp_path)
    try:
        document = _study().model_dump(mode="json")
        registered = app.post("/api/studies/register", document)
        protocol = registered["registered_protocol"]
        definitions = {item["constraint_key"]: item for item in protocol["constraint_definitions"]}
        experiment = _experiment(protocol, definitions).model_dump(mode="json")
        run_id = protocol["planned_runs"][0]["id"]
        worksheet = app.post(f"/api/study-runs/{run_id}/structured-worksheet", {"proposal": experiment})
        assert worksheet["constraints"][0]["subjects"][0]["subject_kind"] == "RUN"
        structured = _run_payload(definitions["structured"]["id"]).model_dump(mode="json")
        preview = app.post(f"/api/study-runs/{run_id}/structured-preview", {
            "proposal": experiment, "structured_evaluation": structured,
        })
        assert preview["complete"]
        realized = app.post(f"/api/study-runs/{run_id}/realize-structured-experiment", {
            "proposal": experiment, "structured_evaluation": structured,
        })
        assert realized["record"]["constraints"][0]["result"]["status"] == "PASS"
        context = realized["record"]["constraints"][0]
        assert context["study_constraint_definition_id"] == definitions["structured"]["id"]
        terminal, _ = app.get(f"/api/study-runs/{run_id}/structured-evaluation")
        persisted = __import__("json").loads(terminal)
        assert persisted["experiment"]["id"] == realized["record_id"]
        assert persisted["constraints"][0]["structured"]["instrumentation_classification"] == "STRUCTURED_DERIVABLE"
    finally:
        app.close()


def test_mixed_and_legacy_ui_paths_remain_explicit_and_nc1_has_no_structured_plan():
    script = open("src/playlist_narrative_engine/maestro_workbench/static/app.js", encoding="utf-8").read()
    html = open("src/playlist_narrative_engine/maestro_workbench/static/index.html", encoding="utf-8").read()
    assert "Structured Evaluation Worksheet" in html
    assert "STRUCTURED_REQUIRED" in script and "LEGACY_AGGREGATE_ONLY" in script
    assert "realize-structured-experiment" in script
    assert "data-subject-result" in script and "data-aggregate-result" in script
    assert "Subjects and deterministic results come from the registered protocol" in html
    assert "add structured subject" not in script.lower()
    assert 'row.dataset.authority !== "STRUCTURAL_DERIVATION"' in script
    assert 'measurement.unavailable_policy === "MAY_BE_UNAVAILABLE"' in script
    assert "MUST_HAVE_VALUE" not in script  # absence of the MAY control is the non-overridable policy
    assert "Return to Studies" in script and "No post-realization edits are available" in script
    assert "NC-1" not in script


def test_direct_boolean_and_lexical_field_worksheets_use_exact_governed_values(research_session):
    boolean_params = [
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "PLACEMENT_FIELD", "explicit_flag", "subject.boolean_equals", "BOOLEAN",
        evidence_required=True, aggregate="aggregate.all_subjects_required",
        parameters=boolean_params,
    ))
    experiment = _experiment(protocol, definitions, count=2, explicit=[False, True], evidence=True)
    subjects = [{
        "subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": ordinal,
        "track_observed_ordinal": ordinal, "governed_field": "explicit_flag",
        "measurements": [{
            "measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION",
            "value_type": "BOOLEAN", "boolean_value": value, "recorded_by": "operator",
            "evidence": [{"source_key": "screen", "evidence_link_field": "explicit_flag",
                          "evidence_role": "OBSERVED_VALUE", "provenance_type": "DIRECT_OBSERVATION",
                          "support_status": "FULL"}],
        }],
    } for ordinal, value in enumerate([False, True], 1)]
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"], "subjects": subjects,
    }]})
    preview = service.preview_structured_study_evaluation(protocol["planned_runs"][0]["id"], experiment, payload)
    assert preview["complete"]
    assert [row["status"] for row in preview["constraints"][0]["subject_results"]] == ["PASS", "FAIL"]
    tampered = payload.model_dump(mode="python")
    tampered["constraints"][0]["subjects"][0]["measurements"][0]["boolean_value"] = True
    refused = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment,
        StructuredStudyEvaluationInput.model_validate(tampered),
    )
    assert not refused["complete"]
    assert "DIRECT_VALUE_CONTRADICTS_FIELD" in {issue["code"] for issue in refused["constraints"][0]["issues"]}

    lexical_params = [
        {"parameter_key": "token", "value_type": "TEXT", "text_value": "night"},
        {"parameter_key": "case_sensitive", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    protocol2, definitions2 = _register(service, _study(
        "PLACEMENT_FIELD", "display_title", "subject.lexical_standalone_token", "TEXT",
        aggregate="aggregate.all_subjects_required", parameters=lexical_params,
    ).model_copy(update={"study_key": "P7E-LEXICAL"}))
    experiment2 = _experiment(protocol2, definitions2, count=2)
    experiment2 = experiment2.model_copy(update={"tracks": [
        experiment2.tracks[0].model_copy(update={"title": "Night Moves"}),
        experiment2.tracks[1].model_copy(update={"title": "Daylight"}),
    ]})
    lexical_subjects = [{
        "subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": ordinal,
        "track_observed_ordinal": ordinal, "governed_field": "display_title",
        "measurements": [{"measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION",
                          "value_type": "TEXT", "text_value": track.title, "recorded_by": "operator"}],
    } for ordinal, track in enumerate(experiment2.tracks, 1)]
    lexical = service.preview_structured_study_evaluation(
        protocol2["planned_runs"][0]["id"], experiment2,
        StructuredStudyEvaluationInput.model_validate({"constraints": [{
            "study_constraint_definition_id": definitions2["structured"]["id"], "subjects": lexical_subjects,
        }]}),
    )
    assert lexical["constraints"][0]["aggregate_constraint_result"]["status"] == "PARTIAL"


def test_external_fact_and_human_assessment_are_typed_distinct_and_unavailable_is_policy_bound(research_session):
    date_params = [
        {"parameter_key": "start_date", "value_type": "DATE", "date_value": "2020-01-01"},
        {"parameter_key": "end_date", "value_type": "DATE", "date_value": "2020-12-31"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "EXPERIMENT_PLACEMENT", None, "subject.date_inclusive_window", "DATE",
        evidence_required=True, parameters=date_params,
    ))
    experiment_doc = _experiment(protocol, definitions, count=1).model_dump(mode="python")
    experiment_doc["evidence_sources"] = [{"source_key": "external", "source_type": "AUTHORITATIVE_REFERENCE", "source_reference": "catalog"}]
    experiment = ExperimentInput.model_validate(experiment_doc)
    external = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"], "subjects": [{
            "subject_kind": "EXPERIMENT_PLACEMENT", "enumeration_ordinal": 1,
            "track_observed_ordinal": 1, "measurements": [{
                "measurement_key": "observed", "authority_kind": "EXTERNAL_FACT_VERIFICATION",
                "value_type": "DATE", "date_value": "2020-06-01", "recorded_by": "operator",
                "evidence": [{"source_key": "external", "evidence_role": "EXTERNAL_FACT",
                              "provenance_type": "DIRECT_OBSERVATION", "support_status": "FULL"}],
            }],
        }],
    }]})
    assert service.preview_structured_study_evaluation(protocol["planned_runs"][0]["id"], experiment, external)["complete"]
    missing = external.model_dump(mode="python")
    missing["constraints"][0]["subjects"][0]["measurements"][0].update(
        value_type="UNAVAILABLE", date_value=None, unavailable_reason="not established"
    )
    refused = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment,
        StructuredStudyEvaluationInput.model_validate(missing),
    )
    assert "UNAVAILABLE_PROHIBITED" in {issue["code"] for issue in refused["constraints"][0]["issues"]}

    human_doc = _study().model_dump(mode="python")
    human_doc["study_key"] = "P7E-HUMAN"
    measurement = human_doc["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]["measurement_definitions"][0]
    measurement.update(authority="HUMAN_ASSESSMENT", derivation_key=None, derivation_version=None,
                       unavailable_policy="MAY_BE_UNAVAILABLE")
    human = StudyRegistrationInput.model_validate(human_doc)
    protocol2, definitions2 = _register(service, human)
    experiment2 = _experiment(protocol2, definitions2)
    unavailable = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions2["structured"]["id"], "subjects": [{
            "subject_kind": "RUN", "enumeration_ordinal": 1, "measurements": [{
                "measurement_key": "observed", "authority_kind": "HUMAN_ASSESSMENT",
                "value_type": "UNAVAILABLE", "unavailable_reason": "correspondence unresolved",
                "recorded_by": "operator",
            }],
        }],
    }]})
    human_preview = service.preview_structured_study_evaluation(protocol2["planned_runs"][0]["id"], experiment2, unavailable)
    assert human_preview["complete"]
    assert human_preview["constraints"][0]["aggregate_constraint_result"]["status"] == "UNKNOWN"


def test_mixed_run_realizes_once_and_legacy_only_has_no_worksheet(research_session):
    params = [
        {"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False},
        {"parameter_key": "mixed_status", "value_type": "TEXT", "text_value": "PARTIAL"},
        {"parameter_key": "all_fail_status", "value_type": "TEXT", "text_value": "FAIL"},
        {"parameter_key": "unknown_status", "value_type": "TEXT", "text_value": "UNKNOWN"},
    ]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "PLACEMENT_FIELD", "explicit_flag", "subject.boolean_equals", "BOOLEAN",
        aggregate="aggregate.all_subjects_required", parameters=params, legacy=True,
    ))
    experiment = _experiment(protocol, definitions, count=1, explicit=[False], legacy=True)
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"], "subjects": [{
            "subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": 1,
            "track_observed_ordinal": 1, "governed_field": "explicit_flag",
            "measurements": [{"measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION",
                              "value_type": "BOOLEAN", "boolean_value": False, "recorded_by": "operator"}],
        }],
    }]})
    realization = service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], experiment, payload)
    stored = service.get_experiment(realization["experiment_id"])
    assert len(stored["constraints"]) == 2
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == 1
    research_session.rollback()

    legacy_doc = deepcopy(_study().model_dump(mode="python"))
    legacy_doc["study_key"] = "P7E-LEGACY-ONLY"
    legacy_doc["protocol"]["constraint_definitions"][0].pop("structured_evaluation_plan")
    legacy_doc["protocol"]["constraint_definitions"][0]["permitted_result_provenance"] = "HUMAN_ASSESSMENT"
    legacy = service.register_study(StudyRegistrationInput.model_validate(legacy_doc))
    legacy_protocol = service.get_protocol_version(legacy["id"], 1)
    legacy_experiment = _experiment(legacy_protocol, {"structured": legacy_protocol["constraint_definitions"][0]}, count=1)
    worksheet = service.prepare_structured_evaluation_worksheet(legacy_protocol["planned_runs"][0]["id"], legacy_experiment)
    assert worksheet["constraints"] == []


def test_cross_experiment_evidence_link_is_rejected_by_atomic_realization(research_session):
    service = ResearchStoreService(ResearchRepository(research_session))
    foreign_id = service.ingest_experiment(ExperimentInput.model_validate({
        "tracks": [{"position": 1, "title": "Foreign", "artist": "Artist",
                    "evidence": [{"source_key": "foreign", "field_name": "explicit_flag"}]}],
        "evidence_sources": [{"source_key": "foreign", "source_type": "SCREENSHOT", "source_reference": "foreign"}],
    })).record_id
    foreign_link_id = research_session.scalar(select(EvidenceLink.id).order_by(EvidenceLink.id))
    research_session.rollback()
    params = [{"parameter_key": "expected", "value_type": "BOOLEAN", "boolean_value": False}]
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, _study(
        "PLACEMENT_FIELD", "explicit_flag", "subject.boolean_equals", "BOOLEAN",
        evidence_required=True, parameters=params,
    ))
    experiment = _experiment(protocol, definitions, count=1, explicit=[False], evidence=True)
    payload = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"], "subjects": [{
            "subject_kind": "PLACEMENT_FIELD", "enumeration_ordinal": 1,
            "track_observed_ordinal": 1, "governed_field": "explicit_flag",
            "measurements": [{"measurement_key": "observed", "authority_kind": "DIRECT_OBSERVATION",
                              "value_type": "BOOLEAN", "boolean_value": False, "recorded_by": "operator",
                              "evidence": [{"source_key": "screen", "evidence_link_id": foreign_link_id,
                                            "evidence_role": "OBSERVED_VALUE", "provenance_type": "DIRECT_OBSERVATION",
                                            "support_status": "FULL"}]}],
        }],
    }]})
    import pytest
    with pytest.raises(ValueError, match="not owned by the selected Experiment source"):
        service.realize_structured_study_experiment(protocol["planned_runs"][0]["id"], experiment, payload)


def test_incomplete_measurement_reports_exact_issue_without_breaking_other_constraint_preview(research_session):
    document = deepcopy(_study().model_dump(mode="python"))
    second = deepcopy(document["protocol"]["constraint_definitions"][0])
    second["constraint_key"] = "structured_second"
    second["constraint_text"] = "Second independently evaluated structured constraint"
    second_measurement = second["structured_evaluation_plan"]["measurement_definitions"][0]
    second_measurement.update(
        authority="HUMAN_ASSESSMENT", derivation_key=None, derivation_version=None
    )
    document["protocol"]["constraint_definitions"].append(second)
    document["protocol"]["planned_runs"][0]["applicable_constraint_keys"].append("structured_second")

    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, StudyRegistrationInput.model_validate(document))
    experiment_document = _experiment(protocol, definitions).model_dump(mode="python")
    second_constraint = deepcopy(experiment_document["constraints"][0])
    second_constraint.update(
        study_constraint_definition_id=definitions["structured_second"]["id"],
        constraint_text="Second independently evaluated structured constraint",
    )
    experiment_document["constraints"].append(second_constraint)
    experiment = ExperimentInput.model_validate(experiment_document)
    evaluation = StructuredStudyEvaluationInput.model_validate({"constraints": [
        _run_payload(definitions["structured"]["id"]).constraints[0].model_dump(mode="python"),
        {
            "study_constraint_definition_id": definitions["structured_second"]["id"],
            "subjects": [{"subject_kind": "RUN", "enumeration_ordinal": 1, "measurements": []}],
        },
    ]})

    preview = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment, evaluation
    )
    by_key = {
        "structured" if row["study_constraint_definition_id"] == definitions["structured"]["id"]
        else "structured_second": row
        for row in preview["constraints"]
    }
    assert not preview["complete"]
    assert by_key["structured"]["complete"]
    assert by_key["structured"]["aggregate_constraint_result"]["status"] == "PASS"
    assert not by_key["structured_second"]["complete"]
    assert "REQUIRED_MEASUREMENT_MISSING" in {
        issue["code"] for issue in by_key["structured_second"]["issues"]
    }
    assert research_session.scalar(select(func.count()).select_from(Experiment)) == 0


def test_unavailable_reason_and_subject_identity_are_required_for_preview(research_session):
    document = _study().model_dump(mode="python")
    document["study_key"] = "P7E-INCOMPLETE"
    plan = document["protocol"]["constraint_definitions"][0]["structured_evaluation_plan"]
    measurement = plan["measurement_definitions"][0]
    measurement.update(
        authority="HUMAN_ASSESSMENT",
        derivation_key=None,
        derivation_version=None,
        unavailable_policy="MAY_BE_UNAVAILABLE",
    )
    service = ResearchStoreService(ResearchRepository(research_session))
    protocol, definitions = _register(service, StudyRegistrationInput.model_validate(document))
    experiment = _experiment(protocol, definitions)
    missing_reason = StructuredStudyEvaluationInput.model_validate({"constraints": [{
        "study_constraint_definition_id": definitions["structured"]["id"],
        "subjects": [{
            "subject_kind": "RUN",
            "enumeration_ordinal": 1,
            "measurements": [{
                "measurement_key": "observed",
                "authority_kind": "HUMAN_ASSESSMENT",
                "value_type": "UNAVAILABLE",
                "unavailable_reason": None,
                "recorded_by": "operator",
            }],
        }],
    }]})
    preview = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment, missing_reason
    )
    assert not preview["complete"]
    assert "VALUE_SHAPE_INVALID" in {issue["code"] for issue in preview["constraints"][0]["issues"]}

    wrong_subject = missing_reason.model_dump(mode="python")
    wrong_subject["constraints"][0]["subjects"][0]["subject_kind"] = "EXPERIMENT_PLACEMENT"
    wrong_subject["constraints"][0]["subjects"][0]["track_observed_ordinal"] = 1
    wrong_subject["constraints"][0]["subjects"][0]["measurements"][0]["unavailable_reason"] = "not available"
    preview = service.preview_structured_study_evaluation(
        protocol["planned_runs"][0]["id"], experiment,
        StructuredStudyEvaluationInput.model_validate(wrong_subject),
    )
    assert not preview["complete"]
    assert "SUBJECT_SET_MISMATCH" in {issue["code"] for issue in preview["constraints"][0]["issues"]}


def test_proposal_changes_invalidate_structured_preview_before_ingestion():
    script = open("src/playlist_narrative_engine/maestro_workbench/static/app.js", encoding="utf-8").read()
    function_body = script[script.index("function invalidateValidation"):script.index("function draftWorkflowControls")]
    assert "structuredPreviewComplete = false" in function_body
    assert "Recalculate the deterministic preview" in function_body
    assert '$("#ingest").disabled = true' in function_body

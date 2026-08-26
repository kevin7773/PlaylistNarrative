from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from playlist_narrative_engine.research_store.models import (
    Constraint,
    Experiment,
    StudyCondition,
    StudyProtocolVersion,
    StudyRunRealization,
)
from playlist_narrative_engine.research_store.repository import ResearchRepository
from playlist_narrative_engine.research_store.schemas import (
    ExperimentInput,
    GenerationFailureInput,
)
from playlist_narrative_engine.research_store.service import ResearchStoreService
from playlist_narrative_engine.research_store.study_protocol import (
    canonical_protocol_bytes,
    protocol_registration_hash,
)
from playlist_narrative_engine.research_store.study_schemas import (
    StudyOperationalAttemptInput,
    StudyProtocolAmendmentInput,
    StudyRegistrationInput,
    StudyRunDisposition,
)


def _registration(*, study_key: str = "TEST-1") -> StudyRegistrationInput:
    return StudyRegistrationInput.model_validate({
        "study_key": study_key,
        "title": "Narrative competition pilot",
        "protocol": {
            "version_number": 1,
            "objective": "Test one prospective factor.",
            "primary_hypothesis": "Treatment changes constraint compliance.",
            "null_hypothesis": "Treatment does not change constraint compliance.",
            "design_summary": "One blocked control run for persistence tests.",
            "planned_sample_size": 1,
            "randomization_method": "Frozen ordinal generated from supplied seed.",
            "randomization_seed": "seed-001",
            "operational_failure_policy": "Operational failures preserve run eligibility.",
            "refusal_policy": "A Maestro refusal terminally realizes the run.",
            "missing_result_policy": "UNKNOWN remains missing and is not imputed.",
            "conditions": [{
                "condition_key": "control",
                "label": "Control",
                "role": "CONTROL",
                "exact_factor_definition": "No added narrative factor.",
            }],
            "blocks": [{
                "block_key": "block-1",
                "label": "Block 1",
                "block_definition": "One directly observable exact-count constraint.",
            }],
            "constraint_definitions": [{
                "constraint_key": "exact-count",
                "constraint_type": "exact_count",
                "constraint_text": "Return exactly one track.",
                "is_hard_constraint": True,
                "evaluation_rule": "Count directly observed placements.",
                "permitted_result_provenance": "DIRECT_OBSERVATION",
                "unknown_handling": "UNKNOWN is excluded, never imputed.",
            }],
            "outcome_definitions": [{
                "outcome_key": "all-hard-pass",
                "role": "PRIMARY",
                "unit_of_analysis": "planned run",
                "outcome_definition": "All hard constraints pass.",
                "computation_rule": "PASS only when every hard result is PASS.",
                "missing_data_rule": "Any UNKNOWN makes the run unanalyzable.",
                "refusal_handling": "Report separately.",
                "operational_failure_handling": "Exclude without consuming the run.",
            }],
            "analysis_definitions": [{
                "analysis_key": "primary-comparison",
                "outcome_key": "all-hard-pass",
                "analysis_population": "Terminal Maestro outcomes.",
                "comparison_definition": "Report control outcome.",
                "aggregation_rule": "Raw count and proportion.",
                "exclusion_rule": "Exclude operational attempts.",
                "reporting_rule": "Report UNKNOWN and refusals separately.",
            }],
            "planned_runs": [{
                "run_key": "run-1",
                "condition_key": "control",
                "block_key": "block-1",
                "replicate_number": 1,
                "randomized_ordinal": 1,
                "planned_prompt_text": "Return exactly one track.",
                "planned_source_system": "Maestro Beta",
                "applicable_constraint_keys": ["exact-count"],
            }],
        },
    })


def _planned_experiment(definition_id: int, *, prompt: str = "Return exactly one track.") -> ExperimentInput:
    return ExperimentInput.model_validate({
        "prompt": prompt,
        "source_system": "Maestro Beta",
        "generated_title": "One",
        "tracks": [{"position": 1, "title": "Song", "artist": "Artist"}],
        "constraints": [{
            "study_constraint_definition_id": definition_id,
            "constraint_type": "exact_count",
            "constraint_text": "Return exactly one track.",
            "is_hard_constraint": True,
            "result": {"status": "PASS", "provenance_type": "DIRECT_OBSERVATION"},
        }],
    })


def _registered(service: ResearchStoreService):
    proposal = _registration()
    result = service.register_study(proposal)
    protocol = service.get_protocol_version(result["id"], 1)
    return proposal, result, protocol


def test_protocol_schema_and_canonical_hash_are_stable() -> None:
    proposal = _registration()
    first = canonical_protocol_bytes(proposal.study_key, proposal.title, proposal.protocol)
    second = canonical_protocol_bytes(proposal.study_key, proposal.title, proposal.protocol)
    assert first == second
    assert first.startswith(b'{"protocol":')
    assert protocol_registration_hash(proposal.study_key, proposal.title, proposal.protocol) == protocol_registration_hash(
        proposal.study_key, proposal.title, proposal.protocol
    )
    invalid = proposal.model_dump(mode="json")
    invalid["protocol"]["planned_sample_size"] = 2
    assert not ResearchStoreService.validate_study_protocol(invalid).valid


def test_atomic_registration_readback_and_database_immutability(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    proposal, study, protocol = _registered(service)
    assert study["study_key"] == "TEST-1"
    assert study["registered_protocol"]["planned_runs"][0]["run_key"] == "run-1"
    assert protocol["planned_runs"][0]["run_key"] == "run-1"
    assert protocol["registration_hash"] == protocol_registration_hash(
        proposal.study_key, proposal.title, proposal.protocol
    )

    with pytest.raises(IntegrityError, match="registered protocol is immutable"):
        research_session.execute(text(
            "UPDATE study_protocol_versions SET randomization_seed='changed' WHERE id=:id"
        ), {"id": protocol["id"]})
        research_session.commit()
    research_session.rollback()
    with pytest.raises(IntegrityError, match="registered protocol children are immutable"):
        research_session.add(StudyCondition(
            protocol_version_id=protocol["id"], condition_key="late", label="Late",
            role="CONTROL", exact_factor_definition="Post hoc",
        ))
        research_session.commit()
    research_session.rollback()
    original = service.get_protocol_version(study["id"], 1)
    assert original["randomization_seed"] == "seed-001"
    assert len(original["conditions"]) == 1


def test_amendment_creates_visible_immutable_successor(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    proposal, study, first = _registered(service)
    document = proposal.protocol.model_dump(mode="json")
    document["version_number"] = 2
    document["amendment_reason"] = "Prospective wording clarification."
    document["planned_runs"][0]["planned_prompt_text"] = "Return exactly one displayed track."
    amendment = StudyProtocolAmendmentInput.model_validate({
        "predecessor_version": 1,
        "protocol": document,
    })
    second = service.register_protocol_amendment(study["id"], amendment)
    assert second["version_number"] == 2
    assert second["predecessor_version_id"] == first["id"]
    assert service.get_protocol_version(study["id"], 1)["planned_runs"][0]["planned_prompt_text"] == "Return exactly one track."
    assert service.get_protocol_version(study["id"], 2)["planned_runs"][0]["planned_prompt_text"] == "Return exactly one displayed track."


def test_maestro_beta_prompt_limit_is_enforced_prospectively() -> None:
    proposal = _registration(study_key="PROMPT-LIMIT").model_dump(mode="json")
    run = proposal["protocol"]["planned_runs"][0]
    run["planned_prompt_text"] = "x" * 255
    accepted = ResearchStoreService.validate_study_protocol(proposal)
    assert accepted.valid
    assert len(accepted.value.protocol.planned_runs[0].planned_prompt_text) == 255

    run["planned_prompt_text"] = "x" * 256
    refused = ResearchStoreService.validate_study_protocol(proposal)
    assert not refused.valid
    assert "supports at most 255" in refused.issues[0].message


def test_prompt_limit_is_source_specific_and_counts_unicode_code_points() -> None:
    proposal = _registration(study_key="PROMPT-SOURCE").model_dump(mode="json")
    run = proposal["protocol"]["planned_runs"][0]
    run["planned_prompt_text"] = chr(0x1F3B5) * 255
    assert ResearchStoreService.validate_study_protocol(proposal).valid

    run["planned_prompt_text"] = "x" * 256
    run["planned_source_system"] = "Future Authoritative Source"
    assert ResearchStoreService.validate_study_protocol(proposal).valid


def test_operational_attempts_are_append_only_and_do_not_consume_run(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    _, study, protocol = _registered(service)
    run_id = protocol["planned_runs"][0]["id"]
    definition_id = protocol["constraint_definitions"][0]["id"]
    first = service.record_study_operational_attempt(
        run_id, StudyOperationalAttemptInput(failure_code="NETWORK", notes="No request completed.")
    )
    second = service.record_study_operational_attempt(
        run_id, StudyOperationalAttemptInput(failure_code="BROWSER", notes="Capture failed before result.")
    )
    assert (first["attempt_number"], second["attempt_number"]) == (1, 2)
    assert not first["consumes_planned_run"]
    assert service.get_protocol_version(study["id"], 1)["planned_runs"][0]["realization"] is None

    realization = service.ingest_planned_experiment(run_id, _planned_experiment(definition_id))
    assert realization["disposition"] == "EXPERIMENT_RECORDED"
    record = service.get_experiment(realization["experiment_id"])
    assert record["constraints"][0]["study_constraint_definition_id"] == definition_id
    with pytest.raises(ValueError, match="already has"):
        service.record_study_operational_attempt(
            run_id, StudyOperationalAttemptInput(failure_code="LATE", notes="Too late.")
        )


def test_protocol_may_explicitly_consume_run_on_operational_failure(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    document = _registration(study_key="TEST-CONSUME").model_dump(mode="json")
    document["protocol"]["operational_failure_consumes_run"] = True
    registered = service.register_study(StudyRegistrationInput.model_validate(document))
    run_id = registered["registered_protocol"]["planned_runs"][0]["id"]
    attempt = service.record_study_operational_attempt(
        run_id, StudyOperationalAttemptInput(failure_code="POLICY", notes="Protocol consumes this run.")
    )
    assert attempt["consumes_planned_run"]
    with pytest.raises(ValueError, match="consumed"):
        service.record_study_operational_attempt(
            run_id, StudyOperationalAttemptInput(failure_code="RETRY", notes="Not permitted.")
        )


def test_maestro_refusal_terminally_realizes_without_constraint_failure(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    _, _, protocol = _registered(service)
    run_id = protocol["planned_runs"][0]["id"]
    realization = service.record_planned_generation_failure(
        run_id,
        GenerationFailureInput(
            prompt="Return exactly one track.", source_system="Maestro Beta",
            failure_type="REFUSAL", displayed_message="Try something else.",
        ),
        StudyRunDisposition.MAESTRO_REFUSAL_RECORDED,
    )
    assert realization["experiment_id"] is None
    assert realization["generation_failure_id"] is not None
    assert research_session.scalar(select(func.count(Constraint.id))) == 0


def test_planned_realization_rejects_mutation_and_rolls_back(research_session) -> None:
    service = ResearchStoreService(ResearchRepository(research_session))
    _, _, protocol = _registered(service)
    run_id = protocol["planned_runs"][0]["id"]
    definition_id = protocol["constraint_definitions"][0]["id"]
    before = research_session.scalar(select(func.count(Experiment.id)))
    research_session.rollback()
    with pytest.raises(ValueError, match="prompt must exactly match"):
        service.ingest_planned_experiment(
            run_id, _planned_experiment(definition_id, prompt="Changed after registration")
        )
    assert research_session.scalar(select(func.count(Experiment.id))) == before
    research_session.rollback()

    wrong = _planned_experiment(definition_id).model_copy(deep=True)
    wrong.constraints[0].constraint_text = "Retrospectively changed."
    with pytest.raises(ValueError, match="exactly match"):
        service.ingest_planned_experiment(run_id, wrong)
    assert research_session.scalar(select(func.count(Experiment.id))) == before


def test_predating_experiment_cannot_be_attached_and_no_link_api_exists(research_session) -> None:
    old = ResearchRepository(research_session).insert_experiment(ExperimentInput.model_validate({
        "recorded_at": datetime.now(timezone.utc) - timedelta(days=1),
        "prompt": "Return exactly one track.",
        "tracks": [{"position": 1, "title": "Old", "artist": "Artist"}],
    }))
    service = ResearchStoreService(ResearchRepository(research_session))
    _, _, protocol = _registered(service)
    run_id = protocol["planned_runs"][0]["id"]
    assert not hasattr(service, "link_existing_experiment")
    assert not hasattr(service._studies, "link_existing_experiment")
    with pytest.raises(IntegrityError, match="predates protocol registration"):
        research_session.add(StudyRunRealization(
            planned_run_id=run_id,
            disposition="EXPERIMENT_RECORDED",
            experiment_id=old,
            generation_failure_id=None,
        ))
        research_session.commit()
    research_session.rollback()


def test_legacy_constraints_remain_unlinked_and_valid(research_session) -> None:
    experiment_id = ResearchRepository(research_session).insert_experiment(
        ExperimentInput.model_validate({
            "prompt": "Legacy",
            "tracks": [{"position": 1, "title": "Song", "artist": "Artist"}],
            "constraints": [{
                "constraint_type": "count",
                "constraint_text": "Exactly one",
                "result": {"status": "PASS"},
            }],
        })
    )
    record = ResearchRepository(research_session).get_experiment(experiment_id)
    assert record["constraints"][0]["study_constraint_definition_id"] is None

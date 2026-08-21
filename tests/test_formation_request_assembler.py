from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from test_candidate_formation import (
    accepted_objective,
    context,
    familiarity,
    features,
    journey,
    policy,
    taste,
    track_validation,
)
from test_candidate_constraint_eligibility import NON_EXPLICIT
from test_evidence_acquisition import acquisition
from playlist_narrative_engine.candidate_formation import (
    CandidateConstraintField,
    CandidateHardConstraint,
    CandidateEligibilityState,
    CandidateFormer,
    HardConstraintDeclarationArtifact,
    WithholdingReasonCode,
)
from playlist_narrative_engine.candidate_formation.request_assembler import (
    FormationRequestAssembler,
    FormationRequestAssemblyInput,
)


def constraint_declaration() -> HardConstraintDeclarationArtifact:
    return HardConstraintDeclarationArtifact(
        artifact_id="constraints-001",
        declaration_version="1.0",
        source_type="explicit_user_declaration",
        source_reference="request:001",
        constraints=(NON_EXPLICIT,),
    )


def assembly_input(**overrides: object) -> FormationRequestAssemblyInput:
    declaration = constraint_declaration()
    values: dict[str, object] = {
        "request_id": "assembled-request-001",
        "accepted_objective": accepted_objective(),
        "journey_plan": journey(),
        "acquisition": acquisition(),
        "track_validation": track_validation(),
        "taste_evidence": taste(),
        "familiarity_evidence": familiarity(),
        "track_feature_evidence": features(),
        "objective_context_evidence": context(),
        "policy": policy(),
        "hard_constraint_declaration": declaration,
        "authorized_declaration_id": declaration.artifact_id,
        "authorized_declaration_version": declaration.declaration_version,
    }
    values.update(overrides)
    return FormationRequestAssemblyInput(**values)


def test_assembler_preserves_governed_artifacts_and_declaration_lineage() -> None:
    inputs = assembly_input()
    request = FormationRequestAssembler().assemble(inputs)

    assert request.identity_metadata is inputs.acquisition.identity_metadata
    assert request.hard_constraints == inputs.hard_constraint_declaration.constraints
    assert request.hard_constraint_declaration_id == "constraints-001"
    assert request.hard_constraint_declaration_version == "1.0"
    assert request.hard_constraint_declaration_source_type == "explicit_user_declaration"
    assert request.hard_constraint_declaration_source_reference == "request:001"
    assert FormationRequestAssembler().assemble(inputs) == request


def test_declaration_expected_value_and_independent_constraints_survive_exactly() -> None:
    second = CandidateHardConstraint(
        constraint_key="exact-title",
        field=CandidateConstraintField.DISPLAYED_TITLE,
        expected_json='"Title track-a"',
    )
    declaration = HardConstraintDeclarationArtifact(
        artifact_id="constraints-001",
        declaration_version="1.0",
        source_type="explicit_user_declaration",
        source_reference="request:001",
        constraints=(NON_EXPLICIT, second),
    )
    result = FormationRequestAssembler().assemble(assembly_input(
        hard_constraint_declaration=declaration,
        authorized_declaration_id=declaration.artifact_id,
        authorized_declaration_version=declaration.declaration_version,
    ))
    assert tuple(item.constraint_key for item in result.hard_constraints) == (
        "exact-title", "no-explicit"
    )
    assert result.hard_constraints[1].expected_json == "false"


def test_missing_or_mismatched_declaration_authority_is_rejected() -> None:
    with pytest.raises(ValidationError, match="must match exactly"):
        assembly_input(authorized_declaration_version="2.0")
    with pytest.raises(ValidationError, match="requires a declaration"):
        assembly_input(
            hard_constraint_declaration=None,
            authorized_declaration_id="constraints-001",
            authorized_declaration_version="1.0",
        )


def test_direct_constrained_request_without_declaration_authority_is_rejected() -> None:
    from test_candidate_formation import request

    with pytest.raises(ValidationError, match="require explicit declaration authority"):
        request(hard_constraints=(NON_EXPLICIT,))


def test_no_declaration_creates_no_constraint_from_objective_or_prompt_prose() -> None:
    inputs = assembly_input(
        hard_constraint_declaration=None,
        authorized_declaration_id=None,
        authorized_declaration_version=None,
    )
    request = FormationRequestAssembler().assemble(inputs)
    assert "focused coding" in request.accepted_objective.objective.statement.lower()
    assert request.hard_constraints == ()


def test_exact_acquired_snapshot_partition_is_required() -> None:
    validation = track_validation().model_copy(update={"snapshot_id": "other"})
    with pytest.raises(ValueError, match="snapshot identity"):
        FormationRequestAssembler().assemble(assembly_input(track_validation=validation))

    changed = track_validation().validated_records[0].model_copy(
        update={"source_payload_json": '{"different":true}'}
    )
    validation = track_validation().model_copy(update={"validated_records": (changed,)})
    with pytest.raises(ValueError, match="exact acquired snapshot"):
        FormationRequestAssembler().assemble(assembly_input(track_validation=validation))

    wrong_provenance = track_validation().validated_records[0].model_copy(update={
        "provenance": track_validation().validated_records[0].provenance.model_copy(
            update={"source_reference": "other-receipt"}
        )
    })
    validation = track_validation().model_copy(update={"validated_records": (wrong_provenance,)})
    with pytest.raises(ValueError, match="source-receipt lineage"):
        FormationRequestAssembler().assemble(assembly_input(track_validation=validation))


def test_metadata_for_unvalidated_track_is_rejected_but_missing_record_is_allowed() -> None:
    acquired = acquisition()
    bad_record = acquired.identity_metadata.records[0].model_copy(update={"track_id": "unknown"})
    bad_metadata = acquired.identity_metadata.model_copy(update={"records": (bad_record,)})
    bad_acquisition = acquired.model_copy(update={"identity_metadata": bad_metadata})
    with pytest.raises(ValueError, match="unvalidated track identity"):
        FormationRequestAssembler().assemble(assembly_input(acquisition=bad_acquisition))

    empty_metadata = acquired.identity_metadata.model_copy(update={"records": ()})
    empty_acquisition = acquired.model_copy(update={"identity_metadata": empty_metadata})
    request = FormationRequestAssembler().assemble(assembly_input(acquisition=empty_acquisition))
    artifact = CandidateFormer().form(request)
    assert artifact.formed == ()
    assert artifact.withheld[0].constraint_eligibility[0].state is CandidateEligibilityState.UNKNOWN
    assert WithholdingReasonCode.HARD_CONSTRAINT_UNKNOWN in {
        item.code for item in artifact.withheld[0].reasons
    }


def test_known_authoritative_false_is_eligible_and_lineage_reaches_artifact() -> None:
    request = FormationRequestAssembler().assemble(assembly_input())
    artifact = CandidateFormer().form(request)
    assert artifact.summary.formed_count == 1
    assert artifact.formed[0].identity.displayed_explicit is False
    assert artifact.hard_constraint_declaration_id == "constraints-001"


def test_assembler_source_has_no_execution_or_workbench_dependencies() -> None:
    path = Path("src/playlist_narrative_engine/candidate_formation/request_assembler.py")
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    calls = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not {"score", "select", "construct", "form"} & calls
    assert "maestro_workbench" not in source
    assert "research_store" not in source


def test_no_provider_specific_or_workbench_candidate_authority_module_exists() -> None:
    root = Path("src/playlist_narrative_engine")
    acquisition_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "evidence_acquisition").glob("*.py")
    ).lower()
    assert "amazon" not in acquisition_source
    assert "spotify" not in acquisition_source
    assert "apple music" not in acquisition_source
    assert "maestro" not in acquisition_source
    workbench_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "maestro_workbench").rglob("*.py")
    )
    assert "CandidateFormationRequest" not in workbench_source
    assert "SourceNeutralAcquisitionResult" not in workbench_source
    research_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "research_store").rglob("*.py")
    )
    assert "SourceNeutralAcquisitionResult" not in research_source
    assert "FormationRequestAssembler" not in research_source

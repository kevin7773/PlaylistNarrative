from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from journey_authority_helpers import journey_authority
from playlist_narrative_engine.journey import (
    JOURNEY_PLAN_SCHEMA_VERSION,
    ActiveFocusRequest,
    JourneyPlanArtifact,
    JourneyPlanner,
    JourneyPlanningInvalidInput,
    JourneyPlanningRequest,
    serialize_journey_plan_artifact,
    verify_journey_plan_artifact,
)
from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    Objective,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
)
from playlist_narrative_engine.objective_safety import (
    AcceptedObjectiveArtifact,
    DeclinedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyEvaluator,
    ObjectiveSafetyRequest,
)


OBJECTIVE = Objective(
    objective_id="coding-focus",
    statement="Support a focused coding session.",
)


def authority(**values: object):
    return journey_authority(OBJECTIVE, **values)


def test_authoritative_planning_binds_complete_verified_chain() -> None:
    request, accepted, artifact = authority()
    binding = artifact.input_binding

    assert artifact.schema_version == JOURNEY_PLAN_SCHEMA_VERSION == "2.0"
    assert artifact.objective == OBJECTIVE
    assert binding.planning_request_sha256 == request.canonical_sha256
    assert binding.assessment_request_sha256 == (
        request.objective_assessment_request_sha256
    )
    assert binding.assessment_sha256 == request.objective_assessment_sha256
    assert binding.safety_request_sha256 == request.objective_safety_request_sha256
    assert binding.accepted_objective_sha256 == accepted.canonical_sha256
    assert binding.intent_declaration_sha256 == (
        request.objective_safety_request.intent_declaration_sha256
    )
    assert binding.safety_policy_sha256 == (
        request.objective_safety_request.safety_policy_sha256
    )
    assert verify_journey_plan_artifact(artifact, request=request)


def test_exact_authenticated_evidence_supplies_every_planning_parameter() -> None:
    request, _, artifact = authority(
        duration_minutes=120,
        discovery_percent=35,
        starting_energy="low",
        ending_energy="high",
    )

    parameters = artifact.input_binding.planning_parameters
    assert parameters == ActiveFocusRequest(
        duration_minutes=120,
        discovery_percent=35,
        starting_energy="low",
        ending_energy="high",
    )
    assert artifact.plan.duration_minutes == 120
    assert artifact.plan.discovery_percent == 35
    assert artifact.plan.phases[0].start_energy == "low"
    assert artifact.plan.phases[-1].end_energy == "high"
    assert tuple(item.evidence_id for item in artifact.input_binding.planning_evidence) == (
        "journey-context",
        "journey-duration",
        "journey-start-energy",
        "journey-end-energy",
        "journey-discovery",
    )
    assert request.objective_assessment.outcome is AssessmentOutcome.SUFFICIENT


@pytest.mark.parametrize(
    "field",
    (
        "objective_assessment_request_sha256",
        "objective_assessment_sha256",
        "objective_safety_request_sha256",
        "accepted_objective_sha256",
        "canonical_sha256",
    ),
)
def test_digest_substitution_is_invalid_input(field: str) -> None:
    request, _, _ = authority()
    changed = request.model_copy(update={field: "0" * 64})

    with pytest.raises(JourneyPlanningInvalidInput):
        JourneyPlanner().plan_authoritative(changed)


def test_objective_assessment_safety_and_accepted_substitution_are_rejected() -> None:
    request, _, _ = authority()
    other, other_accepted, _ = journey_authority(
        Objective(objective_id="other", statement="Other objective.")
    )
    changed = (
        request.model_copy(
            update={"objective_assessment_request": other.objective_assessment_request}
        ),
        request.model_copy(update={"objective_assessment": other.objective_assessment}),
        request.model_copy(
            update={"objective_safety_request": other.objective_safety_request}
        ),
        request.model_copy(update={"accepted_objective": other_accepted}),
    )

    for substituted in changed:
        with pytest.raises(JourneyPlanningInvalidInput):
            JourneyPlanner().plan_authoritative(substituted)


def test_intent_and_policy_substitution_are_rejected() -> None:
    request, _, _ = authority()
    safety = request.objective_safety_request
    declaration = safety.intent_declaration
    assert declaration is not None
    changed_declaration = declaration.model_copy(
        update={"authority_reference": "operator-declaration:substituted"}
    )
    changed_safety = safety.model_copy(
        update={"intent_declaration": changed_declaration}
    )
    substitutions = (
        request.model_copy(update={"objective_safety_request": changed_safety}),
        request.model_copy(
            update={
                "objective_safety_request": safety.model_copy(
                    update={"safety_policy_sha256": "0" * 64}
                )
            }
        ),
    )

    for substituted in substitutions:
        with pytest.raises(JourneyPlanningInvalidInput):
            JourneyPlanner().plan_authoritative(substituted)


def test_declined_objective_cannot_authorize_planning() -> None:
    request, _, _ = authority()
    safety = request.objective_safety_request
    declaration = safety.intent_declaration
    assert declaration is not None
    blocked_declaration = ObjectiveIntentDeclarationArtifact(
        declaration_id=declaration.declaration_id,
        objective_id=declaration.objective_id,
        objective_statement_sha256=declaration.objective_statement_sha256,
        authority_reference=declaration.authority_reference,
        state=ObjectiveIntentEvidenceState.ESTABLISHED,
        intent_category=ObjectiveIntentCategory.NON_PLAYLIST_ACTION_OR_OUTPUT,
    )
    blocked_safety = ObjectiveSafetyRequest(
        request_id=safety.request_id,
        objective_assessment=safety.objective_assessment,
        objective_sha256=safety.objective_sha256,
        objective_assessment_sha256=safety.objective_assessment_sha256,
        intent_declaration=blocked_declaration,
        intent_declaration_id=blocked_declaration.declaration_id,
        intent_declaration_sha256=blocked_declaration.canonical_sha256,
    )
    declined = ObjectiveSafetyEvaluator().evaluate(blocked_safety)
    assert isinstance(declined, DeclinedObjectiveArtifact)

    with pytest.raises(ValidationError):
        JourneyPlanningRequest(
            request_id="blocked",
            objective_assessment_request=request.objective_assessment_request,
            objective_assessment_request_sha256=(
                request.objective_assessment_request_sha256
            ),
            objective_assessment=request.objective_assessment,
            objective_assessment_sha256=request.objective_assessment_sha256,
            objective_safety_request=blocked_safety,
            objective_safety_request_sha256=blocked_safety.canonical_sha256,
            accepted_objective=declined,
            accepted_objective_sha256=declined.canonical_sha256,
        )


def test_missing_or_unsupported_context_cannot_be_supplied_by_prose_or_metadata() -> None:
    with pytest.raises(ValidationError):
        journey_authority(OBJECTIVE, context="Focused coding")

    request, _, _ = authority()
    incomplete_assessment_request = ObjectiveAssessmentRequest(
        objective=Objective(
            objective_id=OBJECTIVE.objective_id,
            statement="Active Focus for 90 minutes with 20 percent discovery.",
        ),
        evidence=(),
    )
    incomplete_assessment = ObjectiveAssessor().assess(incomplete_assessment_request)
    assert incomplete_assessment.outcome is AssessmentOutcome.CLARIFICATION_REQUIRED
    changed = request.model_copy(
        update={
            "objective_assessment_request": incomplete_assessment_request,
            "objective_assessment": incomplete_assessment,
        }
    )
    with pytest.raises(JourneyPlanningInvalidInput):
        JourneyPlanner().plan_authoritative(changed)


def test_existing_deterministic_calculation_is_unchanged() -> None:
    request, _, artifact = authority()
    expected = JourneyPlanner().plan_active_focus(
        ActiveFocusRequest(
            duration_minutes=90,
            discovery_percent=20,
            starting_energy="medium",
            ending_energy="medium",
        )
    )
    assert artifact.plan == expected
    assert JourneyPlanner().plan_authoritative(request).plan == expected


def test_planning_verifies_safety_authority_without_rerunning_the_evaluator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request, _, expected = authority()

    def forbidden_evaluation(*args: object, **kwargs: object) -> object:
        raise AssertionError("Journey Planning must not rerun Objective Safety")

    monkeypatch.setattr(ObjectiveSafetyEvaluator, "evaluate", forbidden_evaluation)

    assert JourneyPlanner().plan_authoritative(request) == expected


def test_same_authority_reproduces_canonical_artifact_and_tampering_fails() -> None:
    request, _, artifact = authority()
    second = JourneyPlanner().plan_authoritative(request)

    assert artifact == second
    assert serialize_journey_plan_artifact(artifact) == (
        serialize_journey_plan_artifact(second)
    )
    assert json.loads(serialize_journey_plan_artifact(artifact))["canonical_sha256"] == (
        artifact.canonical_sha256
    )
    assert not verify_journey_plan_artifact(
        artifact.model_copy(update={"canonical_sha256": "0" * 64}),
        request=request,
    )
    assert not verify_journey_plan_artifact(
        artifact.model_copy(
            update={
                "plan": artifact.plan.model_copy(update={"duration_minutes": 91})
            }
        ),
        request=request,
    )


def test_direct_construction_and_arbitrary_safety_id_are_not_authority() -> None:
    request, _, artifact = authority()
    direct = JourneyPlanArtifact(
        journey_id="caller-selected",
        input_binding=artifact.input_binding,
        objective=artifact.objective,
        objective_safety_artifact_id=artifact.objective_safety_artifact_id,
        plan=artifact.plan,
    )
    assert not verify_journey_plan_artifact(direct, request=request)
    with pytest.raises(ValidationError):
        JourneyPlanArtifact(
            journey_id="caller-selected",
            objective=artifact.objective,
            objective_safety_artifact_id="accepted-looking-string",
            plan=artifact.plan,
        )


def test_only_journey_planner_constructs_production_journey_artifacts() -> None:
    root = Path("src/playlist_narrative_engine")
    allowed = Path("src/playlist_narrative_engine/journey/planner.py")
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path == allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else None
            )
            if name == "JourneyPlanArtifact":
                violations.append(f"{path}:{node.lineno}")
    assert violations == []

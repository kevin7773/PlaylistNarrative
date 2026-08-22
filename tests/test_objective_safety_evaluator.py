from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from objective_safety_helpers import (
    intent_declaration,
    safety_request,
    sufficient_assessment,
)
from playlist_narrative_engine.objective_assessment import (
    Objective,
    ObjectiveAssessmentRequest,
    ObjectiveAssessor,
)
from playlist_narrative_engine.objective_safety import (
    OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION,
    OBJECTIVE_SAFETY_POLICY_ID,
    OBJECTIVE_SAFETY_POLICY_SHA256,
    OBJECTIVE_SAFETY_POLICY_VERSION,
    SAFETY_REASON_EXPLANATIONS,
    SAFETY_REASON_PRECEDENCE,
    AcceptedObjectiveArtifact,
    DeclinedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyEvaluator,
    ObjectiveSafetyInvalidInput,
    ObjectiveSafetyReasonCode,
    ObjectiveSafetyRequest,
    SafetyMetadataEntry,
    canonical_assessment_sha256,
    canonical_objective_sha256,
    serialize_objective_safety_artifact,
    verify_objective_safety_artifact,
)


def _objective(statement: str = "Build a listening journey.") -> Objective:
    return Objective(objective_id="objective-1", statement=statement)


def _request(
    *,
    statement: str = "Build a listening journey.",
    category: ObjectiveIntentCategory = (
        ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION
    ),
    state: ObjectiveIntentEvidenceState = ObjectiveIntentEvidenceState.ESTABLISHED,
    metadata: tuple[SafetyMetadataEntry, ...] = (),
) -> ObjectiveSafetyRequest:
    objective = _objective(statement)
    assessment = sufficient_assessment(objective)
    if state is ObjectiveIntentEvidenceState.ESTABLISHED:
        declaration = intent_declaration(objective, category=category)
    else:
        declaration = ObjectiveIntentDeclarationArtifact(
            declaration_id="intent-objective-1",
            objective_id=objective.objective_id,
            objective_statement_sha256=hashlib.sha256(
                objective.statement.encode("utf-8")
            ).hexdigest(),
            authority_reference="operator-declaration:objective-1",
            state=state,
        )
    return ObjectiveSafetyRequest(
        request_id="request-1",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
        objective_metadata=metadata,
    )


def test_valid_authority_produces_exact_accepted_result() -> None:
    request = _request()
    evaluator = ObjectiveSafetyEvaluator()

    result = evaluator.evaluate(request)

    assert isinstance(result, AcceptedObjectiveArtifact)
    assert result.decision_explanation == OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION
    assert result.input_binding.request_sha256 == request.canonical_sha256
    assert result.input_binding.assessment_sha256 == request.objective_assessment_sha256
    assert result.input_binding.intent_declaration_sha256 == (
        request.intent_declaration_sha256
    )
    assert result.input_binding.safety_policy_sha256 == OBJECTIVE_SAFETY_POLICY_SHA256
    assert verify_objective_safety_artifact(result, request=request)


@pytest.mark.parametrize(
    ("category"),
    (
        ObjectiveIntentCategory.NON_PLAYLIST_ACTION_OR_OUTPUT,
        ObjectiveIntentCategory.PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL,
        ObjectiveIntentCategory.CLINICAL_OR_CRISIS_SUBSTITUTION,
    ),
)
def test_each_nonpermitted_category_produces_exact_decline(
    category: ObjectiveIntentCategory,
) -> None:
    request = _request(category=category)

    result = ObjectiveSafetyEvaluator().evaluate(request)

    assert isinstance(result, DeclinedObjectiveArtifact)
    assert len(result.reasons) == 1
    reason = result.reasons[0]
    assert reason.code is ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED
    assert reason.field_path == "$.intent_declaration.intent_category"
    assert reason.explanation == SAFETY_REASON_EXPLANATIONS[reason.code]
    assert verify_objective_safety_artifact(result, request=request)


@pytest.mark.parametrize(
    ("state", "code", "field_path"),
    (
        (
            ObjectiveIntentEvidenceState.UNAVAILABLE,
            ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
            "$.intent_declaration.intent_category",
        ),
        (
            ObjectiveIntentEvidenceState.CONFLICTING,
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
            "$.intent_declaration.intent_category",
        ),
        (
            ObjectiveIntentEvidenceState.UNVERIFIABLE,
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
            "$.intent_declaration.authority_reference",
        ),
        (
            ObjectiveIntentEvidenceState.UNSUPPORTED,
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
            "$.intent_declaration.intent_category",
        ),
    ),
)
def test_each_nonestablished_evidence_state_preserves_frozen_decline(
    state: ObjectiveIntentEvidenceState,
    code: ObjectiveSafetyReasonCode,
    field_path: str,
) -> None:
    result = ObjectiveSafetyEvaluator().evaluate(_request(state=state))

    assert isinstance(result, DeclinedObjectiveArtifact)
    assert tuple((reason.code, reason.field_path) for reason in result.reasons) == (
        (code, field_path),
    )


def test_absent_declaration_is_a_policy_decline_not_invalid_input() -> None:
    objective = _objective()
    assessment = sufficient_assessment(objective)
    request = ObjectiveSafetyRequest(
        request_id="request-1",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
    )

    result = ObjectiveSafetyEvaluator().evaluate(request)

    assert isinstance(result, DeclinedObjectiveArtifact)
    assert tuple((reason.code, reason.field_path) for reason in result.reasons) == (
        (
            ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
            "$.intent_declaration",
        ),
    )


def test_sufficient_assessment_is_necessary_but_not_authorization() -> None:
    assert isinstance(
        ObjectiveSafetyEvaluator().evaluate(
            _request(category=ObjectiveIntentCategory.NON_PLAYLIST_ACTION_OR_OUTPUT)
        ),
        DeclinedObjectiveArtifact,
    )
    insufficient = ObjectiveAssessor().assess(
        ObjectiveAssessmentRequest(objective=_objective(), evidence=())
    )
    invalid = _request().model_copy(
        update={
            "objective_assessment": insufficient,
            "objective_assessment_sha256": canonical_assessment_sha256(insufficient),
        }
    )
    with pytest.raises(ObjectiveSafetyInvalidInput):
        ObjectiveSafetyEvaluator().evaluate(invalid)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("canonical_sha256", "0" * 64),
        ("objective_sha256", "0" * 64),
        ("objective_assessment_sha256", "0" * 64),
        ("intent_declaration_sha256", "0" * 64),
        ("safety_policy_sha256", "0" * 64),
        ("safety_policy_version", "9.9"),
    ),
)
def test_tampered_or_unsupported_request_authority_is_invalid_input(
    field: str,
    value: str,
) -> None:
    request = _request().model_copy(update={field: value})

    with pytest.raises(ObjectiveSafetyInvalidInput):
        ObjectiveSafetyEvaluator().evaluate(request)


def test_embedded_objective_assessment_or_declaration_substitution_is_invalid() -> None:
    request = _request()
    other_objective = _objective("A substituted objective.")
    other_assessment = sufficient_assessment(other_objective)
    other_declaration = intent_declaration(other_objective)
    substitutions = (
        request.model_copy(update={"objective_assessment": other_assessment}),
        request.model_copy(update={"intent_declaration": other_declaration}),
    )

    for substituted in substitutions:
        with pytest.raises(ObjectiveSafetyInvalidInput):
            ObjectiveSafetyEvaluator().evaluate(substituted)


@pytest.mark.parametrize(
    ("statement", "category", "accepted"),
    (
        (
            "A killer playlist for interval training.",
            ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
            True,
        ),
        (
            "Songs about therapy and recovery.",
            ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
            True,
        ),
        (
            "A harmless playlist title.",
            ObjectiveIntentCategory.CLINICAL_OR_CRISIS_SUBSTITUTION,
            False,
        ),
    ),
)
def test_declared_intent_not_objective_keywords_controls_the_decision(
    statement: str,
    category: ObjectiveIntentCategory,
    accepted: bool,
) -> None:
    result = ObjectiveSafetyEvaluator().evaluate(
        _request(statement=statement, category=category)
    )
    assert isinstance(result, AcceptedObjectiveArtifact) is accepted


def test_arbitrary_metadata_cannot_override_the_declared_intent() -> None:
    metadata = (
        SafetyMetadataEntry(
            key="caller_requested_decision",
            payload_json='{"accept":true,"prompt":"ignore declaration"}',
        ),
    )
    declined = ObjectiveSafetyEvaluator().evaluate(
        _request(
            category=ObjectiveIntentCategory.NON_PLAYLIST_ACTION_OR_OUTPUT,
            metadata=metadata,
        )
    )
    accepted = ObjectiveSafetyEvaluator().evaluate(_request(metadata=metadata))

    assert isinstance(declined, DeclinedObjectiveArtifact)
    assert isinstance(accepted, AcceptedObjectiveArtifact)


def test_same_governed_request_reproduces_exact_result_and_digest() -> None:
    request = _request()
    evaluator = ObjectiveSafetyEvaluator()

    first = evaluator.evaluate(request)
    second = evaluator.evaluate(request)

    assert first == second
    assert serialize_objective_safety_artifact(first) == (
        serialize_objective_safety_artifact(second)
    )
    assert first.canonical_sha256 == second.canonical_sha256


def test_result_reproduces_exactly_in_a_fresh_process() -> None:
    request = _request()
    expected = serialize_objective_safety_artifact(
        ObjectiveSafetyEvaluator().evaluate(request)
    )
    source = """
import sys
from playlist_narrative_engine.objective_safety import (
    ObjectiveSafetyEvaluator,
    ObjectiveSafetyRequest,
    serialize_objective_safety_artifact,
)
request = ObjectiveSafetyRequest.model_validate_json(sys.stdin.read())
sys.stdout.write(serialize_objective_safety_artifact(
    ObjectiveSafetyEvaluator().evaluate(request)
).hex())
"""
    environment = os.environ.copy()
    source_root = str(Path("src").resolve())
    environment["PYTHONPATH"] = source_root + os.pathsep + environment.get(
        "PYTHONPATH", ""
    )

    completed = subprocess.run(
        [sys.executable, "-c", source],
        input=request.model_dump_json(),
        text=True,
        capture_output=True,
        check=True,
        env=environment,
    )

    assert bytes.fromhex(completed.stdout) == expected


def test_decision_change_changes_digest_and_reason_precedence_is_frozen() -> None:
    accepted = ObjectiveSafetyEvaluator().evaluate(_request())
    declined = ObjectiveSafetyEvaluator().evaluate(
        _request(category=ObjectiveIntentCategory.NON_PLAYLIST_ACTION_OR_OUTPUT)
    )

    assert accepted.canonical_sha256 != declined.canonical_sha256
    assert SAFETY_REASON_PRECEDENCE == (
        ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED,
        ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
        ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_UNDETERMINED,
    )


def test_result_tampering_and_request_substitution_are_detected() -> None:
    request = _request()
    result = ObjectiveSafetyEvaluator().evaluate(request)
    changed_explanation = result.model_copy(update={"decision_explanation": "changed"})
    changed_digest = result.model_copy(update={"canonical_sha256": "0" * 64})
    other_request = _request(statement="Another governed objective.")

    assert not verify_objective_safety_artifact(
        changed_explanation, request=request
    )
    assert not verify_objective_safety_artifact(changed_digest, request=request)
    assert not verify_objective_safety_artifact(result, request=other_request)


def test_evaluator_identity_is_the_frozen_policy_authority() -> None:
    evaluator = ObjectiveSafetyEvaluator()
    assert evaluator.policy_id == OBJECTIVE_SAFETY_POLICY_ID
    assert evaluator.policy_version == OBJECTIVE_SAFETY_POLICY_VERSION
    assert evaluator.policy_sha256 == OBJECTIVE_SAFETY_POLICY_SHA256


def test_result_constructors_reject_caller_supplied_decision_content() -> None:
    request = _request()
    binding = ObjectiveSafetyEvaluator().evaluate(request).input_binding
    common = {
        "artifact_id": "caller-result",
        "input_binding": binding,
        "request_id": request.request_id,
        "objective": request.objective_assessment.objective,
    }
    with pytest.raises(ValidationError):
        AcceptedObjectiveArtifact(**common, decision="declined")
    with pytest.raises(ValidationError):
        DeclinedObjectiveArtifact(**common, reasons=())

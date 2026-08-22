from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from objective_safety_helpers import (
    accepted_objective,
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
    OBJECTIVE_SAFETY_POLICY_SHA256,
    OBJECTIVE_SAFETY_SCHEMA_VERSION,
    SAFETY_REASON_EXPLANATIONS,
    AcceptedObjectiveArtifact,
    DeclinedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyReason,
    ObjectiveSafetyReasonCode,
    ObjectiveSafetyRequest,
    SafetyMetadataEntry,
    canonical_assessment_sha256,
    canonical_objective_sha256,
    create_objective_safety_input_binding,
    serialize_objective_safety_artifact,
    verify_objective_safety_artifact,
    verify_objective_safety_request,
)


def objective() -> Objective:
    return Objective(
        objective_id="coding-focus",
        statement="Support a focused coding session.",
    )


def declined_reason(
    code: ObjectiveSafetyReasonCode,
    path: str,
) -> ObjectiveSafetyReason:
    return ObjectiveSafetyReason(
        code=code,
        field_path=path,
        explanation=SAFETY_REASON_EXPLANATIONS[code],
    )


def declined(
    request: ObjectiveSafetyRequest,
    *reasons: ObjectiveSafetyReason,
) -> DeclinedObjectiveArtifact:
    return DeclinedObjectiveArtifact(
        artifact_id="declined-001",
        input_binding=create_objective_safety_input_binding(request),
        request_id=request.request_id,
        objective=request.objective_assessment.objective,
        reasons=reasons,
        objective_metadata=request.objective_metadata,
        context_metadata=request.context_metadata,
    )


def test_request_binds_policy_objective_assessment_intent_and_metadata() -> None:
    item = objective()
    assessment = sufficient_assessment(item)
    declaration = intent_declaration(item)
    request = ObjectiveSafetyRequest(
        request_id="request",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(item),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
        objective_metadata=(
            SafetyMetadataEntry(key="zeta", payload_json="2"),
            SafetyMetadataEntry(key="alpha", payload_json="1"),
        ),
    )

    assert request.safety_policy_sha256 == OBJECTIVE_SAFETY_POLICY_SHA256
    assert tuple(entry.key for entry in request.objective_metadata) == ("alpha", "zeta")
    assert verify_objective_safety_request(request)


def test_request_requires_sufficient_assessment() -> None:
    insufficient = ObjectiveAssessor().assess(
        ObjectiveAssessmentRequest(objective=objective(), evidence=())
    )
    with pytest.raises(ValidationError, match="requires a sufficient assessment"):
        ObjectiveSafetyRequest(
            request_id="request",
            objective_assessment=insufficient,
            objective_sha256=canonical_objective_sha256(objective()),
            objective_assessment_sha256=canonical_assessment_sha256(insufficient),
        )


@pytest.mark.parametrize(
    "state",
    (
        ObjectiveIntentEvidenceState.UNAVAILABLE,
        ObjectiveIntentEvidenceState.CONFLICTING,
        ObjectiveIntentEvidenceState.UNVERIFIABLE,
        ObjectiveIntentEvidenceState.UNSUPPORTED,
    ),
)
def test_non_established_intent_cannot_carry_a_category(
    state: ObjectiveIntentEvidenceState,
) -> None:
    with pytest.raises(ValidationError, match="cannot contain a category"):
        ObjectiveIntentDeclarationArtifact(
            declaration_id="intent",
            objective_id=objective().objective_id,
            objective_statement_sha256=hashlib.sha256(
                objective().statement.encode("utf-8")
            ).hexdigest(),
            authority_reference="operator-declaration:intent",
            state=state,
            intent_category=ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
        )


def test_accepted_artifact_is_bound_immutable_and_verifiable() -> None:
    request = safety_request(objective())
    artifact = AcceptedObjectiveArtifact(
        artifact_id="accepted-001",
        input_binding=create_objective_safety_input_binding(request),
        request_id=request.request_id,
        objective=objective(),
        decision_explanation=OBJECTIVE_SAFETY_ACCEPTED_EXPLANATION,
    )

    assert artifact.schema_version == OBJECTIVE_SAFETY_SCHEMA_VERSION
    assert artifact.journey_planning_authorized is True
    assert verify_objective_safety_artifact(artifact, request=request)
    with pytest.raises(ValidationError):
        artifact.artifact_id = "changed"


@pytest.mark.parametrize(
    ("state", "code", "path"),
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
def test_frozen_nonaccepted_states_verify_exact_decline(
    state: ObjectiveIntentEvidenceState,
    code: ObjectiveSafetyReasonCode,
    path: str,
) -> None:
    item = objective()
    assessment = sufficient_assessment(item)
    declaration = ObjectiveIntentDeclarationArtifact(
        declaration_id="intent",
        objective_id=item.objective_id,
        objective_statement_sha256=hashlib.sha256(item.statement.encode()).hexdigest(),
        authority_reference="operator-declaration:intent",
        state=state,
    )
    request = ObjectiveSafetyRequest(
        request_id="request",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(item),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
    )
    artifact = declined(request, declined_reason(code, path))

    assert verify_objective_safety_artifact(artifact, request=request)


def test_missing_intent_and_nonpermitted_intent_are_distinct() -> None:
    item = objective()
    assessment = sufficient_assessment(item)
    missing_request = ObjectiveSafetyRequest(
        request_id="missing",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(item),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
    )
    missing = declined(
        missing_request,
        declined_reason(
            ObjectiveSafetyReasonCode.REQUIRED_CONTEXT_MISSING,
            "$.intent_declaration",
        ),
    )
    declaration = intent_declaration(
        item,
        category=ObjectiveIntentCategory.PERSONAL_OUTCOME_GUARANTEE_OR_CONTROL,
    )
    blocked_request = ObjectiveSafetyRequest(
        request_id="blocked",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(item),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=declaration,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
    )
    blocked = declined(
        blocked_request,
        declined_reason(
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED,
            "$.intent_declaration.intent_category",
        ),
    )

    assert verify_objective_safety_artifact(missing, request=missing_request)
    assert verify_objective_safety_artifact(blocked, request=blocked_request)


def test_substitution_or_tampering_is_detected() -> None:
    request = safety_request(objective())
    artifact = accepted_objective(objective())
    other_objective = objective().model_copy(update={"statement": "Other objective."})
    other_request = safety_request(other_objective)

    assert not verify_objective_safety_artifact(artifact, request=other_request)
    for field, value in (
        ("request_sha256", "0" * 64),
        ("assessment_sha256", "0" * 64),
        ("objective_sha256", "0" * 64),
        ("intent_declaration_sha256", "0" * 64),
        ("safety_policy_sha256", "0" * 64),
    ):
        changed_binding = artifact.input_binding.model_copy(update={field: value})
        changed = artifact.model_copy(update={"input_binding": changed_binding})
        assert not verify_objective_safety_artifact(changed, request=request)

    changed_request = request.model_copy(update={"canonical_sha256": "0" * 64})
    assert not verify_objective_safety_request(changed_request)
    changed_artifact = artifact.model_copy(update={"canonical_sha256": "0" * 64})
    assert not verify_objective_safety_artifact(changed_artifact, request=request)


def test_wrong_decision_cannot_verify_against_intent() -> None:
    accepted_request = safety_request(objective())
    wrong_decline = declined(
        accepted_request,
        declined_reason(
            ObjectiveSafetyReasonCode.OBJECTIVE_INTENT_NOT_PERMITTED,
            "$.intent_declaration.intent_category",
        ),
    )
    assert not verify_objective_safety_artifact(wrong_decline, request=accepted_request)


def test_safety_serialization_is_canonical_utf8() -> None:
    item = Objective(objective_id="focus", statement="Björk listening journey.")
    artifact = accepted_objective(item)

    first = serialize_objective_safety_artifact(artifact)
    second = serialize_objective_safety_artifact(artifact)

    assert first == second
    assert "Björk".encode("utf-8") in first
    assert json.loads(first)["canonical_sha256"] == artifact.canonical_sha256

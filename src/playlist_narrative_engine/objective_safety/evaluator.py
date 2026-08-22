from __future__ import annotations

from playlist_narrative_engine.objective_safety.schemas import (
    AcceptedObjectiveArtifact,
    DeclinedObjectiveArtifact,
    OBJECTIVE_SAFETY_POLICY_ID,
    OBJECTIVE_SAFETY_POLICY_SHA256,
    OBJECTIVE_SAFETY_POLICY_VERSION,
    ObjectiveSafetyArtifact,
    ObjectiveSafetyRequest,
    SafetyDecision,
    _expected_decision,
    create_objective_safety_input_binding,
    verify_objective_safety_artifact,
    verify_objective_safety_request,
)


class ObjectiveSafetyInvalidInput(ValueError):
    """The governed request cannot authorize policy execution."""


class ObjectiveSafetyEvaluator:
    """Sole production decision boundary for Objective Safety policy 1.0."""

    policy_id = OBJECTIVE_SAFETY_POLICY_ID
    policy_version = OBJECTIVE_SAFETY_POLICY_VERSION
    policy_sha256 = OBJECTIVE_SAFETY_POLICY_SHA256

    def evaluate(self, request: ObjectiveSafetyRequest) -> ObjectiveSafetyArtifact:
        if not isinstance(request, ObjectiveSafetyRequest):
            raise ObjectiveSafetyInvalidInput(
                "Objective Safety requires a governed ObjectiveSafetyRequest"
            )
        if not verify_objective_safety_request(request):
            raise ObjectiveSafetyInvalidInput(
                "Objective Safety request authority is invalid or unverifiable"
            )

        decision, reasons = _expected_decision(request)
        binding = create_objective_safety_input_binding(request)
        result_id = f"objective-safety-result:{request.canonical_sha256}"
        common = {
            "artifact_id": result_id,
            "input_binding": binding,
            "request_id": request.request_id,
            "objective": request.objective_assessment.objective,
            "objective_metadata": request.objective_metadata,
            "context_metadata": request.context_metadata,
        }
        if decision is SafetyDecision.ACCEPTED:
            result: ObjectiveSafetyArtifact = AcceptedObjectiveArtifact(**common)
        else:
            result = DeclinedObjectiveArtifact(**common, reasons=reasons)

        if not verify_objective_safety_artifact(result, request=request):
            raise RuntimeError(
                "Objective Safety evaluator produced an unverifiable result"
            )
        return result

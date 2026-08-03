from __future__ import annotations

import hashlib

from playlist_narrative_engine.crossing_understanding.schemas import (
    CLARIFICATION_REASON_EXPLANATIONS,
    CrossingClarificationReason,
    CrossingClarificationReasonCode,
    CrossingUnderstandingArtifact,
    CrossingUnderstandingOutcome,
    CrossingUnderstandingRequest,
    TransitionCandidate,
    TransitionDerivation,
)
from playlist_narrative_engine.objective_safety.serialization import (
    serialize_objective_safety_artifact,
)


class CrossingUnderstandingBoundary:
    """Preserve supported crossing understanding without choosing accompaniment."""

    def understand(
        self,
        request: CrossingUnderstandingRequest,
        *,
        artifact_id: str,
    ) -> CrossingUnderstandingArtifact:
        expected_digest = hashlib.sha256(
            serialize_objective_safety_artifact(request.accepted_objective)
        ).hexdigest()
        if request.accepted_objective_sha256 != expected_digest:
            raise ValueError("accepted Objective Safety artifact digest must match exactly")

        reasons: list[CrossingClarificationReason] = []
        authenticated_by_id = {
            item.authenticated_characteristic_id: item
            for item in request.evidence_authentication_artifact.content.authenticated_characteristics
        }
        supported_transitions = tuple(
            TransitionCandidate(
                candidate_id=item.candidate_id,
                ending=authenticated_by_id[item.ending_authenticated_characteristic_id],
                beginning=authenticated_by_id[item.beginning_authenticated_characteristic_id],
                derivation=TransitionDerivation(
                    input_authenticated_characteristic_ids=(
                        item.ending_authenticated_characteristic_id,
                        item.beginning_authenticated_characteristic_id,
                    )
                ),
            )
            for item in request.directional_transition_requests
        )
        if not request.directional_transition_requests:
            for code, path in (
                (CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE, "transition.ending"),
                (CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE, "transition.beginning"),
            ):
                reasons.append(
                    CrossingClarificationReason(
                        code=code,
                        field_path=path,
                        explanation=CLARIFICATION_REASON_EXPLANATIONS[code],
                    )
                )
        if len(supported_transitions) > 1:
            code = CrossingClarificationReasonCode.MULTIPLE_TRANSITIONS_PLAUSIBLE
            reasons.append(
                CrossingClarificationReason(
                    code=code,
                    field_path="transition_candidates",
                    explanation=CLARIFICATION_REASON_EXPLANATIONS[code],
                )
            )

        precedence = {
            code: index
            for index, code in enumerate(CrossingClarificationReasonCode)
        }
        ordered_reasons = tuple(
            sorted(
                reasons,
                key=lambda reason: (
                    precedence[reason.code],
                    reason.field_path.encode("utf-8"),
                ),
            )
        )
        clarification_required = bool(ordered_reasons)
        resolved_transition_id = (
            None
            if clarification_required or len(supported_transitions) != 1
            else supported_transitions[0].candidate_id
        )
        return CrossingUnderstandingArtifact(
            artifact_id=artifact_id,
            request_id=request.request_id,
            accepted_objective=request.accepted_objective,
            accepted_objective_sha256=request.accepted_objective_sha256,
            crossing_policy_id=request.crossing_policy_id,
            crossing_policy_version=request.crossing_policy_version,
            evidence_authentication_artifact=request.evidence_authentication_artifact,
            evidence_authentication_sha256=request.evidence_authentication_sha256,
            lived_evidence=request.lived_evidence,
            transition_candidates=supported_transitions,
            resolved_transition_id=resolved_transition_id,
            recurring_condition_candidates=request.recurring_condition_candidates,
            particular_need=request.particular_need,
            outcome=(
                CrossingUnderstandingOutcome.CLARIFICATION_REQUIRED
                if clarification_required
                else CrossingUnderstandingOutcome.UNDERSTOOD
            ),
            clarification_required=clarification_required,
            clarification_reasons=ordered_reasons,
        )

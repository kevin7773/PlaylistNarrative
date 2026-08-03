from __future__ import annotations

import hashlib

from playlist_narrative_engine.crossing_understanding.schemas import (
    CLARIFICATION_REASON_EXPLANATIONS,
    CrossingClaim,
    CrossingClaimBasis,
    CrossingClarificationReason,
    CrossingClarificationReasonCode,
    CrossingEvidenceState,
    CrossingUnderstandingArtifact,
    CrossingUnderstandingOutcome,
    CrossingUnderstandingRequest,
    TransitionCandidate,
)
from playlist_narrative_engine.objective_safety.serialization import (
    serialize_objective_safety_artifact,
)


def _claim_reason(
    claim: CrossingClaim | None,
    *,
    unavailable: CrossingClarificationReasonCode,
    unsupported: CrossingClarificationReasonCode,
    conflicting: CrossingClarificationReasonCode,
    field_path: str,
    explicitly_inapplicable_is_valid: bool = False,
) -> CrossingClarificationReason | None:
    if claim is None or claim.state is CrossingEvidenceState.UNAVAILABLE:
        code = unavailable
    elif claim.state is CrossingEvidenceState.CONFLICTING:
        code = conflicting
    elif claim.state is CrossingEvidenceState.UNSUPPORTED or (
        claim.state is CrossingEvidenceState.EXPLICITLY_INAPPLICABLE
        and not explicitly_inapplicable_is_valid
    ):
        code = unsupported
    else:
        return None
    return CrossingClarificationReason(
        code=code,
        field_path=field_path,
        explanation=CLARIFICATION_REASON_EXPLANATIONS[code],
    )


def _transition_is_supported(candidate: TransitionCandidate) -> bool:
    directional_states = (candidate.ending.state, candidate.beginning.state)
    allowed = {
        CrossingEvidenceState.SUPPORTED,
        CrossingEvidenceState.EXPLICITLY_INAPPLICABLE,
    }
    return all(state in allowed for state in directional_states) and any(
        state is CrossingEvidenceState.SUPPORTED for state in directional_states
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
        supported_lived = tuple(
            claim
            for claim in request.lived_evidence
            if claim.state is CrossingEvidenceState.SUPPORTED
        )
        if not supported_lived:
            states = {claim.state for claim in request.lived_evidence}
            if CrossingEvidenceState.CONFLICTING in states:
                event_code = CrossingClarificationReasonCode.EVENT_CONFLICTING
            elif states & {
                CrossingEvidenceState.UNSUPPORTED,
                CrossingEvidenceState.EXPLICITLY_INAPPLICABLE,
            }:
                event_code = CrossingClarificationReasonCode.EVENT_UNSUPPORTED
            else:
                event_code = CrossingClarificationReasonCode.EVENT_UNAVAILABLE
            reasons.append(
                CrossingClarificationReason(
                    code=event_code,
                    field_path="lived_evidence",
                    explanation=CLARIFICATION_REASON_EXPLANATIONS[event_code],
                )
            )

        supported_transitions = tuple(
            candidate
            for candidate in request.transition_candidates
            if _transition_is_supported(candidate)
        )
        for index, candidate in enumerate(request.transition_candidates):
            ending_reason = _claim_reason(
                candidate.ending,
                unavailable=CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE,
                unsupported=CrossingClarificationReasonCode.TRANSITION_UNSUPPORTED,
                conflicting=CrossingClarificationReasonCode.TRANSITION_CONFLICTING,
                field_path=f"transition_candidates.{index}.ending",
                explicitly_inapplicable_is_valid=True,
            )
            beginning_reason = _claim_reason(
                candidate.beginning,
                unavailable=CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE,
                unsupported=CrossingClarificationReasonCode.TRANSITION_UNSUPPORTED,
                conflicting=CrossingClarificationReasonCode.TRANSITION_CONFLICTING,
                field_path=f"transition_candidates.{index}.beginning",
                explicitly_inapplicable_is_valid=True,
            )
            if ending_reason is not None:
                reasons.append(ending_reason)
            if beginning_reason is not None:
                reasons.append(beginning_reason)
        if not request.transition_candidates:
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
        elif not supported_transitions and not any(
            reason.code
            in {
                CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE,
                CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE,
                CrossingClarificationReasonCode.TRANSITION_UNSUPPORTED,
                CrossingClarificationReasonCode.TRANSITION_CONFLICTING,
            }
            for reason in reasons
        ):
            code = CrossingClarificationReasonCode.TRANSITION_UNSUPPORTED
            reasons.append(
                CrossingClarificationReason(
                    code=code,
                    field_path="transition_candidates",
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

        need_reason = _claim_reason(
            request.particular_need,
            unavailable=CrossingClarificationReasonCode.NEED_UNAVAILABLE,
            unsupported=CrossingClarificationReasonCode.NEED_UNSUPPORTED,
            conflicting=CrossingClarificationReasonCode.NEED_CONFLICTING,
            field_path="particular_need",
        )
        if need_reason is not None:
            reasons.append(need_reason)
        elif request.particular_need is not None and request.particular_need.basis not in {
            CrossingClaimBasis.USER_STATED,
            CrossingClaimBasis.USER_CONFIRMED,
        }:
            code = CrossingClarificationReasonCode.USER_CONFIRMATION_REQUIRED
            reasons.append(
                CrossingClarificationReason(
                    code=code,
                    field_path="particular_need",
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
            lived_evidence=request.lived_evidence,
            transition_candidates=request.transition_candidates,
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

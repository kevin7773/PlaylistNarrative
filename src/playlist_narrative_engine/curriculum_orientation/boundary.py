from __future__ import annotations

from playlist_narrative_engine.curriculum_orientation.schemas import (
    ORIENTATION_REASON_EXPLANATIONS,
    CurriculumOrientationArtifact,
    CurriculumOrientationCandidate,
    CurriculumOrientationOutcome,
    CurriculumOrientationReason,
    CurriculumOrientationReasonCode,
    CurriculumOrientationRequest,
    OrientationTransitionEvidence,
)


class CurriculumOrientationBoundary:
    """Execute immutable curriculum rules over exact CU-1 authenticated lineage."""

    def orient(self, request: CurriculumOrientationRequest, *, artifact_id: str) -> CurriculumOrientationArtifact:
        parent = request.crossing_understanding
        resolved = tuple(
            item for item in parent.transition_candidates
            if item.candidate_id == parent.resolved_transition_id
        )
        transition = resolved[0] if len(resolved) == 1 else None
        transition_evidence = None if transition is None else OrientationTransitionEvidence(
            transition_id=transition.candidate_id,
            ending=transition.ending,
            beginning=transition.beginning,
        )

        if transition_evidence is None:
            candidates: tuple[CurriculumOrientationCandidate, ...] = ()
            outcome = CurriculumOrientationOutcome.CLARIFICATION_REQUIRED
            reason_code = CurriculumOrientationReasonCode.PARENT_CROSSING_UNRESOLVED
            reason_path = "crossing_understanding.resolved_transition_id"
        else:
            matched = tuple(
                rule for rule in request.orientation_rule_set.rules
                if rule.ending_predicate.matches(transition_evidence.ending)
                and rule.beginning_predicate.matches(transition_evidence.beginning)
            )
            candidates = tuple(CurriculumOrientationCandidate(
                candidate_id=rule.candidate_id,
                condition_id=rule.condition_id,
                pattern=rule.pattern,
                rule_id=rule.rule_id,
                rule_version=rule.rule_version,
                input_authenticated_characteristic_ids=(
                    transition_evidence.ending.authenticated_characteristic_id,
                    transition_evidence.beginning.authenticated_characteristic_id,
                ),
            ) for rule in matched)
            outcome = (
                CurriculumOrientationOutcome.ORIENTED
                if candidates else CurriculumOrientationOutcome.NO_ORIENTATION_SUPPORTED
            )
            reason_code = None if candidates else CurriculumOrientationReasonCode.NO_APPROVED_RULE_MATCHED
            reason_path = "transition_evidence"

        reasons = () if reason_code is None else (CurriculumOrientationReason(
            code=reason_code,
            field_path=reason_path,
            explanation=ORIENTATION_REASON_EXPLANATIONS[reason_code],
        ),)
        return CurriculumOrientationArtifact(
            artifact_id=artifact_id,
            request_id=request.request_id,
            crossing_understanding=parent,
            parent_crossing_sha256=request.crossing_understanding_sha256,
            accepted_objective=request.accepted_objective,
            curriculum_id=request.curriculum_id,
            curriculum_version=request.curriculum_version,
            orientation_policy_id=request.orientation_policy_id,
            orientation_policy_version=request.orientation_policy_version,
            orientation_rule_set=request.orientation_rule_set,
            orientation_rule_set_sha256=request.orientation_rule_set_sha256,
            transition_evidence=transition_evidence,
            candidates=candidates,
            outcome=outcome,
            reasons=reasons,
        )

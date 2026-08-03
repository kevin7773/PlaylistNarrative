from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.crossing_understanding import (
    CrossingClaim,
    CrossingClaimBasis,
    CrossingClaimRole,
    CrossingClarificationReasonCode,
    CrossingEvidenceObservation,
    CrossingEvidenceState,
    CrossingUnderstandingBoundary,
    CrossingUnderstandingOutcome,
    CrossingUnderstandingRequest,
    RecurringConditionCandidate,
    RecurringConditionOrientationBasis,
    RecurringConditionRuleProvenance,
    TransitionCandidate,
    TransitionDerivation,
    serialize_crossing_understanding,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import (
    serialize_objective_safety_artifact,
)


def _accepted_objective() -> AcceptedObjectiveArtifact:
    return AcceptedObjectiveArtifact(
        artifact_id="safety-1",
        request_id="safety-request-1",
        objective=Objective(
            objective_id="objective-1",
            statement="I am starting a new job and want to understand this transition.",
        ),
        safety_policy_id="objective-safety",
        safety_policy_version="1.0",
        decision_explanation="The objective may proceed.",
    )


def _digest(accepted: AcceptedObjectiveArtifact) -> str:
    return hashlib.sha256(serialize_objective_safety_artifact(accepted)).hexdigest()


def _observation(evidence_id: str, value: str) -> CrossingEvidenceObservation:
    return CrossingEvidenceObservation(
        evidence_id=evidence_id,
        source_type="user_statement",
        source_reference=f"conversation:{evidence_id}",
        payload_json=json.dumps(value, ensure_ascii=False, separators=(",", ":")),
    )


def _supported_claim(
    claim_id: str,
    role: CrossingClaimRole,
    value: str,
    *,
    basis: CrossingClaimBasis = CrossingClaimBasis.USER_STATED,
) -> CrossingClaim:
    return CrossingClaim(
        claim_id=claim_id,
        role=role,
        state=CrossingEvidenceState.SUPPORTED,
        value=value,
        basis=basis,
        observations=(_observation(f"evidence-{claim_id}", value),),
    )


def _transition(
    candidate_id: str = "transition-1",
    *,
    ending_value: str = "being new to the role",
    beginning_value: str = "growing into competence",
    basis: CrossingClaimBasis = CrossingClaimBasis.USER_CONFIRMED,
) -> TransitionCandidate:
    ending = _supported_claim(
        f"{candidate_id}-ending",
        CrossingClaimRole.ENDING,
        ending_value,
        basis=CrossingClaimBasis.USER_CONFIRMED,
    )
    beginning = _supported_claim(
        f"{candidate_id}-beginning",
        CrossingClaimRole.BEGINNING,
        beginning_value,
        basis=CrossingClaimBasis.USER_CONFIRMED,
    )
    derivation = (
        TransitionDerivation(
            input_claim_ids=(ending.claim_id, beginning.claim_id)
        )
        if basis is CrossingClaimBasis.VERSIONED_DERIVATION
        else None
    )
    return TransitionCandidate(
        candidate_id=candidate_id,
        ending=ending,
        beginning=beginning,
        basis=basis,
        derivation=derivation,
    )


def _condition(
    candidate_id: str,
    pattern: str,
) -> RecurringConditionCandidate:
    return RecurringConditionCandidate(
        candidate_id=candidate_id,
        pattern=pattern,
        orientation_basis=RecurringConditionOrientationBasis.USER_OBSERVATION,
        observations=(_observation(f"evidence-{candidate_id}", pattern),),
    )


def _request(**updates: object) -> CrossingUnderstandingRequest:
    accepted = _accepted_objective()
    values: dict[str, object] = {
        "request_id": "crossing-request-1",
        "accepted_objective": accepted,
        "accepted_objective_sha256": _digest(accepted),
        "crossing_policy_id": "crossing-understanding",
        "crossing_policy_version": "1.0",
        "lived_evidence": (
            _supported_claim(
                "event-1",
                CrossingClaimRole.VISIBLE_EVENT,
                "starting a new job",
            ),
        ),
        "transition_candidates": (_transition(),),
        "recurring_condition_candidates": (),
        "particular_need": _supported_claim(
            "need-1",
            CrossingClaimRole.PARTICULAR_NEED,
            "steadiness while learning",
            basis=CrossingClaimBasis.USER_CONFIRMED,
        ),
    }
    values.update(updates)
    return CrossingUnderstandingRequest(**values)


def test_understood_artifact_preserves_first_four_steps_and_non_claims() -> None:
    artifact = CrossingUnderstandingBoundary().understand(
        _request(), artifact_id="crossing-1"
    )

    assert artifact.outcome is CrossingUnderstandingOutcome.UNDERSTOOD
    assert artifact.resolved_transition_id == "transition-1"
    assert artifact.particular_need is not None
    assert artifact.particular_need.value == "steadiness while learning"
    assert artifact.recurring_condition_candidates == ()
    assert artifact.clarification_reasons == ()
    assert artifact.person_classified is False
    assert artifact.particular_need_inferred_from_curriculum is False
    assert artifact.accompaniment_selected is False
    assert artifact.soundtrack_objective_created is False
    assert artifact.journey_planning_performed is False
    assert artifact.candidate_formation_performed is False
    assert artifact.music_scored is False
    assert artifact.music_selected is False
    assert artifact.explanation_generated is False


def test_directional_derivation_represents_inference_without_classifying_event() -> None:
    transition = _transition(basis=CrossingClaimBasis.VERSIONED_DERIVATION)
    artifact = CrossingUnderstandingBoundary().understand(
        _request(transition_candidates=(transition,)), artifact_id="crossing-1"
    )

    assert artifact.outcome is CrossingUnderstandingOutcome.UNDERSTOOD
    assert artifact.transition_candidates[0].derivation is not None
    assert artifact.transition_candidates[0].derivation.input_claim_ids == (
        "transition-1-ending",
        "transition-1-beginning",
    )


def test_multiple_plausible_transitions_are_retained_without_selection() -> None:
    request = _request(
        transition_candidates=(
            _transition("transition-z", beginning_value="proving competence"),
            _transition("transition-a", beginning_value="finding belonging"),
        )
    )
    artifact = CrossingUnderstandingBoundary().understand(
        request, artifact_id="crossing-1"
    )

    assert tuple(item.candidate_id for item in artifact.transition_candidates) == (
        "transition-a",
        "transition-z",
    )
    assert artifact.resolved_transition_id is None
    assert artifact.outcome is CrossingUnderstandingOutcome.CLARIFICATION_REQUIRED
    assert tuple(reason.code for reason in artifact.clarification_reasons) == (
        CrossingClarificationReasonCode.MULTIPLE_TRANSITIONS_PLAUSIBLE,
    )


def test_missing_transition_and_need_retain_all_reasons_in_fixed_order() -> None:
    artifact = CrossingUnderstandingBoundary().understand(
        _request(transition_candidates=(), particular_need=None),
        artifact_id="crossing-1",
    )

    assert tuple(reason.code for reason in artifact.clarification_reasons) == (
        CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE,
        CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE,
        CrossingClarificationReasonCode.NEED_UNAVAILABLE,
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (CrossingEvidenceState.UNAVAILABLE, CrossingClarificationReasonCode.EVENT_UNAVAILABLE),
        (CrossingEvidenceState.UNSUPPORTED, CrossingClarificationReasonCode.EVENT_UNSUPPORTED),
        (CrossingEvidenceState.CONFLICTING, CrossingClarificationReasonCode.EVENT_CONFLICTING),
    ),
)
def test_lived_evidence_states_remain_distinct(
    state: CrossingEvidenceState,
    expected: CrossingClarificationReasonCode,
) -> None:
    observations: tuple[CrossingEvidenceObservation, ...]
    if state is CrossingEvidenceState.UNAVAILABLE:
        observations = ()
    elif state is CrossingEvidenceState.CONFLICTING:
        observations = (_observation("evidence-a", "arrival"), _observation("evidence-b", "departure"))
    else:
        observations = (_observation("evidence-a", "unclear"),)
    event = CrossingClaim(
        claim_id="event-1",
        role=CrossingClaimRole.VISIBLE_EVENT,
        state=state,
        observations=observations,
    )
    artifact = CrossingUnderstandingBoundary().understand(
        _request(lived_evidence=(event,)), artifact_id="crossing-1"
    )
    assert artifact.clarification_reasons[0].code is expected


def test_explicitly_inapplicable_direction_is_not_treated_as_missing() -> None:
    ending = CrossingClaim(
        claim_id="ending-inapplicable",
        role=CrossingClaimRole.ENDING,
        state=CrossingEvidenceState.EXPLICITLY_INAPPLICABLE,
        observations=(_observation("evidence-ending", "nothing established is ending"),),
    )
    beginning = _supported_claim(
        "beginning-1", CrossingClaimRole.BEGINNING, "waiting without an outcome"
    )
    transition = TransitionCandidate(
        candidate_id="transition-1",
        ending=ending,
        beginning=beginning,
        basis=CrossingClaimBasis.USER_CONFIRMED,
    )
    artifact = CrossingUnderstandingBoundary().understand(
        _request(transition_candidates=(transition,)), artifact_id="crossing-1"
    )
    assert artifact.outcome is CrossingUnderstandingOutcome.UNDERSTOOD


def test_non_supported_claims_cannot_manufacture_values() -> None:
    with pytest.raises(ValidationError, match="non-supported"):
        CrossingClaim(
            claim_id="need-1",
            role=CrossingClaimRole.PARTICULAR_NEED,
            state=CrossingEvidenceState.UNAVAILABLE,
            value="neutral",
            basis=CrossingClaimBasis.USER_STATED,
        )


def test_supported_claim_requires_actual_value_and_provenance() -> None:
    with pytest.raises(ValidationError, match="require value, basis, and observations"):
        CrossingClaim(
            claim_id="need-1",
            role=CrossingClaimRole.PARTICULAR_NEED,
            state=CrossingEvidenceState.SUPPORTED,
        )


def test_particular_need_cannot_be_versioned_derivation() -> None:
    with pytest.raises(ValidationError, match="derived values belong to transition"):
        _supported_claim(
            "need-1",
            CrossingClaimRole.PARTICULAR_NEED,
            "confidence",
            basis=CrossingClaimBasis.VERSIONED_DERIVATION,
        )


def test_derived_transition_requires_exact_named_rule_inputs() -> None:
    transition = _transition(basis=CrossingClaimBasis.VERSIONED_DERIVATION)
    with pytest.raises(ValidationError, match="inputs must match"):
        TransitionCandidate(
            candidate_id="transition-1",
            ending=transition.ending,
            beginning=transition.beginning,
            basis=CrossingClaimBasis.VERSIONED_DERIVATION,
            derivation=TransitionDerivation(
                input_claim_ids=(transition.beginning.claim_id, transition.ending.claim_id)
            ),
        )


def test_exact_parent_digest_is_required() -> None:
    with pytest.raises(ValidationError, match="digest must match exactly"):
        _request(accepted_objective_sha256="0" * 64)


def test_input_permutations_are_equal_and_serialize_identically_without_mutation() -> None:
    condition_a = _condition("condition-a", "uncertainty before competence")
    condition_z = _condition("condition-z", "identity during change")
    original_conditions = [condition_z, condition_a]
    original_transitions = [_transition("transition-z"), _transition("transition-a")]
    request_one = _request(
        transition_candidates=original_transitions,
        recurring_condition_candidates=original_conditions,
    )
    request_two = _request(
        transition_candidates=tuple(reversed(original_transitions)),
        recurring_condition_candidates=tuple(reversed(original_conditions)),
    )

    artifact_one = CrossingUnderstandingBoundary().understand(
        request_one, artifact_id="crossing-1"
    )
    artifact_two = CrossingUnderstandingBoundary().understand(
        request_two, artifact_id="crossing-1"
    )

    assert artifact_one == artifact_two
    assert serialize_crossing_understanding(artifact_one) == serialize_crossing_understanding(artifact_two)
    assert original_conditions == [condition_z, condition_a]
    assert original_transitions[0].candidate_id == "transition-z"


def test_recurring_condition_is_always_unresolved_and_not_person_applicable() -> None:
    condition = _condition(
        "condition-1", "loss of interest and social withdrawal may orient further listening"
    )
    artifact = CrossingUnderstandingBoundary().understand(
        _request(recurring_condition_candidates=(condition,)), artifact_id="crossing-1"
    )
    retained = artifact.recurring_condition_candidates[0]
    assert retained.outcome == "unresolved_orientation"
    assert retained.applicability_to_person_established is False
    assert retained.person_membership_claimed is False
    assert retained.diagnosis_claimed is False


def test_recurring_condition_cannot_be_marked_resolved_or_applicable() -> None:
    base = _condition("condition-1", "uncertainty before competence").model_dump()
    with pytest.raises(ValidationError):
        RecurringConditionCandidate(**{**base, "outcome": "resolved"})
    with pytest.raises(ValidationError):
        RecurringConditionCandidate(
            **{**base, "applicability_to_person_established": True}
        )


def test_supported_observations_do_not_establish_condition_applicability() -> None:
    condition = _condition("condition-1", "identity after departure")
    assert condition.observations
    assert condition.outcome == "unresolved_orientation"
    assert condition.applicability_to_person_established is False


def test_recurring_condition_is_never_authoritative_for_particular_need() -> None:
    condition = _condition("condition-1", "uncertainty before competence")
    assert condition.authoritative_for_particular_need is False
    with pytest.raises(ValidationError):
        RecurringConditionCandidate(
            **{
                **condition.model_dump(),
                "authoritative_for_particular_need": True,
            }
        )

    with pytest.raises(ValidationError):
        _request(particular_need=condition)


def test_direct_user_condition_statement_remains_orientation_evidence() -> None:
    condition = _condition("condition-1", "I feel like I no longer belong here")
    assert condition.orientation_basis is RecurringConditionOrientationBasis.USER_OBSERVATION
    assert condition.person_membership_claimed is False
    assert condition.diagnosis_claimed is False


def test_classification_like_wording_cannot_acquire_classification_authority() -> None:
    condition = _condition("condition-1", "This person is clinically depressed")
    artifact = CrossingUnderstandingBoundary().understand(
        _request(recurring_condition_candidates=(condition,)), artifact_id="crossing-1"
    )
    retained = artifact.recurring_condition_candidates[0]
    assert retained.pattern == "This person is clinically depressed"
    assert retained.outcome == "unresolved_orientation"
    assert retained.applicability_to_person_established is False
    assert retained.person_membership_claimed is False
    assert retained.diagnosis_claimed is False
    assert artifact.person_classified is False


def test_rule_oriented_condition_requires_exact_versioned_provenance() -> None:
    observation = _observation("evidence-a", "first attempt in an unfamiliar role")
    condition = RecurringConditionCandidate(
        candidate_id="condition-1",
        pattern="uncertainty before competence may orient further listening",
        orientation_basis=RecurringConditionOrientationBasis.VERSIONED_RULE,
        observations=(observation,),
        rule_provenance=RecurringConditionRuleProvenance(
            rule_id="curriculum.orientation",
            rule_version="1.0",
            input_evidence_ids=(observation.evidence_id,),
        ),
    )
    assert condition.applicability_to_person_established is False


def test_serialization_preserves_orientation_only_condition_status() -> None:
    artifact = CrossingUnderstandingBoundary().understand(
        _request(recurring_condition_candidates=(
            _condition("condition-1", "return without reversal"),
        )),
        artifact_id="crossing-1",
    )
    payload = json.loads(serialize_crossing_understanding(artifact))
    condition = payload["recurring_condition_candidates"][0]
    assert condition["outcome"] == "unresolved_orientation"
    assert condition["applicability_to_person_established"] is False
    assert condition["authoritative_for_particular_need"] is False


def test_serialization_is_compact_utf8_schema_order_json() -> None:
    artifact = CrossingUnderstandingBoundary().understand(
        _request(), artifact_id="crossing-1"
    )
    serialized = serialize_crossing_understanding(artifact)

    assert b'": ' not in serialized
    assert b', "' not in serialized
    assert serialized.startswith(b'{"schema_version":"1.0","artifact_kind":"crossing_understanding"')
    assert json.loads(serialized.decode("utf-8"))["resolved_transition_id"] == "transition-1"


def test_crossing_package_has_no_music_pipeline_or_provider_imports() -> None:
    package_root = (
        Path(__file__).parents[1]
        / "src"
        / "playlist_narrative_engine"
        / "crossing_understanding"
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in package_root.glob("*.py"))
    forbidden_imports = (
        "playlist_narrative_engine.candidate_formation",
        "playlist_narrative_engine.journey",
        "playlist_narrative_engine.sequencing",
        "playlist_narrative_engine.evaluation",
        "playlist_narrative_engine.providers",
    )
    assert all(name not in source for name in forbidden_imports)

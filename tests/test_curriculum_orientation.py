from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from objective_safety_helpers import accepted_objective

from playlist_narrative_engine.crossing_understanding import (
    CrossingClaim, CrossingClaimBasis, CrossingClaimRole, CrossingEvidenceObservation,
    CrossingEvidenceState, CrossingUnderstandingBoundary, CrossingUnderstandingRequest,
    DirectionalTransitionRequest, RecurringConditionCandidate,
    RecurringConditionOrientationBasis, serialize_crossing_understanding,
)
from playlist_narrative_engine.curriculum_orientation import (
    APPROVED_ORIENTATION_RULE_SET, APPROVED_ORIENTATION_RULE_SET_SHA256,
    CurriculumOrientationArtifact, CurriculumOrientationBoundary,
    CurriculumOrientationOutcome, CurriculumOrientationRequest,
    OrientationRuleSet, serialize_curriculum_orientation, serialize_orientation_rule_set,
)
from playlist_narrative_engine.evidence_authentication import (
    APPROVED_AUTHENTICATION_RULE_SET, APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    GOVERNED_CHARACTERISTICS, AuthenticationSourceObservation, CharacteristicProposal,
    EvidenceAuthenticationBoundary, EvidenceAuthenticationRequest, ExactConfirmationAttempt,
    ObservationSourceType, ObservationState, ObservationType, confirmation_payload,
    serialize_evidence_authentication,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import serialize_objective_safety_artifact


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _accepted() -> AcceptedObjectiveArtifact:
    return accepted_objective(
        Objective(objective_id="objective-1", statement="I am describing a crossing."),
        artifact_id="safety-1",
    )


def _ea_artifact(definitions=None):
    accepted = _accepted()
    selected = tuple(definitions or GOVERNED_CHARACTERISTICS[:2])
    observations = []
    attempts = []
    for index, definition in enumerate(selected):
        evidence_id = f"evidence-{index}"
        attempt_id = f"authenticated-{index}"
        observations.append(AuthenticationSourceObservation(
            evidence_id=evidence_id, observation_type=ObservationType.USER_CONFIRMATION,
            source_type=ObservationSourceType.USER, source_reference=f"conversation:{evidence_id}",
            state=ObservationState.AVAILABLE, payload_json=confirmation_payload(definition),
        ))
        attempts.append(ExactConfirmationAttempt(
            attempt_id=attempt_id,
            proposal=CharacteristicProposal(
                role=definition.role, characteristic_id=definition.characteristic_id,
                canonical_value_json=definition.canonical_value_json,
            ), confirmation_evidence_id=evidence_id,
        ))
    request = EvidenceAuthenticationRequest(
        request_id="ea-request-1", accepted_objective=accepted,
        accepted_objective_sha256=_sha(serialize_objective_safety_artifact(accepted)),
        observations=observations, attempts=attempts,
        authentication_rule_set=APPROVED_AUTHENTICATION_RULE_SET,
        authentication_rule_set_sha256=APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    )
    return EvidenceAuthenticationBoundary().authenticate(request, artifact_id="ea-1")


def _claim(claim_id: str, role: CrossingClaimRole, value: str) -> CrossingClaim:
    return CrossingClaim(
        claim_id=claim_id, role=role, state=CrossingEvidenceState.SUPPORTED,
        value=value, basis=CrossingClaimBasis.USER_CONFIRMED,
        observations=(CrossingEvidenceObservation(
            evidence_id=f"crossing-{claim_id}", source_type="user_statement",
            source_reference=f"conversation:{claim_id}",
            payload_json=json.dumps(value, separators=(",", ":")),
        ),),
    )


def _parent(*, ending_index: int = 0, beginning_index: int = 1, resolved: bool = True, prior=()):
    accepted = _accepted()
    ea = _ea_artifact(GOVERNED_CHARACTERISTICS)
    request = CrossingUnderstandingRequest(
        request_id="crossing-request-1", accepted_objective=accepted,
        accepted_objective_sha256=_sha(serialize_objective_safety_artifact(accepted)),
        crossing_policy_id="crossing-understanding", crossing_policy_version="2.0",
        evidence_authentication_artifact=ea,
        evidence_authentication_sha256=_sha(serialize_evidence_authentication(ea)),
        lived_evidence=(_claim("event-1", CrossingClaimRole.VISIBLE_EVENT, "a doorway"),),
        directional_transition_requests=() if not resolved else (DirectionalTransitionRequest(
            candidate_id="transition-1",
            ending_authenticated_characteristic_id=f"authenticated-{ending_index}",
            beginning_authenticated_characteristic_id=f"authenticated-{beginning_index}",
        ),),
        recurring_condition_candidates=prior,
        particular_need=_claim("need-1", CrossingClaimRole.PARTICULAR_NEED, "steadiness"),
    )
    return CrossingUnderstandingBoundary().understand(request, artifact_id="crossing-1")


def _request(parent=None, **updates):
    crossing = parent or _parent()
    values = {
        "request_id": "orientation-request-1", "accepted_objective": crossing.accepted_objective,
        "crossing_understanding": crossing,
        "crossing_understanding_sha256": _sha(serialize_crossing_understanding(crossing)),
        "orientation_rule_set": APPROVED_ORIENTATION_RULE_SET,
        "orientation_rule_set_sha256": APPROVED_ORIENTATION_RULE_SET_SHA256,
    }
    values.update(updates)
    return CurriculumOrientationRequest(**values)


@pytest.mark.parametrize("ending_index,beginning_index,condition", (
    (0, 1, "condition.uncertainty_before_competence"),
    (2, 3, "condition.identity_after_departure"),
    (4, 5, "condition.return_without_reversal"),
))
def test_exact_revised_cu1_lineage_orients(ending_index, beginning_index, condition) -> None:
    parent = _parent(ending_index=ending_index, beginning_index=beginning_index)
    artifact = CurriculumOrientationBoundary().orient(_request(parent), artifact_id="orientation-1")
    assert artifact.outcome is CurriculumOrientationOutcome.ORIENTED
    assert artifact.crossing_understanding == parent
    assert artifact.transition_evidence is not None
    assert artifact.candidates[0].condition_id == condition
    assert artifact.candidates[0].input_authenticated_characteristic_ids == (
        f"authenticated-{ending_index}", f"authenticated-{beginning_index}"
    )


def test_cross_pair_has_honest_no_orientation_and_no_fallback() -> None:
    artifact = CurriculumOrientationBoundary().orient(
        _request(_parent(ending_index=0, beginning_index=3)), artifact_id="orientation-1"
    )
    assert artifact.outcome is CurriculumOrientationOutcome.NO_ORIENTATION_SUPPORTED
    assert artifact.candidates == ()
    assert len(artifact.reasons) == 1


def test_unresolved_parent_is_non_failure_clarification() -> None:
    artifact = CurriculumOrientationBoundary().orient(_request(_parent(resolved=False)), artifact_id="orientation-1")
    assert artifact.outcome is CurriculumOrientationOutcome.CLARIFICATION_REQUIRED
    assert artifact.transition_evidence is None
    assert artifact.candidates == ()


def test_old_free_text_authority_paths_are_rejected() -> None:
    payload = _request().model_dump()
    payload["ending_value"] = "established role"
    payload["event"] = "starting school"
    with pytest.raises(ValidationError):
        CurriculumOrientationRequest(**payload)


def test_forged_parent_instance_is_structurally_revalidated() -> None:
    parent = _parent()
    transition = parent.transition_candidates[0]
    forged_ending = transition.ending.model_copy(update={"canonical_value_json": '"forged text"'})
    forged_transition = transition.model_copy(update={"ending": forged_ending})
    forged_parent = parent.model_copy(update={"transition_candidates": (forged_transition,)})
    with pytest.raises(ValidationError):
        _request(
            forged_parent,
            crossing_understanding_sha256=_sha(serialize_crossing_understanding(forged_parent)),
        )


@pytest.mark.parametrize("field", ("rule_id", "candidate_id", "condition_id"))
def test_rule_registry_identity_dimensions_are_unique(field: str) -> None:
    rules = [rule.model_dump() for rule in APPROVED_ORIENTATION_RULE_SET.rules]
    rules[1][field] = rules[0][field]
    with pytest.raises(ValidationError, match="requires unique"):
        OrientationRuleSet(rules=rules)


def test_rule_registry_exact_predicates_are_unique() -> None:
    rules = [rule.model_dump() for rule in APPROVED_ORIENTATION_RULE_SET.rules]
    rules[1]["ending_predicate"] = rules[0]["ending_predicate"]
    rules[1]["beginning_predicate"] = rules[0]["beginning_predicate"]
    with pytest.raises(ValidationError, match="unique exact predicates"):
        OrientationRuleSet(rules=rules)


def test_rule_set_digest_is_stable_and_mismatch_is_rejected() -> None:
    reversed_set = OrientationRuleSet(rules=tuple(reversed(APPROVED_ORIENTATION_RULE_SET.rules)))
    assert reversed_set == APPROVED_ORIENTATION_RULE_SET
    assert _sha(serialize_orientation_rule_set(reversed_set)) == APPROVED_ORIENTATION_RULE_SET_SHA256
    with pytest.raises(ValidationError, match="digest must match"):
        _request(orientation_rule_set_sha256="0" * 64)


def test_rule_change_with_same_identity_and_version_is_rejected() -> None:
    rules = [rule.model_dump() for rule in APPROVED_ORIENTATION_RULE_SET.rules]
    rules[0]["pattern"] = "changed body of knowledge"
    changed = OrientationRuleSet(rules=rules)
    with pytest.raises(ValidationError, match="complete approved"):
        _request(orientation_rule_set=changed, orientation_rule_set_sha256=_sha(serialize_orientation_rule_set(changed)))


def test_forbidden_parent_fields_are_blind_to_execution() -> None:
    base = _parent()
    changed = base.model_copy(update={
        "lived_evidence": (_claim("event-2", CrossingClaimRole.METAPHOR, "entirely different metaphor"),),
        "particular_need": None,
    })
    first = CurriculumOrientationBoundary().orient(_request(base), artifact_id="orientation-1")
    second = CurriculumOrientationBoundary().orient(_request(changed), artifact_id="orientation-1")
    assert first.transition_evidence == second.transition_evidence
    assert first.candidates == second.candidates
    assert first.outcome == second.outcome


def test_prior_candidates_cannot_bootstrap_orientation() -> None:
    observation = CrossingEvidenceObservation(
        evidence_id="prior-evidence", source_type="user_statement",
        source_reference="conversation:prior", payload_json='"uncertainty before competence"',
    )
    prior = RecurringConditionCandidate(
        candidate_id="prior-condition", pattern="uncertainty before competence",
        orientation_basis=RecurringConditionOrientationBasis.USER_OBSERVATION,
        observations=(observation,),
    )
    # A cross-pair remains unmatched even when the parent carries the exact
    # condition text that another rule would produce.
    parent = _parent(ending_index=0, beginning_index=3, prior=(prior,))
    assert parent.recurring_condition_candidates == (prior,)
    artifact = CurriculumOrientationBoundary().orient(_request(parent), artifact_id="orientation-1")
    assert artifact.outcome is CurriculumOrientationOutcome.NO_ORIENTATION_SUPPORTED


def test_candidates_are_structurally_orientation_only() -> None:
    candidate = CurriculumOrientationBoundary().orient(_request(), artifact_id="orientation-1").candidates[0]
    assert candidate.outcome == "unresolved_orientation"
    assert candidate.applicability_to_person_established is False
    assert candidate.person_membership_claimed is False
    assert candidate.diagnosis_claimed is False
    assert candidate.authoritative_for_particular_need is False
    assert candidate.accompaniment_inferred is False


def test_artifact_recomputes_candidates_and_rejects_tampering() -> None:
    artifact = CurriculumOrientationBoundary().orient(_request(), artifact_id="orientation-1")
    payload = artifact.model_dump()
    payload["candidates"][0]["pattern"] = "invented interpretation"
    with pytest.raises(ValidationError, match="exactly derived"):
        CurriculumOrientationArtifact(**payload)


def test_deterministic_order_and_canonical_bytes_do_not_mutate_inputs() -> None:
    rules = list(reversed(APPROVED_ORIENTATION_RULE_SET.rules))
    rule_set = OrientationRuleSet(rules=rules)
    request = _request(orientation_rule_set=rule_set, orientation_rule_set_sha256=_sha(serialize_orientation_rule_set(rule_set)))
    one = CurriculumOrientationBoundary().orient(request, artifact_id="orientation-1")
    two = CurriculumOrientationBoundary().orient(_request(), artifact_id="orientation-1")
    assert one == two
    assert serialize_curriculum_orientation(one) == serialize_curriculum_orientation(two)
    assert rules[0] == APPROVED_ORIENTATION_RULE_SET.rules[-1]


def test_structural_isolation_and_forbidden_input_blindness() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "curriculum_orientation"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    for forbidden_field in ("lived_evidence", "particular_need", "recurring_condition_candidates", "payload_json", ".observations"):
        assert forbidden_field not in (Path(root / "boundary.py").read_text(encoding="utf-8"))
    for forbidden_import in ("journey", "candidate_formation", "sequencing", "evaluation", "providers", "experience_explanation"):
        assert f"playlist_narrative_engine.{forbidden_import}" not in source

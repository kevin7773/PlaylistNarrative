from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from objective_safety_helpers import accepted_objective

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
    DirectionalTransitionRequest,
    serialize_crossing_understanding,
)
from playlist_narrative_engine.evidence_authentication import (
    APPROVED_AUTHENTICATION_RULE_SET,
    APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    GOVERNED_CHARACTERISTICS,
    AuthenticationSourceObservation,
    CharacteristicProposal,
    CharacteristicRole,
    EvidenceAuthenticationBoundary,
    EvidenceAuthenticationRequest,
    ExactConfirmationAttempt,
    ObservationSourceType,
    ObservationState,
    ObservationType,
    confirmation_payload,
    serialize_evidence_authentication,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import serialize_objective_safety_artifact


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _accepted() -> AcceptedObjectiveArtifact:
    return accepted_objective(
        Objective(objective_id="objective-1", statement="I am beginning an unfamiliar role."),
        artifact_id="safety-1",
    )


def _definition(role: CharacteristicRole):
    characteristic_id = "role.established" if role is CharacteristicRole.ENDING else "role.unproven"
    return next(item for item in GOVERNED_CHARACTERISTICS if item.role is role and item.characteristic_id == characteristic_id)


def _ea_artifact(*, reverse: bool = False):
    accepted = _accepted()
    definitions = (_definition(CharacteristicRole.ENDING), _definition(CharacteristicRole.BEGINNING))
    observations = []
    attempts = []
    for index, definition in enumerate(definitions, 1):
        evidence_id = f"confirmation-{index}"
        attempt_id = "authenticated-ending" if definition.role is CharacteristicRole.ENDING else "authenticated-beginning"
        observations.append(AuthenticationSourceObservation(
            evidence_id=evidence_id,
            observation_type=ObservationType.USER_CONFIRMATION,
            source_type=ObservationSourceType.USER,
            source_reference=f"conversation:{evidence_id}",
            state=ObservationState.AVAILABLE,
            payload_json=confirmation_payload(definition),
        ))
        attempts.append(ExactConfirmationAttempt(
            attempt_id=attempt_id,
            proposal=CharacteristicProposal(
                role=definition.role,
                characteristic_id=definition.characteristic_id,
                canonical_value_json=definition.canonical_value_json,
            ),
            confirmation_evidence_id=evidence_id,
        ))
    if reverse:
        observations.reverse()
        attempts.reverse()
    request = EvidenceAuthenticationRequest(
        request_id="ea-request-1",
        accepted_objective=accepted,
        accepted_objective_sha256=_sha(serialize_objective_safety_artifact(accepted)),
        observations=observations,
        attempts=attempts,
        authentication_rule_set=APPROVED_AUTHENTICATION_RULE_SET,
        authentication_rule_set_sha256=APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    )
    return EvidenceAuthenticationBoundary().authenticate(request, artifact_id="ea-artifact-1")


def _observation(evidence_id: str, value: str) -> CrossingEvidenceObservation:
    return CrossingEvidenceObservation(
        evidence_id=evidence_id,
        source_type="user_statement",
        source_reference=f"conversation:{evidence_id}",
        payload_json=json.dumps(value, ensure_ascii=False, separators=(",", ":")),
    )


def _claim(claim_id: str, role: CrossingClaimRole, value: str) -> CrossingClaim:
    return CrossingClaim(
        claim_id=claim_id,
        role=role,
        state=CrossingEvidenceState.SUPPORTED,
        value=value,
        basis=CrossingClaimBasis.USER_CONFIRMED,
        observations=(_observation(f"evidence-{claim_id}", value),),
    )


def _request(**updates: object) -> CrossingUnderstandingRequest:
    accepted = _accepted()
    parent = _ea_artifact()
    values: dict[str, object] = {
        "request_id": "crossing-request-1",
        "accepted_objective": accepted,
        "accepted_objective_sha256": _sha(serialize_objective_safety_artifact(accepted)),
        "crossing_policy_id": "crossing-understanding",
        "crossing_policy_version": "2.0",
        "evidence_authentication_artifact": parent,
        "evidence_authentication_sha256": _sha(serialize_evidence_authentication(parent)),
        "lived_evidence": (_claim("event-1", CrossingClaimRole.VISIBLE_EVENT, "starting a new job"),),
        "directional_transition_requests": (DirectionalTransitionRequest(
            candidate_id="transition-1",
            ending_authenticated_characteristic_id="authenticated-ending",
            beginning_authenticated_characteristic_id="authenticated-beginning",
        ),),
        "particular_need": _claim("need-1", CrossingClaimRole.PARTICULAR_NEED, "steadiness while learning"),
    }
    values.update(updates)
    return CrossingUnderstandingRequest(**values)


def test_cu1_derives_crossing_only_from_exact_authenticated_characteristics() -> None:
    artifact = CrossingUnderstandingBoundary().understand(_request(), artifact_id="crossing-1")
    transition = artifact.transition_candidates[0]
    assert artifact.outcome is CrossingUnderstandingOutcome.UNDERSTOOD
    assert transition.ending.authenticated_characteristic_id == "authenticated-ending"
    assert transition.beginning.authenticated_characteristic_id == "authenticated-beginning"
    assert transition.derivation.input_authenticated_characteristic_ids == (
        "authenticated-ending", "authenticated-beginning"
    )
    assert transition.ending in artifact.evidence_authentication_artifact.content.authenticated_characteristics


def test_legacy_free_text_transition_input_has_no_compatibility_path() -> None:
    payload = _request().model_dump()
    payload.pop("directional_transition_requests")
    payload["transition_candidates"] = ({"candidate_id": "legacy", "ending": "free text", "beginning": "free text"},)
    with pytest.raises(ValidationError):
        CrossingUnderstandingRequest(**payload)


@pytest.mark.parametrize("field,value", (
    ("ending_authenticated_characteristic_id", "authenticated-beginning"),
    ("beginning_authenticated_characteristic_id", "authenticated-ending"),
    ("ending_authenticated_characteristic_id", " authenticated-ending"),
    ("beginning_authenticated_characteristic_id", "AUTHENTICATED-BEGINNING"),
))
def test_identity_and_role_correspondence_fail_closed(field: str, value: str) -> None:
    data = {
        "candidate_id": "transition-1",
        "ending_authenticated_characteristic_id": "authenticated-ending",
        "beginning_authenticated_characteristic_id": "authenticated-beginning",
        field: value,
    }
    with pytest.raises(ValidationError):
        _request(directional_transition_requests=(DirectionalTransitionRequest(**data),))


def test_withheld_attempt_cannot_be_used_as_crossing_input() -> None:
    with pytest.raises(ValidationError, match="authenticated characteristics"):
        _request(directional_transition_requests=(DirectionalTransitionRequest(
            candidate_id="transition-1",
            ending_authenticated_characteristic_id="not-authenticated",
            beginning_authenticated_characteristic_id="authenticated-beginning",
        ),))


def test_exact_parent_digest_and_objective_lineage_are_required() -> None:
    with pytest.raises(ValidationError, match="Evidence Authentication artifact digest"):
        _request(evidence_authentication_sha256="0" * 64)
    other = accepted_objective(
        Objective(
            objective_id="objective-1",
            statement="I am beginning an unfamiliar role.",
        ),
        artifact_id="safety-other",
    )
    with pytest.raises(ValidationError, match="objective lineage"):
        _request(
            accepted_objective=other,
            accepted_objective_sha256=_sha(serialize_objective_safety_artifact(other)),
        )


def test_missing_transition_requires_clarification_without_interpreting_need() -> None:
    artifact = CrossingUnderstandingBoundary().understand(
        _request(directional_transition_requests=(), particular_need=None), artifact_id="crossing-1"
    )
    assert tuple(reason.code for reason in artifact.clarification_reasons) == (
        CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE,
        CrossingClarificationReasonCode.TRANSITION_BEGINNING_UNAVAILABLE,
    )


def test_lived_evidence_and_need_are_preserved_but_do_not_control_crossing() -> None:
    unavailable_event = CrossingClaim(
        claim_id="event-unknown",
        role=CrossingClaimRole.VISIBLE_EVENT,
        state=CrossingEvidenceState.UNAVAILABLE,
    )
    artifact = CrossingUnderstandingBoundary().understand(
        _request(lived_evidence=(unavailable_event,), particular_need=None),
        artifact_id="crossing-1",
    )
    assert artifact.outcome is CrossingUnderstandingOutcome.UNDERSTOOD
    assert artifact.resolved_transition_id == "transition-1"
    assert artifact.lived_evidence == (unavailable_event,)
    assert artifact.particular_need is None
    assert artifact.clarification_reasons == ()


def test_artifact_cannot_claim_clarification_from_preserved_evidence() -> None:
    artifact = CrossingUnderstandingBoundary().understand(_request(), artifact_id="crossing-1")
    payload = artifact.model_dump()
    payload["clarification_required"] = True
    payload["outcome"] = CrossingUnderstandingOutcome.CLARIFICATION_REQUIRED
    payload["resolved_transition_id"] = None
    payload["clarification_reasons"] = ({
        "code": CrossingClarificationReasonCode.TRANSITION_ENDING_UNAVAILABLE,
        "field_path": "lived_evidence",
        "explanation": "What is ending or changing is unavailable.",
    },)
    from playlist_narrative_engine.crossing_understanding import CrossingUnderstandingArtifact
    with pytest.raises(ValidationError, match="exactly derivable"):
        CrossingUnderstandingArtifact(**payload)


def test_multiple_authenticated_crossings_remain_unresolved() -> None:
    requests = (
        DirectionalTransitionRequest(candidate_id="transition-z", ending_authenticated_characteristic_id="authenticated-ending", beginning_authenticated_characteristic_id="authenticated-beginning"),
        DirectionalTransitionRequest(candidate_id="transition-a", ending_authenticated_characteristic_id="authenticated-ending", beginning_authenticated_characteristic_id="authenticated-beginning"),
    )
    artifact = CrossingUnderstandingBoundary().understand(_request(directional_transition_requests=requests), artifact_id="crossing-1")
    assert tuple(item.candidate_id for item in artifact.transition_candidates) == ("transition-a", "transition-z")
    assert artifact.resolved_transition_id is None
    assert artifact.clarification_reasons[-1].code is CrossingClarificationReasonCode.MULTIPLE_TRANSITIONS_PLAUSIBLE


def test_equivalent_input_order_is_byte_identical_without_mutation() -> None:
    parent_one = _ea_artifact(reverse=False)
    parent_two = _ea_artifact(reverse=True)
    request_one = _request(evidence_authentication_artifact=parent_one, evidence_authentication_sha256=_sha(serialize_evidence_authentication(parent_one)))
    request_two = _request(evidence_authentication_artifact=parent_two, evidence_authentication_sha256=_sha(serialize_evidence_authentication(parent_two)))
    artifact_one = CrossingUnderstandingBoundary().understand(request_one, artifact_id="crossing-1")
    artifact_two = CrossingUnderstandingBoundary().understand(request_two, artifact_id="crossing-1")
    assert artifact_one == artifact_two
    assert serialize_crossing_understanding(artifact_one) == serialize_crossing_understanding(artifact_two)


def test_serialization_preserves_parent_and_schema_version() -> None:
    payload = json.loads(serialize_crossing_understanding(CrossingUnderstandingBoundary().understand(_request(), artifact_id="crossing-1")))
    assert payload["schema_version"] == "2.0"
    assert payload["evidence_authentication_artifact"]["content"]["artifact_id"] == "ea-artifact-1"
    assert payload["transition_candidates"][0]["ending"]["characteristic_id"] == "role.established"


def test_cu1_retains_non_claims() -> None:
    artifact = CrossingUnderstandingBoundary().understand(_request(), artifact_id="crossing-1")
    assert artifact.person_classified is False
    assert artifact.particular_need_inferred_from_curriculum is False
    assert artifact.accompaniment_selected is False
    assert artifact.music_selected is False


def test_package_has_no_legacy_transition_authentication_or_downstream_imports() -> None:
    root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine" / "crossing_understanding"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "transition_candidates: tuple[TransitionCandidate" in source
    assert "directional_transition_requests: tuple[DirectionalTransitionRequest" in source
    assert "input_claim_ids" not in source
    for forbidden in ("curriculum_orientation", "candidate_formation", "journey", "providers"):
        assert f"playlist_narrative_engine.{forbidden}" not in source

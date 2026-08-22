from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import pytest
from pydantic import ValidationError

from objective_safety_helpers import accepted_objective

from playlist_narrative_engine.evidence_authentication import (
    APPROVED_AUTHENTICATION_RULE_SET,
    APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    GOVERNED_CHARACTERISTICS,
    AuthenticationMethod,
    AuthenticationReasonCode,
    AuthenticationRuleSet,
    AuthenticationSourceObservation,
    AuthenticatedStructuredCharacteristic,
    AuthenticatedStructuredCharacteristicArtifact,
    CharacteristicProposal,
    CharacteristicRole,
    EvidenceAuthenticationBoundary,
    EvidenceAuthenticationRequest,
    ExactConfirmationAttempt,
    ObservationSourceType,
    ObservationState,
    ObservationType,
    RuleInputRequirement,
    VersionedDerivationAttempt,
    canonicalize_json_value,
    confirmation_payload,
    serialize_authentication_artifact_content,
    serialize_authentication_rule_set,
    serialize_evidence_authentication,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.objective_safety.serialization import (
    serialize_objective_safety_artifact,
)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _accepted_objective(
    *, statement: str = "I am describing evidence of a life transition."
) -> AcceptedObjectiveArtifact:
    return accepted_objective(
        Objective(objective_id="objective-1", statement=statement),
        artifact_id="safety-1",
    )


def _definition(
    characteristic_id: str = "role.established",
    role: CharacteristicRole = CharacteristicRole.ENDING,
):
    return next(
        item
        for item in GOVERNED_CHARACTERISTICS
        if item.characteristic_id == characteristic_id and item.role is role
    )


def _proposal(definition=None) -> CharacteristicProposal:
    value = definition or _definition()
    return CharacteristicProposal(
        role=value.role,
        characteristic_id=value.characteristic_id,
        canonical_value_json=value.canonical_value_json,
    )


def _confirmation_observation(
    definition=None,
    *,
    evidence_id: str = "confirmation-1",
    payload_json: str | None = None,
    observation_type: ObservationType = ObservationType.USER_CONFIRMATION,
    source_type: ObservationSourceType = ObservationSourceType.USER,
    state: ObservationState = ObservationState.AVAILABLE,
) -> AuthenticationSourceObservation:
    value = definition or _definition()
    payload = confirmation_payload(value) if payload_json is None else payload_json
    return AuthenticationSourceObservation(
        evidence_id=evidence_id,
        observation_type=observation_type,
        source_type=source_type,
        source_reference=f"conversation:{evidence_id}",
        state=state,
        payload_json=payload if state is ObservationState.AVAILABLE else None,
    )


def _confirmation_attempt(
    definition=None,
    *,
    attempt_id: str = "attempt-confirmation-1",
    evidence_id: str = "confirmation-1",
) -> ExactConfirmationAttempt:
    return ExactConfirmationAttempt(
        attempt_id=attempt_id,
        proposal=_proposal(definition),
        confirmation_evidence_id=evidence_id,
    )


def _rule(rule_id: str = "ea1.derive_role_established"):
    return next(
        item for item in APPROVED_AUTHENTICATION_RULE_SET.rules if item.rule_id == rule_id
    )


def _derivation_observation(
    rule=None,
    *,
    evidence_id: str = "fact-1",
    state: ObservationState = ObservationState.AVAILABLE,
    payload_json: str | None = None,
) -> AuthenticationSourceObservation:
    value = rule or _rule()
    requirement = value.input_requirements[0]
    payload = requirement.payload_json if payload_json is None else payload_json
    return AuthenticationSourceObservation(
        evidence_id=evidence_id,
        observation_type=requirement.observation_type,
        source_type=requirement.source_type,
        source_reference=f"validated:{evidence_id}",
        state=state,
        payload_json=payload if state is ObservationState.AVAILABLE else None,
    )


def _derivation_attempt(
    rule=None,
    *,
    attempt_id: str = "attempt-derivation-1",
    evidence_id: str = "fact-1",
    rule_id: str | None = None,
    rule_version: str | None = None,
    proposal: CharacteristicProposal | None = None,
) -> VersionedDerivationAttempt:
    value = rule or _rule()
    return VersionedDerivationAttempt(
        attempt_id=attempt_id,
        proposal=proposal or _proposal(value.output),
        rule_id=rule_id or value.rule_id,
        rule_version=rule_version or value.rule_version,
        input_evidence_ids=(evidence_id,),
    )


def _request(
    observations=None,
    attempts=None,
    **updates: object,
) -> EvidenceAuthenticationRequest:
    accepted = _accepted_objective()
    values: dict[str, object] = {
        "request_id": "authentication-request-1",
        "accepted_objective": accepted,
        "accepted_objective_sha256": _sha256(
            serialize_objective_safety_artifact(accepted)
        ),
        "observations": observations or (_confirmation_observation(),),
        "attempts": attempts or (_confirmation_attempt(),),
        "authentication_rule_set": APPROVED_AUTHENTICATION_RULE_SET,
        "authentication_rule_set_sha256": APPROVED_AUTHENTICATION_RULE_SET_SHA256,
    }
    values.update(updates)
    return EvidenceAuthenticationRequest(**values)


def _authenticate(request=None):
    return EvidenceAuthenticationBoundary().authenticate(
        request or _request(), artifact_id="authentication-1"
    )


def test_exact_user_confirmation_mints_governed_characteristic() -> None:
    artifact = _authenticate()
    content = artifact.content

    assert content.summary.attempt_count == 1
    assert content.summary.authenticated_count == 1
    assert content.summary.withheld_count == 0
    assert content.withheld_authentication_attempts == ()
    characteristic = content.authenticated_characteristics[0]
    assert characteristic.characteristic_id == "role.established"
    assert characteristic.canonical_value_json == canonicalize_json_value(
        "established role"
    )
    assert characteristic.authentication_method is AuthenticationMethod.EXACT_USER_CONFIRMATION
    assert characteristic.source_observations == content.source_observations


@pytest.mark.parametrize(
    "changed_value",
    (
        "Established role",
        "established role.",
        " established role",
        unicodedata.normalize("NFD", "establishéd role"),
    ),
)
def test_confirmation_requires_exact_typed_value_reproduction(
    changed_value: str,
) -> None:
    definition = _definition()
    mismatched_payload = canonicalize_json_value(
        {
            "characteristic_id": definition.characteristic_id,
            "role": definition.role.value,
            "value": changed_value,
            "value_schema_id": "penny.crossing_characteristic",
            "value_schema_version": "1.0",
        }
    )
    artifact = _authenticate(
        _request(observations=(_confirmation_observation(payload_json=mismatched_payload),))
    )
    withheld = artifact.content.withheld_authentication_attempts[0]
    assert tuple(reason.code for reason in withheld.reasons) == (
        AuthenticationReasonCode.CONFIRMATION_VALUE_MISMATCH,
    )


@pytest.mark.parametrize(
    ("observation_type", "source_type"),
    (
        (ObservationType.GENERIC_STATEMENT, ObservationSourceType.USER),
        (ObservationType.USER_CONFIRMATION, ObservationSourceType.VALIDATED_RECORD),
    ),
)
def test_generic_or_mislabeled_evidence_cannot_masquerade_as_confirmation(
    observation_type: ObservationType,
    source_type: ObservationSourceType,
) -> None:
    observation = _confirmation_observation(
        observation_type=observation_type,
        source_type=source_type,
    )
    artifact = _authenticate(_request(observations=(observation,)))
    reasons = artifact.content.withheld_authentication_attempts[0].reasons
    assert tuple(reason.code for reason in reasons) == (
        AuthenticationReasonCode.CONFIRMATION_TYPE_NOT_AUTHORIZED,
    )


def test_unsupported_characteristic_is_withheld_not_authenticated() -> None:
    proposal = CharacteristicProposal(
        role=CharacteristicRole.ENDING,
        characteristic_id="person.confident",
        canonical_value_json=canonicalize_json_value("confident person"),
    )
    attempt = ExactConfirmationAttempt(
        attempt_id="unsupported-attempt",
        proposal=proposal,
        confirmation_evidence_id="confirmation-1",
    )
    artifact = _authenticate(_request(attempts=(attempt,)))
    codes = tuple(
        reason.code
        for reason in artifact.content.withheld_authentication_attempts[0].reasons
    )
    assert codes == (
        AuthenticationReasonCode.CONFIRMATION_VALUE_MISMATCH,
        AuthenticationReasonCode.CHARACTERISTIC_SCHEMA_UNSUPPORTED,
    )


@pytest.mark.parametrize("rule", APPROVED_AUTHENTICATION_RULE_SET.rules)
def test_each_approved_versioned_rule_reexecutes_exact_inputs(rule) -> None:
    observation = _derivation_observation(rule)
    attempt = _derivation_attempt(rule)
    artifact = _authenticate(
        _request(observations=(observation,), attempts=(attempt,))
    )

    characteristic = artifact.content.authenticated_characteristics[0]
    assert characteristic.characteristic_id == rule.output.characteristic_id
    assert characteristic.role is rule.output.role
    assert characteristic.canonical_value_json == rule.output.canonical_value_json
    assert characteristic.authentication_method is AuthenticationMethod.VERSIONED_DERIVATION
    assert characteristic.lineage.rule_id == rule.rule_id
    assert characteristic.lineage.rule_version == rule.rule_version
    assert characteristic.lineage.rule_set_sha256 == APPROVED_AUTHENTICATION_RULE_SET_SHA256


def test_unknown_rule_and_missing_input_retain_all_applicable_reasons() -> None:
    attempt = _derivation_attempt(
        rule_id="ea1.unknown",
        evidence_id="missing-evidence",
    )
    artifact = _authenticate(
        _request(observations=(_confirmation_observation(),), attempts=(attempt,))
    )
    codes = tuple(
        reason.code
        for reason in artifact.content.withheld_authentication_attempts[0].reasons
    )
    assert codes == (
        AuthenticationReasonCode.DERIVATION_RULE_NOT_APPROVED,
        AuthenticationReasonCode.DERIVATION_INPUT_UNAVAILABLE,
    )


def test_wrong_rule_version_is_distinct() -> None:
    observation = _derivation_observation()
    attempt = _derivation_attempt(rule_version="2.0")
    artifact = _authenticate(
        _request(observations=(observation,), attempts=(attempt,))
    )
    assert artifact.content.withheld_authentication_attempts[0].reasons[0].code is (
        AuthenticationReasonCode.DERIVATION_RULE_VERSION_UNSUPPORTED
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    (
        (ObservationState.UNAVAILABLE, AuthenticationReasonCode.DERIVATION_INPUT_UNAVAILABLE),
        (ObservationState.UNSUPPORTED, AuthenticationReasonCode.DERIVATION_INPUT_UNSUPPORTED),
        (ObservationState.CONFLICTING, AuthenticationReasonCode.DERIVATION_INPUT_CONFLICTING),
    ),
)
def test_derivation_input_states_remain_distinct(
    state: ObservationState,
    expected: AuthenticationReasonCode,
) -> None:
    observation = _derivation_observation(state=state)
    artifact = _authenticate(
        _request(
            observations=(observation,),
            attempts=(_derivation_attempt(),),
        )
    )
    assert artifact.content.withheld_authentication_attempts[0].reasons[0].code is expected


def test_derivation_input_mismatch_is_not_interpreted() -> None:
    observation = _derivation_observation(
        payload_json=canonicalize_json_value(
            {"fact_id": "role_status", "value": "similar-but-not-exact"}
        )
    )
    artifact = _authenticate(
        _request(observations=(observation,), attempts=(_derivation_attempt(),))
    )
    assert artifact.content.withheld_authentication_attempts[0].reasons[0].code is (
        AuthenticationReasonCode.DERIVATION_INPUT_MISMATCH
    )


def test_derivation_output_mismatch_is_withheld() -> None:
    wrong_output = _definition("role.unproven", CharacteristicRole.BEGINNING)
    attempt = _derivation_attempt(proposal=_proposal(wrong_output))
    artifact = _authenticate(
        _request(
            observations=(_derivation_observation(),),
            attempts=(attempt,),
        )
    )
    assert artifact.content.withheld_authentication_attempts[0].reasons[0].code is (
        AuthenticationReasonCode.DERIVATION_OUTPUT_MISMATCH
    )


def test_complete_partition_accounts_for_every_attempt_once() -> None:
    confirmation = _confirmation_observation()
    fact = _derivation_observation(evidence_id="fact-mismatch", payload_json=canonicalize_json_value({"wrong": True}))
    attempts = (
        _confirmation_attempt(),
        _derivation_attempt(attempt_id="attempt-withheld", evidence_id="fact-mismatch"),
    )
    artifact = _authenticate(
        _request(observations=(fact, confirmation), attempts=attempts)
    )
    content = artifact.content
    assert content.summary.attempt_count == 2
    assert content.summary.authenticated_count == 1
    assert content.summary.withheld_count == 1
    partition_ids = {
        *(item.attempt_id for item in content.authenticated_characteristics),
        *(item.attempt_id for item in content.withheld_authentication_attempts),
    }
    assert partition_ids == {item.attempt_id for item in attempts}


def test_artifact_rejects_incomplete_withholding_reasons() -> None:
    attempt = _derivation_attempt(
        rule_id="ea1.unknown",
        evidence_id="missing-evidence",
    )
    artifact = _authenticate(
        _request(observations=(_confirmation_observation(),), attempts=(attempt,))
    )
    content_payload = artifact.content.model_dump()
    withheld = content_payload["withheld_authentication_attempts"][0]
    withheld["reasons"] = withheld["reasons"][:1]
    with pytest.raises(ValidationError, match="complete and exact"):
        type(artifact.content)(**content_payload)


def test_request_authority_correspondence_is_exact() -> None:
    with pytest.raises(ValidationError, match="accepted-objective"):
        _request(accepted_objective_sha256="0" * 64)
    with pytest.raises(ValidationError, match="rule-set digest"):
        _request(authentication_rule_set_sha256="0" * 64)
    different = _accepted_objective(statement="Different objective.")
    with pytest.raises(ValidationError, match="accepted-objective"):
        _request(accepted_objective=different)


def test_rule_set_enforces_unique_rule_identity() -> None:
    rule = APPROVED_AUTHENTICATION_RULE_SET.rules[0]
    with pytest.raises(ValidationError, match="rule identities must be unique"):
        AuthenticationRuleSet(rules=(rule, rule))


def test_rule_set_enforces_unique_output_grants() -> None:
    rule = APPROVED_AUTHENTICATION_RULE_SET.rules[0]
    changed = rule.model_copy(
        update={
            "rule_id": "ea1.different_rule",
            "input_requirements": (
                RuleInputRequirement(
                    observation_type=ObservationType.STRUCTURED_FACT,
                    source_type=ObservationSourceType.VALIDATED_RECORD,
                    payload_json=canonicalize_json_value(
                        {"fact_id": "different", "value": "different"}
                    ),
                ),
            ),
        }
    )
    with pytest.raises(ValidationError, match="output grants"):
        AuthenticationRuleSet(rules=(rule, changed))


def test_rule_set_enforces_unique_input_contracts() -> None:
    first, second = APPROVED_AUTHENTICATION_RULE_SET.rules[:2]
    changed = second.model_copy(update={"input_requirements": first.input_requirements})
    with pytest.raises(ValidationError, match="input contracts"):
        AuthenticationRuleSet(rules=(first, changed))


def test_rule_set_digest_is_order_stable_and_changes_with_substance() -> None:
    reversed_rule_set = AuthenticationRuleSet(
        rules=tuple(reversed(APPROVED_AUTHENTICATION_RULE_SET.rules))
    )
    assert reversed_rule_set == APPROVED_AUTHENTICATION_RULE_SET
    assert _sha256(serialize_authentication_rule_set(reversed_rule_set)) == (
        APPROVED_AUTHENTICATION_RULE_SET_SHA256
    )

    first = APPROVED_AUTHENTICATION_RULE_SET.rules[0]
    changed_requirement = RuleInputRequirement(
        observation_type=ObservationType.STRUCTURED_FACT,
        source_type=ObservationSourceType.VALIDATED_RECORD,
        payload_json=canonicalize_json_value(
            {"fact_id": "role_status", "value": "changed"}
        ),
    )
    changed_rule = first.model_copy(
        update={"input_requirements": (changed_requirement,)}
    )
    changed_rule_set = AuthenticationRuleSet(
        rules=(changed_rule, *APPROVED_AUTHENTICATION_RULE_SET.rules[1:])
    )
    assert _sha256(serialize_authentication_rule_set(changed_rule_set)) != (
        APPROVED_AUTHENTICATION_RULE_SET_SHA256
    )
    with pytest.raises(ValidationError, match="exact approved"):
        _request(
            authentication_rule_set=changed_rule_set,
            authentication_rule_set_sha256=_sha256(
                serialize_authentication_rule_set(changed_rule_set)
            ),
        )


def test_provenance_reproduces_exact_source_and_rule_lineage() -> None:
    rule = _rule()
    observation = _derivation_observation(rule)
    artifact = _authenticate(
        _request(
            observations=(observation,),
            attempts=(_derivation_attempt(rule),),
        )
    )
    characteristic = artifact.content.authenticated_characteristics[0]
    assert characteristic.source_observations == (observation,)
    assert characteristic.lineage.input_evidence_ids == (observation.evidence_id,)
    assert characteristic.lineage.rule_id == rule.rule_id
    assert characteristic.lineage.rule_set_sha256 == (
        artifact.content.authentication_rule_set_sha256
    )


def test_artifact_content_digest_verifies_canonical_content_bytes() -> None:
    artifact = _authenticate()
    assert artifact.artifact_content_sha256 == _sha256(
        serialize_authentication_artifact_content(artifact.content)
    )
    with pytest.raises(ValidationError, match="content digest"):
        AuthenticatedStructuredCharacteristicArtifact(
            content=artifact.content,
            artifact_content_sha256="0" * 64,
        )


def test_equivalent_input_permutations_are_byte_identical_without_mutation() -> None:
    confirmation = _confirmation_observation()
    fact = _derivation_observation(evidence_id="fact-1")
    confirmation_attempt = _confirmation_attempt()
    derivation_attempt = _derivation_attempt(
        attempt_id="attempt-derivation-1", evidence_id="fact-1"
    )
    caller_observations = [fact, confirmation]
    caller_attempts = [derivation_attempt, confirmation_attempt]
    first = _authenticate(
        _request(observations=caller_observations, attempts=caller_attempts)
    )
    second = _authenticate(
        _request(
            observations=tuple(reversed(caller_observations)),
            attempts=tuple(reversed(caller_attempts)),
        )
    )

    assert first == second
    assert serialize_evidence_authentication(first) == serialize_evidence_authentication(second)
    assert caller_observations == [fact, confirmation]
    assert caller_attempts == [derivation_attempt, confirmation_attempt]


def test_canonical_serialization_is_compact_schema_order_utf8() -> None:
    artifact = _authenticate()
    serialized = serialize_evidence_authentication(artifact)
    assert b'": ' not in serialized
    assert b', "' not in serialized
    assert serialized.startswith(b'{"content":{"schema_version":"1.0"')
    assert json.loads(serialized.decode("utf-8"))["artifact_content_sha256"] == (
        artifact.artifact_content_sha256
    )


def test_explicit_non_claims_are_literal_false() -> None:
    content = _authenticate().content
    false_fields = (
        "crossing_inferred",
        "recurring_condition_inferred",
        "person_classified",
        "person_diagnosed",
        "particular_need_inferred",
        "particular_need_confirmed",
        "particular_need_modified",
        "clarification_performed",
        "accompaniment_inferred",
        "explanation_generated",
        "journey_planning_performed",
        "provider_accessed",
        "music_inspected",
        "music_formed",
        "music_scored",
        "music_ranked",
        "music_selected",
        "music_sequenced",
    )
    assert all(getattr(content, field) is False for field in false_fields)


def test_ea1_is_structurally_isolated_from_cognitive_and_music_layers() -> None:
    package_root = (
        Path(__file__).parents[1]
        / "src"
        / "playlist_narrative_engine"
        / "evidence_authentication"
    )
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in package_root.glob("*.py")
    )
    forbidden_imports = (
        "playlist_narrative_engine.crossing_understanding",
        "playlist_narrative_engine.curriculum_orientation",
        "playlist_narrative_engine.journey",
        "playlist_narrative_engine.candidate_formation",
        "playlist_narrative_engine.sequencing",
        "playlist_narrative_engine.evaluation",
        "playlist_narrative_engine.providers",
    )
    assert all(name not in source for name in forbidden_imports)


def test_only_ea1_production_code_mints_authenticated_characteristics() -> None:
    src_root = Path(__file__).parents[1] / "src" / "playlist_narrative_engine"
    occurrences = []
    for path in src_root.rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(
            "AuthenticatedStructuredCharacteristic(" in line
            and not line.lstrip().startswith("class ")
            for line in lines
        ):
            occurrences.append(path.relative_to(src_root).as_posix())
    assert occurrences == ["evidence_authentication/boundary.py"]

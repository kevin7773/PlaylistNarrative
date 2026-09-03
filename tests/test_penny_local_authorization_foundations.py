from __future__ import annotations

import inspect
import threading
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.local_authorization import (
    AUTHORIZATION_METHOD_SHA256,
    OWNER_POLICY_SHA256,
    LOCAL_PRINCIPAL_REGISTRY_SHA256,
    AcceptedObjectiveOwnerAuthorityArtifact,
    AcceptedObjectiveOwnerAuthorityProducer,
    AcceptedObjectiveOwnerAuthorityRequest,
    AcceptedObjectiveOwnerAuthorityVerifier,
    CaptureOutcome,
    ConstraintPreauthorizationPayload,
    LocalConstraintAuthorizationConfirmationEvidence,
    LocalConstraintAuthorizationPresentation,
    LocalConstraintConfirmationCaptureProducer,
    LocalConstraintConfirmationInvalidInput,
    LocalObjectiveOwnerInvalidInput,
    LocalObjectiveSubmissionAuthorityRepository,
    LocalObjectiveSubmissionCaptureProducer,
    LocalObjectiveSubmissionEvidence,
    LocalPrincipalAuthorityArtifact,
    LocalPrincipalAuthorityInvalidInput,
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
    LocalPrincipalAuthorityVerifier,
    PrincipalRelationship,
    serialize_accepted_objective_owner_artifact,
    serialize_accepted_objective_owner_request,
    serialize_constraint_preauthorization_payload,
    serialize_local_constraint_authorization_presentation,
    serialize_local_constraint_confirmation_evidence,
    serialize_local_objective_submission,
    serialize_local_principal_authority,
    verify_authorization_method,
    verify_local_principal_registry,
    verify_owner_policy,
)
from playlist_narrative_engine.local_authorization.canonical import canonical_sha256
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import (
    AcceptedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveSafetyEvaluator,
    ObjectiveSafetyRequest,
    canonical_assessment_sha256,
    canonical_objective_sha256,
)
from objective_safety_helpers import intent_declaration, sufficient_assessment


FIXTURE_DEFINITION_ID = "example.invalid/definition-001"
FIXTURE_DEFINITION_VERSION = "1.0"
FIXTURE_DEFINITION_SHA256 = "1" * 64


class _FixtureDefinitionResolver:
    def __init__(self) -> None:
        self.enabled = True

    def verifies(
        self,
        *,
        definition_id: str,
        definition_version: str,
        definition_sha256: str,
        parameters: dict[str, Any],
    ) -> bool:
        return self.enabled and (
            definition_id,
            definition_version,
            definition_sha256,
            parameters,
        ) == (
            FIXTURE_DEFINITION_ID,
            FIXTURE_DEFINITION_VERSION,
            FIXTURE_DEFINITION_SHA256,
            {"expected_json": '"example"'},
        )


def _principal_foundation() -> tuple[
    LocalPrincipalAuthorityRepository,
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityArtifact,
]:
    repository = LocalPrincipalAuthorityRepository()
    producer = LocalPrincipalAuthorityProducer(repository)
    return repository, producer, producer.create_initial()


def _owner_foundation():
    principal_repository, principal_producer, principal = _principal_foundation()
    submission_repository = LocalObjectiveSubmissionAuthorityRepository()
    submission_producer = LocalObjectiveSubmissionCaptureProducer(
        principal_producer.verifier, submission_repository
    )
    objective = Objective(
        objective_id="objective-001", statement="Build a listening journey."
    )
    submission = submission_producer.capture(
        objective=objective,
        intent_category=ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
    )
    assessment = sufficient_assessment(objective)
    safety_request = ObjectiveSafetyRequest(
        request_id="safety-request-objective-001",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=submission.intent_declaration,
        intent_declaration_id=submission.intent_declaration.declaration_id,
        intent_declaration_sha256=submission.intent_declaration.canonical_sha256,
    )
    accepted = ObjectiveSafetyEvaluator().evaluate(safety_request)
    assert isinstance(accepted, AcceptedObjectiveArtifact)
    owner_verifier = AcceptedObjectiveOwnerAuthorityVerifier(
        principal_producer.verifier, submission_repository
    )
    owner_bundle = AcceptedObjectiveOwnerAuthorityProducer(owner_verifier).produce(
        submission=submission,
        objective_safety_request=safety_request,
        accepted_objective=accepted,
    )
    return (
        principal_repository,
        principal_producer,
        principal,
        submission_repository,
        owner_verifier,
        owner_bundle,
    )


def _payload(owner_bundle) -> ConstraintPreauthorizationPayload:
    accepted = owner_bundle.accepted_objective
    return ConstraintPreauthorizationPayload(
        accepted_objective_artifact_id=accepted.artifact_id,
        accepted_objective_sha256=accepted.canonical_sha256,
        constraint_request_id="example.invalid/constraint-request-001",
        constraint_request_version="1.0",
        constraint_definition_id=FIXTURE_DEFINITION_ID,
        constraint_definition_version=FIXTURE_DEFINITION_VERSION,
        constraint_definition_sha256=FIXTURE_DEFINITION_SHA256,
        parameters={"expected_json": '"example"'},
    )


def test_principal_ids_are_internal_opaque_and_public_creation_accepts_none() -> None:
    repository, producer, artifact = _principal_foundation()

    assert artifact.installation_id.startswith("penny-local-installation:")
    assert artifact.principal_id.startswith("penny-local-principal:")
    assert artifact.artifact_id.startswith("local-principal-authority:")
    assert artifact.installation_id != artifact.principal_id
    assert tuple(inspect.signature(producer.create_initial).parameters) == ()
    assert producer.verifier.verify(artifact, require_active=True)
    assert repository.artifacts == (artifact,)


def test_exactly_one_active_principal_and_immutable_successor_lineage() -> None:
    repository, producer, initial = _principal_foundation()
    initial_bytes = serialize_local_principal_authority(initial)

    with pytest.raises(LocalPrincipalAuthorityInvalidInput):
        producer.create_initial()
    successor = producer.create_successor(initial)

    assert serialize_local_principal_authority(initial) == initial_bytes
    assert successor.installation_id == initial.installation_id
    assert successor.principal_id != initial.principal_id
    assert successor.predecessor_artifact_sha256 == initial.canonical_sha256
    assert producer.verifier.resolve_active() == successor
    assert producer.verifier.verify(initial)
    assert not producer.verifier.verify(initial, require_active=True)
    assert repository.artifacts == (initial, successor)
    with pytest.raises(LocalPrincipalAuthorityInvalidInput):
        producer.create_successor(initial)


def test_verified_principal_lineage_prefix_is_source_neutral_and_historical() -> None:
    _, producer, initial = _principal_foundation()
    initial_prefix = producer.verifier.verified_lineage_prefix_sha256(
        initial,
        require_current_tip=True,
    )
    successor = producer.create_successor(initial)

    assert producer.verifier.verified_lineage_prefix_sha256(initial) == initial_prefix
    assert producer.verifier.verified_lineage_prefix_sha256(
        successor,
        require_current_tip=True,
    ) != initial_prefix
    with pytest.raises(LocalPrincipalAuthorityInvalidInput, match="current applicable"):
        producer.verifier.verified_lineage_prefix_sha256(
            initial,
            require_current_tip=True,
        )
    substituted = initial.model_copy(update={"principal_id": "substituted"})
    with pytest.raises(LocalPrincipalAuthorityInvalidInput, match="not exact"):
        producer.verifier.verified_lineage_prefix_sha256(substituted)


def test_guarded_current_tip_accepts_exact_tip_and_rejects_stale_tip() -> None:
    _, producer, initial = _principal_foundation()

    assert producer.verifier.guarded_current_tip(initial, lambda: "accepted") == "accepted"
    successor = producer.create_successor(initial)
    with pytest.raises(LocalPrincipalAuthorityInvalidInput, match="current applicable"):
        producer.verifier.guarded_current_tip(initial, lambda: "must-not-run")
    assert producer.verifier.guarded_current_tip(successor, lambda: 7) == 7
    assert producer.verifier.verify(initial)


def test_guarded_current_tip_and_succession_share_synchronization_boundary() -> None:
    _, producer, initial = _principal_foundation()
    action_entered = threading.Event()
    release_action = threading.Event()
    action_completed = threading.Event()
    succession_started = threading.Event()
    succession_completed = threading.Event()
    failures: list[BaseException] = []

    def guarded_acceptance() -> None:
        try:
            def action() -> None:
                action_entered.set()
                assert release_action.wait(5)
                action_completed.set()

            producer.verifier.guarded_current_tip(initial, action)
        except BaseException as exc:  # pragma: no cover - diagnostic capture
            failures.append(exc)

    def succeed() -> None:
        try:
            succession_started.set()
            producer.create_successor(initial)
            succession_completed.set()
        except BaseException as exc:  # pragma: no cover - diagnostic capture
            failures.append(exc)

    guarded_thread = threading.Thread(target=guarded_acceptance)
    guarded_thread.start()
    assert action_entered.wait(5)
    successor_thread = threading.Thread(target=succeed)
    successor_thread.start()
    assert succession_started.wait(5)
    assert not succession_completed.wait(0.1)
    release_action.set()
    guarded_thread.join(5)
    successor_thread.join(5)

    assert not failures
    assert action_completed.is_set()
    assert succession_completed.is_set()
    assert producer.verifier.verify(initial)
    assert producer.verifier.resolve_active() != initial


def test_principal_schema_forbids_identity_substitution_and_partial_lineage() -> None:
    _, producer, initial = _principal_foundation()
    substituted = initial.model_copy(update={"principal_id": "caller-selected"})
    assert not producer.verifier.verify(substituted)
    with pytest.raises(ValidationError, match="complete or absent"):
        LocalPrincipalAuthorityArtifact(
            **initial.model_dump(mode="json", exclude={"canonical_sha256"}),
            predecessor_artifact_id="only-one-field",
        )


def test_principal_contract_fixture_and_registry_digests_reproduce() -> None:
    fixture = LocalPrincipalAuthorityArtifact(
        artifact_id="example.invalid/local-principal-authority-001",
        installation_id="example.invalid/installation-001",
        principal_id="example.invalid/principal-001",
        principal_version="1.0",
    )

    assert verify_local_principal_registry()
    assert LOCAL_PRINCIPAL_REGISTRY_SHA256 == (
        "0d132a5ba0b1e619d9c1b6b7f807878ad3e321abcbe352cc36e20c9d4d655ab3"
    )
    assert fixture.canonical_sha256 == (
        "a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55"
    )
    assert not LocalPrincipalAuthorityVerifier(
        LocalPrincipalAuthorityRepository()
    ).verify(fixture)
    with pytest.raises(LocalPrincipalAuthorityInvalidInput, match="only the principal"):
        LocalPrincipalAuthorityRepository()._record_initial(fixture, object())


def test_objective_submission_binds_exact_active_principal_and_declaration() -> None:
    _, principal_producer, principal = _principal_foundation()
    repository = LocalObjectiveSubmissionAuthorityRepository()
    capture = LocalObjectiveSubmissionCaptureProducer(
        principal_producer.verifier, repository
    )
    objective = Objective(objective_id="o", statement="An exact objective.")

    bundle = capture.capture(
        objective=objective,
        intent_category=ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
    )

    assert bundle.principal_authority == principal
    assert bundle.evidence.local_principal_authority_sha256 == principal.canonical_sha256
    assert bundle.intent_declaration.authority_reference == bundle.evidence.evidence_id
    assert bundle.evidence.intent_declaration_sha256 == (
        bundle.intent_declaration.canonical_sha256
    )
    assert repository.verify(bundle)


def test_owner_authority_is_deterministic_and_all_substitutions_fail_closed() -> None:
    *_, owner_verifier, bundle = _owner_foundation()

    assert owner_verifier.verify(bundle)
    reproduced = AcceptedObjectiveOwnerAuthorityProducer(owner_verifier).produce(
        submission=bundle.submission,
        objective_safety_request=bundle.objective_safety_request,
        accepted_objective=bundle.accepted_objective,
    )
    assert reproduced.request == bundle.request
    assert reproduced.artifact == bundle.artifact
    assert serialize_accepted_objective_owner_request(reproduced.request) == (
        serialize_accepted_objective_owner_request(bundle.request)
    )
    assert serialize_accepted_objective_owner_artifact(reproduced.artifact) == (
        serialize_accepted_objective_owner_artifact(bundle.artifact)
    )

    wrong_principal = bundle.submission.principal_authority.model_copy(
        update={"principal_id": "penny-local-principal:substituted"}
    )
    wrong_submission = bundle.submission.__class__(
        wrong_principal,
        bundle.submission.evidence,
        bundle.submission.intent_declaration,
    )
    assert not owner_verifier.verify(
        bundle.__class__(
            wrong_submission,
            bundle.objective_safety_request,
            bundle.accepted_objective,
            bundle.request,
            bundle.artifact,
        )
    )
    substituted_evidence = bundle.submission.evidence.model_copy(
        update={"evidence_id": "local-objective-submission:substituted"}
    )
    assert not owner_verifier.verify(
        bundle.__class__(
            bundle.submission.__class__(
                bundle.submission.principal_authority,
                substituted_evidence,
                bundle.submission.intent_declaration,
            ),
            bundle.objective_safety_request,
            bundle.accepted_objective,
            bundle.request,
            bundle.artifact,
        )
    )
    substituted_accepted = bundle.accepted_objective.model_copy(
        update={"artifact_id": "accepted-objective:substituted"}
    )
    assert not owner_verifier.verify(
        bundle.__class__(
            bundle.submission,
            bundle.objective_safety_request,
            substituted_accepted,
            bundle.request,
            bundle.artifact,
        )
    )
    for field in (
        "accepted_objective_sha256",
        "objective_submission_evidence_sha256",
        "intent_declaration_sha256",
        "owner_policy_sha256",
    ):
        changed_request = bundle.request.model_copy(update={field: "0" * 64})
        changed = bundle.__class__(
            bundle.submission,
            bundle.objective_safety_request,
            bundle.accepted_objective,
            changed_request,
            bundle.artifact,
        )
        assert not owner_verifier.verify(changed)


def test_historical_accepted_objective_cannot_gain_retrospective_owner() -> None:
    (
        _,
        principal_producer,
        _,
        submission_repository,
        owner_verifier,
        _,
    ) = _owner_foundation()
    historical_objective = Objective(
        objective_id="historical", statement="Historical objective."
    )
    assessment = sufficient_assessment(historical_objective)
    historical_declaration = intent_declaration(historical_objective)
    historical_request = ObjectiveSafetyRequest(
        request_id="historical-request",
        objective_assessment=assessment,
        objective_sha256=canonical_objective_sha256(historical_objective),
        objective_assessment_sha256=canonical_assessment_sha256(assessment),
        intent_declaration=historical_declaration,
        intent_declaration_id=historical_declaration.declaration_id,
        intent_declaration_sha256=historical_declaration.canonical_sha256,
    )
    historical_accepted = ObjectiveSafetyEvaluator().evaluate(historical_request)
    assert isinstance(historical_accepted, AcceptedObjectiveArtifact)
    later_submission = LocalObjectiveSubmissionCaptureProducer(
        principal_producer.verifier, submission_repository
    ).capture(
        objective=historical_objective,
        intent_category=ObjectiveIntentCategory.LISTENING_JOURNEY_EXPRESSION,
    )

    with pytest.raises(LocalObjectiveOwnerInvalidInput):
        AcceptedObjectiveOwnerAuthorityProducer(owner_verifier).produce(
            submission=later_submission,
            objective_safety_request=historical_request,
            accepted_objective=historical_accepted,
        )


def test_owner_contract_fixtures_and_policy_digest_reproduce() -> None:
    evidence = LocalObjectiveSubmissionEvidence(
        evidence_id="example.invalid/objective-submission-001",
        local_principal_authority_artifact_id=(
            "example.invalid/local-principal-authority-001"
        ),
        local_principal_authority_sha256=(
            "a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55"
        ),
        objective_id="example.invalid/objective-001",
        objective_statement_sha256="4" * 64,
        intent_declaration_id="example.invalid/intent-declaration-001",
        intent_declaration_sha256="5" * 64,
    )
    request = AcceptedObjectiveOwnerAuthorityRequest(
        request_id="example.invalid/objective-owner-request-001",
        local_principal_authority_artifact_id=(
            "example.invalid/local-principal-authority-001"
        ),
        local_principal_authority_sha256=(
            "a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55"
        ),
        objective_submission_evidence_id=evidence.evidence_id,
        objective_submission_evidence_sha256=evidence.canonical_sha256,
        intent_declaration_id="example.invalid/intent-declaration-001",
        intent_declaration_sha256="5" * 64,
        accepted_objective_artifact_id="example.invalid/objective-001",
        accepted_objective_sha256="0" * 64,
    )
    artifact = AcceptedObjectiveOwnerAuthorityArtifact(
        artifact_id=f"accepted-objective-owner:sha256:{request.canonical_sha256}",
        input_request_id=request.request_id,
        input_request_sha256=request.canonical_sha256,
        owner_principal_id="example.invalid/principal-001",
        local_principal_authority_artifact_id=(
            "example.invalid/local-principal-authority-001"
        ),
        local_principal_authority_sha256=(
            "a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55"
        ),
        objective_submission_evidence_id=evidence.evidence_id,
        objective_submission_evidence_sha256=evidence.canonical_sha256,
        intent_declaration_id="example.invalid/intent-declaration-001",
        intent_declaration_sha256="5" * 64,
        accepted_objective_artifact_id="example.invalid/objective-001",
        accepted_objective_sha256="0" * 64,
    )

    assert verify_owner_policy()
    assert OWNER_POLICY_SHA256 == (
        "a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e"
    )
    assert evidence.canonical_sha256 == (
        "d685b6fabc50ae6c042a760560d96b139649712fb7a19027ca33a0ff83534eda"
    )
    assert request.canonical_sha256 == (
        "29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc"
    )
    assert artifact.canonical_sha256 == (
        "9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab"
    )
    assert serialize_local_objective_submission(evidence)


def test_empty_product_definition_registry_fails_closed() -> None:
    principal_repository, principal_producer, _, _, owner_verifier, owner = (
        _owner_foundation()
    )
    producer = LocalConstraintConfirmationCaptureProducer(
        principal_verifier=LocalPrincipalAuthorityVerifier(principal_repository),
        owner_verifier=owner_verifier,
    )
    with pytest.raises(
        LocalConstraintConfirmationInvalidInput,
        match="definition authority is unavailable",
    ) as invalid:
        producer.begin_presentation(owner_authority=owner, payload=_payload(owner))
    assert invalid.value.outcome is CaptureOutcome.NOT_EVALUATED_INVALID_INPUT


def test_presentation_reproduces_and_payload_or_definition_changes_invalidate() -> None:
    principal_repository, _, _, _, owner_verifier, owner = _owner_foundation()
    resolver = _FixtureDefinitionResolver()
    producer = LocalConstraintConfirmationCaptureProducer(
        principal_verifier=LocalPrincipalAuthorityVerifier(principal_repository),
        owner_verifier=owner_verifier,
        definition_resolver=resolver,
    )
    payload = _payload(owner)
    first = producer.begin_presentation(owner_authority=owner, payload=payload)
    second = producer.begin_presentation(owner_authority=owner, payload=payload)

    assert first.presentation == second.presentation
    assert serialize_local_constraint_authorization_presentation(
        first.presentation
    ) == serialize_local_constraint_authorization_presentation(second.presentation)
    assert first.presentation.preauthorization_payload_sha256 == payload.canonical_sha256

    payload.parameters["expected_json"] = '"changed"'
    result = first.activate_acceptance_control()
    assert result.outcome is CaptureOutcome.NOT_EVALUATED_INVALID_INPUT
    assert result.evidence is None

    resolver.enabled = False
    result = second.activate_acceptance_control()
    assert result.outcome is CaptureOutcome.NOT_EVALUATED_INVALID_INPUT
    assert result.evidence is None

    resolver.enabled = True
    definition_changed_payload = _payload(owner)
    third = producer.begin_presentation(
        owner_authority=owner, payload=definition_changed_payload
    )
    object.__setattr__(
        definition_changed_payload, "constraint_definition_sha256", "2" * 64
    )
    result = third.activate_acceptance_control()
    assert result.outcome is CaptureOutcome.NOT_EVALUATED_INVALID_INPUT
    assert result.evidence is None


def test_wrong_current_principal_and_delegate_fail_closed() -> None:
    principal_repository, principal_producer, principal, _, owner_verifier, owner = (
        _owner_foundation()
    )
    producer = LocalConstraintConfirmationCaptureProducer(
        principal_verifier=LocalPrincipalAuthorityVerifier(principal_repository),
        owner_verifier=owner_verifier,
        definition_resolver=_FixtureDefinitionResolver(),
    )
    with pytest.raises(LocalConstraintConfirmationInvalidInput, match="DELEGATE"):
        producer.begin_presentation(
            owner_authority=owner,
            payload=_payload(owner),
            principal_relationship=PrincipalRelationship.DELEGATE,
        )
    principal_producer.create_successor(principal)
    with pytest.raises(LocalConstraintConfirmationInvalidInput, match="does not exactly"):
        producer.begin_presentation(owner_authority=owner, payload=_payload(owner))


def test_deliberate_acceptance_and_refusal_create_exact_immutable_evidence() -> None:
    principal_repository, _, _, _, owner_verifier, owner = _owner_foundation()
    producer = LocalConstraintConfirmationCaptureProducer(
        principal_verifier=LocalPrincipalAuthorityVerifier(principal_repository),
        owner_verifier=owner_verifier,
        definition_resolver=_FixtureDefinitionResolver(),
    )
    payload = _payload(owner)

    accepted = producer.begin_presentation(
        owner_authority=owner, payload=payload
    ).activate_acceptance_control()
    refused = producer.begin_presentation(
        owner_authority=owner, payload=payload
    ).activate_refusal_control()

    assert accepted.outcome is CaptureOutcome.EVIDENCE_PRODUCED
    assert accepted.evidence is not None
    assert accepted.evidence.decision.value == "ACCEPTED"
    assert accepted.evidence.interaction_event == "ACCEPTANCE_CONTROL_ACTIVATED"
    assert refused.outcome is CaptureOutcome.EVIDENCE_PRODUCED
    assert refused.evidence is not None
    assert refused.evidence.decision.value == "REFUSED"
    assert refused.evidence.interaction_event == "REFUSAL_CONTROL_ACTIVATED"
    assert producer.verify_evidence(
        accepted.evidence, owner_authority=owner, payload=payload
    )
    assert producer.verify_evidence(
        refused.evidence, owner_authority=owner, payload=payload
    )
    assert serialize_local_constraint_confirmation_evidence(accepted.evidence)


def test_cancellation_and_invalid_reuse_produce_no_evidence() -> None:
    principal_repository, _, _, _, owner_verifier, owner = _owner_foundation()
    producer = LocalConstraintConfirmationCaptureProducer(
        principal_verifier=LocalPrincipalAuthorityVerifier(principal_repository),
        owner_verifier=owner_verifier,
        definition_resolver=_FixtureDefinitionResolver(),
    )
    session = producer.begin_presentation(
        owner_authority=owner, payload=_payload(owner)
    )

    cancelled = session.cancel()
    reused = session.activate_acceptance_control()

    assert cancelled == cancelled.__class__(CaptureOutcome.CANCELLED, None)
    assert reused.outcome is CaptureOutcome.NOT_EVALUATED_INVALID_INPUT
    assert reused.evidence is None


def test_production_interfaces_have_no_bare_approval_or_decision_input() -> None:
    prohibited = {
        "approved",
        "accepted",
        "is_authorized",
        "checked",
        "checkbox_state",
        "decision",
        "interaction_event",
    }
    production_methods = (
        LocalConstraintConfirmationCaptureProducer.begin_presentation,
        LocalConstraintConfirmationCaptureProducer.__init__,
    )
    for method in production_methods:
        parameters = set(inspect.signature(method).parameters) - {"self"}
        assert parameters.isdisjoint(prohibited)


def test_confirmation_contract_examples_and_method_digest_reproduce() -> None:
    presentation = LocalConstraintAuthorizationPresentation(
        accepted_objective_artifact_id="example.invalid/objective-001",
        accepted_objective_sha256="0" * 64,
        objective_owner_authority_artifact_id=(
            "accepted-objective-owner:sha256:"
            "29e92a59d9bc2bb42362d3284005615bf83f7cff0c46192e483a1093a70aaacc"
        ),
        objective_owner_authority_sha256=(
            "9f886b469a5eb298d4dc29d8dc8a72878c2d3de836f52246d8fc9d206a0fc3ab"
        ),
        authorizing_principal_id="example.invalid/principal-001",
        local_principal_authority_artifact_id=(
            "example.invalid/local-principal-authority-001"
        ),
        local_principal_authority_sha256=(
            "a101720cb221a90d4ded1f6f36b17db2afdcd292cc54abe1fff5e8d5e8502c55"
        ),
        constraint_request_id="example.invalid/constraint-request-001",
        constraint_request_version="1.0",
        constraint_definition_id=FIXTURE_DEFINITION_ID,
        constraint_definition_version=FIXTURE_DEFINITION_VERSION,
        constraint_definition_sha256=FIXTURE_DEFINITION_SHA256,
        parameters={"expected_json": '"example"'},
        preauthorization_payload_sha256=(
            "18a3f54a258b079676040f5b08e79994a92ebfa36ccf931ecceb1456c71edbfa"
        ),
    )
    presentation_digest = canonical_sha256(presentation)
    evidence = LocalConstraintAuthorizationConfirmationEvidence(
        evidence_id=(
            f"local-constraint-confirmation:sha256:{presentation_digest}:accepted"
        ),
        decision="ACCEPTED",
        interaction_event="ACCEPTANCE_CONTROL_ACTIVATED",
        activated_control_id="ACCEPT_PRODUCT_CONSTRAINT_REQUEST",
        presentation=presentation,
        presentation_sha256=presentation_digest,
        authorizing_principal_id=presentation.authorizing_principal_id,
        local_principal_authority_artifact_id=(
            presentation.local_principal_authority_artifact_id
        ),
        local_principal_authority_sha256=(
            presentation.local_principal_authority_sha256
        ),
        objective_owner_authority_artifact_id=(
            presentation.objective_owner_authority_artifact_id
        ),
        objective_owner_authority_sha256=(
            presentation.objective_owner_authority_sha256
        ),
        accepted_objective_artifact_id=presentation.accepted_objective_artifact_id,
        accepted_objective_sha256=presentation.accepted_objective_sha256,
        preauthorization_payload_sha256=(
            presentation.preauthorization_payload_sha256
        ),
    )

    assert verify_authorization_method()
    assert AUTHORIZATION_METHOD_SHA256 == (
        "0ab7d3c9278acc79b115e7773ed3feeca36167b6f18f5a1dddfd46d50ee8a9c5"
    )
    assert presentation_digest == (
        "5e059ca19d11b56a4835cb7c333f96b291de333207e57662ff255d18f01b84b2"
    )
    assert evidence.canonical_sha256 == (
        "3770969764e5a89c77a76183460c97195af3bb0f63fd90a8e759018f191930f7"
    )
    assert serialize_constraint_preauthorization_payload(
        ConstraintPreauthorizationPayload(
            accepted_objective_artifact_id="example.invalid/objective-001",
            accepted_objective_sha256="0" * 64,
            constraint_request_id="example.invalid/constraint-request-001",
            constraint_request_version="1.0",
            constraint_definition_id=FIXTURE_DEFINITION_ID,
            constraint_definition_version=FIXTURE_DEFINITION_VERSION,
            constraint_definition_sha256=FIXTURE_DEFINITION_SHA256,
            parameters={"expected_json": '"example"'},
        )
    )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("authorization_method_id", "substituted-method"),
        ("authorization_method_version", "2.0"),
        ("authorization_method_sha256", "0" * 64),
    ),
)
def test_method_authority_substitution_and_extra_fields_fail(
    field: str, value: str
) -> None:
    presentation = LocalConstraintAuthorizationPresentation(
        accepted_objective_artifact_id="o",
        accepted_objective_sha256="0" * 64,
        objective_owner_authority_artifact_id="owner",
        objective_owner_authority_sha256="1" * 64,
        authorizing_principal_id="p",
        local_principal_authority_artifact_id="pa",
        local_principal_authority_sha256="2" * 64,
        constraint_request_id="r",
        constraint_request_version="1.0",
        constraint_definition_id="d",
        constraint_definition_version="1.0",
        constraint_definition_sha256="3" * 64,
        parameters={"expected_json": "false"},
        preauthorization_payload_sha256="4" * 64,
    )
    with pytest.raises(ValidationError):
        LocalConstraintAuthorizationConfirmationEvidence(
            evidence_id=f"local-constraint-confirmation:sha256:{canonical_sha256(presentation)}:accepted",
            decision="ACCEPTED",
            interaction_event="ACCEPTANCE_CONTROL_ACTIVATED",
            activated_control_id="ACCEPT_PRODUCT_CONSTRAINT_REQUEST",
            **{field: value},
            presentation=presentation,
            presentation_sha256=canonical_sha256(presentation),
            authorizing_principal_id="p",
            local_principal_authority_artifact_id="pa",
            local_principal_authority_sha256="2" * 64,
            objective_owner_authority_artifact_id="owner",
            objective_owner_authority_sha256="1" * 64,
            accepted_objective_artifact_id="o",
            accepted_objective_sha256="0" * 64,
            preauthorization_payload_sha256="4" * 64,
        )
    with pytest.raises(ValidationError):
        LocalConstraintAuthorizationPresentation.model_validate(
            {**presentation.model_dump(mode="json"), "approved": True}
        )


def test_local_authorization_package_has_no_research_or_workbench_imports() -> None:
    package = (
        Path(__file__).parents[1]
        / "src"
        / "playlist_narrative_engine"
        / "local_authorization"
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in package.glob("*.py"))
    assert "research_store" not in source
    assert "maestro_workbench" not in source

from __future__ import annotations

import secrets
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.local_authorization.canonical import (
    FrozenAuthorityModel,
    canonical_json_bytes,
    canonical_sha256,
    require_exact,
    validate_json_value,
    verify_or_set_digest,
)
from playlist_narrative_engine.local_authorization.objective_owner import (
    AcceptedObjectiveOwnerAuthorityBundle,
    AcceptedObjectiveOwnerAuthorityVerifier,
)
from playlist_narrative_engine.local_authorization.principal import (
    LocalPrincipalAuthorityInvalidInput,
    LocalPrincipalAuthorityVerifier,
)


AUTHORIZATION_METHOD_ID = (
    "pne.constraint-authorization.local-explicit-confirmation"
)
AUTHORIZATION_METHOD_VERSION = "1.0"
AUTHORIZATION_METHOD_SHA256 = (
    "0ab7d3c9278acc79b115e7773ed3feeca36167b6f18f5a1dddfd46d50ee8a9c5"
)
AUTHORIZATION_ACTION = "ACCEPT_PRODUCT_CONSTRAINT_REQUEST"
ACCEPTANCE_CONTROL_ID = "ACCEPT_PRODUCT_CONSTRAINT_REQUEST"
REFUSAL_CONTROL_ID = "REFUSE_PRODUCT_CONSTRAINT_REQUEST"
ACCEPTANCE_CONTROL_TEXT = "Authorize this exact structured constraint request"
REFUSAL_CONTROL_TEXT = "Do not authorize this structured constraint request"
CAPTURE_PRODUCER_ID = "pne.local-constraint-confirmation-capture-producer"
CAPTURE_PRODUCER_VERSION = "1.0"

AUTHORIZATION_METHOD_CONTENT = {
    "schema_version": "1.0",
    "definition_kind": "constraint_authorization_method",
    "authorization_method_id": AUTHORIZATION_METHOD_ID,
    "authorization_method_version": AUTHORIZATION_METHOD_VERSION,
    "authorization_action": AUTHORIZATION_ACTION,
    "principal_relationship": "OBJECTIVE_OWNER",
    "principal_authority_schema_version": "1.0",
    "objective_owner_authority_schema_version": "1.0",
    "confirmation_evidence_schema_version": "1.0",
    "acceptance_control_id": ACCEPTANCE_CONTROL_ID,
    "refusal_control_id": REFUSAL_CONTROL_ID,
    "acceptance_event": "ACCEPTANCE_CONTROL_ACTIVATED",
    "refusal_event": "REFUSAL_CONTROL_ACTIVATED",
    "caller_boolean_authority": False,
    "delegation_supported": False,
    "authoritative_time_claim": False,
    "global_order_claim": False,
    "canonicalization_profile": "pne.canonical-json.utf8-schema-order/1.0",
}


def verify_authorization_method() -> bool:
    return canonical_sha256(AUTHORIZATION_METHOD_CONTENT) == (
        AUTHORIZATION_METHOD_SHA256
    )


class PrincipalRelationship(StrEnum):
    OBJECTIVE_OWNER = "OBJECTIVE_OWNER"
    DELEGATE = "DELEGATE"


class ConfirmationDecision(StrEnum):
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"


class CaptureOutcome(StrEnum):
    EVIDENCE_PRODUCED = "EVIDENCE_PRODUCED"
    CANCELLED = "CANCELLED"
    NOT_EVALUATED_INVALID_INPUT = "NOT_EVALUATED_INVALID_INPUT"


class ConstraintPreauthorizationPayload(FrozenAuthorityModel):
    authorization_action: Literal["ACCEPT_PRODUCT_CONSTRAINT_REQUEST"] = (
        AUTHORIZATION_ACTION
    )
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: Literal["2.0"] = "2.0"
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    constraint_request_schema_version: Literal["1.0"] = "1.0"
    constraint_request_id: str
    constraint_request_version: str
    constraint_definition_id: str
    constraint_definition_version: str
    constraint_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameters: dict[str, Any]

    @field_validator(
        "accepted_objective_artifact_id",
        "constraint_request_id",
        "constraint_request_version",
        "constraint_definition_id",
        "constraint_definition_version",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @field_validator("parameters", mode="before")
    @classmethod
    def require_exact_json_parameters(cls, value: object) -> dict[str, Any]:
        validated = validate_json_value(value)
        if not isinstance(validated, dict):
            raise ValueError("constraint parameters must be a closed JSON object")
        return validated

    @property
    def canonical_sha256(self) -> str:
        return canonical_sha256(self)


class LocalConstraintAuthorizationPresentation(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    presentation_kind: Literal[
        "local_constraint_authorization_confirmation"
    ] = "local_constraint_authorization_confirmation"
    authorization_action: Literal["ACCEPT_PRODUCT_CONSTRAINT_REQUEST"] = (
        AUTHORIZATION_ACTION
    )
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: Literal["2.0"] = "2.0"
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_owner_authority_artifact_id: str
    objective_owner_authority_schema_version: Literal["1.0"] = "1.0"
    objective_owner_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorizing_principal_id: str
    local_principal_authority_artifact_id: str
    local_principal_authority_schema_version: Literal["1.0"] = "1.0"
    local_principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_relationship: Literal["OBJECTIVE_OWNER"] = "OBJECTIVE_OWNER"
    constraint_request_schema_version: Literal["1.0"] = "1.0"
    constraint_request_id: str
    constraint_request_version: str
    constraint_definition_id: str
    constraint_definition_version: str
    constraint_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    parameters: dict[str, Any]
    preauthorization_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acceptance_control_id: Literal[
        "ACCEPT_PRODUCT_CONSTRAINT_REQUEST"
    ] = ACCEPTANCE_CONTROL_ID
    acceptance_control_text: Literal[
        "Authorize this exact structured constraint request"
    ] = ACCEPTANCE_CONTROL_TEXT
    refusal_control_id: Literal[
        "REFUSE_PRODUCT_CONSTRAINT_REQUEST"
    ] = REFUSAL_CONTROL_ID
    refusal_control_text: Literal[
        "Do not authorize this structured constraint request"
    ] = REFUSAL_CONTROL_TEXT

    @field_validator(
        "accepted_objective_artifact_id",
        "objective_owner_authority_artifact_id",
        "authorizing_principal_id",
        "local_principal_authority_artifact_id",
        "constraint_request_id",
        "constraint_request_version",
        "constraint_definition_id",
        "constraint_definition_version",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @field_validator("parameters", mode="before")
    @classmethod
    def require_exact_json_parameters(cls, value: object) -> dict[str, Any]:
        validated = validate_json_value(value)
        if not isinstance(validated, dict):
            raise ValueError("constraint parameters must be a closed JSON object")
        return validated


class LocalConstraintAuthorizationConfirmationEvidence(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal[
        "local_constraint_authorization_confirmation_evidence"
    ] = "local_constraint_authorization_confirmation_evidence"
    evidence_id: str
    evidence_version: Literal["1.0"] = "1.0"
    decision: ConfirmationDecision
    interaction_event: str
    activated_control_id: str
    authorization_method_id: Literal[
        "pne.constraint-authorization.local-explicit-confirmation"
    ] = AUTHORIZATION_METHOD_ID
    authorization_method_version: Literal["1.0"] = AUTHORIZATION_METHOD_VERSION
    authorization_method_sha256: Literal[
        "0ab7d3c9278acc79b115e7773ed3feeca36167b6f18f5a1dddfd46d50ee8a9c5"
    ] = AUTHORIZATION_METHOD_SHA256
    presentation: LocalConstraintAuthorizationPresentation
    presentation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorizing_principal_id: str
    local_principal_authority_artifact_id: str
    local_principal_authority_schema_version: Literal["1.0"] = "1.0"
    local_principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_owner_authority_artifact_id: str
    objective_owner_authority_schema_version: Literal["1.0"] = "1.0"
    objective_owner_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: Literal["2.0"] = "2.0"
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_action: Literal["ACCEPT_PRODUCT_CONSTRAINT_REQUEST"] = (
        AUTHORIZATION_ACTION
    )
    preauthorization_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_producer_authority_id: Literal[
        "pne.local-constraint-confirmation-capture-producer"
    ] = CAPTURE_PRODUCER_ID
    capture_producer_authority_version: Literal["1.0"] = CAPTURE_PRODUCER_VERSION
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "evidence_id",
        "interaction_event",
        "activated_control_id",
        "authorizing_principal_id",
        "local_principal_authority_artifact_id",
        "objective_owner_authority_artifact_id",
        "accepted_objective_artifact_id",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def require_correspondence_and_digest(
        self,
    ) -> LocalConstraintAuthorizationConfirmationEvidence:
        if self.decision is ConfirmationDecision.ACCEPTED:
            expected = (
                "ACCEPTANCE_CONTROL_ACTIVATED",
                ACCEPTANCE_CONTROL_ID,
                "accepted",
            )
        else:
            expected = (
                "REFUSAL_CONTROL_ACTIVATED",
                REFUSAL_CONTROL_ID,
                "refused",
            )
        event, control, suffix = expected
        expected_id = (
            f"local-constraint-confirmation:sha256:{self.presentation_sha256}:"
            f"{suffix}"
        )
        presentation = self.presentation
        if (
            self.interaction_event != event
            or self.activated_control_id != control
            or self.evidence_id != expected_id
            or self.presentation_sha256 != canonical_sha256(presentation)
            or self.authorizing_principal_id != presentation.authorizing_principal_id
            or self.local_principal_authority_artifact_id
            != presentation.local_principal_authority_artifact_id
            or self.local_principal_authority_schema_version
            != presentation.local_principal_authority_schema_version
            or self.local_principal_authority_sha256
            != presentation.local_principal_authority_sha256
            or self.objective_owner_authority_artifact_id
            != presentation.objective_owner_authority_artifact_id
            or self.objective_owner_authority_schema_version
            != presentation.objective_owner_authority_schema_version
            or self.objective_owner_authority_sha256
            != presentation.objective_owner_authority_sha256
            or self.accepted_objective_artifact_id
            != presentation.accepted_objective_artifact_id
            or self.accepted_objective_schema_version
            != presentation.accepted_objective_schema_version
            or self.accepted_objective_sha256 != presentation.accepted_objective_sha256
            or self.authorization_action != presentation.authorization_action
            or self.preauthorization_payload_sha256
            != presentation.preauthorization_payload_sha256
        ):
            raise ValueError("confirmation evidence correspondence is invalid")
        if not verify_authorization_method():
            raise ValueError("authorization method authority is invalid")
        verify_or_set_digest(self)
        return self


class ConstraintDefinitionAuthorityResolver(Protocol):
    """Trusted product composition boundary; the shipped implementation is empty."""

    def verifies(
        self,
        *,
        definition_id: str,
        definition_version: str,
        definition_sha256: str,
        parameters: dict[str, Any],
    ) -> bool: ...


class EmptyConstraintDefinitionAuthorityResolver:
    """The intentionally empty Penny product constraint-definition registry."""

    def verifies(
        self,
        *,
        definition_id: str,
        definition_version: str,
        definition_sha256: str,
        parameters: dict[str, Any],
    ) -> bool:
        return False


@dataclass(frozen=True)
class CaptureResult:
    outcome: CaptureOutcome
    evidence: LocalConstraintAuthorizationConfirmationEvidence | None = None


class LocalConstraintConfirmationInvalidInput(ValueError):
    outcome = CaptureOutcome.NOT_EVALUATED_INVALID_INPUT


@dataclass
class _CaptureState:
    owner_bundle: AcceptedObjectiveOwnerAuthorityBundle
    payload: ConstraintPreauthorizationPayload
    presentation: LocalConstraintAuthorizationPresentation
    presentation_bytes: bytes
    active: bool = True


class LocalConstraintAuthorizationCaptureSession:
    def __init__(
        self,
        producer: LocalConstraintConfirmationCaptureProducer,
        capability_id: str,
        presentation: LocalConstraintAuthorizationPresentation,
    ) -> None:
        self._producer = producer
        self._capability_id = capability_id
        self.presentation = presentation

    def activate_acceptance_control(self) -> CaptureResult:
        return self._producer._activate_acceptance(self._capability_id)

    def activate_refusal_control(self) -> CaptureResult:
        return self._producer._activate_refusal(self._capability_id)

    def cancel(self) -> CaptureResult:
        return self._producer._cancel(self._capability_id)


class LocalConstraintConfirmationCaptureProducer:
    def __init__(
        self,
        *,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        owner_verifier: AcceptedObjectiveOwnerAuthorityVerifier,
        definition_resolver: ConstraintDefinitionAuthorityResolver | None = None,
    ) -> None:
        self._principal_verifier = principal_verifier
        self._owner_verifier = owner_verifier
        self._definition_resolver = (
            definition_resolver or EmptyConstraintDefinitionAuthorityResolver()
        )
        self._sessions: dict[str, _CaptureState] = {}
        self._issued_evidence: dict[
            str, LocalConstraintAuthorizationConfirmationEvidence
        ] = {}

    def begin_presentation(
        self,
        *,
        owner_authority: AcceptedObjectiveOwnerAuthorityBundle,
        payload: ConstraintPreauthorizationPayload,
        principal_relationship: PrincipalRelationship = (
            PrincipalRelationship.OBJECTIVE_OWNER
        ),
    ) -> LocalConstraintAuthorizationCaptureSession:
        if principal_relationship is PrincipalRelationship.DELEGATE:
            raise LocalConstraintConfirmationInvalidInput(
                "DELEGATE is unsupported and fails closed in Penny Local v1"
            )
        if principal_relationship is not PrincipalRelationship.OBJECTIVE_OWNER:
            raise LocalConstraintConfirmationInvalidInput(
                "principal relationship authority is unsupported"
            )
        presentation = self._reproduce_presentation(owner_authority, payload)
        capability_id = secrets.token_hex(32)
        self._sessions[capability_id] = _CaptureState(
            owner_authority,
            payload,
            presentation,
            canonical_json_bytes(presentation),
        )
        return LocalConstraintAuthorizationCaptureSession(
            self, capability_id, presentation
        )

    def _activate_acceptance(self, capability_id: str) -> CaptureResult:
        return self._activate(
            capability_id,
            decision=ConfirmationDecision.ACCEPTED,
            interaction_event="ACCEPTANCE_CONTROL_ACTIVATED",
            activated_control_id=ACCEPTANCE_CONTROL_ID,
        )

    def _activate_refusal(self, capability_id: str) -> CaptureResult:
        return self._activate(
            capability_id,
            decision=ConfirmationDecision.REFUSED,
            interaction_event="REFUSAL_CONTROL_ACTIVATED",
            activated_control_id=REFUSAL_CONTROL_ID,
        )

    def _activate(
        self,
        capability_id: str,
        *,
        decision: ConfirmationDecision,
        interaction_event: str,
        activated_control_id: str,
    ) -> CaptureResult:
        state = self._sessions.get(capability_id)
        if state is None or not state.active:
            return CaptureResult(CaptureOutcome.NOT_EVALUATED_INVALID_INPUT)
        state.active = False
        try:
            reproduced = self._reproduce_presentation(
                state.owner_bundle, state.payload
            )
            if (
                reproduced != state.presentation
                or canonical_json_bytes(reproduced) != state.presentation_bytes
            ):
                return CaptureResult(CaptureOutcome.NOT_EVALUATED_INVALID_INPUT)
            evidence = _build_confirmation_evidence(
                reproduced,
                decision=decision,
                interaction_event=interaction_event,
                activated_control_id=activated_control_id,
            )
        except (TypeError, ValueError):
            return CaptureResult(CaptureOutcome.NOT_EVALUATED_INVALID_INPUT)
        existing = self._issued_evidence.get(evidence.evidence_id)
        if existing is not None and existing != evidence:
            return CaptureResult(CaptureOutcome.NOT_EVALUATED_INVALID_INPUT)
        self._issued_evidence[evidence.evidence_id] = evidence
        return CaptureResult(CaptureOutcome.EVIDENCE_PRODUCED, evidence)

    def _cancel(self, capability_id: str) -> CaptureResult:
        state = self._sessions.get(capability_id)
        if state is None or not state.active:
            return CaptureResult(CaptureOutcome.NOT_EVALUATED_INVALID_INPUT)
        state.active = False
        return CaptureResult(CaptureOutcome.CANCELLED)

    def verify_evidence(
        self,
        evidence: LocalConstraintAuthorizationConfirmationEvidence,
        *,
        owner_authority: AcceptedObjectiveOwnerAuthorityBundle,
        payload: ConstraintPreauthorizationPayload,
    ) -> bool:
        try:
            validated = LocalConstraintAuthorizationConfirmationEvidence.model_validate(
                evidence.model_dump(mode="json")
            )
            if validated != evidence:
                return False
            issued = self._issued_evidence.get(evidence.evidence_id)
            if issued != evidence:
                return False
            presentation = self._reproduce_presentation(
                owner_authority, payload, require_current_active=False
            )
            return evidence.presentation == presentation
        except (TypeError, ValueError):
            return False

    def _reproduce_presentation(
        self,
        owner_authority: AcceptedObjectiveOwnerAuthorityBundle,
        payload: ConstraintPreauthorizationPayload,
        *,
        require_current_active: bool = True,
    ) -> LocalConstraintAuthorizationPresentation:
        if not verify_authorization_method():
            raise LocalConstraintConfirmationInvalidInput(
                "authorization method authority is invalid"
            )
        if not isinstance(payload, ConstraintPreauthorizationPayload):
            raise LocalConstraintConfirmationInvalidInput(
                "exact preauthorization payload is required"
            )
        payload = ConstraintPreauthorizationPayload.model_validate(
            payload.model_dump(mode="json")
        )
        if not self._owner_verifier.verify(owner_authority):
            raise LocalConstraintConfirmationInvalidInput(
                "objective-owner authority is invalid"
            )
        principal = owner_authority.submission.principal_authority
        if require_current_active:
            try:
                active = self._principal_verifier.resolve_active()
            except LocalPrincipalAuthorityInvalidInput as exc:
                raise LocalConstraintConfirmationInvalidInput(str(exc)) from exc
            if active != principal:
                raise LocalConstraintConfirmationInvalidInput(
                    "active principal does not exactly equal objective owner authority"
                )
        elif not self._principal_verifier.verify(principal):
            raise LocalConstraintConfirmationInvalidInput(
                "historical principal authority is invalid"
            )
        owner = owner_authority.artifact
        accepted = owner_authority.accepted_objective
        if (
            owner.owner_principal_id != principal.principal_id
            or owner.local_principal_authority_artifact_id != principal.artifact_id
            or owner.local_principal_authority_sha256 != principal.canonical_sha256
            or payload.accepted_objective_artifact_id != accepted.artifact_id
            or payload.accepted_objective_schema_version != accepted.schema_version
            or payload.accepted_objective_sha256 != accepted.canonical_sha256
        ):
            raise LocalConstraintConfirmationInvalidInput(
                "principal, owner, or objective authority does not correspond"
            )
        if not self._definition_resolver.verifies(
            definition_id=payload.constraint_definition_id,
            definition_version=payload.constraint_definition_version,
            definition_sha256=payload.constraint_definition_sha256,
            parameters=payload.parameters,
        ):
            raise LocalConstraintConfirmationInvalidInput(
                "approved constraint-definition authority is unavailable or invalid"
            )
        return LocalConstraintAuthorizationPresentation(
            accepted_objective_artifact_id=accepted.artifact_id,
            accepted_objective_sha256=accepted.canonical_sha256,
            objective_owner_authority_artifact_id=owner.artifact_id,
            objective_owner_authority_sha256=owner.canonical_sha256,
            authorizing_principal_id=principal.principal_id,
            local_principal_authority_artifact_id=principal.artifact_id,
            local_principal_authority_sha256=principal.canonical_sha256,
            constraint_request_id=payload.constraint_request_id,
            constraint_request_version=payload.constraint_request_version,
            constraint_definition_id=payload.constraint_definition_id,
            constraint_definition_version=payload.constraint_definition_version,
            constraint_definition_sha256=payload.constraint_definition_sha256,
            parameters=payload.parameters,
            preauthorization_payload_sha256=payload.canonical_sha256,
        )


def serialize_constraint_preauthorization_payload(
    payload: ConstraintPreauthorizationPayload,
) -> bytes:
    return canonical_json_bytes(
        ConstraintPreauthorizationPayload.model_validate(payload.model_dump(mode="json"))
    )


def serialize_local_constraint_authorization_presentation(
    presentation: LocalConstraintAuthorizationPresentation,
) -> bytes:
    return canonical_json_bytes(
        LocalConstraintAuthorizationPresentation.model_validate(
            presentation.model_dump(mode="json")
        )
    )


def serialize_local_constraint_confirmation_evidence(
    evidence: LocalConstraintAuthorizationConfirmationEvidence,
) -> bytes:
    return canonical_json_bytes(
        LocalConstraintAuthorizationConfirmationEvidence.model_validate(
            evidence.model_dump(mode="json")
        )
    )


def _build_confirmation_evidence(
    presentation: LocalConstraintAuthorizationPresentation,
    *,
    decision: ConfirmationDecision,
    interaction_event: str,
    activated_control_id: str,
) -> LocalConstraintAuthorizationConfirmationEvidence:
    presentation_sha256 = canonical_sha256(presentation)
    suffix = "accepted" if decision is ConfirmationDecision.ACCEPTED else "refused"
    return LocalConstraintAuthorizationConfirmationEvidence(
        evidence_id=(
            f"local-constraint-confirmation:sha256:{presentation_sha256}:{suffix}"
        ),
        decision=decision,
        interaction_event=interaction_event,
        activated_control_id=activated_control_id,
        presentation=presentation,
        presentation_sha256=presentation_sha256,
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

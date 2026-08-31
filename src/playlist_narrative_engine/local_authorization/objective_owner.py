from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.local_authorization.canonical import (
    FrozenAuthorityModel,
    canonical_json_bytes,
    canonical_sha256,
    require_exact,
    verify_or_set_digest,
)
from playlist_narrative_engine.local_authorization.principal import (
    LocalPrincipalAuthorityArtifact,
    LocalPrincipalAuthorityInvalidInput,
    LocalPrincipalAuthorityVerifier,
)
from playlist_narrative_engine.objective_assessment import Objective
from playlist_narrative_engine.objective_safety import (
    AcceptedObjectiveArtifact,
    ObjectiveIntentCategory,
    ObjectiveIntentDeclarationArtifact,
    ObjectiveIntentEvidenceState,
    ObjectiveSafetyRequest,
    verify_objective_safety_artifact,
    verify_objective_safety_request,
)


LOCAL_OBJECTIVE_SUBMISSION_METHOD_ID = (
    "pne.local-objective-submission.exact-structured"
)
LOCAL_OBJECTIVE_SUBMISSION_METHOD_VERSION = "1.0"
LOCAL_OBJECTIVE_SUBMISSION_PRODUCER_ID = (
    "pne.local-objective-submission-capture-producer"
)
LOCAL_OBJECTIVE_SUBMISSION_PRODUCER_VERSION = "1.0"
OWNER_POLICY_ID = "pne.accepted-objective-owner.local-principal"
OWNER_POLICY_VERSION = "1.0"
OWNER_POLICY_SHA256 = (
    "a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e"
)
OWNER_PRODUCER_ID = "pne.accepted-objective-owner-authority-producer"
OWNER_PRODUCER_VERSION = "1.0"
_SUBMISSION_PRODUCER_CAPABILITY = object()

OWNER_POLICY_CONTENT = {
    "schema_version": "1.0",
    "definition_kind": "accepted_objective_owner_policy",
    "policy_id": OWNER_POLICY_ID,
    "policy_version": OWNER_POLICY_VERSION,
    "principal_authority_schema_version": "1.0",
    "submission_evidence_schema_version": "1.0",
    "intent_declaration_schema_version": "1.0",
    "accepted_objective_schema_version": "2.0",
    "ownership_basis": "PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION",
    "retrospective_database_locality_authority": False,
    "historical_objective_authorization_eligibility": False,
    "canonicalization_profile": "pne.canonical-json.utf8-schema-order/1.0",
}


def verify_owner_policy() -> bool:
    return canonical_sha256(OWNER_POLICY_CONTENT) == OWNER_POLICY_SHA256


class LocalObjectiveSubmissionEvidence(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    evidence_kind: Literal["local_objective_submission"] = (
        "local_objective_submission"
    )
    evidence_id: str
    submission_action: Literal["SUBMIT_OBJECTIVE_FOR_SAFETY_EVALUATION"] = (
        "SUBMIT_OBJECTIVE_FOR_SAFETY_EVALUATION"
    )
    local_principal_authority_artifact_id: str
    local_principal_authority_schema_version: Literal["1.0"] = "1.0"
    local_principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_id: str
    objective_statement_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration_id: str
    intent_declaration_schema_version: Literal["1.0"] = "1.0"
    intent_declaration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_method_id: Literal[
        "pne.local-objective-submission.exact-structured"
    ] = LOCAL_OBJECTIVE_SUBMISSION_METHOD_ID
    capture_method_version: Literal["1.0"] = LOCAL_OBJECTIVE_SUBMISSION_METHOD_VERSION
    capture_producer_authority_id: Literal[
        "pne.local-objective-submission-capture-producer"
    ] = LOCAL_OBJECTIVE_SUBMISSION_PRODUCER_ID
    capture_producer_authority_version: Literal["1.0"] = (
        LOCAL_OBJECTIVE_SUBMISSION_PRODUCER_VERSION
    )
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "evidence_id",
        "local_principal_authority_artifact_id",
        "objective_id",
        "intent_declaration_id",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def require_digest(self) -> LocalObjectiveSubmissionEvidence:
        verify_or_set_digest(self)
        return self


class AcceptedObjectiveOwnerAuthorityRequest(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    request_kind: Literal["accepted_objective_owner_authority"] = (
        "accepted_objective_owner_authority"
    )
    request_id: str
    request_version: Literal["1.0"] = "1.0"
    local_principal_authority_artifact_id: str
    local_principal_authority_schema_version: Literal["1.0"] = "1.0"
    local_principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_submission_evidence_id: str
    objective_submission_evidence_schema_version: Literal["1.0"] = "1.0"
    objective_submission_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration_id: str
    intent_declaration_schema_version: Literal["1.0"] = "1.0"
    intent_declaration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: Literal["2.0"] = "2.0"
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_policy_id: Literal[
        "pne.accepted-objective-owner.local-principal"
    ] = OWNER_POLICY_ID
    owner_policy_version: Literal["1.0"] = OWNER_POLICY_VERSION
    owner_policy_sha256: Literal[
        "a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e"
    ] = OWNER_POLICY_SHA256
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "request_id",
        "local_principal_authority_artifact_id",
        "objective_submission_evidence_id",
        "intent_declaration_id",
        "accepted_objective_artifact_id",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def require_policy_and_digest(self) -> AcceptedObjectiveOwnerAuthorityRequest:
        if not verify_owner_policy():
            raise ValueError("accepted-objective owner policy authority is invalid")
        verify_or_set_digest(self)
        return self


class AcceptedObjectiveOwnerAuthorityArtifact(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["accepted_objective_owner_authority"] = (
        "accepted_objective_owner_authority"
    )
    artifact_id: str
    artifact_version: Literal["1.0"] = "1.0"
    input_request_id: str
    input_request_schema_version: Literal["1.0"] = "1.0"
    input_request_version: Literal["1.0"] = "1.0"
    input_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    owner_principal_id: str
    local_principal_authority_artifact_id: str
    local_principal_authority_schema_version: Literal["1.0"] = "1.0"
    local_principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    objective_submission_evidence_id: str
    objective_submission_evidence_schema_version: Literal["1.0"] = "1.0"
    objective_submission_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intent_declaration_id: str
    intent_declaration_schema_version: Literal["1.0"] = "1.0"
    intent_declaration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    accepted_objective_artifact_id: str
    accepted_objective_schema_version: Literal["2.0"] = "2.0"
    accepted_objective_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    ownership_basis: Literal["PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION"] = (
        "PROSPECTIVE_LOCAL_OBJECTIVE_SUBMISSION"
    )
    owner_policy_id: Literal[
        "pne.accepted-objective-owner.local-principal"
    ] = OWNER_POLICY_ID
    owner_policy_version: Literal["1.0"] = OWNER_POLICY_VERSION
    owner_policy_sha256: Literal[
        "a94a53108f25f1f4fe16c12638529633314e7d68962a31d9b0505e136641229e"
    ] = OWNER_POLICY_SHA256
    producer_authority_id: Literal[
        "pne.accepted-objective-owner-authority-producer"
    ] = OWNER_PRODUCER_ID
    producer_authority_version: Literal["1.0"] = OWNER_PRODUCER_VERSION
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "artifact_id",
        "input_request_id",
        "owner_principal_id",
        "local_principal_authority_artifact_id",
        "objective_submission_evidence_id",
        "intent_declaration_id",
        "accepted_objective_artifact_id",
    )
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def require_identity_and_digest(self) -> AcceptedObjectiveOwnerAuthorityArtifact:
        expected_id = f"accepted-objective-owner:sha256:{self.input_request_sha256}"
        if self.artifact_id != expected_id:
            raise ValueError("owner artifact identity must bind the input request digest")
        verify_or_set_digest(self)
        return self


@dataclass(frozen=True)
class LocalObjectiveSubmissionBundle:
    principal_authority: LocalPrincipalAuthorityArtifact
    evidence: LocalObjectiveSubmissionEvidence
    intent_declaration: ObjectiveIntentDeclarationArtifact


@dataclass(frozen=True)
class AcceptedObjectiveOwnerAuthorityBundle:
    submission: LocalObjectiveSubmissionBundle
    objective_safety_request: ObjectiveSafetyRequest
    accepted_objective: AcceptedObjectiveArtifact
    request: AcceptedObjectiveOwnerAuthorityRequest
    artifact: AcceptedObjectiveOwnerAuthorityArtifact


class LocalObjectiveSubmissionAuthorityRepository:
    def __init__(self) -> None:
        self._records: dict[str, LocalObjectiveSubmissionBundle] = {}

    def _record(
        self, bundle: LocalObjectiveSubmissionBundle, capability: object
    ) -> None:
        if capability is not _SUBMISSION_PRODUCER_CAPABILITY:
            raise LocalObjectiveOwnerInvalidInput(
                "only the submission capture producer may record evidence"
            )
        if bundle.evidence.evidence_id in self._records:
            raise LocalObjectiveOwnerInvalidInput("submission evidence identity exists")
        self._records[bundle.evidence.evidence_id] = bundle

    def verify(self, bundle: LocalObjectiveSubmissionBundle) -> bool:
        stored = self._records.get(bundle.evidence.evidence_id)
        if stored != bundle:
            return False
        try:
            evidence = LocalObjectiveSubmissionEvidence.model_validate(
                bundle.evidence.model_dump(mode="json")
            )
            declaration = ObjectiveIntentDeclarationArtifact.model_validate(
                bundle.intent_declaration.model_dump(mode="json")
            )
        except (TypeError, ValueError):
            return False
        return evidence == bundle.evidence and declaration == bundle.intent_declaration


class LocalObjectiveOwnerInvalidInput(ValueError):
    pass


class LocalObjectiveSubmissionCaptureProducer:
    def __init__(
        self,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        repository: LocalObjectiveSubmissionAuthorityRepository,
    ) -> None:
        self._principal_verifier = principal_verifier
        self._repository = repository

    def capture(
        self,
        *,
        objective: Objective,
        intent_category: ObjectiveIntentCategory,
    ) -> LocalObjectiveSubmissionBundle:
        if not isinstance(objective, Objective) or not isinstance(
            intent_category, ObjectiveIntentCategory
        ):
            raise LocalObjectiveOwnerInvalidInput(
                "governed objective submission requires exact structured input"
            )
        try:
            principal = self._principal_verifier.resolve_active()
        except LocalPrincipalAuthorityInvalidInput as exc:
            raise LocalObjectiveOwnerInvalidInput(str(exc)) from exc
        evidence_id = f"local-objective-submission:{secrets.token_hex(16)}"
        declaration = ObjectiveIntentDeclarationArtifact(
            declaration_id=f"local-objective-intent:{secrets.token_hex(16)}",
            objective_id=objective.objective_id,
            objective_statement_sha256=_statement_sha256(objective.statement),
            authority_reference=evidence_id,
            state=ObjectiveIntentEvidenceState.ESTABLISHED,
            intent_category=intent_category,
        )
        evidence = LocalObjectiveSubmissionEvidence(
            evidence_id=evidence_id,
            local_principal_authority_artifact_id=principal.artifact_id,
            local_principal_authority_sha256=principal.canonical_sha256,
            objective_id=objective.objective_id,
            objective_statement_sha256=_statement_sha256(objective.statement),
            intent_declaration_id=declaration.declaration_id,
            intent_declaration_sha256=declaration.canonical_sha256,
        )
        bundle = LocalObjectiveSubmissionBundle(principal, evidence, declaration)
        self._repository._record(bundle, _SUBMISSION_PRODUCER_CAPABILITY)
        if not self._repository.verify(bundle):
            raise RuntimeError("submission capture produced unverifiable evidence")
        return bundle


class AcceptedObjectiveOwnerAuthorityVerifier:
    def __init__(
        self,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        submission_repository: LocalObjectiveSubmissionAuthorityRepository,
    ) -> None:
        self._principal_verifier = principal_verifier
        self._submission_repository = submission_repository

    def verify(self, bundle: AcceptedObjectiveOwnerAuthorityBundle) -> bool:
        try:
            submission = bundle.submission
            principal = submission.principal_authority
            evidence = submission.evidence
            declaration = submission.intent_declaration
            safety_request = bundle.objective_safety_request
            accepted = bundle.accepted_objective
            request = AcceptedObjectiveOwnerAuthorityRequest.model_validate(
                bundle.request.model_dump(mode="json")
            )
            artifact = AcceptedObjectiveOwnerAuthorityArtifact.model_validate(
                bundle.artifact.model_dump(mode="json")
            )
        except (TypeError, ValueError):
            return False
        if not self._principal_verifier.verify(principal):
            return False
        if not self._submission_repository.verify(submission):
            return False
        if (
            evidence.local_principal_authority_artifact_id != principal.artifact_id
            or evidence.local_principal_authority_schema_version
            != principal.schema_version
            or evidence.local_principal_authority_sha256 != principal.canonical_sha256
            or evidence.objective_id != declaration.objective_id
            or evidence.objective_statement_sha256
            != declaration.objective_statement_sha256
            or evidence.intent_declaration_id != declaration.declaration_id
            or evidence.intent_declaration_schema_version != declaration.schema_version
            or evidence.intent_declaration_sha256 != declaration.canonical_sha256
            or declaration.authority_reference != evidence.evidence_id
        ):
            return False
        if not verify_objective_safety_request(safety_request):
            return False
        if not verify_objective_safety_artifact(accepted, request=safety_request):
            return False
        objective = safety_request.objective_assessment.objective
        if (
            safety_request.intent_declaration != declaration
            or accepted.input_binding.intent_declaration_id != declaration.declaration_id
            or accepted.input_binding.intent_declaration_schema_version
            != declaration.schema_version
            or accepted.input_binding.intent_declaration_sha256
            != declaration.canonical_sha256
            or accepted.objective.objective_id != evidence.objective_id
            or _statement_sha256(accepted.objective.statement)
            != evidence.objective_statement_sha256
            or objective != accepted.objective
        ):
            return False
        expected_request = _build_owner_request(principal, evidence, declaration, accepted)
        if request != bundle.request or request != expected_request:
            return False
        expected_artifact = _build_owner_artifact(
            request, principal, evidence, declaration, accepted
        )
        return artifact == bundle.artifact and artifact == expected_artifact


class AcceptedObjectiveOwnerAuthorityProducer:
    def __init__(self, verifier: AcceptedObjectiveOwnerAuthorityVerifier) -> None:
        self.verifier = verifier

    def produce(
        self,
        *,
        submission: LocalObjectiveSubmissionBundle,
        objective_safety_request: ObjectiveSafetyRequest,
        accepted_objective: AcceptedObjectiveArtifact,
    ) -> AcceptedObjectiveOwnerAuthorityBundle:
        request = _build_owner_request(
            submission.principal_authority,
            submission.evidence,
            submission.intent_declaration,
            accepted_objective,
        )
        artifact = _build_owner_artifact(
            request,
            submission.principal_authority,
            submission.evidence,
            submission.intent_declaration,
            accepted_objective,
        )
        bundle = AcceptedObjectiveOwnerAuthorityBundle(
            submission,
            objective_safety_request,
            accepted_objective,
            request,
            artifact,
        )
        if not self.verifier.verify(bundle):
            raise LocalObjectiveOwnerInvalidInput(
                "objective owner authority inputs do not correspond exactly"
            )
        return bundle


def serialize_local_objective_submission(
    evidence: LocalObjectiveSubmissionEvidence,
) -> bytes:
    return canonical_json_bytes(
        LocalObjectiveSubmissionEvidence.model_validate(
            evidence.model_dump(mode="json")
        )
    )


def serialize_accepted_objective_owner_request(
    request: AcceptedObjectiveOwnerAuthorityRequest,
) -> bytes:
    return canonical_json_bytes(
        AcceptedObjectiveOwnerAuthorityRequest.model_validate(
            request.model_dump(mode="json")
        )
    )


def serialize_accepted_objective_owner_artifact(
    artifact: AcceptedObjectiveOwnerAuthorityArtifact,
) -> bytes:
    return canonical_json_bytes(
        AcceptedObjectiveOwnerAuthorityArtifact.model_validate(
            artifact.model_dump(mode="json")
        )
    )


def _build_owner_request(
    principal: LocalPrincipalAuthorityArtifact,
    evidence: LocalObjectiveSubmissionEvidence,
    declaration: ObjectiveIntentDeclarationArtifact,
    accepted: AcceptedObjectiveArtifact,
) -> AcceptedObjectiveOwnerAuthorityRequest:
    return AcceptedObjectiveOwnerAuthorityRequest(
        request_id=f"accepted-objective-owner-request:{accepted.canonical_sha256}",
        local_principal_authority_artifact_id=principal.artifact_id,
        local_principal_authority_sha256=principal.canonical_sha256,
        objective_submission_evidence_id=evidence.evidence_id,
        objective_submission_evidence_sha256=evidence.canonical_sha256,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
        accepted_objective_artifact_id=accepted.artifact_id,
        accepted_objective_sha256=accepted.canonical_sha256,
    )


def _build_owner_artifact(
    request: AcceptedObjectiveOwnerAuthorityRequest,
    principal: LocalPrincipalAuthorityArtifact,
    evidence: LocalObjectiveSubmissionEvidence,
    declaration: ObjectiveIntentDeclarationArtifact,
    accepted: AcceptedObjectiveArtifact,
) -> AcceptedObjectiveOwnerAuthorityArtifact:
    return AcceptedObjectiveOwnerAuthorityArtifact(
        artifact_id=f"accepted-objective-owner:sha256:{request.canonical_sha256}",
        input_request_id=request.request_id,
        input_request_sha256=request.canonical_sha256,
        owner_principal_id=principal.principal_id,
        local_principal_authority_artifact_id=principal.artifact_id,
        local_principal_authority_sha256=principal.canonical_sha256,
        objective_submission_evidence_id=evidence.evidence_id,
        objective_submission_evidence_sha256=evidence.canonical_sha256,
        intent_declaration_id=declaration.declaration_id,
        intent_declaration_sha256=declaration.canonical_sha256,
        accepted_objective_artifact_id=accepted.artifact_id,
        accepted_objective_sha256=accepted.canonical_sha256,
    )


def _statement_sha256(statement: str) -> str:
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()

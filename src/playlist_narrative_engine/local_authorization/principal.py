from __future__ import annotations

import secrets
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.local_authorization.canonical import (
    FrozenAuthorityModel,
    canonical_json_bytes,
    canonical_sha256,
    model_content,
    require_exact,
    verify_or_set_digest,
)


LOCAL_PRINCIPAL_REGISTRY_ID = "pne.local-principal-authority-registry"
LOCAL_PRINCIPAL_REGISTRY_VERSION = "1.0"
LOCAL_PRINCIPAL_REGISTRY_SHA256 = (
    "0d132a5ba0b1e619d9c1b6b7f807878ad3e321abcbe352cc36e20c9d4d655ab3"
)
LOCAL_PRINCIPAL_PRODUCER_ID = "pne.local-principal-authority-producer"
LOCAL_PRINCIPAL_PRODUCER_VERSION = "1.0"
_PRODUCER_CAPABILITY = object()

LOCAL_PRINCIPAL_REGISTRY_CONTENT = {
    "schema_version": "1.0",
    "definition_kind": "local_principal_policy_registry",
    "registry_id": LOCAL_PRINCIPAL_REGISTRY_ID,
    "registry_version": LOCAL_PRINCIPAL_REGISTRY_VERSION,
    "principal_scope": "PENNY_LOCAL_INSTALLATION",
    "principal_id_assignment": "SOLE_PRODUCER_GENERATED_OPAQUE",
    "installation_id_assignment": "SOLE_PRODUCER_GENERATED_OPAQUE",
    "active_principal_limit": 1,
    "initial_predecessor_required": False,
    "successor_predecessor_required": True,
    "caller_identity_authority": False,
    "real_world_identity_claim": False,
    "os_identity_claim": False,
    "account_identity_claim": False,
    "authoritative_time_claim": False,
    "canonicalization_profile": "pne.canonical-json.utf8-schema-order/1.0",
}


def verify_local_principal_registry() -> bool:
    return canonical_sha256(LOCAL_PRINCIPAL_REGISTRY_CONTENT) == (
        LOCAL_PRINCIPAL_REGISTRY_SHA256
    )


class LocalPrincipalAuthorityArtifact(FrozenAuthorityModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["local_principal_authority"] = (
        "local_principal_authority"
    )
    artifact_id: str
    artifact_version: Literal["1.0"] = "1.0"
    installation_id: str
    principal_id: str
    principal_version: str
    principal_scope: Literal["PENNY_LOCAL_INSTALLATION"] = (
        "PENNY_LOCAL_INSTALLATION"
    )
    principal_state_at_issuance: Literal["ACTIVE"] = "ACTIVE"
    predecessor_artifact_id: str | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    predecessor_artifact_schema_version: str | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    predecessor_artifact_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )
    predecessor_principal_id: str | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    principal_registry_id: Literal[
        "pne.local-principal-authority-registry"
    ] = LOCAL_PRINCIPAL_REGISTRY_ID
    principal_registry_version: Literal["1.0"] = LOCAL_PRINCIPAL_REGISTRY_VERSION
    principal_registry_sha256: Literal[
        "0d132a5ba0b1e619d9c1b6b7f807878ad3e321abcbe352cc36e20c9d4d655ab3"
    ] = LOCAL_PRINCIPAL_REGISTRY_SHA256
    producer_authority_id: Literal[
        "pne.local-principal-authority-producer"
    ] = LOCAL_PRINCIPAL_PRODUCER_ID
    producer_authority_version: Literal["1.0"] = LOCAL_PRINCIPAL_PRODUCER_VERSION
    legal_identity_established: Literal[False] = False
    biological_identity_established: Literal[False] = False
    os_identity_established: Literal[False] = False
    account_ownership_established: Literal[False] = False
    physical_operator_identity_established: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "artifact_id",
        "installation_id",
        "principal_id",
        "principal_version",
        "predecessor_artifact_id",
        "predecessor_artifact_schema_version",
        "predecessor_principal_id",
    )
    @classmethod
    def require_exact_identity(cls, value: str | None) -> str | None:
        return require_exact(value) if value is not None else None

    @model_validator(mode="after")
    def require_variant_and_digest(self) -> LocalPrincipalAuthorityArtifact:
        predecessor = (
            self.predecessor_artifact_id,
            self.predecessor_artifact_schema_version,
            self.predecessor_artifact_sha256,
            self.predecessor_principal_id,
        )
        if any(item is not None for item in predecessor) and not all(
            item is not None for item in predecessor
        ):
            raise ValueError("predecessor lineage must be complete or absent")
        if not verify_local_principal_registry():
            raise ValueError("local principal registry authority is invalid")
        verify_or_set_digest(self)
        return self


class LocalPrincipalAuthorityRepository:
    """One installation-local immutable principal lineage."""

    def __init__(self) -> None:
        self._installation_id: str | None = None
        self._artifacts: list[LocalPrincipalAuthorityArtifact] = []

    @property
    def artifacts(self) -> tuple[LocalPrincipalAuthorityArtifact, ...]:
        return tuple(self._artifacts)

    def _record_initial(
        self, artifact: LocalPrincipalAuthorityArtifact, capability: object
    ) -> None:
        if capability is not _PRODUCER_CAPABILITY:
            raise LocalPrincipalAuthorityInvalidInput(
                "only the principal producer may record authority"
            )
        if self._artifacts or self._installation_id is not None:
            raise LocalPrincipalAuthorityInvalidInput(
                "installation already has a principal lineage"
            )
        self._installation_id = artifact.installation_id
        self._artifacts.append(artifact)

    def _record_successor(
        self, artifact: LocalPrincipalAuthorityArtifact, capability: object
    ) -> None:
        if capability is not _PRODUCER_CAPABILITY:
            raise LocalPrincipalAuthorityInvalidInput(
                "only the principal producer may record authority"
            )
        if self._installation_id != artifact.installation_id:
            raise LocalPrincipalAuthorityInvalidInput(
                "successor installation authority does not correspond"
            )
        self._artifacts.append(artifact)


class LocalPrincipalAuthorityInvalidInput(ValueError):
    pass


class LocalPrincipalAuthorityVerifier:
    def __init__(self, repository: LocalPrincipalAuthorityRepository) -> None:
        self._repository = repository

    def resolve_active(self) -> LocalPrincipalAuthorityArtifact:
        lineage = self._verified_lineage()
        referenced = {
            item.predecessor_artifact_id
            for item in lineage
            if item.predecessor_artifact_id is not None
        }
        tips = tuple(item for item in lineage if item.artifact_id not in referenced)
        if len(tips) != 1:
            raise LocalPrincipalAuthorityInvalidInput(
                "principal lineage must have exactly one applicable tip"
            )
        return tips[0]

    def verify(
        self,
        artifact: LocalPrincipalAuthorityArtifact,
        *,
        require_active: bool = False,
    ) -> bool:
        try:
            lineage = self._verified_lineage()
            exact = next(
                item for item in lineage if item.artifact_id == artifact.artifact_id
            )
            if exact != artifact:
                return False
            return not require_active or self.resolve_active() == artifact
        except (StopIteration, TypeError, ValueError):
            return False

    def _verified_lineage(self) -> tuple[LocalPrincipalAuthorityArtifact, ...]:
        artifacts = self._repository.artifacts
        if not artifacts:
            raise LocalPrincipalAuthorityInvalidInput("principal lineage is absent")
        reparsed = tuple(
            LocalPrincipalAuthorityArtifact.model_validate(item.model_dump(mode="json"))
            for item in artifacts
        )
        if reparsed != artifacts:
            raise LocalPrincipalAuthorityInvalidInput("principal lineage is not exact")
        if any(
            value.startswith("example.invalid/")
            for artifact in artifacts
            for value in (
                artifact.artifact_id,
                artifact.installation_id,
                artifact.principal_id,
            )
        ):
            raise LocalPrincipalAuthorityInvalidInput(
                "conformance fixture identities have no production authority"
            )
        installation_ids = {item.installation_id for item in artifacts}
        artifact_ids = {item.artifact_id for item in artifacts}
        principal_ids = {item.principal_id for item in artifacts}
        initials = tuple(item for item in artifacts if item.predecessor_artifact_id is None)
        if (
            len(installation_ids) != 1
            or len(initials) != 1
            or len(artifact_ids) != len(artifacts)
            or len(principal_ids) != len(artifacts)
        ):
            raise LocalPrincipalAuthorityInvalidInput(
                "principal lineage identity or initial authority is ambiguous"
            )
        by_id = {item.artifact_id: item for item in artifacts}
        successor_counts: dict[str, int] = {}
        for item in artifacts:
            predecessor_id = item.predecessor_artifact_id
            if predecessor_id is None:
                continue
            predecessor = by_id.get(predecessor_id)
            if (
                predecessor is None
                or item.predecessor_artifact_schema_version != predecessor.schema_version
                or item.predecessor_artifact_sha256 != predecessor.canonical_sha256
                or item.predecessor_principal_id != predecessor.principal_id
                or item.installation_id != predecessor.installation_id
            ):
                raise LocalPrincipalAuthorityInvalidInput(
                    "principal predecessor authority does not correspond"
                )
            successor_counts[predecessor_id] = successor_counts.get(predecessor_id, 0) + 1
        if any(count != 1 for count in successor_counts.values()):
            raise LocalPrincipalAuthorityInvalidInput("principal lineage branches")
        visited: set[str] = set()
        current = initials[0]
        while True:
            if current.artifact_id in visited:
                raise LocalPrincipalAuthorityInvalidInput("principal lineage cycles")
            visited.add(current.artifact_id)
            successors = tuple(
                item
                for item in artifacts
                if item.predecessor_artifact_id == current.artifact_id
            )
            if not successors:
                break
            current = successors[0]
        if visited != artifact_ids:
            raise LocalPrincipalAuthorityInvalidInput(
                "principal lineage contains disconnected authority"
            )
        return artifacts


class LocalPrincipalAuthorityProducer:
    def __init__(self, repository: LocalPrincipalAuthorityRepository) -> None:
        self._repository = repository
        self.verifier = LocalPrincipalAuthorityVerifier(repository)

    def create_initial(self) -> LocalPrincipalAuthorityArtifact:
        if self._repository.artifacts:
            raise LocalPrincipalAuthorityInvalidInput(
                "installation already has an active principal"
            )
        installation_id = _opaque_id("penny-local-installation")
        principal_id = _opaque_id("penny-local-principal")
        artifact = _build_principal_artifact(
            artifact_id=_opaque_id("local-principal-authority"),
            installation_id=installation_id,
            principal_id=principal_id,
        )
        self._repository._record_initial(artifact, _PRODUCER_CAPABILITY)
        if not self.verifier.verify(artifact, require_active=True):
            raise RuntimeError("principal producer created unverifiable authority")
        return artifact

    def create_successor(
        self, predecessor: LocalPrincipalAuthorityArtifact
    ) -> LocalPrincipalAuthorityArtifact:
        active = self.verifier.resolve_active()
        if predecessor != active:
            raise LocalPrincipalAuthorityInvalidInput(
                "successor requires the exact applicable predecessor"
            )
        artifact = _build_principal_artifact(
            artifact_id=_opaque_id("local-principal-authority"),
            installation_id=active.installation_id,
            principal_id=_opaque_id("penny-local-principal"),
            predecessor=active,
        )
        self._repository._record_successor(artifact, _PRODUCER_CAPABILITY)
        if not self.verifier.verify(artifact, require_active=True):
            raise RuntimeError("principal producer created unverifiable successor")
        return artifact


def serialize_local_principal_authority(
    artifact: LocalPrincipalAuthorityArtifact,
) -> bytes:
    validated = LocalPrincipalAuthorityArtifact.model_validate(
        artifact.model_dump(mode="json")
    )
    return canonical_json_bytes(validated)


def _opaque_id(kind: str) -> str:
    return f"{kind}:{secrets.token_hex(16)}"


def _build_principal_artifact(
    *,
    artifact_id: str,
    installation_id: str,
    principal_id: str,
    predecessor: LocalPrincipalAuthorityArtifact | None = None,
) -> LocalPrincipalAuthorityArtifact:
    content: dict[str, object] = {
        "schema_version": "1.0",
        "artifact_kind": "local_principal_authority",
        "artifact_id": artifact_id,
        "artifact_version": "1.0",
        "installation_id": installation_id,
        "principal_id": principal_id,
        "principal_version": "1.0",
        "principal_scope": "PENNY_LOCAL_INSTALLATION",
        "principal_state_at_issuance": "ACTIVE",
    }
    if predecessor is not None:
        content.update(
            {
                "predecessor_artifact_id": predecessor.artifact_id,
                "predecessor_artifact_schema_version": predecessor.schema_version,
                "predecessor_artifact_sha256": predecessor.canonical_sha256,
                "predecessor_principal_id": predecessor.principal_id,
            }
        )
    content.update(
        {
            "principal_registry_id": LOCAL_PRINCIPAL_REGISTRY_ID,
            "principal_registry_version": LOCAL_PRINCIPAL_REGISTRY_VERSION,
            "principal_registry_sha256": LOCAL_PRINCIPAL_REGISTRY_SHA256,
            "producer_authority_id": LOCAL_PRINCIPAL_PRODUCER_ID,
            "producer_authority_version": LOCAL_PRINCIPAL_PRODUCER_VERSION,
            "legal_identity_established": False,
            "biological_identity_established": False,
            "os_identity_established": False,
            "account_ownership_established": False,
            "physical_operator_identity_established": False,
        }
    )
    digest = canonical_sha256(content)
    return LocalPrincipalAuthorityArtifact(**content, canonical_sha256=digest)

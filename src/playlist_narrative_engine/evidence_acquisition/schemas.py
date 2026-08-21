from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.schemas import (
    CandidateIdentityMetadataArtifact,
    CandidateIdentityMetadataRecord,
    EvidenceState,
)
from playlist_narrative_engine.track_evidence import EvidenceSnapshot


ACQUISITION_SCHEMA_VERSION = "1.0"


class FrozenAcquisitionModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AuthoritativeMetadataField(StrEnum):
    SOURCE_CATALOG_IDENTITY = "source_catalog_identity"
    RELEASE_VERSION_IDENTITY = "release_version_identity"
    DISPLAYED_EXPLICIT = "displayed_explicit"


class MetadataCapability(FrozenAcquisitionModel):
    field: AuthoritativeMetadataField
    authoritative: bool


class SourceCapabilityDeclaration(FrozenAcquisitionModel):
    schema_version: Literal["1.0"] = ACQUISITION_SCHEMA_VERSION
    declaration_id: str = Field(min_length=1, max_length=200)
    declaration_version: str = Field(min_length=1, max_length=100)
    adapter_id: str = Field(min_length=1, max_length=200)
    adapter_version: str = Field(min_length=1, max_length=100)
    capabilities: tuple[MetadataCapability, ...]

    @field_validator(
        "declaration_id", "declaration_version", "adapter_id", "adapter_version"
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("capabilities", mode="before")
    @classmethod
    def canonicalize_capabilities(cls, value: object) -> tuple[object, ...]:
        return tuple(
            sorted(
                tuple(value),
                key=lambda item: _field_value(item).encode("utf-8"),
            )
        )

    @model_validator(mode="after")
    def require_complete_capability_matrix(self) -> SourceCapabilityDeclaration:
        fields = tuple(item.field for item in self.capabilities)
        if len(fields) != len(set(fields)):
            raise ValueError("metadata capability fields must be unique")
        if set(fields) != set(AuthoritativeMetadataField):
            raise ValueError("capability declaration must cover every metadata field")
        return self

    def supports(self, field: AuthoritativeMetadataField) -> bool:
        return next(item.authoritative for item in self.capabilities if item.field is field)


class SourceNeutralAcquisitionResult(FrozenAcquisitionModel):
    schema_version: Literal["1.0"] = ACQUISITION_SCHEMA_VERSION
    artifact_kind: Literal["source_neutral_acquisition"] = "source_neutral_acquisition"
    acquisition_id: str = Field(min_length=1, max_length=200)
    source_receipt_id: str = Field(min_length=1, max_length=500)
    source_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    adapter_id: str = Field(min_length=1, max_length=200)
    adapter_version: str = Field(min_length=1, max_length=100)
    capability_declaration: SourceCapabilityDeclaration
    evidence_snapshot: EvidenceSnapshot
    evidence_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_metadata: CandidateIdentityMetadataArtifact

    @field_validator(
        "acquisition_id",
        "source_receipt_id",
        "source_type",
        "source_reference",
        "adapter_id",
        "adapter_version",
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_atomic_lineage_and_authority(self) -> SourceNeutralAcquisitionResult:
        declaration = self.capability_declaration
        if (
            declaration.adapter_id != self.adapter_id
            or declaration.adapter_version != self.adapter_version
        ):
            raise ValueError("capability declaration must match exact adapter identity")
        if self.identity_metadata.track_snapshot_id != self.evidence_snapshot.snapshot_id:
            raise ValueError("identity metadata must correspond to the acquired snapshot")
        expected_digest = hashlib.sha256(
            serialize_evidence_snapshot(self.evidence_snapshot)
        ).hexdigest()
        if self.evidence_snapshot_sha256 != expected_digest:
            raise ValueError("evidence snapshot digest must match canonical snapshot bytes")
        for record in self.identity_metadata.records:
            self._validate_record_authority(record)
        return self

    def _validate_record_authority(self, record: CandidateIdentityMetadataRecord) -> None:
        values = {
            AuthoritativeMetadataField.SOURCE_CATALOG_IDENTITY: record.source_catalog_identity,
            AuthoritativeMetadataField.RELEASE_VERSION_IDENTITY: record.release_version_identity,
            AuthoritativeMetadataField.DISPLAYED_EXPLICIT: record.displayed_explicit,
        }
        for field, evidence in values.items():
            supported = self.capability_declaration.supports(field)
            if supported and evidence.state is EvidenceState.UNSUPPORTED:
                raise ValueError(f"supported capability {field.value} cannot be UNSUPPORTED")
            if not supported and evidence.state is not EvidenceState.UNSUPPORTED:
                raise ValueError(
                    f"unsupported capability {field.value} must remain UNSUPPORTED"
                )
            for observation in evidence.observations:
                if (
                    observation.source_type != self.source_type
                    or observation.source_reference != self.source_reference
                ):
                    raise ValueError("metadata observation must match source-receipt lineage")


def serialize_evidence_snapshot(snapshot: EvidenceSnapshot) -> bytes:
    return json.dumps(
        snapshot.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def serialize_acquisition_result(result: SourceNeutralAcquisitionResult) -> bytes:
    return json.dumps(
        result.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("acquisition identities must be nonblank and exact")
    return value


def _field_value(item: object) -> str:
    value = item.get("field") if isinstance(item, dict) else getattr(item, "field", "")
    return value.value if isinstance(value, AuthoritativeMetadataField) else str(value)

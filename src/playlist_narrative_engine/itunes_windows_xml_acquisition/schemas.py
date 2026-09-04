from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation import (
    CandidateIdentityMetadataArtifact,
)
from playlist_narrative_engine.evidence_acquisition import (
    SourceCapabilityDeclaration,
    SourceNeutralAcquisitionResult,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    FrozenModel,
    require_exact,
    sha256_bytes,
    verify_or_set_digest,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    ACQUISITION_AUTHORITY_JSON,
    ACQUISITION_AUTHORITY_SHA256,
    ACQUISITION_AUTHORITY_V11_JSON,
    ACQUISITION_AUTHORITY_V11_SHA256,
    ADAPTER_ID,
    ADAPTER_VERSION,
    ADAPTER_VERSION_V11,
    CAPABILITY_DECLARATION,
    CAPABILITY_DECLARATION_JSON,
    CAPABILITY_DECLARATION_SHA256,
    CAPABILITY_DECLARATION_V11,
    CAPABILITY_DECLARATION_V11_JSON,
    CAPABILITY_DECLARATION_V11_SHA256,
    MAPPING_DEFINITION_JSON,
    MAPPING_DEFINITION_SHA256,
    SELECTION_MECHANISM,
    SOURCE_DEFINITION_JSON,
    SOURCE_DEFINITION_SHA256,
    SOURCE_DEFINITION_V11_JSON,
    SOURCE_DEFINITION_V11_SHA256,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityArtifact,
)
from playlist_narrative_engine.source_receipt import (
    ACQUISITION_INTERFACE_SHA256,
    ACQUISITION_INTERFACE_VERSION,
    CAPTURE_POINT_SHA256,
    CAPTURE_POINT_VERSION,
    SOURCE_RECEIPT_POLICY_SHA256,
    SOURCE_RECEIPT_POLICY_VERSION,
    SourceReceiptArtifact,
)
from playlist_narrative_engine.track_evidence import EvidenceSnapshot


class FrozenDefinitionBinding(FrozenModel):
    definition_id: str
    definition_version: Literal["1.0"] = "1.0"
    canonical_json: str
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("definition_id")
    @classmethod
    def exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_exact_content(self) -> FrozenDefinitionBinding:
        expected = {
            "pne.source-definition.itunes-windows-xml-single-playlist": (
                SOURCE_DEFINITION_JSON,
                SOURCE_DEFINITION_SHA256,
            ),
            "pne.source-mapping.itunes-windows-xml-track-evidence": (
                MAPPING_DEFINITION_JSON,
                MAPPING_DEFINITION_SHA256,
            ),
            "pne.acquisition-authority.itunes-windows-xml-single-playlist": (
                ACQUISITION_AUTHORITY_JSON,
                ACQUISITION_AUTHORITY_SHA256,
            ),
        }.get(self.definition_id)
        if expected is None or (self.canonical_json, self.canonical_sha256) != expected:
            raise ValueError("definition binding is not exact frozen authority")
        return self


SOURCE_DEFINITION = FrozenDefinitionBinding(
    definition_id="pne.source-definition.itunes-windows-xml-single-playlist",
    canonical_json=SOURCE_DEFINITION_JSON,
    canonical_sha256=SOURCE_DEFINITION_SHA256,
)
MAPPING_DEFINITION = FrozenDefinitionBinding(
    definition_id="pne.source-mapping.itunes-windows-xml-track-evidence",
    canonical_json=MAPPING_DEFINITION_JSON,
    canonical_sha256=MAPPING_DEFINITION_SHA256,
)
ACQUISITION_AUTHORITY_DEFINITION = FrozenDefinitionBinding(
    definition_id="pne.acquisition-authority.itunes-windows-xml-single-playlist",
    canonical_json=ACQUISITION_AUTHORITY_JSON,
    canonical_sha256=ACQUISITION_AUTHORITY_SHA256,
)


class FrozenDefinitionBindingV11(FrozenModel):
    definition_id: str
    definition_version: Literal["1.1"] = "1.1"
    canonical_json: str
    canonical_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("definition_id")
    @classmethod
    def exact_identity(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_exact_content(self) -> FrozenDefinitionBindingV11:
        expected = {
            "pne.source-definition.itunes-windows-xml-single-playlist": (
                SOURCE_DEFINITION_V11_JSON,
                SOURCE_DEFINITION_V11_SHA256,
            ),
            "pne.acquisition-authority.itunes-windows-xml-single-playlist": (
                ACQUISITION_AUTHORITY_V11_JSON,
                ACQUISITION_AUTHORITY_V11_SHA256,
            ),
        }.get(self.definition_id)
        if expected is None or (self.canonical_json, self.canonical_sha256) != expected:
            raise ValueError("definition binding is not exact frozen 1.1 authority")
        return self


SOURCE_DEFINITION_V11 = FrozenDefinitionBindingV11(
    definition_id="pne.source-definition.itunes-windows-xml-single-playlist",
    canonical_json=SOURCE_DEFINITION_V11_JSON,
    canonical_sha256=SOURCE_DEFINITION_V11_SHA256,
)
ACQUISITION_AUTHORITY_DEFINITION_V11 = FrozenDefinitionBindingV11(
    definition_id="pne.acquisition-authority.itunes-windows-xml-single-playlist",
    canonical_json=ACQUISITION_AUTHORITY_V11_JSON,
    canonical_sha256=ACQUISITION_AUTHORITY_V11_SHA256,
)


class PennyLocalITunesXMLIntakeRequest(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    request_kind: Literal["penny_local_itunes_xml_intake"] = (
        "penny_local_itunes_xml_intake"
    )
    intake_request_id: str
    principal_authority: LocalPrincipalAuthorityArtifact
    principal_lineage_prefix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_definition: FrozenDefinitionBinding = SOURCE_DEFINITION
    selection_mechanism: Literal[
        "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"
    ] = SELECTION_MECHANISM
    expected_item_count: Literal[1] = 1
    producer_authority_id: Literal[
        "pne.producer.penny-local-itunes-xml-intake"
    ] = "pne.producer.penny-local-itunes-xml-intake"
    producer_authority_version: Literal["1.0"] = "1.0"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("intake_request_id")
    @classmethod
    def exact_request_id(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_digest(self) -> PennyLocalITunesXMLIntakeRequest:
        if self.source_definition != SOURCE_DEFINITION:
            raise ValueError("intake request must bind frozen source definition")
        verify_or_set_digest(self)
        return self


class PennyLocalITunesXMLIntakeRequestV11(FrozenModel):
    schema_version: Literal["1.1"] = "1.1"
    request_kind: Literal["penny_local_itunes_xml_intake"] = (
        "penny_local_itunes_xml_intake"
    )
    intake_request_id: str
    principal_authority: LocalPrincipalAuthorityArtifact
    principal_lineage_prefix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_definition: FrozenDefinitionBindingV11 = SOURCE_DEFINITION_V11
    selection_mechanism: Literal[
        "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"
    ] = SELECTION_MECHANISM
    expected_item_count: Literal[1] = 1
    producer_authority_id: Literal[
        "pne.producer.penny-local-itunes-xml-intake"
    ] = "pne.producer.penny-local-itunes-xml-intake"
    producer_authority_version: Literal["1.1"] = "1.1"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("intake_request_id")
    @classmethod
    def exact_request_id(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_digest(self) -> PennyLocalITunesXMLIntakeRequestV11:
        if self.source_definition != SOURCE_DEFINITION_V11:
            raise ValueError("intake request must bind frozen 1.1 source definition")
        verify_or_set_digest(self)
        return self


class SourceReceiptImplementationConformanceArtifact(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["source_receipt_implementation_conformance"] = (
        "source_receipt_implementation_conformance"
    )
    artifact_id: str
    intake_request_id: str
    implementation_id: Literal[
        "pne.implementation.windows-native-single-file-picker-source-receipt"
    ] = "pne.implementation.windows-native-single-file-picker-source-receipt"
    implementation_version: Literal["1.0"] = "1.0"
    acquisition_interface_version: Literal["1.1"] = ACQUISITION_INTERFACE_VERSION
    acquisition_interface_sha256: Literal[
        "3c0fa70094789a07acd596188c6aa2a461b20e2ed1deb49d01740a9bfb8f8de8"
    ] = ACQUISITION_INTERFACE_SHA256
    capture_point_version: Literal["1.1"] = CAPTURE_POINT_VERSION
    capture_point_sha256: Literal[
        "0465a499cfcaeb9d9dea2886389038f9ce540489b372663df2875e724a3c5856"
    ] = CAPTURE_POINT_SHA256
    source_receipt_policy_version: Literal["1.1"] = SOURCE_RECEIPT_POLICY_VERSION
    source_receipt_policy_sha256: Literal[
        "6dc9164c3413436b582f08d83de154dd954cf2824ccdaa6e3e6d2c7476619e83"
    ] = SOURCE_RECEIPT_POLICY_SHA256
    selection_mechanism: Literal[
        "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"
    ] = SELECTION_MECHANISM
    observation_handle: str
    byte_length: int = Field(gt=0)
    byte_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt_id: str
    receipt_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    complete_one_item_response: Literal[True] = True
    bytes_captured_before_interpretation: Literal[True] = True
    path_authority_established: Literal[False] = False
    provider_conformance_established: Literal[False] = False
    producer_authority_id: Literal[
        "pne.producer.itunes-windows-xml-source-receipt-conformance"
    ] = "pne.producer.itunes-windows-xml-source-receipt-conformance"
    verifier_authority_id: Literal[
        "pne.verifier.itunes-windows-xml-source-receipt-conformance"
    ] = "pne.verifier.itunes-windows-xml-source-receipt-conformance"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id", "intake_request_id", "observation_handle", "receipt_id")
    @classmethod
    def exact_text(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_digest(self) -> SourceReceiptImplementationConformanceArtifact:
        verify_or_set_digest(self)
        return self


class PennyLocalITunesXMLFileSelectionEvidence(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["penny_local_itunes_xml_file_selection"] = (
        "penny_local_itunes_xml_file_selection"
    )
    evidence_id: str
    intake_request: PennyLocalITunesXMLIntakeRequest
    intake_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_id: str
    principal_authority_artifact_id: str
    principal_authority_schema_version: Literal["1.0"] = "1.0"
    principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    installation_id: str
    principal_lineage_prefix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_definition: FrozenDefinitionBinding = SOURCE_DEFINITION
    selection_mechanism: Literal[
        "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"
    ] = SELECTION_MECHANISM
    item_count: Literal[1] = 1
    byte_length: int = Field(gt=0)
    byte_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_receipt: SourceReceiptArtifact
    source_receipt_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_receipt_item_id: Literal["item-000001"] = "item-000001"
    implementation_conformance: SourceReceiptImplementationConformanceArtifact
    producer_authority_id: Literal[
        "pne.producer.penny-local-itunes-xml-intake"
    ] = "pne.producer.penny-local-itunes-xml-intake"
    producer_authority_version: Literal["1.0"] = "1.0"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "evidence_id", "principal_id", "principal_authority_artifact_id", "installation_id"
    )
    @classmethod
    def exact_text(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_complete_correspondence(self) -> PennyLocalITunesXMLFileSelectionEvidence:
        request = self.intake_request
        principal = request.principal_authority
        receipt = self.source_receipt
        if self.intake_request_sha256 != request.canonical_sha256:
            raise ValueError("selection evidence request digest mismatch")
        if (
            self.principal_id != principal.principal_id
            or self.principal_authority_artifact_id != principal.artifact_id
            or self.principal_authority_sha256 != principal.canonical_sha256
            or self.installation_id != principal.installation_id
            or self.principal_lineage_prefix_sha256
            != request.principal_lineage_prefix_sha256
        ):
            raise ValueError("selection evidence principal authority mismatch")
        if self.source_definition != request.source_definition:
            raise ValueError("selection evidence source definition mismatch")
        if len(receipt.items) != 1 or receipt.declared_item_count != 1:
            raise ValueError("selection evidence requires exactly one receipt item")
        item = receipt.items[0]
        if (
            item.item_id != self.source_receipt_item_id
            or len(item.payload) != self.byte_length
            or sha256_bytes(item.payload) != self.byte_sha256
        ):
            raise ValueError("selected bytes do not correspond to receipt item")
        conformance = self.implementation_conformance
        if (
            conformance.intake_request_id != request.intake_request_id
            or conformance.observation_handle != item.observation_handle.value
            or conformance.byte_length != self.byte_length
            or conformance.byte_sha256 != self.byte_sha256
            or conformance.receipt_id != receipt.receipt_id
            or conformance.receipt_artifact_sha256
            != self.source_receipt_artifact_sha256
        ):
            raise ValueError("implementation conformance does not correspond")
        verify_or_set_digest(self)
        return self


class PennyLocalITunesXMLFileSelectionEvidenceV11(FrozenModel):
    schema_version: Literal["1.1"] = "1.1"
    artifact_kind: Literal["penny_local_itunes_xml_file_selection"] = (
        "penny_local_itunes_xml_file_selection"
    )
    evidence_id: str
    intake_request: PennyLocalITunesXMLIntakeRequestV11
    intake_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    principal_id: str
    principal_authority_artifact_id: str
    principal_authority_schema_version: Literal["1.0"] = "1.0"
    principal_authority_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    installation_id: str
    principal_lineage_prefix_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_definition: FrozenDefinitionBindingV11 = SOURCE_DEFINITION_V11
    selection_mechanism: Literal[
        "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"
    ] = SELECTION_MECHANISM
    item_count: Literal[1] = 1
    byte_length: int = Field(gt=0)
    byte_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_receipt: SourceReceiptArtifact
    source_receipt_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_receipt_item_id: Literal["item-000001"] = "item-000001"
    implementation_conformance: SourceReceiptImplementationConformanceArtifact
    producer_authority_id: Literal[
        "pne.producer.penny-local-itunes-xml-intake"
    ] = "pne.producer.penny-local-itunes-xml-intake"
    producer_authority_version: Literal["1.1"] = "1.1"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator(
        "evidence_id", "principal_id", "principal_authority_artifact_id", "installation_id"
    )
    @classmethod
    def exact_text(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_complete_correspondence(self) -> PennyLocalITunesXMLFileSelectionEvidenceV11:
        request = self.intake_request
        principal = request.principal_authority
        receipt = self.source_receipt
        if self.intake_request_sha256 != request.canonical_sha256:
            raise ValueError("selection evidence request digest mismatch")
        if (
            self.principal_id != principal.principal_id
            or self.principal_authority_artifact_id != principal.artifact_id
            or self.principal_authority_sha256 != principal.canonical_sha256
            or self.installation_id != principal.installation_id
            or self.principal_lineage_prefix_sha256
            != request.principal_lineage_prefix_sha256
        ):
            raise ValueError("selection evidence principal authority mismatch")
        if self.source_definition != request.source_definition:
            raise ValueError("selection evidence source definition mismatch")
        if len(receipt.items) != 1 or receipt.declared_item_count != 1:
            raise ValueError("selection evidence requires exactly one receipt item")
        item = receipt.items[0]
        if (
            item.item_id != self.source_receipt_item_id
            or len(item.payload) != self.byte_length
            or sha256_bytes(item.payload) != self.byte_sha256
        ):
            raise ValueError("selected bytes do not correspond to receipt item")
        conformance = self.implementation_conformance
        if (
            conformance.intake_request_id != request.intake_request_id
            or conformance.observation_handle != item.observation_handle.value
            or conformance.byte_length != self.byte_length
            or conformance.byte_sha256 != self.byte_sha256
            or conformance.receipt_id != receipt.receipt_id
            or conformance.receipt_artifact_sha256
            != self.source_receipt_artifact_sha256
        ):
            raise ValueError("implementation conformance does not correspond")
        verify_or_set_digest(self)
        return self


class OrderedTrackAuthority(FrozenModel):
    ordinal: int = Field(gt=0)
    track_id: str
    source_duration_milliseconds: int = Field(gt=0)

    @field_validator("track_id")
    @classmethod
    def exact_track_id(cls, value: str) -> str:
        return require_exact(value)


class PennyLocalITunesXMLAcquisitionAuthorityArtifact(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["penny_local_itunes_xml_acquisition_authority"] = (
        "penny_local_itunes_xml_acquisition_authority"
    )
    artifact_id: str
    file_selection_evidence: PennyLocalITunesXMLFileSelectionEvidence
    file_selection_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquisition_authority_definition: FrozenDefinitionBinding = (
        ACQUISITION_AUTHORITY_DEFINITION
    )
    source_definition: FrozenDefinitionBinding = SOURCE_DEFINITION
    mapping_definition: FrozenDefinitionBinding = MAPPING_DEFINITION
    capability_declaration: SourceCapabilityDeclaration = CAPABILITY_DECLARATION
    capability_declaration_json: Literal[CAPABILITY_DECLARATION_JSON] = (
        CAPABILITY_DECLARATION_JSON
    )
    capability_declaration_sha256: Literal[
        "f5a8cda68b976a14a6efef6f45f39a8f22f15178ecc4165a0d84d32b3e71f514"
    ] = CAPABILITY_DECLARATION_SHA256
    adapter_id: Literal["pne.adapter.itunes-windows-xml-single-playlist"] = ADAPTER_ID
    adapter_version: Literal["1.0"] = ADAPTER_VERSION
    library_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    playlist_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    ordered_tracks: tuple[OrderedTrackAuthority, ...]
    evidence_snapshot: EvidenceSnapshot
    evidence_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_metadata: CandidateIdentityMetadataArtifact
    identity_metadata_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_neutral_acquisition_result: SourceNeutralAcquisitionResult
    source_neutral_acquisition_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    producer_authority_id: Literal[
        "pne.producer.itunes-windows-xml-acquisition-authority"
    ] = "pne.producer.itunes-windows-xml-acquisition-authority"
    producer_authority_version: Literal["1.0"] = "1.0"
    verifier_authority_id: Literal[
        "pne.verifier.itunes-windows-xml-acquisition-authority"
    ] = "pne.verifier.itunes-windows-xml-acquisition-authority"
    verifier_authority_version: Literal["1.0"] = "1.0"
    apple_authorship_established: Literal[False] = False
    pre_intake_integrity_established: Literal[False] = False
    export_freshness_established: Literal[False] = False
    current_state_established: Literal[False] = False
    provider_authentication_established: Literal[False] = False
    media_inspection_performed: Literal[False] = False
    release_version_identity_established: Literal[False] = False
    displayed_explicit_established: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id")
    @classmethod
    def exact_artifact_id(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_structure(self) -> PennyLocalITunesXMLAcquisitionAuthorityArtifact:
        if (
            self.acquisition_authority_definition != ACQUISITION_AUTHORITY_DEFINITION
            or self.source_definition != SOURCE_DEFINITION
            or self.mapping_definition != MAPPING_DEFINITION
            or self.capability_declaration != CAPABILITY_DECLARATION
        ):
            raise ValueError("wrapper definitions are not exact frozen authority")
        if self.file_selection_evidence_sha256 != self.file_selection_evidence.canonical_sha256:
            raise ValueError("wrapper selection evidence digest mismatch")
        ordinals = tuple(item.ordinal for item in self.ordered_tracks)
        if not ordinals or ordinals != tuple(range(1, len(ordinals) + 1)):
            raise ValueError("ordered track authority must be contiguous and nonempty")
        identities = tuple(item.track_id for item in self.ordered_tracks)
        if len(identities) != len(set(identities)):
            raise ValueError("ordered track identities must be unique")
        verify_or_set_digest(self)
        return self


class PennyLocalITunesXMLAcquisitionAuthorityArtifactV11(FrozenModel):
    schema_version: Literal["1.1"] = "1.1"
    artifact_kind: Literal["penny_local_itunes_xml_acquisition_authority"] = (
        "penny_local_itunes_xml_acquisition_authority"
    )
    artifact_id: str
    file_selection_evidence: PennyLocalITunesXMLFileSelectionEvidenceV11
    file_selection_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquisition_authority_definition: FrozenDefinitionBindingV11 = (
        ACQUISITION_AUTHORITY_DEFINITION_V11
    )
    source_definition: FrozenDefinitionBindingV11 = SOURCE_DEFINITION_V11
    mapping_definition: FrozenDefinitionBinding = MAPPING_DEFINITION
    capability_declaration: SourceCapabilityDeclaration = CAPABILITY_DECLARATION_V11
    capability_declaration_json: Literal[CAPABILITY_DECLARATION_V11_JSON] = (
        CAPABILITY_DECLARATION_V11_JSON
    )
    capability_declaration_sha256: Literal[
        "270b636c2d18e36920f32fcb16328543ac767cda172df6d325ed36d47844b140"
    ] = CAPABILITY_DECLARATION_V11_SHA256
    adapter_id: Literal["pne.adapter.itunes-windows-xml-single-playlist"] = ADAPTER_ID
    adapter_version: Literal["1.1"] = ADAPTER_VERSION_V11
    library_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    playlist_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    ordered_tracks: tuple[OrderedTrackAuthority, ...]
    evidence_snapshot: EvidenceSnapshot
    evidence_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    identity_metadata: CandidateIdentityMetadataArtifact
    identity_metadata_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_neutral_acquisition_result: SourceNeutralAcquisitionResult
    source_neutral_acquisition_result_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    producer_authority_id: Literal[
        "pne.producer.itunes-windows-xml-acquisition-authority"
    ] = "pne.producer.itunes-windows-xml-acquisition-authority"
    producer_authority_version: Literal["1.1"] = "1.1"
    verifier_authority_id: Literal[
        "pne.verifier.itunes-windows-xml-acquisition-authority"
    ] = "pne.verifier.itunes-windows-xml-acquisition-authority"
    verifier_authority_version: Literal["1.1"] = "1.1"
    apple_authorship_established: Literal[False] = False
    pre_intake_integrity_established: Literal[False] = False
    export_freshness_established: Literal[False] = False
    current_state_established: Literal[False] = False
    provider_authentication_established: Literal[False] = False
    media_inspection_performed: Literal[False] = False
    release_version_identity_established: Literal[False] = False
    displayed_explicit_established: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id")
    @classmethod
    def exact_artifact_id(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_structure(self) -> PennyLocalITunesXMLAcquisitionAuthorityArtifactV11:
        if (
            self.acquisition_authority_definition
            != ACQUISITION_AUTHORITY_DEFINITION_V11
            or self.source_definition != SOURCE_DEFINITION_V11
            or self.mapping_definition != MAPPING_DEFINITION
            or self.capability_declaration != CAPABILITY_DECLARATION_V11
        ):
            raise ValueError("wrapper definitions are not exact frozen 1.1 authority")
        if self.file_selection_evidence_sha256 != self.file_selection_evidence.canonical_sha256:
            raise ValueError("wrapper selection evidence digest mismatch")
        ordinals = tuple(item.ordinal for item in self.ordered_tracks)
        if not ordinals or ordinals != tuple(range(1, len(ordinals) + 1)):
            raise ValueError("ordered track authority must be contiguous and nonempty")
        identities = tuple(item.track_id for item in self.ordered_tracks)
        if len(identities) != len(set(identities)):
            raise ValueError("ordered track identities must be unique")
        verify_or_set_digest(self)
        return self


def serialize_intake_request(value: PennyLocalITunesXMLIntakeRequest) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)


def serialize_file_selection_evidence(
    value: PennyLocalITunesXMLFileSelectionEvidence,
) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)


def serialize_acquisition_authority(
    value: PennyLocalITunesXMLAcquisitionAuthorityArtifact,
) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)


def serialize_intake_request_v11(value: PennyLocalITunesXMLIntakeRequestV11) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)


def serialize_file_selection_evidence_v11(
    value: PennyLocalITunesXMLFileSelectionEvidenceV11,
) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)


def serialize_acquisition_authority_v11(
    value: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
) -> bytes:
    from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import canonical_json_bytes

    return canonical_json_bytes(value)

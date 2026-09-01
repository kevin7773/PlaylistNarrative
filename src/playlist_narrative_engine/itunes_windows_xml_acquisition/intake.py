from __future__ import annotations

import secrets
import sys
from pathlib import Path

from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    derived_digest,
    sha256_bytes,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    SOURCE_TYPE,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    PennyLocalITunesXMLFileSelectionEvidence,
    PennyLocalITunesXMLIntakeRequest,
    SourceReceiptImplementationConformanceArtifact,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityInvalidInput,
    LocalPrincipalAuthorityVerifier,
)
from playlist_narrative_engine.source_receipt import (
    ACQUISITION_INTERFACE_DEFINITION,
    CAPTURE_POINT_DEFINITION,
    SOURCE_RECEIPT_POLICY,
    ObservationHandle,
    SourceObservationItem,
    SourceObservationRequest,
    SourceReceiptArtifact,
    SourceReceiptProducer,
    serialize_source_receipt_artifact,
    verify_source_receipt_artifact,
    verify_source_receipt_authority_definition,
)


class ITunesWindowsXMLIntakeInvalidInput(ValueError):
    pass


_INTAKE_PRODUCER_CAPABILITY = object()


class ITunesWindowsXMLIntakeAuthorityRepository:
    """In-memory authority ledger writable only by the governed intake producer."""

    def __init__(self) -> None:
        self._requests: dict[str, PennyLocalITunesXMLIntakeRequest] = {}
        self._evidence: dict[str, PennyLocalITunesXMLFileSelectionEvidence] = {}

    def _record_request(
        self,
        request: PennyLocalITunesXMLIntakeRequest,
        capability: object,
    ) -> None:
        if capability is not _INTAKE_PRODUCER_CAPABILITY:
            raise ITunesWindowsXMLIntakeInvalidInput("only the intake producer may record")
        if request.intake_request_id in self._requests:
            raise ITunesWindowsXMLIntakeInvalidInput("duplicate intake request identity")
        self._requests[request.intake_request_id] = request

    def _record_evidence(
        self,
        evidence: PennyLocalITunesXMLFileSelectionEvidence,
        capability: object,
    ) -> None:
        if capability is not _INTAKE_PRODUCER_CAPABILITY:
            raise ITunesWindowsXMLIntakeInvalidInput("only the intake producer may record")
        if evidence.evidence_id in self._evidence:
            raise ITunesWindowsXMLIntakeInvalidInput("duplicate selection evidence identity")
        self._evidence[evidence.evidence_id] = evidence


class PennyLocalITunesXMLIntakeVerifier:
    def __init__(
        self,
        repository: ITunesWindowsXMLIntakeAuthorityRepository,
        principal_verifier: LocalPrincipalAuthorityVerifier,
    ) -> None:
        self._repository = repository
        self._principal_verifier = principal_verifier

    def verify_request(
        self,
        request: PennyLocalITunesXMLIntakeRequest,
        *,
        require_current_tip: bool = False,
    ) -> bool:
        if not isinstance(request, PennyLocalITunesXMLIntakeRequest):
            return False
        recorded = self._repository._requests.get(request.intake_request_id)
        if recorded != request:
            return False
        try:
            validated = PennyLocalITunesXMLIntakeRequest.model_validate(
                request.model_dump(mode="json")
            )
            prefix = self._principal_verifier.verified_lineage_prefix_sha256(
                validated.principal_authority,
                require_current_tip=require_current_tip,
            )
            return validated == request and prefix == validated.principal_lineage_prefix_sha256
        except (TypeError, ValueError):
            return False

    def verify_evidence(
        self,
        evidence: PennyLocalITunesXMLFileSelectionEvidence,
        *,
        require_current_tip: bool = False,
    ) -> bool:
        if not isinstance(evidence, PennyLocalITunesXMLFileSelectionEvidence):
            return False
        recorded = self._repository._evidence.get(evidence.evidence_id)
        if recorded != evidence:
            return False
        return _verify_file_selection_evidence_structure(
            evidence,
            principal_verifier=self._principal_verifier,
            require_current_tip=require_current_tip,
        )


def _native_windows_single_file_selection() -> Path | None:
    if sys.platform != "win32":
        raise ITunesWindowsXMLIntakeInvalidInput(
            "the governed production picker is available only on Windows"
        )
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    try:
        selected = filedialog.askopenfilename(
            title="Select one iTunes XML playlist export",
            filetypes=(("XML files", "*.xml"),),
            multiple=False,
        )
    finally:
        root.destroy()
    return Path(selected) if selected else None


class PennyLocalITunesXMLIntakeProducer:
    """Sole public production seam for active-principal native file selection."""

    def __init__(self, principal_verifier: LocalPrincipalAuthorityVerifier) -> None:
        self._principal_verifier = principal_verifier
        self._repository = ITunesWindowsXMLIntakeAuthorityRepository()
        self.verifier = PennyLocalITunesXMLIntakeVerifier(
            self._repository,
            principal_verifier,
        )

    def create_request(self) -> PennyLocalITunesXMLIntakeRequest:
        principal = self._principal_verifier.resolve_active()
        prefix = self._principal_verifier.verified_lineage_prefix_sha256(
            principal,
            require_current_tip=True,
        )
        request = PennyLocalITunesXMLIntakeRequest(
            intake_request_id=f"pne.itunes-xml-intake-request:{secrets.token_hex(16)}",
            principal_authority=principal,
            principal_lineage_prefix_sha256=prefix,
        )
        self._repository._record_request(request, _INTAKE_PRODUCER_CAPABILITY)
        return request

    def capture_selected_file(
        self,
        request: PennyLocalITunesXMLIntakeRequest,
    ) -> PennyLocalITunesXMLFileSelectionEvidence:
        if not isinstance(request, PennyLocalITunesXMLIntakeRequest):
            raise ITunesWindowsXMLIntakeInvalidInput(
                "governed intake requires an exact intake request"
            )
        try:
            validated = PennyLocalITunesXMLIntakeRequest.model_validate(
                request.model_dump(mode="json")
            )
            if not self.verifier.verify_request(validated, require_current_tip=True):
                raise ValueError("intake request is not producer-recorded current authority")
            selected_path = _native_windows_single_file_selection()
            if selected_path is None:
                raise ValueError("file selection was cancelled")
            with selected_path.open("rb") as selected_stream:
                payload = selected_stream.read()
            if not payload:
                raise ValueError("selected file must contain a finite nonempty payload")
            self._verify_request_is_current(validated)
            observation_handle = ObservationHandle(
                value=f"itunes-windows-xml-selection:{secrets.token_hex(16)}"
            )
            observation = SourceObservationRequest(
                source_type=SOURCE_TYPE,
                source_reference=f"pne.intake-request:{validated.intake_request_id}",
                complete_response=True,
                declared_item_count=1,
                items=(
                    SourceObservationItem(
                        observation_handle=observation_handle,
                        payload=payload,
                    ),
                ),
            )
            receipt = SourceReceiptProducer().produce_authoritative(observation)
            receipt_sha256 = sha256_bytes(serialize_source_receipt_artifact(receipt))
            byte_sha256 = sha256_bytes(payload)
            conformance = SourceReceiptImplementationConformanceArtifact(
                artifact_id=(
                    "pne.source-receipt-conformance/sha256/"
                    + derived_digest(
                        "pne.source-receipt-conformance/1.0",
                        validated.canonical_sha256,
                        observation_handle.value,
                        byte_sha256,
                        receipt_sha256,
                    )
                ),
                intake_request_id=validated.intake_request_id,
                observation_handle=observation_handle.value,
                byte_length=len(payload),
                byte_sha256=byte_sha256,
                receipt_id=receipt.receipt_id,
                receipt_artifact_sha256=receipt_sha256,
            )
            if not _verify_source_receipt_implementation_conformance_structure(
                conformance,
                receipt=receipt,
            ):
                raise ValueError("source receipt implementation conformance failed")
            evidence = PennyLocalITunesXMLFileSelectionEvidence(
                evidence_id=f"pne.itunes-xml-file-selection:{secrets.token_hex(16)}",
                intake_request=validated,
                intake_request_sha256=validated.canonical_sha256,
                principal_id=validated.principal_authority.principal_id,
                principal_authority_artifact_id=(
                    validated.principal_authority.artifact_id
                ),
                principal_authority_sha256=(
                    validated.principal_authority.canonical_sha256
                ),
                installation_id=validated.principal_authority.installation_id,
                principal_lineage_prefix_sha256=(
                    validated.principal_lineage_prefix_sha256
                ),
                byte_length=len(payload),
                byte_sha256=byte_sha256,
                source_receipt=receipt,
                source_receipt_artifact_sha256=receipt_sha256,
                implementation_conformance=conformance,
            )
            self._repository._record_evidence(evidence, _INTAKE_PRODUCER_CAPABILITY)
            if not self.verifier.verify_evidence(evidence, require_current_tip=True):
                raise ValueError("file selection evidence is not authoritative")
            return evidence
        except (OSError, TypeError, ValueError, LocalPrincipalAuthorityInvalidInput) as exc:
            if isinstance(exc, ITunesWindowsXMLIntakeInvalidInput):
                raise
            raise ITunesWindowsXMLIntakeInvalidInput(
                "governed iTunes XML selection failed closed"
            ) from exc

    def _verify_request_is_current(
        self,
        request: PennyLocalITunesXMLIntakeRequest,
    ) -> None:
        principal = request.principal_authority
        digest = self._principal_verifier.verified_lineage_prefix_sha256(
            principal,
            require_current_tip=True,
        )
        if digest != request.principal_lineage_prefix_sha256:
            raise LocalPrincipalAuthorityInvalidInput(
                "intake request principal lineage does not correspond"
            )


def _verify_source_receipt_implementation_conformance_structure(
    artifact: SourceReceiptImplementationConformanceArtifact,
    *,
    receipt: SourceReceiptArtifact,
) -> bool:
    if not isinstance(artifact, SourceReceiptImplementationConformanceArtifact):
        return False
    try:
        validated = SourceReceiptImplementationConformanceArtifact.model_validate(
            artifact.model_dump(mode="json")
        )
        if not all(
            verify_source_receipt_authority_definition(definition)
            for definition in (
                ACQUISITION_INTERFACE_DEFINITION,
                CAPTURE_POINT_DEFINITION,
                SOURCE_RECEIPT_POLICY,
            )
        ):
            return False
        if len(receipt.items) != 1:
            return False
        item = receipt.items[0]
        reconstructed = SourceObservationRequest(
            source_type=receipt.source_type,
            source_reference=receipt.source_reference,
            complete_response=True,
            declared_item_count=1,
            items=(
                SourceObservationItem(
                    observation_handle=item.observation_handle,
                    payload=item.payload,
                ),
            ),
        )
        return (
            validated == artifact
            and validated.observation_handle == item.observation_handle.value
            and validated.byte_length == len(item.payload)
            and validated.byte_sha256 == sha256_bytes(item.payload)
            and validated.receipt_id == receipt.receipt_id
            and validated.receipt_artifact_sha256
            == sha256_bytes(serialize_source_receipt_artifact(receipt))
            and verify_source_receipt_artifact(receipt, request=reconstructed)
        )
    except (TypeError, ValueError):
        return False


def _verify_file_selection_evidence_structure(
    evidence: PennyLocalITunesXMLFileSelectionEvidence,
    *,
    principal_verifier: LocalPrincipalAuthorityVerifier,
    require_current_tip: bool = False,
) -> bool:
    if not isinstance(evidence, PennyLocalITunesXMLFileSelectionEvidence):
        return False
    try:
        validated = PennyLocalITunesXMLFileSelectionEvidence.model_validate(
            evidence.model_dump(mode="json")
        )
        prefix = principal_verifier.verified_lineage_prefix_sha256(
            validated.intake_request.principal_authority,
            require_current_tip=require_current_tip,
        )
        return (
            validated == evidence
            and prefix == validated.principal_lineage_prefix_sha256
            and _verify_source_receipt_implementation_conformance_structure(
                validated.implementation_conformance,
                receipt=validated.source_receipt,
            )
        )
    except (TypeError, ValueError):
        return False

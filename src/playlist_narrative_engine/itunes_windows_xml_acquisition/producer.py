from __future__ import annotations

from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    derived_digest,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    CAPABILITY_DECLARATION_SHA256,
    MAPPING_DEFINITION_SHA256,
    SOURCE_DEFINITION_SHA256,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.intake import (
    PennyLocalITunesXMLIntakeVerifier,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.mapping import (
    map_verified_profile,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.profile import (
    verify_frozen_itunes_windows_xml_profile,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifact,
    PennyLocalITunesXMLFileSelectionEvidence,
)
class ITunesWindowsXMLAcquisitionInvalidInput(ValueError):
    pass


class PennyLocalITunesXMLAcquisitionProducer:
    """Sole producer of the frozen source-specific acquisition wrapper."""

    def __init__(self, intake_verifier: PennyLocalITunesXMLIntakeVerifier) -> None:
        self._intake_verifier = intake_verifier

    def produce_authoritative(
        self,
        evidence: PennyLocalITunesXMLFileSelectionEvidence,
    ) -> PennyLocalITunesXMLAcquisitionAuthorityArtifact:
        try:
            if not self._intake_verifier.verify_evidence(evidence):
                raise ValueError("file selection evidence does not verify")
            profile = verify_frozen_itunes_windows_xml_profile(evidence)
            mapped = map_verified_profile(evidence, profile)
            artifact_id = "pne.itunes-xml-acquisition-authority/sha256/" + derived_digest(
                "pne.itunes-xml-acquisition-authority/1.0",
                evidence.canonical_sha256,
                evidence.source_receipt_artifact_sha256,
                SOURCE_DEFINITION_SHA256,
                MAPPING_DEFINITION_SHA256,
                CAPABILITY_DECLARATION_SHA256,
                mapped.source_neutral_acquisition_result_sha256,
            )
            return PennyLocalITunesXMLAcquisitionAuthorityArtifact(
                artifact_id=artifact_id,
                file_selection_evidence=evidence,
                file_selection_evidence_sha256=evidence.canonical_sha256,
                library_persistent_id=profile.library_persistent_id,
                playlist_persistent_id=profile.playlist_persistent_id,
                ordered_tracks=mapped.ordered_tracks,
                evidence_snapshot=mapped.evidence_snapshot,
                evidence_snapshot_sha256=mapped.evidence_snapshot_sha256,
                identity_metadata=mapped.identity_metadata,
                identity_metadata_sha256=mapped.identity_metadata_sha256,
                source_neutral_acquisition_result=(
                    mapped.source_neutral_acquisition_result
                ),
                source_neutral_acquisition_result_sha256=(
                    mapped.source_neutral_acquisition_result_sha256
                ),
            )
        except (TypeError, ValueError) as exc:
            raise ITunesWindowsXMLAcquisitionInvalidInput(
                "iTunes Windows XML acquisition failed closed"
            ) from exc

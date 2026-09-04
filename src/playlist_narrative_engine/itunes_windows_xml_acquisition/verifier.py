from __future__ import annotations

from playlist_narrative_engine.candidate_formation import (
    serialize_candidate_source_evidence,
)
from playlist_narrative_engine.evidence_acquisition import (
    serialize_acquisition_result,
    serialize_evidence_snapshot,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    derived_digest,
    sha256_bytes,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    CAPABILITY_DECLARATION_SHA256,
    CAPABILITY_DECLARATION_V11_SHA256,
    MAPPING_DEFINITION_SHA256,
    SOURCE_DEFINITION_SHA256,
    SOURCE_DEFINITION_V11_SHA256,
    verify_frozen_definitions,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.intake import (
    PennyLocalITunesXMLIntakeVerifier,
    PennyLocalITunesXMLIntakeVerifierV11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.mapping import (
    map_verified_profile,
    map_verified_profile_v11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.profile import (
    verify_frozen_itunes_windows_xml_profile,
    verify_frozen_itunes_windows_xml_profile_v11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifact,
    PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
)
class PennyLocalITunesXMLAcquisitionVerifier:
    """Independently reconstruct and compare every source-specific result layer."""

    def __init__(self, intake_verifier: PennyLocalITunesXMLIntakeVerifier) -> None:
        self._intake_verifier = intake_verifier

    def verify(
        self,
        artifact: PennyLocalITunesXMLAcquisitionAuthorityArtifact,
    ) -> bool:
        if not isinstance(artifact, PennyLocalITunesXMLAcquisitionAuthorityArtifact):
            return False
        try:
            validated = PennyLocalITunesXMLAcquisitionAuthorityArtifact.model_validate(
                artifact.model_dump(mode="json")
            )
            if validated != artifact or not verify_frozen_definitions():
                return False
            evidence = validated.file_selection_evidence
            if not self._intake_verifier.verify_evidence(evidence):
                return False
            profile = verify_frozen_itunes_windows_xml_profile(evidence)
            mapped = map_verified_profile(evidence, profile)
            expected_artifact_id = (
                "pne.itunes-xml-acquisition-authority/sha256/"
                + derived_digest(
                    "pne.itunes-xml-acquisition-authority/1.0",
                    evidence.canonical_sha256,
                    evidence.source_receipt_artifact_sha256,
                    SOURCE_DEFINITION_SHA256,
                    MAPPING_DEFINITION_SHA256,
                    CAPABILITY_DECLARATION_SHA256,
                    mapped.source_neutral_acquisition_result_sha256,
                )
            )
            return all(
                (
                    validated.artifact_id == expected_artifact_id,
                    validated.file_selection_evidence_sha256
                    == evidence.canonical_sha256,
                    validated.library_persistent_id
                    == profile.library_persistent_id,
                    validated.playlist_persistent_id
                    == profile.playlist_persistent_id,
                    validated.ordered_tracks == mapped.ordered_tracks,
                    validated.evidence_snapshot == mapped.evidence_snapshot,
                    validated.evidence_snapshot_sha256
                    == sha256_bytes(
                        serialize_evidence_snapshot(validated.evidence_snapshot)
                    )
                    == mapped.evidence_snapshot_sha256,
                    validated.identity_metadata == mapped.identity_metadata,
                    validated.identity_metadata_sha256
                    == sha256_bytes(
                        serialize_candidate_source_evidence(
                            validated.identity_metadata
                        )
                    )
                    == mapped.identity_metadata_sha256,
                    validated.source_neutral_acquisition_result
                    == mapped.source_neutral_acquisition_result,
                    validated.source_neutral_acquisition_result_sha256
                    == sha256_bytes(
                        serialize_acquisition_result(
                            validated.source_neutral_acquisition_result
                        )
                    )
                    == mapped.source_neutral_acquisition_result_sha256,
                )
            )
        except (TypeError, ValueError):
            return False


class PennyLocalITunesXMLAcquisitionVerifierV11:
    """Independently reconstruct and compare every 1.1 result layer."""

    def __init__(self, intake_verifier: PennyLocalITunesXMLIntakeVerifierV11) -> None:
        self._intake_verifier = intake_verifier

    def verify(
        self,
        artifact: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
    ) -> bool:
        if (
            not isinstance(artifact, PennyLocalITunesXMLAcquisitionAuthorityArtifactV11)
            or not isinstance(self._intake_verifier, PennyLocalITunesXMLIntakeVerifierV11)
        ):
            return False
        try:
            validated = PennyLocalITunesXMLAcquisitionAuthorityArtifactV11.model_validate(
                artifact.model_dump(mode="json")
            )
            if validated != artifact or not verify_frozen_definitions():
                return False
            evidence = validated.file_selection_evidence
            if not self._intake_verifier.verify_evidence(evidence):
                return False
            profile = verify_frozen_itunes_windows_xml_profile_v11(evidence)
            mapped = map_verified_profile_v11(evidence, profile)
            expected_artifact_id = (
                "pne.itunes-xml-acquisition-authority/sha256/"
                + derived_digest(
                    "pne.itunes-xml-acquisition-authority/1.1",
                    evidence.canonical_sha256,
                    evidence.source_receipt_artifact_sha256,
                    SOURCE_DEFINITION_V11_SHA256,
                    MAPPING_DEFINITION_SHA256,
                    CAPABILITY_DECLARATION_V11_SHA256,
                    mapped.source_neutral_acquisition_result_sha256,
                )
            )
            return all(
                (
                    validated.artifact_id == expected_artifact_id,
                    validated.file_selection_evidence_sha256
                    == evidence.canonical_sha256,
                    validated.library_persistent_id == profile.library_persistent_id,
                    validated.playlist_persistent_id == profile.playlist_persistent_id,
                    validated.ordered_tracks == mapped.ordered_tracks,
                    validated.evidence_snapshot == mapped.evidence_snapshot,
                    validated.evidence_snapshot_sha256
                    == sha256_bytes(
                        serialize_evidence_snapshot(validated.evidence_snapshot)
                    )
                    == mapped.evidence_snapshot_sha256,
                    validated.identity_metadata == mapped.identity_metadata,
                    validated.identity_metadata_sha256
                    == sha256_bytes(
                        serialize_candidate_source_evidence(
                            validated.identity_metadata
                        )
                    )
                    == mapped.identity_metadata_sha256,
                    validated.source_neutral_acquisition_result
                    == mapped.source_neutral_acquisition_result,
                    validated.source_neutral_acquisition_result_sha256
                    == sha256_bytes(
                        serialize_acquisition_result(
                            validated.source_neutral_acquisition_result
                        )
                    )
                    == mapped.source_neutral_acquisition_result_sha256,
                )
            )
        except (TypeError, ValueError):
            return False

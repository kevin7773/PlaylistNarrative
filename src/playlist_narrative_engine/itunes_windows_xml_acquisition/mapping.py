from __future__ import annotations

import json

from playlist_narrative_engine.candidate_formation import (
    BooleanEvidence,
    CandidateIdentityMetadataArtifact,
    CandidateIdentityMetadataRecord,
    EvidenceObservation,
    EvidenceState,
    ExactStringEvidence,
    serialize_candidate_source_evidence,
)
from playlist_narrative_engine.evidence_acquisition import (
    SourceCapabilityDeclaration,
    SourceNeutralAcquisitionResult,
    serialize_acquisition_result,
    serialize_evidence_snapshot,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    FrozenModel,
    derived_digest,
    sha256_bytes,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    ADAPTER_ID,
    ADAPTER_VERSION,
    ADAPTER_VERSION_V11,
    CAPABILITY_DECLARATION,
    CAPABILITY_DECLARATION_SHA256,
    CAPABILITY_DECLARATION_V11,
    CAPABILITY_DECLARATION_V11_SHA256,
    MAPPING_DEFINITION_SHA256,
    SOURCE_DEFINITION_SHA256,
    SOURCE_DEFINITION_V11_SHA256,
    SOURCE_TYPE,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.profile import (
    VerifiedITunesWindowsXMLProfile,
    VerifiedITunesWindowsXMLProfileV11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    OrderedTrackAuthority,
    PennyLocalITunesXMLFileSelectionEvidence,
    PennyLocalITunesXMLFileSelectionEvidenceV11,
)
from playlist_narrative_engine.track_evidence import (
    EvidenceSnapshot,
    EvidenceSnapshotRecord,
)


class DeterministicMappingResult(FrozenModel):
    ordered_tracks: tuple[OrderedTrackAuthority, ...]
    evidence_snapshot: EvidenceSnapshot
    evidence_snapshot_sha256: str
    identity_metadata: CandidateIdentityMetadataArtifact
    identity_metadata_sha256: str
    source_neutral_acquisition_result: SourceNeutralAcquisitionResult
    source_neutral_acquisition_result_sha256: str


def map_verified_profile(
    evidence: PennyLocalITunesXMLFileSelectionEvidence,
    profile: VerifiedITunesWindowsXMLProfile,
) -> DeterministicMappingResult:
    return _map_verified_profile(
        evidence,
        profile,
        source_definition_sha256=SOURCE_DEFINITION_SHA256,
        capability_declaration=CAPABILITY_DECLARATION,
        capability_declaration_sha256=CAPABILITY_DECLARATION_SHA256,
        adapter_version=ADAPTER_VERSION,
    )


def map_verified_profile_v11(
    evidence: PennyLocalITunesXMLFileSelectionEvidenceV11,
    profile: VerifiedITunesWindowsXMLProfileV11,
) -> DeterministicMappingResult:
    return _map_verified_profile(
        evidence,
        profile,
        source_definition_sha256=SOURCE_DEFINITION_V11_SHA256,
        capability_declaration=CAPABILITY_DECLARATION_V11,
        capability_declaration_sha256=CAPABILITY_DECLARATION_V11_SHA256,
        adapter_version=ADAPTER_VERSION_V11,
    )


def _map_verified_profile(
    evidence: PennyLocalITunesXMLFileSelectionEvidence
    | PennyLocalITunesXMLFileSelectionEvidenceV11,
    profile: VerifiedITunesWindowsXMLProfile | VerifiedITunesWindowsXMLProfileV11,
    *,
    source_definition_sha256: str,
    capability_declaration: SourceCapabilityDeclaration,
    capability_declaration_sha256: str,
    adapter_version: str,
) -> DeterministicMappingResult:
    receipt = evidence.source_receipt
    receipt_sha256 = evidence.source_receipt_artifact_sha256
    source_reference = f"source-receipt:{receipt.receipt_id}/item:item-000001"
    snapshot_id = "pne.evidence-snapshot/sha256/" + derived_digest(
        "pne.evidence-snapshot/1.0",
        receipt_sha256,
        source_definition_sha256,
        MAPPING_DEFINITION_SHA256,
    )
    ordered: list[OrderedTrackAuthority] = []
    snapshot_records: list[EvidenceSnapshotRecord] = []
    metadata_records: list[CandidateIdentityMetadataRecord] = []
    for ordinal, correspondence_id in enumerate(profile.playlist_track_ids, start=1):
        source = profile.tracks_by_correspondence_id[correspondence_id]
        record_id = f"itunes-playlist-item/{ordinal:06d}"
        track_id = (
            f"itunes-windows-library:{profile.library_persistent_id}"
            f"/track:{source.persistent_id}"
        )
        ordered.append(
            OrderedTrackAuthority(
                ordinal=ordinal,
                track_id=track_id,
                source_duration_milliseconds=source.total_time_milliseconds,
            )
        )
        payload = {
            "track_id": track_id,
            "title": source.name,
            "artist_name": source.artist,
            "duration_seconds": source.total_time_milliseconds // 1000,
            "provenance": {
                "source_type": SOURCE_TYPE,
                "source_reference": source_reference,
                "rationale": (
                    "Mapped from a profile-verified iTunes Windows XML "
                    "single-playlist export."
                ),
            },
        }
        snapshot_records.append(
            EvidenceSnapshotRecord(
                record_id=record_id,
                payload_json=json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            )
        )
        common = {"source_type": SOURCE_TYPE, "source_reference": source_reference}
        metadata_records.append(
            CandidateIdentityMetadataRecord(
                track_id=track_id,
                source_catalog_identity=ExactStringEvidence(
                    state=EvidenceState.MEASURED,
                    value=track_id,
                    observations=(
                        EvidenceObservation(
                            evidence_id=f"{record_id}/source-catalog",
                            payload_json=json.dumps(
                                {
                                    "library_persistent_id": profile.library_persistent_id,
                                    "track_persistent_id": source.persistent_id,
                                },
                                separators=(",", ":"),
                            ),
                            **common,
                        ),
                    ),
                ),
                release_version_identity=ExactStringEvidence(
                    state=EvidenceState.UNSUPPORTED,
                    value=None,
                    observations=(
                        EvidenceObservation(
                            evidence_id=f"{record_id}/release-version-unsupported",
                            payload_json=(
                                '{"capability":"UNSUPPORTED",'
                                '"field":"release_version_identity"}'
                            ),
                            **common,
                        ),
                    ),
                ),
                displayed_explicit=BooleanEvidence(
                    state=EvidenceState.UNSUPPORTED,
                    value=None,
                    observations=(
                        EvidenceObservation(
                            evidence_id=f"{record_id}/displayed-explicit-unsupported",
                            payload_json=(
                                '{"capability":"UNSUPPORTED",'
                                '"field":"displayed_explicit"}'
                            ),
                            **common,
                        ),
                    ),
                ),
            )
        )

    snapshot = EvidenceSnapshot(snapshot_id=snapshot_id, records=tuple(snapshot_records))
    snapshot_sha256 = sha256_bytes(serialize_evidence_snapshot(snapshot))
    metadata_id = "pne.candidate-identity-metadata/sha256/" + derived_digest(
        "pne.candidate-identity-metadata/1.0",
        snapshot_sha256,
        capability_declaration_sha256,
    )
    metadata = CandidateIdentityMetadataArtifact(
        artifact_id=metadata_id,
        track_snapshot_id=snapshot.snapshot_id,
        records=tuple(metadata_records),
    )
    metadata_sha256 = sha256_bytes(serialize_candidate_source_evidence(metadata))
    acquisition_id = "pne.source-neutral-acquisition/sha256/" + derived_digest(
        "pne.source-neutral-acquisition/1.0",
        receipt_sha256,
        source_definition_sha256,
        MAPPING_DEFINITION_SHA256,
        capability_declaration_sha256,
        snapshot_sha256,
        metadata_sha256,
    )
    acquisition = SourceNeutralAcquisitionResult(
        acquisition_id=acquisition_id,
        source_receipt_id=receipt.receipt_id,
        source_receipt_sha256=receipt_sha256,
        source_type=SOURCE_TYPE,
        source_reference=source_reference,
        adapter_id=ADAPTER_ID,
        adapter_version=adapter_version,
        capability_declaration=capability_declaration,
        evidence_snapshot=snapshot,
        evidence_snapshot_sha256=snapshot_sha256,
        identity_metadata=metadata,
    )
    acquisition_sha256 = sha256_bytes(serialize_acquisition_result(acquisition))
    return DeterministicMappingResult(
        ordered_tracks=tuple(ordered),
        evidence_snapshot=snapshot,
        evidence_snapshot_sha256=snapshot_sha256,
        identity_metadata=metadata,
        identity_metadata_sha256=metadata_sha256,
        source_neutral_acquisition_result=acquisition,
        source_neutral_acquisition_result_sha256=acquisition_sha256,
    )

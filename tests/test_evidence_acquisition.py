from __future__ import annotations

import hashlib

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.candidate_formation import (
    BooleanEvidence,
    CandidateIdentityMetadataArtifact,
    CandidateIdentityMetadataRecord,
    EvidenceObservation,
    EvidenceState,
    ExactStringEvidence,
)
from playlist_narrative_engine.evidence_acquisition import (
    AuthoritativeMetadataField,
    MetadataCapability,
    SourceCapabilityDeclaration,
    SourceNeutralAcquisitionResult,
    serialize_acquisition_result,
    serialize_evidence_snapshot,
)
from playlist_narrative_engine.track_evidence import EvidenceSnapshot, EvidenceSnapshotRecord


SOURCE_TYPE = "manual_evidence"
SOURCE_REFERENCE = "source:track-a"


def observation(key: str, value: object, *, reference: str = SOURCE_REFERENCE) -> EvidenceObservation:
    return EvidenceObservation(
        evidence_id=key,
        source_type=SOURCE_TYPE,
        source_reference=reference,
        payload_json=f'{{"value":{str(value).lower()}}}' if isinstance(value, bool) else "{}",
    )


def declaration(*, catalog: bool = True, version: bool = False, explicit: bool = True) -> SourceCapabilityDeclaration:
    return SourceCapabilityDeclaration(
        declaration_id="capabilities-001",
        declaration_version="1.0",
        adapter_id="future-adapter-contract",
        adapter_version="1.0",
        capabilities=(
            MetadataCapability(field=AuthoritativeMetadataField.DISPLAYED_EXPLICIT, authoritative=explicit),
            MetadataCapability(field=AuthoritativeMetadataField.RELEASE_VERSION_IDENTITY, authoritative=version),
            MetadataCapability(field=AuthoritativeMetadataField.SOURCE_CATALOG_IDENTITY, authoritative=catalog),
        ),
    )


def unsupported(key: str) -> ExactStringEvidence:
    return ExactStringEvidence(
        state=EvidenceState.UNSUPPORTED,
        value=None,
        observations=(observation(key, None),),
    )


def metadata_record(*, explicit: bool | None = False, explicit_state: EvidenceState = EvidenceState.MEASURED) -> CandidateIdentityMetadataRecord:
    explicit_observations = (
        (observation("explicit", explicit),)
        if explicit_state is EvidenceState.MEASURED
        else ()
    )
    return CandidateIdentityMetadataRecord(
        track_id="track-a",
        source_catalog_identity=ExactStringEvidence(
            state=EvidenceState.MEASURED,
            value="catalog:Å-001",
            observations=(observation("catalog", "catalog:Å-001"),),
        ),
        release_version_identity=unsupported("version-unsupported"),
        displayed_explicit=BooleanEvidence(
            state=explicit_state,
            value=explicit if explicit_state is EvidenceState.MEASURED else None,
            observations=explicit_observations,
        ),
    )


def acquisition(
    *,
    metadata: CandidateIdentityMetadataArtifact | None = None,
    capabilities: SourceCapabilityDeclaration | None = None,
    snapshot: EvidenceSnapshot | None = None,
) -> SourceNeutralAcquisitionResult:
    snapshot = snapshot or EvidenceSnapshot(
        snapshot_id="snapshot-001",
        records=(EvidenceSnapshotRecord(record_id="record-a", payload_json="{}"),),
    )
    metadata = metadata or CandidateIdentityMetadataArtifact(
        artifact_id="metadata-001",
        track_snapshot_id=snapshot.snapshot_id,
        records=(metadata_record(),),
    )
    return SourceNeutralAcquisitionResult(
        acquisition_id="acquisition-001",
        source_receipt_id="source-receipt-001",
        source_receipt_sha256="a" * 64,
        source_type=SOURCE_TYPE,
        source_reference=SOURCE_REFERENCE,
        adapter_id="future-adapter-contract",
        adapter_version="1.0",
        capability_declaration=capabilities or declaration(),
        evidence_snapshot=snapshot,
        evidence_snapshot_sha256=hashlib.sha256(serialize_evidence_snapshot(snapshot)).hexdigest(),
        identity_metadata=metadata,
    )


def test_atomic_acquisition_preserves_exact_lineage_and_authoritative_false() -> None:
    result = acquisition()
    record = result.identity_metadata.records[0]

    assert result.source_receipt_id == "source-receipt-001"
    assert result.adapter_id == "future-adapter-contract"
    assert result.adapter_version == "1.0"
    assert record.source_catalog_identity.value == "catalog:Å-001"
    assert record.release_version_identity.state is EvidenceState.UNSUPPORTED
    assert record.displayed_explicit.value is False
    assert serialize_acquisition_result(result) == serialize_acquisition_result(result)


def test_capability_declaration_is_frozen_versioned_and_complete() -> None:
    value = declaration()
    assert value.declaration_version == "1.0"
    with pytest.raises(ValidationError):
        value.declaration_version = "2.0"
    with pytest.raises(ValidationError, match="cover every metadata field"):
        SourceCapabilityDeclaration(
            declaration_id="bad", declaration_version="1", adapter_id="a", adapter_version="1",
            capabilities=(MetadataCapability(field=AuthoritativeMetadataField.DISPLAYED_EXPLICIT, authoritative=True),),
        )


def test_unsupported_capability_cannot_claim_measured_authority() -> None:
    with pytest.raises(ValidationError, match="must remain UNSUPPORTED"):
        acquisition(capabilities=declaration(catalog=False))


def test_supported_absent_value_remains_unavailable_and_never_false() -> None:
    record = metadata_record(explicit=None, explicit_state=EvidenceState.UNAVAILABLE)
    result = acquisition(metadata=CandidateIdentityMetadataArtifact(
        artifact_id="metadata-001", track_snapshot_id="snapshot-001", records=(record,)
    ))
    assert result.identity_metadata.records[0].displayed_explicit.state is EvidenceState.UNAVAILABLE
    assert result.identity_metadata.records[0].displayed_explicit.value is None


def test_conflicting_observations_remain_conflicting() -> None:
    record = metadata_record()
    conflicting = record.model_copy(update={"displayed_explicit": BooleanEvidence(
        state=EvidenceState.CONFLICTING,
        value=None,
        observations=(observation("explicit-false", False), observation("explicit-true", True)),
    )})
    result = acquisition(metadata=CandidateIdentityMetadataArtifact(
        artifact_id="metadata-001", track_snapshot_id="snapshot-001", records=(conflicting,)
    ))
    assert result.identity_metadata.records[0].displayed_explicit.state is EvidenceState.CONFLICTING


def test_snapshot_metadata_and_observation_lineage_must_match() -> None:
    wrong_snapshot = CandidateIdentityMetadataArtifact(
        artifact_id="metadata-001", track_snapshot_id="other", records=(metadata_record(),)
    )
    with pytest.raises(ValidationError, match="correspond to the acquired snapshot"):
        acquisition(metadata=wrong_snapshot)

    record = metadata_record().model_copy(update={"displayed_explicit": BooleanEvidence(
        state=EvidenceState.MEASURED,
        value=False,
        observations=(observation("explicit", False, reference="other-receipt"),),
    )})
    with pytest.raises(ValidationError, match="source-receipt lineage"):
        acquisition(metadata=CandidateIdentityMetadataArtifact(
            artifact_id="metadata-001", track_snapshot_id="snapshot-001", records=(record,)
        ))


def test_duplicate_metadata_identity_is_rejected() -> None:
    duplicate = metadata_record()
    with pytest.raises(ValidationError, match="must be unique"):
        CandidateIdentityMetadataArtifact(
            artifact_id="metadata-001",
            track_snapshot_id="snapshot-001",
            records=(duplicate, duplicate),
        )


def test_similar_display_strings_do_not_collapse_distinct_catalog_objects() -> None:
    first = metadata_record()
    second = metadata_record().model_copy(update={
        "track_id": "track-b",
        "source_catalog_identity": ExactStringEvidence(
            state=EvidenceState.MEASURED,
            value="catalog:Å-002",
            observations=(observation("catalog-b", "catalog:Å-002"),),
        ),
    })
    snapshot = EvidenceSnapshot(
        snapshot_id="snapshot-001",
        records=(
            EvidenceSnapshotRecord(record_id="record-a", payload_json='{"title":"Song"}'),
            EvidenceSnapshotRecord(record_id="record-b", payload_json='{"title":"song"}'),
        ),
    )
    result = acquisition(
        snapshot=snapshot,
        metadata=CandidateIdentityMetadataArtifact(
            artifact_id="metadata-001",
            track_snapshot_id="snapshot-001",
            records=(first, second),
        ),
    )
    assert tuple(
        item.source_catalog_identity.value for item in result.identity_metadata.records
    ) == ("catalog:Å-001", "catalog:Å-002")


def test_snapshot_digest_is_structural_not_caller_asserted() -> None:
    result = acquisition()
    with pytest.raises(ValidationError, match="digest"):
        SourceNeutralAcquisitionResult.model_validate({
            **result.model_dump(mode="json"), "evidence_snapshot_sha256": "0" * 64,
        })


def test_adapter_identity_must_match_capability_authority() -> None:
    result = acquisition()
    with pytest.raises(ValidationError, match="exact adapter identity"):
        SourceNeutralAcquisitionResult.model_validate({
            **result.model_dump(mode="json"), "adapter_version": "2.0",
        })


def test_title_suffix_does_not_manufacture_release_identity() -> None:
    snapshot = EvidenceSnapshot(
        snapshot_id="snapshot-001",
        records=(EvidenceSnapshotRecord(
            record_id="record-a",
            payload_json='{"track_id":"track-a","title":"Song (Clean Edit)","artist_name":"Artist","duration_seconds":200,"provenance":{"source_type":"x","source_reference":"y","rationale":"z"}}',
        ),),
    )
    record = metadata_record().model_copy(update={
        "release_version_identity": unsupported("version-unsupported")
    })
    result = acquisition(
        snapshot=snapshot,
        metadata=CandidateIdentityMetadataArtifact(
            artifact_id="metadata-001", track_snapshot_id="snapshot-001", records=(record,)
        ),
    )
    assert "Clean Edit" in result.evidence_snapshot.records[0].payload_json
    assert result.identity_metadata.records[0].release_version_identity.value is None

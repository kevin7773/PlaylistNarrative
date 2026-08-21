"""Source-neutral authority boundary for future evidence acquisition adapters."""

from playlist_narrative_engine.evidence_acquisition.schemas import (
    ACQUISITION_SCHEMA_VERSION,
    AuthoritativeMetadataField,
    MetadataCapability,
    SourceCapabilityDeclaration,
    SourceNeutralAcquisitionResult,
    serialize_acquisition_result,
    serialize_evidence_snapshot,
)

__all__ = [
    "ACQUISITION_SCHEMA_VERSION",
    "AuthoritativeMetadataField",
    "MetadataCapability",
    "SourceCapabilityDeclaration",
    "SourceNeutralAcquisitionResult",
    "serialize_acquisition_result",
    "serialize_evidence_snapshot",
]

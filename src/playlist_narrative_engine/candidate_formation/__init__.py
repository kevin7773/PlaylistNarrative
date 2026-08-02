"""Immutable source-evidence contracts for future Candidate Formation."""

from playlist_narrative_engine.candidate_formation.schemas import (
    CANDIDATE_EVIDENCE_SCHEMA_VERSION,
    CandidateSourceEvidenceArtifact,
    ContextInputEvidence,
    EvidenceObservation,
    EvidenceState,
    FamiliarityEvidenceArtifact,
    FamiliarityEvidenceRecord,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    ObjectiveContextEvidenceRecord,
    TasteEvidenceRecord,
    TrackFeatureEvidenceArtifact,
    TrackFeatureEvidenceRecord,
    UnitIntervalEvidence,
)
from playlist_narrative_engine.candidate_formation.serialization import (
    serialize_candidate_source_evidence,
)

__all__ = [
    "CANDIDATE_EVIDENCE_SCHEMA_VERSION",
    "CandidateSourceEvidenceArtifact",
    "ContextInputEvidence",
    "EvidenceObservation",
    "EvidenceState",
    "FamiliarityEvidenceArtifact",
    "FamiliarityEvidenceRecord",
    "LocalTasteEvidenceArtifact",
    "ObjectiveContextEvidenceArtifact",
    "ObjectiveContextEvidenceRecord",
    "TasteEvidenceRecord",
    "TrackFeatureEvidenceArtifact",
    "TrackFeatureEvidenceRecord",
    "UnitIntervalEvidence",
    "serialize_candidate_source_evidence",
]

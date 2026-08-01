from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from playlist_narrative_engine.elicitation import ArtistQuestionnaireSeed
from playlist_narrative_engine.objective_assessment import (
    AssessmentOutcome,
    ObjectiveAssessment,
)


TRACK_EVIDENCE_SCHEMA_VERSION = "1.0"


class FrozenTrackEvidenceModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvidenceDomain(StrEnum):
    TRACK = "track"


class TrackEvidenceIssueCode(StrEnum):
    RECORD_INVALID_JSON = "EVIDENCE_RECORD_INVALID_JSON"
    RECORD_DUPLICATE_KEY = "EVIDENCE_RECORD_DUPLICATE_KEY"
    RECORD_NOT_OBJECT = "EVIDENCE_RECORD_NOT_OBJECT"
    RECORD_EXTRA_FIELD = "EVIDENCE_RECORD_EXTRA_FIELD"
    TRACK_ID_MISSING = "TRACK_ID_MISSING"
    TRACK_ID_INVALID = "TRACK_ID_INVALID"
    TRACK_TITLE_MISSING = "TRACK_TITLE_MISSING"
    TRACK_TITLE_INVALID = "TRACK_TITLE_INVALID"
    TRACK_ARTIST_MISSING = "TRACK_ARTIST_MISSING"
    TRACK_ARTIST_INVALID = "TRACK_ARTIST_INVALID"
    TRACK_ARTIST_OUT_OF_SCOPE = "TRACK_ARTIST_OUT_OF_SCOPE"
    TRACK_DURATION_MISSING = "TRACK_DURATION_MISSING"
    TRACK_DURATION_INVALID = "TRACK_DURATION_INVALID"
    EVIDENCE_PROVENANCE_MISSING = "EVIDENCE_PROVENANCE_MISSING"
    EVIDENCE_PROVENANCE_INVALID = "EVIDENCE_PROVENANCE_INVALID"
    DUPLICATE_TRACK_ID = "DUPLICATE_TRACK_ID"


ISSUE_PRECEDENCE = tuple(TrackEvidenceIssueCode)

ISSUE_EXPLANATIONS = {
    TrackEvidenceIssueCode.RECORD_INVALID_JSON: (
        "The serialized evidence payload is not valid JSON."
    ),
    TrackEvidenceIssueCode.RECORD_DUPLICATE_KEY: (
        "The serialized evidence payload contains a duplicate JSON object key."
    ),
    TrackEvidenceIssueCode.RECORD_NOT_OBJECT: (
        "The serialized evidence payload must be a JSON object."
    ),
    TrackEvidenceIssueCode.RECORD_EXTRA_FIELD: (
        "The serialized evidence payload contains an unsupported field."
    ),
    TrackEvidenceIssueCode.TRACK_ID_MISSING: "Track identity is required.",
    TrackEvidenceIssueCode.TRACK_ID_INVALID: (
        "Track identity must be an explicit nonblank string without surrounding whitespace."
    ),
    TrackEvidenceIssueCode.TRACK_TITLE_MISSING: "Track title is required.",
    TrackEvidenceIssueCode.TRACK_TITLE_INVALID: (
        "Track title must be an explicit nonblank string without surrounding whitespace."
    ),
    TrackEvidenceIssueCode.TRACK_ARTIST_MISSING: "Track artist identity is required.",
    TrackEvidenceIssueCode.TRACK_ARTIST_INVALID: (
        "Track artist identity must be an explicit nonblank string without surrounding whitespace."
    ),
    TrackEvidenceIssueCode.TRACK_ARTIST_OUT_OF_SCOPE: (
        "Track artist identity is outside the exact artist inspection scope."
    ),
    TrackEvidenceIssueCode.TRACK_DURATION_MISSING: "Track duration is required.",
    TrackEvidenceIssueCode.TRACK_DURATION_INVALID: (
        "Track duration must be a strict positive integer number of seconds."
    ),
    TrackEvidenceIssueCode.EVIDENCE_PROVENANCE_MISSING: (
        "Evidence provenance is required."
    ),
    TrackEvidenceIssueCode.EVIDENCE_PROVENANCE_INVALID: (
        "Evidence provenance must contain explicit source type, source reference, and rationale strings."
    ),
    TrackEvidenceIssueCode.DUPLICATE_TRACK_ID: (
        "Every record sharing a duplicate exact track identity is rejected."
    ),
}


class EvidenceSnapshotRecord(FrozenTrackEvidenceModel):
    record_id: str = Field(min_length=1, max_length=200)
    payload_json: str = Field(max_length=100_000)

    @field_validator("record_id")
    @classmethod
    def require_exact_record_id(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("record ID cannot contain surrounding whitespace")
        return value


class EvidenceSnapshot(FrozenTrackEvidenceModel):
    schema_version: Literal["1.0"] = TRACK_EVIDENCE_SCHEMA_VERSION
    snapshot_id: str = Field(min_length=1, max_length=200)
    evidence_domain: Literal[EvidenceDomain.TRACK] = EvidenceDomain.TRACK
    records: tuple[EvidenceSnapshotRecord, ...]

    @field_validator("snapshot_id")
    @classmethod
    def require_exact_snapshot_id(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("snapshot ID cannot contain surrounding whitespace")
        return value

    @model_validator(mode="after")
    def require_identifiable_unique_records(self) -> EvidenceSnapshot:
        record_ids = tuple(record.record_id for record in self.records)
        if len(record_ids) != len(set(record_ids)):
            raise ValueError("snapshot record IDs must be unique")
        return self


class TrackEvidenceValidationRequest(FrozenTrackEvidenceModel):
    schema_version: Literal["1.0"] = TRACK_EVIDENCE_SCHEMA_VERSION
    objective_assessment: ObjectiveAssessment
    artist_questionnaire: ArtistQuestionnaireSeed
    snapshot: EvidenceSnapshot
    approved_local_rules: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_snapshot_level_correspondence(self) -> TrackEvidenceValidationRequest:
        if self.objective_assessment.outcome is not AssessmentOutcome.SUFFICIENT:
            raise ValueError("objective assessment must be sufficient")
        assessment_objective = self.objective_assessment.objective
        questionnaire_objective = self.artist_questionnaire.objective
        if (
            assessment_objective.objective_id != questionnaire_objective.objective_id
            or assessment_objective.statement != questionnaire_objective.statement
        ):
            raise ValueError("objective artifacts must correspond exactly")
        if self.approved_local_rules:
            raise ValueError(
                "schema 1.0 approves no local validation rules; "
                "approved_local_rules must be empty"
            )
        return self


class EvidenceProvenance(FrozenTrackEvidenceModel):
    source_type: str
    source_reference: str
    rationale: str

    @field_validator("source_type", "source_reference", "rationale")
    @classmethod
    def require_exact_nonblank_provenance(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError(
                "provenance strings must be nonblank without surrounding whitespace"
            )
        return value


class TrackEvidenceIssue(FrozenTrackEvidenceModel):
    code: TrackEvidenceIssueCode
    field_path: str
    explanation: str

    @model_validator(mode="after")
    def require_fixed_explanation(self) -> TrackEvidenceIssue:
        if self.explanation != ISSUE_EXPLANATIONS[self.code]:
            raise ValueError("issue explanation must match the fixed issue contract")
        return self


class ValidatedTrackEvidence(FrozenTrackEvidenceModel):
    ordinal: int = Field(gt=0)
    record_id: str
    source_payload_json: str
    track_id: str
    title: str
    artist_name: str
    duration_seconds: int = Field(gt=0)
    provenance: EvidenceProvenance
    inclusion_basis: Literal["complete_serialized_track_evidence"] = (
        "complete_serialized_track_evidence"
    )

    @field_validator("record_id", "track_id", "title", "artist_name")
    @classmethod
    def require_exact_nonblank_identity(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError(
                "validated identity strings must be nonblank without surrounding whitespace"
            )
        return value


class RejectedTrackEvidence(FrozenTrackEvidenceModel):
    record_id: str
    source_payload_json: str
    issues: tuple[TrackEvidenceIssue, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_fixed_issue_order(self) -> RejectedTrackEvidence:
        precedence = {code: index for index, code in enumerate(ISSUE_PRECEDENCE)}
        expected = tuple(
            sorted(
                self.issues,
                key=lambda issue: (
                    precedence[issue.code],
                    issue.field_path.encode("utf-8"),
                ),
            )
        )
        if self.issues != expected:
            raise ValueError("rejection issues must use fixed issue precedence")
        issue_keys = tuple((issue.code, issue.field_path) for issue in self.issues)
        if len(issue_keys) != len(set(issue_keys)):
            raise ValueError("rejection issues must be unique by code and field path")
        return self


class TrackEvidenceValidationSummary(FrozenTrackEvidenceModel):
    input_record_count: int = Field(ge=0)
    validated_record_count: int = Field(ge=0)
    rejected_record_count: int = Field(ge=0)

    @model_validator(mode="after")
    def partition_counts_match(self) -> TrackEvidenceValidationSummary:
        if self.input_record_count != (
            self.validated_record_count + self.rejected_record_count
        ):
            raise ValueError("validated and rejected counts must partition input count")
        return self


class TrackEvidenceValidationArtifact(FrozenTrackEvidenceModel):
    schema_version: Literal["1.0"] = TRACK_EVIDENCE_SCHEMA_VERSION
    artifact_kind: Literal["track_evidence_validation"] = (
        "track_evidence_validation"
    )
    snapshot_id: str
    objective_id: str
    objective_statement: str
    ordering_rule: Literal["record_id_utf8_bytes"] = "record_id_utf8_bytes"
    issue_ordering_rule: Literal["schema_1_0_issue_precedence"] = (
        "schema_1_0_issue_precedence"
    )
    artist_inspection_scope: tuple[str, ...]
    input_record_ids: tuple[str, ...]
    validated_records: tuple[ValidatedTrackEvidence, ...]
    rejected_records: tuple[RejectedTrackEvidence, ...]
    summary: TrackEvidenceValidationSummary
    preference_established: Literal[False] = False
    eligibility_established: Literal[False] = False
    suitability_established: Literal[False] = False
    familiarity_established: Literal[False] = False
    recommendation_claims: Literal[False] = False
    playlist_membership_claims: Literal[False] = False
    scoring_performed: Literal[False] = False
    selection_performed: Literal[False] = False
    playlist_construction_performed: Literal[False] = False

    @model_validator(mode="after")
    def enforce_complete_deterministic_partition(self) -> TrackEvidenceValidationArtifact:
        utf8_sorted_scope = tuple(
            sorted(self.artist_inspection_scope, key=lambda value: value.encode("utf-8"))
        )
        if self.artist_inspection_scope != utf8_sorted_scope:
            raise ValueError("artist inspection scope must use UTF-8 byte order")
        if len(self.artist_inspection_scope) != len(set(self.artist_inspection_scope)):
            raise ValueError("artist inspection scope must contain unique identities")

        expected_input_ids = tuple(
            sorted(self.input_record_ids, key=lambda value: value.encode("utf-8"))
        )
        if self.input_record_ids != expected_input_ids:
            raise ValueError("input record IDs must use UTF-8 byte order")
        if len(self.input_record_ids) != len(set(self.input_record_ids)):
            raise ValueError("input record IDs must be unique")

        validated_ids = tuple(record.record_id for record in self.validated_records)
        rejected_ids = tuple(record.record_id for record in self.rejected_records)
        if validated_ids != tuple(sorted(validated_ids, key=lambda value: value.encode("utf-8"))):
            raise ValueError("validated records must use record-ID order")
        if rejected_ids != tuple(sorted(rejected_ids, key=lambda value: value.encode("utf-8"))):
            raise ValueError("rejected records must use record-ID order")
        if set(validated_ids) & set(rejected_ids):
            raise ValueError("a record cannot appear in both partitions")
        if tuple(sorted(validated_ids + rejected_ids, key=lambda value: value.encode("utf-8"))) != self.input_record_ids:
            raise ValueError("every input record must appear in exactly one partition")
        if tuple(record.ordinal for record in self.validated_records) != tuple(
            range(1, len(self.validated_records) + 1)
        ):
            raise ValueError("validated ordinals must be contiguous and one-based")
        validated_track_ids = tuple(
            record.track_id for record in self.validated_records
        )
        if len(validated_track_ids) != len(set(validated_track_ids)):
            raise ValueError("validated track identities must be unique")
        if any(
            record.artist_name not in set(self.artist_inspection_scope)
            for record in self.validated_records
        ):
            raise ValueError("validated track artists must be in exact inspection scope")
        if self.summary != TrackEvidenceValidationSummary(
            input_record_count=len(self.input_record_ids),
            validated_record_count=len(self.validated_records),
            rejected_record_count=len(self.rejected_records),
        ):
            raise ValueError("summary must match the artifact partitions")
        return self

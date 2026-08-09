from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProvenanceType(StrEnum):
    DIRECT_OBSERVATION = "DIRECT_OBSERVATION"
    HUMAN_ASSESSMENT = "HUMAN_ASSESSMENT"
    DERIVED_QUERY_RESULT = "DERIVED_QUERY_RESULT"
    MIGRATION_DERIVATION = "MIGRATION_DERIVATION"


class ConstraintStatus(StrEnum):
    PASS = "PASS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"


class TracklistCompleteness(StrEnum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    NOT_OBSERVED = "NOT_OBSERVED"


class BoundaryKnowledge(StrEnum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"


class SegmentRelationship(StrEnum):
    FIRST = "FIRST"
    CONTIGUOUS = "CONTIGUOUS"
    GAP_UNKNOWN_SIZE = "GAP_UNKNOWN_SIZE"


class EvidenceStandard(StrEnum):
    LEGACY_V1 = "LEGACY_V1"
    CONTEMPORARY_MANUAL = "CONTEMPORARY_MANUAL"
    RECOVERED_HISTORICAL = "RECOVERED_HISTORICAL"


class SupportStatus(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"


class EvidenceSourceInput(StrictModel):
    source_key: str
    source_type: str
    source_reference: str
    original_filename: str | None = None
    local_path: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    source_timestamp: datetime | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_checksum_for_local_bytes(self) -> EvidenceSourceInput:
        if self.local_path is not None and self.sha256 is None:
            raise ValueError("local evidence bytes require sha256")
        return self


class FieldEvidenceInput(StrictModel):
    source_key: str
    field_name: str
    provenance_type: ProvenanceType = ProvenanceType.DIRECT_OBSERVATION
    support_status: SupportStatus = SupportStatus.FULL
    notes: str | None = None


class TrackInput(StrictModel):
    observed_ordinal: int = Field(gt=0)
    evidence_segment: int = Field(gt=0)
    segment_ordinal: int = Field(gt=0)
    absolute_position: int | None = Field(default=None, gt=0)
    title: str | None = None
    artist: str | None = None
    canonical_identity_established: bool = True
    canonical_title: str | None = None
    canonical_artist: str | None = None
    normalized_title: str | None = None
    normalized_artist: str | None = None
    explicit_flag: bool | None = None
    version_or_remaster_text: str | None = None
    notes: str | None = None
    evidence: list[FieldEvidenceInput] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_v1_position(cls, value: object) -> object:
        if isinstance(value, dict) and "position" in value and "observed_ordinal" not in value:
            result = dict(value)
            position = result.pop("position")
            result.update(
                observed_ordinal=position,
                evidence_segment=1,
                segment_ordinal=position,
                absolute_position=position,
            )
            return result
        return value

    @model_validator(mode="after")
    def validate_identity(self) -> TrackInput:
        if not any((self.title, self.artist, self.version_or_remaster_text, self.notes)):
            raise ValueError("an observed placement requires at least one preserved raw field")
        if (self.canonical_title is None) != (self.canonical_artist is None):
            raise ValueError("canonical title and artist must be supplied together")
        if self.canonical_identity_established and (
            (self.canonical_title is None or self.canonical_artist is None)
            and (self.title is None or self.artist is None)
        ):
            raise ValueError("established canonical identity requires both title and artist")
        return self


class SegmentInput(StrictModel):
    segment_ordinal: int = Field(gt=0)
    relationship_to_previous: SegmentRelationship
    captures_playlist_start: BoundaryKnowledge = BoundaryKnowledge.UNKNOWN
    captures_playlist_end: BoundaryKnowledge = BoundaryKnowledge.UNKNOWN
    notes: str | None = None
    evidence: list[FieldEvidenceInput] = Field(default_factory=list)


class ConstraintResultInput(StrictModel):
    status: ConstraintStatus
    evidence: str | None = None
    provenance_type: ProvenanceType = ProvenanceType.HUMAN_ASSESSMENT
    recorded_by: str | None = None
    provenance_notes: str | None = None


class ConstraintInput(StrictModel):
    constraint_type: str
    constraint_text: str
    is_hard_constraint: bool = True
    result: ConstraintResultInput | None = None


class ObservationInput(StrictModel):
    observation_type: str
    observation_text: str
    severity: str | None = None
    track_observed_ordinal: int | None = Field(default=None, gt=0)
    track_position: int | None = Field(default=None, gt=0)
    provenance_type: ProvenanceType = ProvenanceType.DIRECT_OBSERVATION
    recorded_by: str | None = None
    provenance_notes: str | None = None


class ExperimentInput(StrictModel):
    recorded_at: datetime | None = None
    created_at: datetime | None = Field(default=None, exclude=True)
    generated_at: datetime | None = None
    prompt: str | None = None
    prompt_title: str | None = None
    source_system: str | None = "Maestro Beta"
    generated_title: str | None = None
    generated_description: str | None = None
    requested_track_count: int | None = Field(default=None, ge=0)
    generated_track_count: int | None = Field(default=None, ge=0)
    saved: bool | None = None
    tracklist_completeness: TracklistCompleteness | None = None
    evidence_standard: EvidenceStandard = EvidenceStandard.CONTEMPORARY_MANUAL
    assessment: str | None = None
    notes: str | None = None
    segments: list[SegmentInput] = Field(default_factory=list)
    tracks: list[TrackInput]
    evidence_sources: list[EvidenceSourceInput] = Field(default_factory=list)
    evidence: list[FieldEvidenceInput] = Field(default_factory=list)
    constraints: list[ConstraintInput] = Field(default_factory=list)
    observations: list[ObservationInput] = Field(default_factory=list)
    prompt_labels: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def accept_v1_shape(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        result = dict(value)
        if result.get("recorded_at") is None and result.get("created_at") is not None:
            result["recorded_at"] = result["created_at"]
        tracks = result.get("tracks", [])
        if tracks and "segments" not in result:
            result["segments"] = [{
                "segment_ordinal": 1,
                "relationship_to_previous": "FIRST",
                "captures_playlist_start": "YES",
                "captures_playlist_end": "YES",
            }]
            result.setdefault("tracklist_completeness", "COMPLETE")
            result.setdefault("generated_track_count", len(tracks))
        elif not tracks:
            result.setdefault("tracklist_completeness", "NOT_OBSERVED")
        return result

    @model_validator(mode="after")
    def validate_evidence_model(self) -> ExperimentInput:
        if self.recorded_at is None and self.created_at is not None:
            self.recorded_at = self.created_at
        completeness = self.tracklist_completeness
        if completeness is None:
            raise ValueError("tracklist_completeness is required")
        segment_numbers = [item.segment_ordinal for item in self.segments]
        if segment_numbers != list(range(1, len(segment_numbers) + 1)):
            raise ValueError("segment ordinals must be contiguous from 1")
        if self.segments and self.segments[0].relationship_to_previous != SegmentRelationship.FIRST:
            raise ValueError("the first segment must have relationship FIRST")
        if any(item.relationship_to_previous == SegmentRelationship.FIRST for item in self.segments[1:]):
            raise ValueError("only the first segment may use relationship FIRST")
        observed = [item.observed_ordinal for item in self.tracks]
        if len(observed) == len(set(observed)) and sorted(observed) != list(range(1, len(observed) + 1)):
            raise ValueError("observed ordinals must be contiguous from 1")
        absolute = [item.absolute_position for item in self.tracks if item.absolute_position is not None]
        segment_set = set(segment_numbers)
        for number in segment_numbers:
            local = [item.segment_ordinal for item in self.tracks if item.evidence_segment == number]
            if len(local) == len(set(local)) and sorted(local) != list(range(1, len(local) + 1)):
                raise ValueError("track segment ordinals must be contiguous from 1")
        if any(item.evidence_segment not in segment_set for item in self.tracks):
            raise ValueError("every track must reference an existing evidence segment")
        if completeness == TracklistCompleteness.NOT_OBSERVED and (self.tracks or self.segments):
            raise ValueError("NOT_OBSERVED requires no segments or placements")
        if completeness == TracklistCompleteness.PARTIAL and not self.tracks:
            raise ValueError("PARTIAL requires at least one observed placement")
        if completeness == TracklistCompleteness.COMPLETE:
            if not self.segments or not self.tracks:
                raise ValueError("COMPLETE requires observed track evidence")
            if self.segments[0].captures_playlist_start != BoundaryKnowledge.YES:
                raise ValueError("COMPLETE requires established playlist start")
            if self.segments[-1].captures_playlist_end != BoundaryKnowledge.YES:
                raise ValueError("COMPLETE requires established playlist end")
            if any(item.relationship_to_previous == SegmentRelationship.GAP_UNKNOWN_SIZE for item in self.segments):
                raise ValueError("COMPLETE forbids unknown gaps")
            if len(absolute) == len(set(absolute)) and sorted(absolute) != list(range(1, len(self.tracks) + 1)):
                raise ValueError("COMPLETE requires contiguous absolute positions from 1")
            if self.generated_track_count != len(self.tracks):
                raise ValueError("COMPLETE requires generated count to equal observed placements")
        known_observed = set(observed)
        known_positions = set(absolute)
        for observation in self.observations:
            if observation.track_observed_ordinal is not None and observation.track_observed_ordinal not in known_observed:
                raise ValueError("observation track_observed_ordinal must identify an ingested placement")
            if observation.track_position is not None and observation.track_position not in known_positions:
                raise ValueError("observation track_position must identify a known absolute position")
        source_keys = [item.source_key for item in self.evidence_sources]
        if len(source_keys) != len(set(source_keys)):
            raise ValueError("evidence source keys must be unique")
        all_links = self.evidence + [link for track in self.tracks for link in track.evidence]
        all_links += [link for segment in self.segments for link in segment.evidence]
        if any(link.source_key not in set(source_keys) for link in all_links):
            raise ValueError("evidence links must reference declared source keys")
        if self.evidence_standard == EvidenceStandard.RECOVERED_HISTORICAL:
            required = {"tracklist_completeness"}
            for field, value in {
                "prompt": self.prompt,
                "source_system": self.source_system,
                "generated_title": self.generated_title,
                "generated_description": self.generated_description,
                "generated_at": self.generated_at,
                "requested_track_count": self.requested_track_count,
                "generated_track_count": self.generated_track_count,
                "saved": self.saved,
            }.items():
                if value is not None:
                    required.add(field)
            supported = {item.field_name for item in self.evidence}
            missing = required - supported
            if missing:
                raise ValueError(f"recovered historical fields lack evidence: {sorted(missing)}")
            for track in self.tracks:
                asserted = {name for name, value in {
                    "title": track.title,
                    "artist": track.artist,
                    "absolute_position": track.absolute_position,
                    "version_or_remaster_text": track.version_or_remaster_text,
                }.items() if value is not None}
                track_supported = {item.field_name for item in track.evidence}
                if not asserted <= track_supported:
                    raise ValueError("recovered historical track fields lack evidence")
        return self


class GenerationFailureInput(StrictModel):
    recorded_at: datetime | None = None
    created_at: datetime | None = Field(default=None, exclude=True)
    generated_at: datetime | None = None
    prompt: str | None = None
    source_system: str | None = "Maestro Beta"
    failure_type: str
    displayed_message: str | None = None
    evidence_standard: EvidenceStandard = EvidenceStandard.CONTEMPORARY_MANUAL
    evidence_sources: list[EvidenceSourceInput] = Field(default_factory=list)
    evidence: list[FieldEvidenceInput] = Field(default_factory=list)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_failure_evidence(self) -> GenerationFailureInput:
        keys = {item.source_key for item in self.evidence_sources}
        if any(item.source_key not in keys for item in self.evidence):
            raise ValueError("failure evidence links must reference declared source keys")
        if self.evidence_standard == EvidenceStandard.RECOVERED_HISTORICAL:
            required = {"failure_type"}
            for field, value in {
                "prompt": self.prompt, "source_system": self.source_system,
                "generated_at": self.generated_at, "displayed_message": self.displayed_message,
            }.items():
                if value is not None:
                    required.add(field)
            supported = {item.field_name for item in self.evidence}
            if not required <= supported:
                raise ValueError("recovered historical failure fields lack evidence")
        return self

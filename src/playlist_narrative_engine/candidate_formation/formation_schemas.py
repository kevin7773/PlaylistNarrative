from __future__ import annotations

import json
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.schemas import (
    CandidateIdentityMetadataArtifact,
    EvidenceState,
    FamiliarityEvidenceArtifact,
    FrozenCandidateEvidenceModel,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    TrackFeatureEvidenceArtifact,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.sequencing.schemas import TrackCandidate
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.track_evidence import (
    TrackEvidenceValidationArtifact,
    ValidatedTrackEvidence,
)


CANDIDATE_FORMATION_SCHEMA_VERSION = "1.0"


class CandidateFieldName(StrEnum):
    TRACK_ID = "track_id"
    TITLE = "title"
    ARTIST_NAME = "artist_name"
    DURATION_SECONDS = "duration_seconds"
    ENERGY = "energy"
    FAMILIARITY = "familiarity"
    PREFERENCE = "preference"
    CONTEXT_FIT = "context_fit"
    INSTRUMENTALNESS = "instrumentalness"
    LYRICAL_DISTRACTION = "lyrical_distraction"
    GROOVE = "groove"


CANDIDATE_FIELD_ORDER = tuple(CandidateFieldName)


class PreferenceMappingEntry(FrozenCandidateEvidenceModel):
    rating: Rating
    value: float = Field(ge=0.0, le=1.0, strict=True)


class PreferenceMappingRule(FrozenCandidateEvidenceModel):
    rule_name: str = Field(min_length=1, max_length=200)
    rule_version: str = Field(min_length=1, max_length=100)
    mappings: tuple[PreferenceMappingEntry, ...]

    @field_validator("rule_name", "rule_version")
    @classmethod
    def require_exact_rule_identity(cls, value: str) -> str:
        return _exact(value)

    @field_validator("mappings", mode="before")
    @classmethod
    def canonicalize_mappings(cls, value: Any) -> tuple[object, ...]:
        return tuple(sorted(tuple(value), key=lambda item: _mapping_rating(item).encode("utf-8")))

    @model_validator(mode="after")
    def require_exact_supported_mapping(self) -> PreferenceMappingRule:
        ratings = tuple(entry.rating for entry in self.mappings)
        if len(ratings) != len(set(ratings)):
            raise ValueError("preference mapping ratings must be unique")
        if set(ratings) != {Rating.LOVE, Rating.LIKE, Rating.MEH}:
            raise ValueError(
                "preference mapping must define exactly Love, Like, and Meh"
            )
        return self


class CandidateFormationPolicy(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_FORMATION_SCHEMA_VERSION
    policy_id: str = Field(min_length=1, max_length=200)
    policy_version: str = Field(min_length=1, max_length=100)
    preference_rule: PreferenceMappingRule
    hard_excluded_ratings: tuple[Rating, ...] = (
        Rating.NO_THANKS,
        Rating.PENCIL,
        Rating.FORBIDDEN,
    )
    unsupported_ratings: tuple[Rating, ...] = (Rating.UNKNOWN,)

    @field_validator("policy_id", "policy_version")
    @classmethod
    def require_exact_policy_identity(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_fixed_rating_boundaries(self) -> CandidateFormationPolicy:
        if self.hard_excluded_ratings != (
            Rating.NO_THANKS,
            Rating.PENCIL,
            Rating.FORBIDDEN,
        ):
            raise ValueError("hard excluded ratings must use the fixed policy order")
        if self.unsupported_ratings != (Rating.UNKNOWN,):
            raise ValueError("Unknown must remain the sole unsupported rating")
        return self


class CandidateFormationRequest(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_FORMATION_SCHEMA_VERSION
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    journey_plan: JourneyPlanArtifact
    track_validation: TrackEvidenceValidationArtifact
    taste_evidence: LocalTasteEvidenceArtifact
    familiarity_evidence: FamiliarityEvidenceArtifact
    track_feature_evidence: TrackFeatureEvidenceArtifact
    objective_context_evidence: ObjectiveContextEvidenceArtifact
    identity_metadata: CandidateIdentityMetadataArtifact | None = None
    hard_constraints: tuple[CandidateHardConstraint, ...] = ()
    policy: CandidateFormationPolicy

    @field_validator("request_id")
    @classmethod
    def require_exact_request_id(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def validate_source_correspondence(self) -> CandidateFormationRequest:
        objective = self.accepted_objective.objective
        if self.journey_plan.objective != objective:
            raise ValueError("Journey Plan objective must correspond exactly")
        if (
            self.journey_plan.objective_safety_artifact_id
            != self.accepted_objective.artifact_id
        ):
            raise ValueError("Journey Plan must reference the accepted objective artifact")
        if (
            self.track_validation.objective_id != objective.objective_id
            or self.track_validation.objective_statement != objective.statement
        ):
            raise ValueError("Track validation objective must correspond exactly")
        context = self.objective_context_evidence
        if (
            context.objective_id != objective.objective_id
            or context.objective_statement != objective.statement
            or context.journey_id != self.journey_plan.journey_id
        ):
            raise ValueError("Objective-context evidence must correspond exactly")
        snapshot_id = self.track_validation.snapshot_id
        if any(
            artifact.track_snapshot_id != snapshot_id
            for artifact in (
                self.familiarity_evidence,
                self.track_feature_evidence,
                self.objective_context_evidence,
            )
        ):
            raise ValueError("track-scoped evidence must reference the validated snapshot")
        if self.taste_evidence.profile_id != self.familiarity_evidence.profile_id:
            raise ValueError("taste and familiarity evidence must use one exact profile")
        if self.identity_metadata is not None and self.identity_metadata.track_snapshot_id != snapshot_id:
            raise ValueError("candidate identity metadata must reference the validated snapshot")
        keys = tuple(item.constraint_key for item in self.hard_constraints)
        if len(keys) != len(set(keys)):
            raise ValueError("hard constraint keys must be unique")
        validated_track_ids = {
            record.track_id for record in self.track_validation.validated_records
        }
        for artifact in (
            self.familiarity_evidence,
            self.track_feature_evidence,
            self.objective_context_evidence,
        ):
            if any(record.track_id not in validated_track_ids for record in artifact.records):
                raise ValueError("track-scoped evidence contains an unvalidated track identity")
        return self


class CandidateConstraintField(StrEnum):
    DISPLAYED_TITLE = "displayed_title"
    DISPLAYED_ARTIST = "displayed_artist"
    SOURCE_CATALOG_IDENTITY = "source_catalog_identity"
    RELEASE_VERSION_IDENTITY = "release_version_identity"
    DISPLAYED_EXPLICIT = "displayed_explicit"


class CandidateHardConstraint(FrozenCandidateEvidenceModel):
    constraint_key: str = Field(min_length=1, max_length=200)
    field: CandidateConstraintField
    expected_json: str

    @field_validator("constraint_key")
    @classmethod
    def require_exact_key(cls, value: str) -> str:
        return _exact(value)

    @field_validator("expected_json")
    @classmethod
    def require_typed_expected_value(cls, value: str, info: Any) -> str:
        parsed = json.loads(value, parse_constant=_reject_json_constant)
        field = info.data.get("field")
        if field is CandidateConstraintField.DISPLAYED_EXPLICIT:
            if type(parsed) is not bool:
                raise ValueError("displayed Explicit constraints require a Boolean")
        elif not isinstance(parsed, str) or not parsed or parsed != parsed.strip():
            raise ValueError("identity constraints require an exact nonblank string")
        return value


class CandidateEligibilityState(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNKNOWN = "UNKNOWN"


class CandidateEligibilityReason(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
    EXACT_MISMATCH = "EXACT_MISMATCH"
    PROPERTY_MATCH = "PROPERTY_MATCH"
    PROPERTY_MISMATCH = "PROPERTY_MISMATCH"
    REQUIRED_METADATA_UNKNOWN = "REQUIRED_METADATA_UNKNOWN"


class CandidateConstraintEligibility(FrozenCandidateEvidenceModel):
    constraint_key: str
    field: CandidateConstraintField
    state: CandidateEligibilityState
    reason: CandidateEligibilityReason
    expected_json: str
    observed_json: str | None
    source_evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def require_decision_consistency(self) -> CandidateConstraintEligibility:
        expected = json.loads(self.expected_json, parse_constant=_reject_json_constant)
        if self.state is CandidateEligibilityState.UNKNOWN:
            if self.observed_json is not None or self.reason is not CandidateEligibilityReason.REQUIRED_METADATA_UNKNOWN:
                raise ValueError("UNKNOWN eligibility requires an unknown observed value")
            return self
        if self.observed_json is None or not self.source_evidence_ids:
            raise ValueError("decided eligibility requires provenance-backed observed metadata")
        observed = json.loads(self.observed_json, parse_constant=_reject_json_constant)
        matches = observed == expected and type(observed) is type(expected)
        if (self.state is CandidateEligibilityState.ELIGIBLE) != matches:
            raise ValueError("eligibility state must match exact typed comparison")
        expected_reason = (
            CandidateEligibilityReason.PROPERTY_MATCH
            if matches and self.field is CandidateConstraintField.DISPLAYED_EXPLICIT
            else CandidateEligibilityReason.EXACT_MATCH
            if matches
            else CandidateEligibilityReason.PROPERTY_MISMATCH
            if self.field is CandidateConstraintField.DISPLAYED_EXPLICIT
            else CandidateEligibilityReason.EXACT_MISMATCH
        )
        if self.reason is not expected_reason:
            raise ValueError("eligibility reason must match its deterministic comparison")
        return self


class CandidateIdentitySnapshot(FrozenCandidateEvidenceModel):
    exact_displayed_title: str
    exact_displayed_artist: str
    source_catalog_identity: str | None = None
    release_version_identity: str | None = None
    displayed_explicit: bool | None = None
    metadata_artifact_id: str | None = None
    source_catalog_state: EvidenceState | None = None
    release_version_state: EvidenceState | None = None
    displayed_explicit_state: EvidenceState | None = None
    source_catalog_evidence_ids: tuple[str, ...] = ()
    release_version_evidence_ids: tuple[str, ...] = ()
    displayed_explicit_evidence_ids: tuple[str, ...] = ()


class CandidateMechanismEvent(StrEnum):
    DISCOVERED = "CANDIDATE_DISCOVERED"
    IDENTITY_CAPTURED = "IDENTITY_CAPTURED"
    METADATA_CAPTURED = "METADATA_CAPTURED"
    ELIGIBILITY_EVALUATED = "ELIGIBILITY_EVALUATED"
    RETAINED = "RETAINED_FOR_RANKING"
    WITHHELD = "WITHHELD_BEFORE_RANKING"


class CandidateMechanismTrace(FrozenCandidateEvidenceModel):
    track_id: str
    identity: CandidateIdentitySnapshot
    eligibility: tuple[CandidateConstraintEligibility, ...]
    events: tuple[CandidateMechanismEvent, ...]


class FormationBasis(StrEnum):
    DIRECT_EVIDENCE = "direct_evidence"
    VERSIONED_DERIVATION = "versioned_derivation"


class CandidateFieldEvidence(FrozenCandidateEvidenceModel):
    field: CandidateFieldName
    source_artifact_kind: str = Field(min_length=1, max_length=200)
    source_artifact_id: str = Field(min_length=1, max_length=200)
    source_record_identity: str = Field(min_length=1, max_length=500)
    source_evidence_ids: tuple[str, ...]
    basis: FormationBasis
    rule_name: str | None = None
    rule_version: str | None = None
    serialized_inputs_json: str
    result_json: str
    explanation: str = Field(min_length=1, max_length=1_000)

    @field_validator(
        "source_artifact_kind",
        "source_artifact_id",
        "source_record_identity",
        "explanation",
    )
    @classmethod
    def require_exact_text(cls, value: str) -> str:
        return _exact(value)

    @field_validator("source_evidence_ids")
    @classmethod
    def require_exact_evidence_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item or item != item.strip() for item in value):
            raise ValueError("source evidence IDs must be nonblank and exact")
        return value

    @field_validator("serialized_inputs_json", "result_json")
    @classmethod
    def require_valid_json(cls, value: str) -> str:
        try:
            json.loads(value, parse_constant=_reject_json_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("field evidence values must be valid JSON") from exc
        return value

    @model_validator(mode="after")
    def require_basis_contract(self) -> CandidateFieldEvidence:
        expected_ids = tuple(sorted(self.source_evidence_ids, key=lambda item: item.encode("utf-8")))
        if self.source_evidence_ids != expected_ids:
            raise ValueError("source evidence IDs must use UTF-8 order")
        if len(expected_ids) != len(set(expected_ids)):
            raise ValueError("source evidence IDs must be unique")
        if self.basis is FormationBasis.VERSIONED_DERIVATION:
            if not self.rule_name or not self.rule_version:
                raise ValueError("derived fields require a named versioned rule")
        elif self.rule_name is not None or self.rule_version is not None:
            raise ValueError("direct fields cannot claim a derivation rule")
        return self


class WithholdingReasonCode(StrEnum):
    HARD_ELIGIBILITY_EXCLUDED = "HARD_ELIGIBILITY_EXCLUDED"
    TRACK_IDENTITY_CONFLICTING = "TRACK_IDENTITY_CONFLICTING"
    ARTIST_IDENTITY_CONFLICTING = "ARTIST_IDENTITY_CONFLICTING"
    EVIDENCE_CONFLICTING = "EVIDENCE_CONFLICTING"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    EVIDENCE_INAPPLICABLE = "EVIDENCE_INAPPLICABLE"
    DERIVATION_RULE_UNAPPROVED = "DERIVATION_RULE_UNAPPROVED"
    DERIVATION_INPUT_UNAVAILABLE = "DERIVATION_INPUT_UNAVAILABLE"
    DERIVED_VALUE_INVALID = "DERIVED_VALUE_INVALID"
    HARD_CONSTRAINT_INELIGIBLE = "HARD_CONSTRAINT_INELIGIBLE"
    HARD_CONSTRAINT_UNKNOWN = "HARD_CONSTRAINT_UNKNOWN"


WITHHOLDING_REASON_PRECEDENCE = tuple(WithholdingReasonCode)
WITHHOLDING_REASON_EXPLANATIONS = {
    WithholdingReasonCode.HARD_ELIGIBILITY_EXCLUDED: "User-owned taste evidence establishes a hard exclusion.",
    WithholdingReasonCode.TRACK_IDENTITY_CONFLICTING: "Source evidence conflicts with the exact validated track identity.",
    WithholdingReasonCode.ARTIST_IDENTITY_CONFLICTING: "Source evidence conflicts with the exact validated artist identity.",
    WithholdingReasonCode.EVIDENCE_CONFLICTING: "Applicable source evidence contains unresolved conflicting claims.",
    WithholdingReasonCode.EVIDENCE_UNAVAILABLE: "Required corresponding source evidence is unavailable.",
    WithholdingReasonCode.EVIDENCE_UNSUPPORTED: "Supplied source evidence is unsupported by this formation policy.",
    WithholdingReasonCode.EVIDENCE_INAPPLICABLE: "Supplied source evidence is explicitly inapplicable to this required field.",
    WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED: "No approved versioned rule can derive this required field from the supplied evidence.",
    WithholdingReasonCode.DERIVATION_INPUT_UNAVAILABLE: "A required input to an approved derivation rule is unavailable.",
    WithholdingReasonCode.DERIVED_VALUE_INVALID: "An approved derivation rule produced a value outside the field contract.",
    WithholdingReasonCode.HARD_CONSTRAINT_INELIGIBLE: "Authoritative candidate metadata establishes a hard-constraint violation.",
    WithholdingReasonCode.HARD_CONSTRAINT_UNKNOWN: "Required candidate metadata is unknown, so hard-constraint compliance is not established.",
}


class WithholdingReason(FrozenCandidateEvidenceModel):
    code: WithholdingReasonCode
    field_path: str = Field(min_length=1, max_length=500)
    source_artifact_id: str = Field(min_length=1, max_length=200)
    explanation: str

    @field_validator("field_path", "source_artifact_id")
    @classmethod
    def require_exact_identity(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_fixed_explanation(self) -> WithholdingReason:
        if self.explanation != WITHHOLDING_REASON_EXPLANATIONS[self.code]:
            raise ValueError("withholding explanation must match its fixed contract")
        return self


class FormedCandidateEntry(FrozenCandidateEvidenceModel):
    ordinal: int = Field(gt=0)
    candidate: TrackCandidate
    field_evidence: tuple[CandidateFieldEvidence, ...]
    identity: CandidateIdentitySnapshot | None = None
    constraint_eligibility: tuple[CandidateConstraintEligibility, ...] = ()
    mechanism_trace: CandidateMechanismTrace | None = None

    @model_validator(mode="after")
    def require_complete_field_evidence(self) -> FormedCandidateEntry:
        if any(
            item.state is not CandidateEligibilityState.ELIGIBLE
            for item in self.constraint_eligibility
        ):
            raise ValueError("formed candidates must satisfy every evaluated hard constraint")
        if tuple(item.field for item in self.field_evidence) != CANDIDATE_FIELD_ORDER:
            raise ValueError("formed fields must have complete documented evidence order")
        for evidence in self.field_evidence:
            expected = getattr(self.candidate, evidence.field.value)
            actual = json.loads(
                evidence.result_json,
                parse_constant=_reject_json_constant,
            )
            if actual != expected or type(actual) is not type(expected):
                raise ValueError(
                    "every candidate field must equal its recorded evidence result"
                )
        return self


class WithheldCandidateEntry(FrozenCandidateEvidenceModel):
    validated_track: ValidatedTrackEvidence
    reasons: tuple[WithholdingReason, ...] = Field(min_length=1)
    identity: CandidateIdentitySnapshot | None = None
    constraint_eligibility: tuple[CandidateConstraintEligibility, ...] = ()
    mechanism_trace: CandidateMechanismTrace | None = None

    @model_validator(mode="after")
    def require_fixed_reason_order(self) -> WithheldCandidateEntry:
        precedence = {code: index for index, code in enumerate(WITHHOLDING_REASON_PRECEDENCE)}
        expected = tuple(
            sorted(
                self.reasons,
                key=lambda reason: (
                    precedence[reason.code],
                    reason.field_path.encode("utf-8"),
                    reason.source_artifact_id.encode("utf-8"),
                ),
            )
        )
        if self.reasons != expected:
            raise ValueError("withholding reasons must use fixed precedence")
        keys = tuple(
            (reason.code, reason.field_path, reason.source_artifact_id)
            for reason in self.reasons
        )
        if len(keys) != len(set(keys)):
            raise ValueError("withholding reason keys must be unique")
        return self


class CandidateFormationSummary(FrozenCandidateEvidenceModel):
    validated_track_count: int = Field(ge=0)
    formed_count: int = Field(ge=0)
    withheld_count: int = Field(ge=0)

    @model_validator(mode="after")
    def require_complete_partition(self) -> CandidateFormationSummary:
        if self.validated_track_count != self.formed_count + self.withheld_count:
            raise ValueError("formed and withheld counts must partition validated tracks")
        return self


class CandidateFormationArtifact(FrozenCandidateEvidenceModel):
    schema_version: Literal["1.0"] = CANDIDATE_FORMATION_SCHEMA_VERSION
    artifact_kind: Literal["candidate_formation"] = "candidate_formation"
    request_id: str
    accepted_objective_artifact_id: str
    objective_id: str
    objective_statement: str
    journey_id: str
    snapshot_id: str
    profile_id: str
    taste_evidence_artifact_id: str
    familiarity_evidence_artifact_id: str
    track_feature_evidence_artifact_id: str
    objective_context_evidence_artifact_id: str
    policy_id: str
    policy_version: str
    preference_rule_name: str
    preference_rule_version: str
    ordering_rule: Literal["track_id_utf8_bytes"] = "track_id_utf8_bytes"
    reason_ordering_rule: Literal["cf_0_reason_precedence"] = "cf_0_reason_precedence"
    input_track_ids: tuple[str, ...]
    formed: tuple[FormedCandidateEntry, ...]
    withheld: tuple[WithheldCandidateEntry, ...]
    summary: CandidateFormationSummary
    hard_eligibility_evaluated: Literal[True] = True
    scoring_performed: Literal[False] = False
    ranking_performed: Literal[False] = False
    selection_performed: Literal[False] = False
    playlist_construction_performed: Literal[False] = False
    recommendation_claims: Literal[False] = False
    playlist_membership_claims: Literal[False] = False

    @field_validator(
        "request_id",
        "accepted_objective_artifact_id",
        "objective_id",
        "objective_statement",
        "journey_id",
        "snapshot_id",
        "profile_id",
        "taste_evidence_artifact_id",
        "familiarity_evidence_artifact_id",
        "track_feature_evidence_artifact_id",
        "objective_context_evidence_artifact_id",
        "policy_id",
        "policy_version",
        "preference_rule_name",
        "preference_rule_version",
    )
    @classmethod
    def require_exact_identities(cls, value: str) -> str:
        return _exact(value)

    @model_validator(mode="after")
    def require_complete_deterministic_partition(self) -> CandidateFormationArtifact:
        expected_ids = tuple(sorted(self.input_track_ids, key=lambda item: item.encode("utf-8")))
        if self.input_track_ids != expected_ids or len(expected_ids) != len(set(expected_ids)):
            raise ValueError("input track IDs must be unique UTF-8 order")
        formed_ids = tuple(item.candidate.track_id for item in self.formed)
        withheld_ids = tuple(item.validated_track.track_id for item in self.withheld)
        if formed_ids != tuple(sorted(formed_ids, key=lambda item: item.encode("utf-8"))):
            raise ValueError("formed candidates must use track-ID order")
        if withheld_ids != tuple(sorted(withheld_ids, key=lambda item: item.encode("utf-8"))):
            raise ValueError("withheld candidates must use track-ID order")
        if set(formed_ids) & set(withheld_ids):
            raise ValueError("formed and withheld partitions must be disjoint")
        if tuple(sorted(formed_ids + withheld_ids, key=lambda item: item.encode("utf-8"))) != self.input_track_ids:
            raise ValueError("every validated track must appear exactly once")
        if tuple(item.ordinal for item in self.formed) != tuple(range(1, len(self.formed) + 1)):
            raise ValueError("formed ordinals must be contiguous and one-based")
        expected_sources = {
            CandidateFieldName.TRACK_ID: (
                "track_evidence_validation",
                self.snapshot_id,
            ),
            CandidateFieldName.TITLE: (
                "track_evidence_validation",
                self.snapshot_id,
            ),
            CandidateFieldName.ARTIST_NAME: (
                "track_evidence_validation",
                self.snapshot_id,
            ),
            CandidateFieldName.DURATION_SECONDS: (
                "track_evidence_validation",
                self.snapshot_id,
            ),
            CandidateFieldName.PREFERENCE: (
                "local_taste_evidence",
                self.taste_evidence_artifact_id,
            ),
            CandidateFieldName.FAMILIARITY: (
                "familiarity_evidence",
                self.familiarity_evidence_artifact_id,
            ),
            CandidateFieldName.ENERGY: (
                "track_feature_evidence",
                self.track_feature_evidence_artifact_id,
            ),
            CandidateFieldName.INSTRUMENTALNESS: (
                "track_feature_evidence",
                self.track_feature_evidence_artifact_id,
            ),
            CandidateFieldName.LYRICAL_DISTRACTION: (
                "track_feature_evidence",
                self.track_feature_evidence_artifact_id,
            ),
            CandidateFieldName.GROOVE: (
                "track_feature_evidence",
                self.track_feature_evidence_artifact_id,
            ),
            CandidateFieldName.CONTEXT_FIT: (
                "objective_context_evidence",
                self.objective_context_evidence_artifact_id,
            ),
        }
        for entry in self.formed:
            for evidence in entry.field_evidence:
                if (
                    evidence.source_artifact_kind,
                    evidence.source_artifact_id,
                ) != expected_sources[evidence.field]:
                    raise ValueError("formed field evidence must use its owned source")
                if evidence.field is CandidateFieldName.PREFERENCE and (
                    evidence.rule_name != self.preference_rule_name
                    or evidence.rule_version != self.preference_rule_version
                ):
                    raise ValueError(
                        "preference evidence must use the recorded versioned rule"
                    )
        expected_summary = CandidateFormationSummary(
            validated_track_count=len(self.input_track_ids),
            formed_count=len(self.formed),
            withheld_count=len(self.withheld),
        )
        if self.summary != expected_summary:
            raise ValueError("formation summary must match the partitions")
        return self


def _mapping_rating(value: object) -> str:
    if isinstance(value, dict):
        rating = value.get("rating")
    else:
        rating = getattr(value, "rating", None)
    return rating.value if isinstance(rating, Rating) else str(rating or "")


def _exact(value: str) -> str:
    if not value or value != value.strip():
        raise ValueError("formation identity text must be nonblank and exact")
    return value


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"unsupported JSON constant: {value}")

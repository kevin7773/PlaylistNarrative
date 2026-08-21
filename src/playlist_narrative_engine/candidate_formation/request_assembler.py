from __future__ import annotations

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.candidate_formation.declarations import (
    HardConstraintDeclarationArtifact,
)
from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CandidateFormationPolicy,
    CandidateFormationRequest,
)
from playlist_narrative_engine.candidate_formation.schemas import (
    FamiliarityEvidenceArtifact,
    FrozenCandidateEvidenceModel,
    LocalTasteEvidenceArtifact,
    ObjectiveContextEvidenceArtifact,
    TrackFeatureEvidenceArtifact,
)
from playlist_narrative_engine.evidence_acquisition import (
    SourceNeutralAcquisitionResult,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.track_evidence import TrackEvidenceValidationArtifact


class FormationRequestAssemblyInput(FrozenCandidateEvidenceModel):
    request_id: str = Field(min_length=1, max_length=200)
    accepted_objective: AcceptedObjectiveArtifact
    journey_plan: JourneyPlanArtifact
    acquisition: SourceNeutralAcquisitionResult
    track_validation: TrackEvidenceValidationArtifact
    taste_evidence: LocalTasteEvidenceArtifact
    familiarity_evidence: FamiliarityEvidenceArtifact
    track_feature_evidence: TrackFeatureEvidenceArtifact
    objective_context_evidence: ObjectiveContextEvidenceArtifact
    policy: CandidateFormationPolicy
    hard_constraint_declaration: HardConstraintDeclarationArtifact | None = None
    authorized_declaration_id: str | None = None
    authorized_declaration_version: str | None = None

    @field_validator("request_id")
    @classmethod
    def require_exact_request_id(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("assembly request identity must be exact")
        return value

    @model_validator(mode="after")
    def require_explicit_declaration_authority(self) -> FormationRequestAssemblyInput:
        declaration = self.hard_constraint_declaration
        authority = (self.authorized_declaration_id, self.authorized_declaration_version)
        if declaration is None:
            if any(value is not None for value in authority):
                raise ValueError("declaration authority requires a declaration artifact")
            return self
        if authority != (declaration.artifact_id, declaration.declaration_version):
            raise ValueError("authorized declaration identity/version must match exactly")
        return self


class FormationRequestAssembler:
    """Join governed artifacts without retrieval, inference, or execution."""

    def assemble(self, value: FormationRequestAssemblyInput) -> CandidateFormationRequest:
        self._validate_acquisition_correspondence(value)
        declaration = value.hard_constraint_declaration
        return CandidateFormationRequest(
            request_id=value.request_id,
            accepted_objective=value.accepted_objective,
            journey_plan=value.journey_plan,
            track_validation=value.track_validation,
            taste_evidence=value.taste_evidence,
            familiarity_evidence=value.familiarity_evidence,
            track_feature_evidence=value.track_feature_evidence,
            objective_context_evidence=value.objective_context_evidence,
            identity_metadata=value.acquisition.identity_metadata,
            hard_constraints=declaration.constraints if declaration else (),
            hard_constraint_declaration_id=declaration.artifact_id if declaration else None,
            hard_constraint_declaration_version=(
                declaration.declaration_version if declaration else None
            ),
            hard_constraint_declaration_source_type=(
                declaration.source_type if declaration else None
            ),
            hard_constraint_declaration_source_reference=(
                declaration.source_reference if declaration else None
            ),
            policy=value.policy,
        )

    @staticmethod
    def _validate_acquisition_correspondence(value: FormationRequestAssemblyInput) -> None:
        acquisition = value.acquisition
        validation = value.track_validation
        if acquisition.evidence_snapshot.snapshot_id != validation.snapshot_id:
            raise ValueError("validated track evidence must match acquired snapshot identity")
        source_records = {
            item.record_id: item.payload_json
            for item in acquisition.evidence_snapshot.records
        }
        validated_records = {
            item.record_id: item.source_payload_json
            for item in validation.validated_records
        }
        rejected_records = {
            item.record_id: item.source_payload_json
            for item in validation.rejected_records
        }
        if source_records != validated_records | rejected_records:
            raise ValueError("track validation must partition the exact acquired snapshot")
        if any(
            item.provenance.source_type != acquisition.source_type
            or item.provenance.source_reference != acquisition.source_reference
            for item in validation.validated_records
        ):
            raise ValueError("validated track provenance must match source-receipt lineage")
        validated_track_ids = {item.track_id for item in validation.validated_records}
        if any(
            item.track_id not in validated_track_ids
            for item in acquisition.identity_metadata.records
        ):
            raise ValueError("acquired metadata contains an unvalidated track identity")

from __future__ import annotations

import secrets

from playlist_narrative_engine.evidence_acquisition import serialize_acquisition_result
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
    PennyLocalITunesXMLAcquisitionVerifierV11,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact
from playlist_narrative_engine.local_authorization import LocalPrincipalAuthorityVerifier
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.track_evidence import (
    TrackEvidenceValidationArtifact,
    serialize_track_evidence_validation,
)

from .producer import (
    ActiveFocusCandidateReadinessProducer,
    CandidateReadinessInvalidInput,
    _FIELDS,
    _project,
    _sha,
)
from .schemas import (
    ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ActiveFocusCandidateReadinessDeclaration,
    CandidateReadinessOccurrenceRepositoryV11,
    TrackReadinessObservation,
    _bind_occurrence_recorder_v11,
)
from .vocabulary import (
    AUTHORITY_DEFINITION_V12_JSON,
    AUTHORITY_DEFINITION_V12_SHA256,
    VOCABULARY_JSON,
    VOCABULARY_SHA256,
    verify_frozen_definitions_v12,
)


class ActiveFocusCandidateReadinessProducerV11(
    ActiveFocusCandidateReadinessProducer
):
    """Candidate-readiness producer 1.1 for governed acquisition 1.1 only."""

    producer_authority_id = "pne.producer.active-focus-candidate-readiness"
    producer_authority_version = "1.1"

    def __init__(
        self,
        *,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifierV11,
        artist_repository: ArtistRepository,
        occurrence_repository: CandidateReadinessOccurrenceRepositoryV11,
    ) -> None:
        if type(acquisition_verifier) is not PennyLocalITunesXMLAcquisitionVerifierV11:
            raise TypeError("the concrete acquisition 1.1 verifier is required")
        if type(occurrence_repository) is not CandidateReadinessOccurrenceRepositoryV11:
            raise TypeError("the concrete readiness 1.1 occurrence repository is required")
        self._principal_verifier = principal_verifier
        self._acquisition_verifier = acquisition_verifier
        self._artist_repository = artist_repository
        self._occurrences = occurrence_repository
        self._declaration_receipts: dict[
            int, tuple[ActiveFocusCandidateReadinessDeclaration, str]
        ] = {}
        self.__record_occurrence = _bind_occurrence_recorder_v11(
            self._occurrences,
            self,
        )

    def capture(
        self,
        *,
        acquisition_authority: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
        track_validation: TrackEvidenceValidationArtifact,
        accepted_objective: AcceptedObjectiveArtifact,
        journey_plan: JourneyPlanArtifact,
        declarations: tuple[ActiveFocusCandidateReadinessDeclaration, ...],
    ) -> ActiveFocusCandidateReadinessAuthorityArtifactV11:
        if (
            not verify_frozen_definitions_v12()
            or _sha(VOCABULARY_JSON.encode("utf-8")) != VOCABULARY_SHA256
            or _sha(AUTHORITY_DEFINITION_V12_JSON.encode("utf-8"))
            != AUTHORITY_DEFINITION_V12_SHA256
            or not isinstance(
                acquisition_authority,
                PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
            )
            or not self._acquisition_verifier.verify(acquisition_authority)
        ):
            raise CandidateReadinessInvalidInput(
                "acquisition 1.1 authority does not verify"
            )
        principal = (
            acquisition_authority.file_selection_evidence.intake_request.principal_authority
        )
        try:
            prefix = self._principal_verifier.verified_lineage_prefix_sha256(
                principal, require_current_tip=True
            )
        except ValueError as exc:
            raise CandidateReadinessInvalidInput(
                "capture requires the current principal tip"
            ) from exc
        self._validate_chain(
            acquisition_authority,
            track_validation,
            accepted_objective,
            journey_plan,
        )
        parsed = tuple(self._recover_declaration(item) for item in declarations)
        ids = tuple(item.track_id for item in parsed)
        if len(ids) != len(set(ids)):
            raise CandidateReadinessInvalidInput(
                "readiness declarations must have unique track identities"
            )
        tracks = {item.track_id: item for item in track_validation.validated_records}
        if any(track_id not in tracks for track_id in ids):
            raise CandidateReadinessInvalidInput(
                "readiness declaration track is not validated"
            )
        artifact_id = "active-focus-readiness-v11:" + secrets.token_hex(16)
        observations = tuple(
            TrackReadinessObservation(
                track_id=item.track_id,
                title=tracks[item.track_id].title,
                artist_name=tracks[item.track_id].artist_name,
                duration_seconds=tracks[item.track_id].duration_seconds,
                **{name: getattr(item, name) for name in _FIELDS},
            )
            for item in parsed
            if any(getattr(item, name) is not None for name in _FIELDS)
        )
        ratings = self._capture_exact_ratings(track_validation)
        projected = _project(
            artifact_id=artifact_id,
            observations=observations,
            ratings=ratings,
            profile_id=principal.installation_id,
            snapshot_id=track_validation.snapshot_id,
            accepted_objective=accepted_objective,
            journey_plan=journey_plan,
        )
        source = acquisition_authority.source_neutral_acquisition_result
        artifact = ActiveFocusCandidateReadinessAuthorityArtifactV11(
            artifact_id=artifact_id,
            principal_authority=principal,
            principal_authority_artifact_id=principal.artifact_id,
            principal_authority_sha256=principal.canonical_sha256,
            principal_lineage_prefix_sha256=prefix,
            installation_id=principal.installation_id,
            acquisition_authority=acquisition_authority,
            acquisition_authority_artifact_id=acquisition_authority.artifact_id,
            acquisition_authority_sha256=acquisition_authority.canonical_sha256,
            acquisition_id=source.acquisition_id,
            acquisition_sha256=_sha(serialize_acquisition_result(source)),
            snapshot_id=source.evidence_snapshot.snapshot_id,
            snapshot_sha256=source.evidence_snapshot_sha256,
            track_validation=track_validation,
            track_validation_sha256=_sha(
                serialize_track_evidence_validation(track_validation)
            ),
            vocabulary_json=VOCABULARY_JSON,
            vocabulary_sha256=VOCABULARY_SHA256,
            authority_definition_json=AUTHORITY_DEFINITION_V12_JSON,
            authority_definition_sha256=AUTHORITY_DEFINITION_V12_SHA256,
            accepted_objective=accepted_objective,
            accepted_objective_artifact_id=accepted_objective.artifact_id,
            accepted_objective_sha256=accepted_objective.canonical_sha256,
            objective_id=accepted_objective.objective.objective_id,
            objective_statement=accepted_objective.objective.statement,
            journey_plan=journey_plan,
            journey_id=journey_plan.journey_id,
            journey_schema_version=journey_plan.schema_version,
            journey_sha256=journey_plan.canonical_sha256,
            observations=observations,
            artist_ratings=ratings,
            familiarity_evidence=projected[0],
            track_feature_evidence=projected[1],
            objective_context_evidence=projected[2],
            local_taste_evidence=projected[3],
        )

        def accept() -> ActiveFocusCandidateReadinessAuthorityArtifactV11:
            accepted_prefix = self._principal_verifier.verified_lineage_prefix_sha256(
                principal,
                require_current_tip=True,
            )
            if accepted_prefix != prefix:
                raise CandidateReadinessInvalidInput(
                    "principal lineage changed during readiness capture"
                )
            self.__record_occurrence(artifact)
            return artifact

        try:
            return self._principal_verifier.guarded_current_tip(principal, accept)
        except ValueError as exc:
            raise CandidateReadinessInvalidInput(
                "capture acceptance requires the current principal tip"
            ) from exc

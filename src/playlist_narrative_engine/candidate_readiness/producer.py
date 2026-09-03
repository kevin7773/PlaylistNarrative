from __future__ import annotations

import hashlib
import json
import secrets

from playlist_narrative_engine.candidate_formation import (
    CandidateFormationPolicy,
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
from playlist_narrative_engine.evidence_acquisition import serialize_acquisition_result
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifact,
    PennyLocalITunesXMLAcquisitionVerifier,
)
from playlist_narrative_engine.journey import JourneyPlanArtifact, journey_plan_matches_accepted_objective
from playlist_narrative_engine.journey.schemas import JourneyContext
from playlist_narrative_engine.local_authorization import LocalPrincipalAuthorityVerifier
from playlist_narrative_engine.objective_safety import AcceptedObjectiveArtifact
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.taste.repository import ArtistRepository
from playlist_narrative_engine.track_evidence import TrackEvidenceValidationArtifact, serialize_track_evidence_validation

from .schemas import (
    ActiveFocusCandidateReadinessAuthorityArtifact,
    ActiveFocusCandidateReadinessDeclaration,
    ArtistRatingObservation,
    CandidateReadinessOccurrenceRepository,
    TrackReadinessObservation,
    _bind_occurrence_recorder,
    canonical_bytes,
    replay_validated_track_payload,
)
from .vocabulary import (
    AUTHORITY_DEFINITION_ID,
    AUTHORITY_DEFINITION_JSON,
    AUTHORITY_DEFINITION_SHA256,
    AUTHORITY_DEFINITION_VERSION,
    PREFERENCE_POLICY_JSON,
    PREFERENCE_POLICY_SHA256,
    VOCABULARY_ID,
    VOCABULARY_JSON,
    VOCABULARY_SHA256,
    VOCABULARY_VERSION,
    ReadinessField,
    ReadinessLevel,
    project_level,
    verify_frozen_definitions,
)


class CandidateReadinessInvalidInput(ValueError):
    pass


def active_focus_candidate_formation_policy() -> CandidateFormationPolicy:
    if (
        not verify_frozen_definitions()
        or _sha(PREFERENCE_POLICY_JSON.encode("utf-8")) != PREFERENCE_POLICY_SHA256
    ):
        raise RuntimeError("candidate-readiness frozen definitions are invalid")
    return CandidateFormationPolicy.model_validate_json(PREFERENCE_POLICY_JSON)


class ActiveFocusCandidateReadinessProducer:
    def __init__(
        self,
        *,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifier,
        artist_repository: ArtistRepository,
        occurrence_repository: CandidateReadinessOccurrenceRepository,
    ) -> None:
        if type(occurrence_repository) is not CandidateReadinessOccurrenceRepository:
            raise TypeError("the concrete readiness occurrence repository is required")
        self._principal_verifier = principal_verifier
        self._acquisition_verifier = acquisition_verifier
        self._artist_repository = artist_repository
        self._occurrences = occurrence_repository
        self._declaration_receipts: dict[
            int, tuple[ActiveFocusCandidateReadinessDeclaration, str]
        ] = {}
        self.__record_occurrence = _bind_occurrence_recorder(
            self._occurrences,
            self,
        )

    def __copy__(self):
        raise TypeError("readiness producer authority cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("readiness producer authority cannot be copied")

    def capture_declaration(
        self,
        serialized_declaration: str,
    ) -> ActiveFocusCandidateReadinessDeclaration:
        """Capture one exact category-only declaration for this producer."""

        if type(serialized_declaration) is not str:
            raise CandidateReadinessInvalidInput("declaration must be exact serialized JSON")

        def reject_constant(value: str) -> None:
            raise ValueError(f"unsupported JSON constant: {value}")

        def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
            result: dict[str, object] = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate declaration key")
                result[key] = value
            return result

        try:
            payload = json.loads(
                serialized_declaration,
                object_pairs_hook=unique_object,
                parse_constant=reject_constant,
            )
            if type(payload) is not dict:
                raise ValueError("declaration must be an object")
            allowed = {"schema_version", "track_id", *_FIELDS}
            if set(payload) - allowed:
                raise ValueError("declaration contains an unsupported field")
            if "schema_version" not in payload or "track_id" not in payload:
                raise ValueError("declaration identity fields must be explicit")
            if any(payload.get(field) is None for field in _FIELDS if field in payload):
                raise ValueError("explicit null readiness measurements are forbidden")
            declaration = ActiveFocusCandidateReadinessDeclaration.model_validate(payload)
            exact = canonical_bytes(declaration, exclude=set(_FIELDS) - set(payload))
            if serialized_declaration.encode("utf-8") != exact:
                raise ValueError("declaration JSON is not exact canonical schema-order JSON")
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise CandidateReadinessInvalidInput("readiness declaration is not exact") from exc
        self._declaration_receipts[id(declaration)] = (declaration, serialized_declaration)
        return declaration

    def capture(
        self,
        *,
        acquisition_authority: PennyLocalITunesXMLAcquisitionAuthorityArtifact,
        track_validation: TrackEvidenceValidationArtifact,
        accepted_objective: AcceptedObjectiveArtifact,
        journey_plan: JourneyPlanArtifact,
        declarations: tuple[ActiveFocusCandidateReadinessDeclaration, ...],
    ) -> ActiveFocusCandidateReadinessAuthorityArtifact:
        if (
            not verify_frozen_definitions()
            or _sha(VOCABULARY_JSON.encode("utf-8")) != VOCABULARY_SHA256
            or _sha(AUTHORITY_DEFINITION_JSON.encode("utf-8")) != AUTHORITY_DEFINITION_SHA256
            or not self._acquisition_verifier.verify(acquisition_authority)
        ):
            raise CandidateReadinessInvalidInput("acquisition authority does not verify")
        principal = acquisition_authority.file_selection_evidence.intake_request.principal_authority
        try:
            prefix = self._principal_verifier.verified_lineage_prefix_sha256(
                principal, require_current_tip=True
            )
        except ValueError as exc:
            raise CandidateReadinessInvalidInput("capture requires the current principal tip") from exc
        self._validate_chain(acquisition_authority, track_validation, accepted_objective, journey_plan)
        parsed = tuple(self._recover_declaration(item) for item in declarations)
        ids = tuple(item.track_id for item in parsed)
        if len(ids) != len(set(ids)):
            raise CandidateReadinessInvalidInput("readiness declarations must have unique track identities")
        tracks = {item.track_id: item for item in track_validation.validated_records}
        if any(track_id not in tracks for track_id in ids):
            raise CandidateReadinessInvalidInput("readiness declaration track is not validated")
        artifact_id = "active-focus-readiness:" + secrets.token_hex(16)
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
        artifact = ActiveFocusCandidateReadinessAuthorityArtifact(
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
            track_validation_sha256=_sha(serialize_track_evidence_validation(track_validation)),
            vocabulary_json=VOCABULARY_JSON,
            vocabulary_sha256=VOCABULARY_SHA256,
            authority_definition_json=AUTHORITY_DEFINITION_JSON,
            authority_definition_sha256=AUTHORITY_DEFINITION_SHA256,
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
        def accept() -> ActiveFocusCandidateReadinessAuthorityArtifact:
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

    def _recover_declaration(
        self,
        value: ActiveFocusCandidateReadinessDeclaration,
    ) -> ActiveFocusCandidateReadinessDeclaration:
        receipt = self._declaration_receipts.get(id(value))
        if receipt is None or receipt[0] is not value:
            raise CandidateReadinessInvalidInput(
                "declaration was not captured by this readiness producer"
            )
        expected = canonical_bytes(
            value,
            exclude=set(_FIELDS) - value.model_fields_set,
        ).decode("utf-8")
        if receipt[1] != expected or set(value.__dict__) != set(value.__class__.model_fields):
            raise CandidateReadinessInvalidInput("captured declaration is no longer exact")
        return value

    def _capture_exact_ratings(self, validation: TrackEvidenceValidationArtifact) -> tuple[ArtistRatingObservation, ...]:
        rows = self._artist_repository.list()
        by_name = {row.name: row for row in rows}
        if len(by_name) != len(rows):
            raise CandidateReadinessInvalidInput("persisted artist identities are ambiguous")
        return tuple(
            ArtistRatingObservation(
                artist_name=name,
                rating=Rating(by_name[name].rating) if name in by_name else None,
                persisted_row_id=by_name[name].id if name in by_name else None,
            )
            for name in sorted({item.artist_name for item in validation.validated_records}, key=lambda value: value.encode("utf-8"))
        )

    @staticmethod
    def _validate_chain(acquisition, validation, accepted, journey) -> None:
        for value, expected_type, label in (
            (validation, TrackEvidenceValidationArtifact, "track validation"),
            (accepted, AcceptedObjectiveArtifact, "accepted objective"),
            (journey, JourneyPlanArtifact, "journey plan"),
        ):
            try:
                reparsed = expected_type.model_validate(value.model_dump(mode="json"))
            except (AttributeError, TypeError, ValueError) as exc:
                raise CandidateReadinessInvalidInput(f"{label} is not exact") from exc
            if reparsed != value or set(value.__dict__) != set(value.__class__.model_fields):
                raise CandidateReadinessInvalidInput(f"{label} is not exact")
        source = acquisition.source_neutral_acquisition_result
        if accepted.schema_version != "2.0" or journey.schema_version != "2.0":
            raise CandidateReadinessInvalidInput("readiness authority requires objective and journey schema 2.0")
        if journey.plan.context is not JourneyContext.ACTIVE_FOCUS or not journey_plan_matches_accepted_objective(journey, accepted):
            raise CandidateReadinessInvalidInput("exact Active Focus journey authority is required")
        if validation.snapshot_id != source.evidence_snapshot.snapshot_id:
            raise CandidateReadinessInvalidInput("validation snapshot does not match acquisition")
        if (validation.objective_id, validation.objective_statement) != (accepted.objective.objective_id, accepted.objective.statement):
            raise CandidateReadinessInvalidInput("validation objective does not correspond")
        source_records = {item.record_id: item.payload_json for item in source.evidence_snapshot.records}
        partition = {item.record_id: item.source_payload_json for item in validation.validated_records} | {item.record_id: item.source_payload_json for item in validation.rejected_records}
        if source_records != partition:
            raise CandidateReadinessInvalidInput("validation must partition the exact acquisition snapshot")
        try:
            for record in validation.validated_records:
                replay_validated_track_payload(record)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise CandidateReadinessInvalidInput(
                "validated track structure does not replay from serialized evidence"
            ) from exc


_FIELDS = (
    "familiarity", "energy", "instrumentalness", "lyrical_distraction", "groove", "active_focus_context_fit"
)


def _unit(artifact_id: str, track_id: str, field: str, level: ReadinessLevel | None) -> UnitIntervalEvidence:
    if level is None:
        return UnitIntervalEvidence(state=EvidenceState.UNAVAILABLE, value=None, observations=())
    payload = json.dumps(
        {"track_id": track_id, "field": field, "category": level.value, "vocabulary_id": VOCABULARY_ID, "vocabulary_version": VOCABULARY_VERSION, "vocabulary_sha256": VOCABULARY_SHA256},
        ensure_ascii=False, separators=(",", ":"),
    )
    evidence_id = "readiness-evidence:" + _sha(f"{artifact_id}\0{track_id}\0{field}".encode())
    observation = EvidenceObservation(evidence_id=evidence_id, source_type="manual_active_focus_candidate_readiness", source_reference=artifact_id, payload_json=payload)
    return UnitIntervalEvidence(state=EvidenceState.MEASURED, value=project_level(ReadinessField(field), level), observations=(observation,))


def _project(*, artifact_id, observations, ratings, profile_id, snapshot_id, accepted_objective, journey_plan):
    familiar = FamiliarityEvidenceArtifact(
        artifact_id=artifact_id + ":familiarity", profile_id=profile_id, track_snapshot_id=snapshot_id,
        records=tuple(FamiliarityEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, familiarity=_unit(artifact_id, item.track_id, "familiarity", item.familiarity)) for item in observations),
    )
    features = TrackFeatureEvidenceArtifact(
        artifact_id=artifact_id + ":features", track_snapshot_id=snapshot_id,
        records=tuple(TrackFeatureEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, energy=_unit(artifact_id,item.track_id,"energy",item.energy), instrumentalness=_unit(artifact_id,item.track_id,"instrumentalness",item.instrumentalness), lyrical_distraction=_unit(artifact_id,item.track_id,"lyrical_distraction",item.lyrical_distraction), groove=_unit(artifact_id,item.track_id,"groove",item.groove)) for item in observations),
    )
    binding_json = json.dumps({"accepted_objective_artifact_id": accepted_objective.artifact_id, "accepted_objective_sha256": accepted_objective.canonical_sha256, "objective_id": accepted_objective.objective.objective_id, "objective_statement": accepted_objective.objective.statement, "journey_id": journey_plan.journey_id, "journey_schema_version": journey_plan.schema_version, "journey_sha256": journey_plan.canonical_sha256, "journey_context": "Active Focus", "occurrence_id": artifact_id}, ensure_ascii=False, separators=(",", ":"))
    contexts = ObjectiveContextEvidenceArtifact(
        artifact_id=artifact_id + ":context", objective_id=accepted_objective.objective.objective_id,
        objective_statement=accepted_objective.objective.statement, journey_id=journey_plan.journey_id,
        context_id="Active Focus", track_snapshot_id=snapshot_id,
        records=tuple(ObjectiveContextEvidenceRecord(track_id=item.track_id, artist_name=item.artist_name, context_fit=_unit(artifact_id,item.track_id,"active_focus_context_fit",item.active_focus_context_fit), inputs=(ContextInputEvidence(input_name="active_focus_authority_binding", state=EvidenceState.MEASURED, resolved_payload_json=binding_json, observations=(EvidenceObservation(evidence_id="context-binding:" + _sha(f"{artifact_id}\0{item.track_id}".encode()), source_type="manual_active_focus_candidate_readiness", source_reference=artifact_id, payload_json=binding_json),)),)) for item in observations),
    )
    taste_records = []
    for item in ratings:
        if item.rating is None:
            taste_records.append(TasteEvidenceRecord(artist_name=item.artist_name, state=EvidenceState.UNAVAILABLE, rating=None, observations=()))
        else:
            payload = json.dumps({"artist_name":item.artist_name,"rating":item.rating.value,"persisted_row_id":item.persisted_row_id}, ensure_ascii=False, separators=(",", ":"))
            taste_records.append(TasteEvidenceRecord(artist_name=item.artist_name, state=EvidenceState.MEASURED, rating=item.rating, observations=(EvidenceObservation(evidence_id="taste-evidence:" + _sha(f"{artifact_id}\0{item.artist_name}".encode()), source_type="maestro_persisted_artist_rating", source_reference=f"maestro-artist-row:{item.persisted_row_id}", payload_json=payload),)))
    taste = LocalTasteEvidenceArtifact(artifact_id=artifact_id + ":taste", profile_id=profile_id, records=tuple(taste_records))
    return familiar, features, contexts, taste


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

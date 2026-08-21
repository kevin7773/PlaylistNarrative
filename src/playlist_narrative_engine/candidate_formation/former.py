from __future__ import annotations

import json
from typing import Callable

from playlist_narrative_engine.candidate_formation.formation_schemas import (
    CANDIDATE_FIELD_ORDER,
    WITHHOLDING_REASON_EXPLANATIONS,
    WITHHOLDING_REASON_PRECEDENCE,
    CandidateFieldEvidence,
    CandidateFieldName,
    CandidateConstraintEligibility,
    CandidateConstraintField,
    CandidateEligibilityReason,
    CandidateEligibilityState,
    CandidateFormationArtifact,
    CandidateFormationRequest,
    CandidateFormationSummary,
    FormationBasis,
    FormedCandidateEntry,
    CandidateIdentitySnapshot,
    CandidateMechanismEvent,
    CandidateMechanismTrace,
    WithheldCandidateEntry,
    WithholdingReason,
    WithholdingReasonCode,
)
from playlist_narrative_engine.candidate_formation.schemas import (
    EvidenceObservation,
    EvidenceState,
    UnitIntervalEvidence,
)
from playlist_narrative_engine.sequencing.schemas import TrackCandidate
from playlist_narrative_engine.taste.ratings import Rating
from playlist_narrative_engine.track_evidence import ValidatedTrackEvidence


_STATE_REASON = {
    EvidenceState.UNAVAILABLE: WithholdingReasonCode.EVIDENCE_UNAVAILABLE,
    EvidenceState.CONFLICTING: WithholdingReasonCode.EVIDENCE_CONFLICTING,
    EvidenceState.UNSUPPORTED: WithholdingReasonCode.EVIDENCE_UNSUPPORTED,
    EvidenceState.EXPLICITLY_INAPPLICABLE: (
        WithholdingReasonCode.EVIDENCE_INAPPLICABLE
    ),
}
_REASON_INDEX = {
    code: index for index, code in enumerate(WITHHOLDING_REASON_PRECEDENCE)
}


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _evidence_ids(observations: tuple[EvidenceObservation, ...]) -> tuple[str, ...]:
    return tuple(item.evidence_id for item in observations)


class CandidateFormer:
    """Form reproducible candidates from immutable corresponding evidence."""

    def form(self, request: CandidateFormationRequest) -> CandidateFormationArtifact:
        taste_by_artist = {
            record.artist_name: record for record in request.taste_evidence.records
        }
        familiarity_by_track = {
            record.track_id: record for record in request.familiarity_evidence.records
        }
        features_by_track = {
            record.track_id: record for record in request.track_feature_evidence.records
        }
        context_by_track = {
            record.track_id: record
            for record in request.objective_context_evidence.records
        }
        metadata_by_track = {
            record.track_id: record
            for record in (request.identity_metadata.records if request.identity_metadata else ())
        }
        preference_values = {
            entry.rating: entry.value
            for entry in request.policy.preference_rule.mappings
        }

        validated = tuple(
            sorted(
                request.track_validation.validated_records,
                key=lambda record: record.track_id.encode("utf-8"),
            )
        )
        formed: list[FormedCandidateEntry] = []
        withheld: list[WithheldCandidateEntry] = []

        for track in validated:
            reasons: list[WithholdingReason] = []
            fields: dict[CandidateFieldName, CandidateFieldEvidence] = {}
            self._catalog_fields(request, track, fields)
            identity, eligibility = self._identity_and_eligibility(
                request, track, metadata_by_track.get(track.track_id)
            )
            for result in eligibility:
                if result.state is CandidateEligibilityState.INELIGIBLE:
                    reasons.append(_reason(
                        WithholdingReasonCode.HARD_CONSTRAINT_INELIGIBLE,
                        f"$.hard_constraints.{result.constraint_key}",
                        request.identity_metadata.artifact_id if request.identity_metadata else request.track_validation.snapshot_id,
                    ))
                elif result.state is CandidateEligibilityState.UNKNOWN:
                    reasons.append(_reason(
                        WithholdingReasonCode.HARD_CONSTRAINT_UNKNOWN,
                        f"$.hard_constraints.{result.constraint_key}",
                        request.identity_metadata.artifact_id if request.identity_metadata else request.track_validation.snapshot_id,
                    ))

            preference = self._preference(
                request,
                track,
                taste_by_artist.get(track.artist_name),
                preference_values,
                reasons,
                fields,
            )
            familiarity_record = familiarity_by_track.get(track.track_id)
            familiarity = self._track_value(
                track,
                familiarity_record,
                CandidateFieldName.FAMILIARITY,
                request.familiarity_evidence.artifact_id,
                "familiarity_evidence",
                lambda record: record.familiarity,
                reasons,
                fields,
            )
            feature_record = features_by_track.get(track.track_id)
            energy = self._track_value(
                track,
                feature_record,
                CandidateFieldName.ENERGY,
                request.track_feature_evidence.artifact_id,
                "track_feature_evidence",
                lambda record: record.energy,
                reasons,
                fields,
            )
            instrumentalness = self._track_value(
                track,
                feature_record,
                CandidateFieldName.INSTRUMENTALNESS,
                request.track_feature_evidence.artifact_id,
                "track_feature_evidence",
                lambda record: record.instrumentalness,
                reasons,
                fields,
            )
            lyrical_distraction = self._track_value(
                track,
                feature_record,
                CandidateFieldName.LYRICAL_DISTRACTION,
                request.track_feature_evidence.artifact_id,
                "track_feature_evidence",
                lambda record: record.lyrical_distraction,
                reasons,
                fields,
            )
            groove = self._track_value(
                track,
                feature_record,
                CandidateFieldName.GROOVE,
                request.track_feature_evidence.artifact_id,
                "track_feature_evidence",
                lambda record: record.groove,
                reasons,
                fields,
            )
            context_record = context_by_track.get(track.track_id)
            context_fit = self._track_value(
                track,
                context_record,
                CandidateFieldName.CONTEXT_FIT,
                request.objective_context_evidence.artifact_id,
                "objective_context_evidence",
                lambda record: record.context_fit,
                reasons,
                fields,
            )

            ordered_reasons = self._ordered_reasons(reasons)
            if ordered_reasons:
                withheld.append(
                    WithheldCandidateEntry(
                        validated_track=track,
                        reasons=ordered_reasons,
                        identity=identity,
                        constraint_eligibility=eligibility,
                        mechanism_trace=self._mechanism_trace(track.track_id, identity, eligibility, retained=False),
                    )
                )
                continue
            values = (
                preference,
                familiarity,
                energy,
                instrumentalness,
                lyrical_distraction,
                groove,
                context_fit,
            )
            if any(value is None for value in values):
                raise AssertionError("reason-free formation must have every numeric value")
            candidate = TrackCandidate(
                track_id=track.track_id,
                title=track.title,
                artist_name=track.artist_name,
                duration_seconds=track.duration_seconds,
                energy=energy,
                familiarity=familiarity,
                preference=preference,
                context_fit=context_fit,
                instrumentalness=instrumentalness,
                lyrical_distraction=lyrical_distraction,
                groove=groove,
            )
            formed.append(
                FormedCandidateEntry(
                    ordinal=len(formed) + 1,
                    candidate=candidate,
                    field_evidence=tuple(fields[field] for field in CANDIDATE_FIELD_ORDER),
                    identity=identity,
                    constraint_eligibility=eligibility,
                    mechanism_trace=self._mechanism_trace(track.track_id, identity, eligibility, retained=True),
                )
            )

        objective = request.accepted_objective.objective
        input_track_ids = tuple(track.track_id for track in validated)
        return CandidateFormationArtifact(
            request_id=request.request_id,
            accepted_objective_artifact_id=request.accepted_objective.artifact_id,
            objective_id=objective.objective_id,
            objective_statement=objective.statement,
            journey_id=request.journey_plan.journey_id,
            snapshot_id=request.track_validation.snapshot_id,
            profile_id=request.taste_evidence.profile_id,
            taste_evidence_artifact_id=request.taste_evidence.artifact_id,
            familiarity_evidence_artifact_id=(
                request.familiarity_evidence.artifact_id
            ),
            track_feature_evidence_artifact_id=(
                request.track_feature_evidence.artifact_id
            ),
            objective_context_evidence_artifact_id=(
                request.objective_context_evidence.artifact_id
            ),
            policy_id=request.policy.policy_id,
            policy_version=request.policy.policy_version,
            preference_rule_name=request.policy.preference_rule.rule_name,
            preference_rule_version=request.policy.preference_rule.rule_version,
            input_track_ids=input_track_ids,
            formed=tuple(formed),
            withheld=tuple(withheld),
            summary=CandidateFormationSummary(
                validated_track_count=len(validated),
                formed_count=len(formed),
                withheld_count=len(withheld),
            ),
        )

    @staticmethod
    def _identity_and_eligibility(
        request: CandidateFormationRequest,
        track: ValidatedTrackEvidence,
        metadata: object | None,
    ) -> tuple[CandidateIdentitySnapshot, tuple[CandidateConstraintEligibility, ...]]:
        catalog = metadata.source_catalog_identity if metadata is not None else None
        version = metadata.release_version_identity if metadata is not None else None
        explicit = metadata.displayed_explicit if metadata is not None else None
        identity = CandidateIdentitySnapshot(
            exact_displayed_title=track.title,
            exact_displayed_artist=track.artist_name,
            source_catalog_identity=(catalog.value if catalog and catalog.state is EvidenceState.MEASURED else None),
            release_version_identity=(version.value if version and version.state is EvidenceState.MEASURED else None),
            displayed_explicit=(explicit.value if explicit and explicit.state is EvidenceState.MEASURED else None),
            metadata_artifact_id=(request.identity_metadata.artifact_id if request.identity_metadata else None),
            source_catalog_state=(catalog.state if catalog else None),
            release_version_state=(version.state if version else None),
            displayed_explicit_state=(explicit.state if explicit else None),
            source_catalog_evidence_ids=CandidateFormer._metadata_value(catalog)[1],
            release_version_evidence_ids=CandidateFormer._metadata_value(version)[1],
            displayed_explicit_evidence_ids=CandidateFormer._metadata_value(explicit)[1],
        )
        actual = {
            CandidateConstraintField.DISPLAYED_TITLE: (track.title, (track.record_id,)),
            CandidateConstraintField.DISPLAYED_ARTIST: (track.artist_name, (track.record_id,)),
            CandidateConstraintField.SOURCE_CATALOG_IDENTITY: CandidateFormer._metadata_value(catalog),
            CandidateConstraintField.RELEASE_VERSION_IDENTITY: CandidateFormer._metadata_value(version),
            CandidateConstraintField.DISPLAYED_EXPLICIT: CandidateFormer._metadata_value(explicit),
        }
        results: list[CandidateConstraintEligibility] = []
        for constraint in request.hard_constraints:
            observed, evidence_ids = actual[constraint.field]
            expected = json.loads(constraint.expected_json)
            if observed is None:
                state = CandidateEligibilityState.UNKNOWN
                reason = CandidateEligibilityReason.REQUIRED_METADATA_UNKNOWN
                observed_json = None
            elif observed == expected and type(observed) is type(expected):
                state = CandidateEligibilityState.ELIGIBLE
                reason = (
                    CandidateEligibilityReason.PROPERTY_MATCH
                    if constraint.field is CandidateConstraintField.DISPLAYED_EXPLICIT
                    else CandidateEligibilityReason.EXACT_MATCH
                )
                observed_json = _json(observed)
            else:
                state = CandidateEligibilityState.INELIGIBLE
                reason = (
                    CandidateEligibilityReason.PROPERTY_MISMATCH
                    if constraint.field is CandidateConstraintField.DISPLAYED_EXPLICIT
                    else CandidateEligibilityReason.EXACT_MISMATCH
                )
                observed_json = _json(observed)
            results.append(CandidateConstraintEligibility(
                constraint_key=constraint.constraint_key,
                field=constraint.field,
                state=state,
                reason=reason,
                expected_json=constraint.expected_json,
                observed_json=observed_json,
                source_evidence_ids=evidence_ids,
            ))
        return identity, tuple(results)

    @staticmethod
    def _metadata_value(evidence: object | None) -> tuple[object | None, tuple[str, ...]]:
        if evidence is None:
            return None, ()
        evidence_ids = _evidence_ids(evidence.observations)
        if evidence.state is not EvidenceState.MEASURED:
            return None, evidence_ids
        return evidence.value, evidence_ids

    @staticmethod
    def _mechanism_trace(
        track_id: str,
        identity: CandidateIdentitySnapshot,
        eligibility: tuple[CandidateConstraintEligibility, ...],
        *,
        retained: bool,
    ) -> CandidateMechanismTrace:
        return CandidateMechanismTrace(
            track_id=track_id,
            identity=identity,
            eligibility=eligibility,
            events=(
                CandidateMechanismEvent.DISCOVERED,
                CandidateMechanismEvent.IDENTITY_CAPTURED,
                CandidateMechanismEvent.METADATA_CAPTURED,
                CandidateMechanismEvent.ELIGIBILITY_EVALUATED,
                CandidateMechanismEvent.RETAINED if retained else CandidateMechanismEvent.WITHHELD,
            ),
        )

    @staticmethod
    def _catalog_fields(
        request: CandidateFormationRequest,
        track: ValidatedTrackEvidence,
        fields: dict[CandidateFieldName, CandidateFieldEvidence],
    ) -> None:
        source_id = request.track_validation.snapshot_id
        values = (
            (CandidateFieldName.TRACK_ID, track.track_id),
            (CandidateFieldName.TITLE, track.title),
            (CandidateFieldName.ARTIST_NAME, track.artist_name),
            (CandidateFieldName.DURATION_SECONDS, track.duration_seconds),
        )
        for field, value in values:
            fields[field] = CandidateFieldEvidence(
                field=field,
                source_artifact_kind="track_evidence_validation",
                source_artifact_id=source_id,
                source_record_identity=track.record_id,
                source_evidence_ids=(track.record_id,),
                basis=FormationBasis.DIRECT_EVIDENCE,
                serialized_inputs_json=_json(value),
                result_json=_json(value),
                explanation="Copied exact validated track evidence.",
            )

    @staticmethod
    def _preference(
        request: CandidateFormationRequest,
        track: ValidatedTrackEvidence,
        record: object | None,
        preference_values: dict[Rating, float],
        reasons: list[WithholdingReason],
        fields: dict[CandidateFieldName, CandidateFieldEvidence],
    ) -> float | None:
        artifact_id = request.taste_evidence.artifact_id
        field_path = "$.preference"
        if record is None:
            reasons.append(_reason(WithholdingReasonCode.EVIDENCE_UNAVAILABLE, field_path, artifact_id))
            return None
        state = record.state
        if state is not EvidenceState.MEASURED:
            reasons.append(_reason(_STATE_REASON[state], field_path, artifact_id))
            return None
        rating = record.rating
        if rating in request.policy.hard_excluded_ratings:
            reasons.append(_reason(WithholdingReasonCode.HARD_ELIGIBILITY_EXCLUDED, "$.eligibility", artifact_id))
            reasons.append(_reason(WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED, field_path, artifact_id))
            return None
        if rating not in preference_values:
            reasons.append(_reason(WithholdingReasonCode.DERIVATION_RULE_UNAPPROVED, field_path, artifact_id))
            return None
        value = preference_values[rating]
        rule = request.policy.preference_rule
        fields[CandidateFieldName.PREFERENCE] = CandidateFieldEvidence(
            field=CandidateFieldName.PREFERENCE,
            source_artifact_kind="local_taste_evidence",
            source_artifact_id=artifact_id,
            source_record_identity=track.artist_name,
            source_evidence_ids=_evidence_ids(record.observations),
            basis=FormationBasis.VERSIONED_DERIVATION,
            rule_name=rule.rule_name,
            rule_version=rule.rule_version,
            serialized_inputs_json=_json({"rating": rating.value}),
            result_json=_json(value),
            explanation="Applied the explicitly supplied categorical preference mapping.",
        )
        return value

    @staticmethod
    def _track_value(
        track: ValidatedTrackEvidence,
        record: object | None,
        field: CandidateFieldName,
        artifact_id: str,
        artifact_kind: str,
        getter: Callable[[object], UnitIntervalEvidence],
        reasons: list[WithholdingReason],
        fields: dict[CandidateFieldName, CandidateFieldEvidence],
    ) -> float | None:
        field_path = f"$.{field.value}"
        if record is None:
            reasons.append(_reason(WithholdingReasonCode.EVIDENCE_UNAVAILABLE, field_path, artifact_id))
            return None
        if record.artist_name != track.artist_name:
            reasons.append(_reason(WithholdingReasonCode.ARTIST_IDENTITY_CONFLICTING, "$.artist_name", artifact_id))
            reasons.append(_reason(WithholdingReasonCode.EVIDENCE_UNAVAILABLE, field_path, artifact_id))
            return None
        evidence = getter(record)
        if evidence.state is not EvidenceState.MEASURED:
            reasons.append(_reason(_STATE_REASON[evidence.state], field_path, artifact_id))
            return None
        if evidence.value is None:
            raise AssertionError("measured evidence must contain a value")
        fields[field] = CandidateFieldEvidence(
            field=field,
            source_artifact_kind=artifact_kind,
            source_artifact_id=artifact_id,
            source_record_identity=track.track_id,
            source_evidence_ids=_evidence_ids(evidence.observations),
            basis=FormationBasis.DIRECT_EVIDENCE,
            serialized_inputs_json=_json(evidence.value),
            result_json=_json(evidence.value),
            explanation="Copied exact provenance-backed measured evidence.",
        )
        return evidence.value

    @staticmethod
    def _ordered_reasons(
        reasons: list[WithholdingReason],
    ) -> tuple[WithholdingReason, ...]:
        unique = {
            (reason.code, reason.field_path, reason.source_artifact_id): reason
            for reason in reasons
        }
        return tuple(
            sorted(
                unique.values(),
                key=lambda reason: (
                    _REASON_INDEX[reason.code],
                    reason.field_path.encode("utf-8"),
                    reason.source_artifact_id.encode("utf-8"),
                ),
            )
        )


def _reason(
    code: WithholdingReasonCode,
    field_path: str,
    artifact_id: str,
) -> WithholdingReason:
    return WithholdingReason(
        code=code,
        field_path=field_path,
        source_artifact_id=artifact_id,
        explanation=WITHHOLDING_REASON_EXPLANATIONS[code],
    )


def serialize_candidate_formation(artifact: CandidateFormationArtifact) -> bytes:
    """Return canonical schema-order JSON encoded as UTF-8."""

    return _json(artifact.model_dump(mode="json")).encode("utf-8")

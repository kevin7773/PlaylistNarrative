from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum


VOCABULARY_ID = "pne.active-focus.candidate-readiness"
VOCABULARY_VERSION = "1.0"
VOCABULARY_SHA256 = "63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d"
AUTHORITY_DEFINITION_ID = "pne.candidate-readiness-authority.active-focus"
AUTHORITY_DEFINITION_VERSION = "1.1"
AUTHORITY_DEFINITION_SHA256 = "a90b57643243966aa5ccbeb0ebb045794967b0ae322c74ad57a543ba32e5e6f1"
AUTHORITY_DEFINITION_V12_VERSION = "1.2"
AUTHORITY_DEFINITION_V12_SHA256 = "6d18b572ebbcd984b431440ce039bcf58a1736ccfd39cf66f7a7c3b9b897f5ba"
SUPERSEDED_AUTHORITY_DEFINITION_SHA256 = "02b62bc079c9ef912ba6e94ce343e2346e0486a9ba8f34e15a86c52f6c581e7d"
PREFERENCE_POLICY_SHA256 = "0628fc50befbcbf97db026c06f8ca5d71a5d7cc45e450b26fd1402591fee66d0"

VOCABULARY_JSON = r'''{"schema_version":"1.0","artifact_kind":"active_focus_candidate_readiness_vocabulary","vocabulary_id":"pne.active-focus.candidate-readiness","vocabulary_version":"1.0","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0","levels":[{"token":"LEVEL_0","projection":"0.00"},{"token":"LEVEL_1","projection":"0.25"},{"token":"LEVEL_2","projection":"0.50"},{"token":"LEVEL_3","projection":"0.75"},{"token":"LEVEL_4","projection":"1.00"}],"dimensions":[{"field":"familiarity","levels":[{"token":"LEVEL_0","definition":"No reliable recognition of the track."},{"token":"LEVEL_1","definition":"Slight recognition, but the track's structure cannot be anticipated reliably."},{"token":"LEVEL_2","definition":"The track is recognizable and partially predictable."},{"token":"LEVEL_3","definition":"The track is well known; its major structure and changes are predictable."},{"token":"LEVEL_4","definition":"The track is deeply familiar; its structure, entries, major changes, and ending are readily anticipated."}]},{"field":"energy","levels":[{"token":"LEVEL_0","definition":"Near-still experience with minimal activation or forward drive."},{"token":"LEVEL_1","definition":"Restrained or gentle activation and drive."},{"token":"LEVEL_2","definition":"Steady, moderate activation and forward drive."},{"token":"LEVEL_3","definition":"Strong, active, sustained forward drive."},{"token":"LEVEL_4","definition":"Maximal or near-maximal sustained activation, intensity, and forward drive."}]},{"field":"instrumentalness","levels":[{"token":"LEVEL_0","definition":"Intelligible sung or spoken words dominate the track."},{"token":"LEVEL_1","definition":"The track is mostly verbal, with limited instrumental-only space."},{"token":"LEVEL_2","definition":"Verbal and instrumental content are both substantial."},{"token":"LEVEL_3","definition":"The track is mostly instrumental; intelligible words are occasional or secondary."},{"token":"LEVEL_4","definition":"The track contains no intelligible sung or spoken verbal content."}]},{"field":"lyrical_distraction","levels":[{"token":"LEVEL_0","definition":"Verbal content does not pull attention away from focused activity."},{"token":"LEVEL_1","definition":"Verbal content causes occasional mild attention pull."},{"token":"LEVEL_2","definition":"Verbal content creates repeated, noticeable but manageable attention pull."},{"token":"LEVEL_3","definition":"Verbal content frequently competes with focused attention."},{"token":"LEVEL_4","definition":"Verbal content dominates attention or reliably prevents focused activity."}]},{"field":"groove","levels":[{"token":"LEVEL_0","definition":"No stable rhythmic pulse or propulsion is perceived."},{"token":"LEVEL_1","definition":"Rhythmic propulsion is weak, diffuse, or irregular."},{"token":"LEVEL_2","definition":"A clear, steady degree of rhythmic movement is perceived."},{"token":"LEVEL_3","definition":"Rhythmic propulsion is strong and consistent."},{"token":"LEVEL_4","definition":"Rhythmic propulsion is dominant and highly driving."}]},{"field":"active_focus_context_fit","levels":[{"token":"LEVEL_0","definition":"The track strongly conflicts with the exact objective and journey for reasons not represented by the separately measured dimensions."},{"token":"LEVEL_1","definition":"The track is more likely to interfere with than support the exact objective and journey for such residual reasons."},{"token":"LEVEL_2","definition":"The track provides mixed, conditional, or neutral residual support for the exact objective and journey."},{"token":"LEVEL_3","definition":"The track reliably supports the exact objective and journey for residual reasons."},{"token":"LEVEL_4","definition":"The track provides exceptionally strong residual support for the exact objective and journey."}]}],"categorical_observation_authority":true,"direct_numeric_capture_authorized":false}'''

AUTHORITY_DEFINITION_JSON = r'''{"schema_version":"1.1","definition_kind":"active_focus_candidate_readiness_authority","authority_definition_id":"pne.candidate-readiness-authority.active-focus","authority_definition_version":"1.1","predecessor_authority_definition_id":"pne.candidate-readiness-authority.active-focus","predecessor_authority_definition_version":"1.0","predecessor_authority_definition_sha256":"02b62bc079c9ef912ba6e94ce343e2346e0486a9ba8f34e15a86c52f6c581e7d","vocabulary_id":"pne.active-focus.candidate-readiness","vocabulary_version":"1.0","vocabulary_sha256":"63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d","principal_scope":"PENNY_LOCAL_INSTALLATION_CURRENT_TIP_AT_CAPTURE","accepted_objective_schema":"AcceptedObjectiveArtifact/2.0","source_acquisition_authority_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.0","acquisition_schema":"SourceNeutralAcquisitionResult/1.0_UNCHANGED","track_validation_schema":"TrackEvidenceValidationArtifact/1.0_UNCHANGED","journey_plan_schema":"JourneyPlanArtifact/2.0","journey_context":"Active Focus","declaration_schema":"ActiveFocusCandidateReadinessDeclaration/1.0","wrapper_schema":"ActiveFocusCandidateReadinessAuthorityArtifact/1.0","producer":"pne.producer.active-focus-candidate-readiness/1.0","verifier":"pne.verifier.active-focus-candidate-readiness/1.0","occurrence_digest":"NUL_DOMAIN_SEPARATED_SHA256/1.0","cf1_outputs":["FamiliarityEvidenceArtifact/1.0","TrackFeatureEvidenceArtifact/1.0","ObjectiveContextEvidenceArtifact/1.0"],"categorical_observation_authority":true,"direct_numeric_capture_authorized":false,"context_fit_reusable":false,"missing_evidence_default_authorized":false,"persistent_restart_safe_authority_established":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''

AUTHORITY_DEFINITION_V12_JSON = r'''{"schema_version":"1.2","definition_kind":"active_focus_candidate_readiness_authority","authority_definition_id":"pne.candidate-readiness-authority.active-focus","authority_definition_version":"1.2","predecessor_authority_definition_id":"pne.candidate-readiness-authority.active-focus","predecessor_authority_definition_version":"1.1","predecessor_authority_definition_sha256":"a90b57643243966aa5ccbeb0ebb045794967b0ae322c74ad57a543ba32e5e6f1","vocabulary_id":"pne.active-focus.candidate-readiness","vocabulary_version":"1.0","vocabulary_sha256":"63bdcf94908d16f8538e1c59e5aed84229627cd68ae6bcb89ebce09b9685be4d","principal_scope":"PENNY_LOCAL_INSTALLATION_CURRENT_TIP_AT_CAPTURE","accepted_objective_schema":"AcceptedObjectiveArtifact/2.0","source_acquisition_authority_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.1","acquisition_schema":"SourceNeutralAcquisitionResult/1.0_UNCHANGED","track_validation_schema":"TrackEvidenceValidationArtifact/1.0_UNCHANGED","journey_plan_schema":"JourneyPlanArtifact/2.0","journey_context":"Active Focus","declaration_schema":"ActiveFocusCandidateReadinessDeclaration/1.0","wrapper_schema":"ActiveFocusCandidateReadinessAuthorityArtifact/1.1","producer":"pne.producer.active-focus-candidate-readiness/1.1","verifier":"pne.verifier.active-focus-candidate-readiness/1.1","occurrence_digest":"NUL_DOMAIN_SEPARATED_SHA256/1.0","cf1_outputs":["FamiliarityEvidenceArtifact/1.0","TrackFeatureEvidenceArtifact/1.0","ObjectiveContextEvidenceArtifact/1.0"],"categorical_observation_authority":true,"direct_numeric_capture_authorized":false,"context_fit_reusable":false,"missing_evidence_default_authorized":false,"persistent_restart_safe_authority_established":false,"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''

PREFERENCE_POLICY_JSON = r'''{"schema_version":"1.0","policy_id":"pne.candidate-formation.active-focus-readiness","policy_version":"1.0","preference_rule":{"rule_name":"pne.preference-map.local-artist-rating","rule_version":"1.0","mappings":[{"rating":"Like","value":0.75},{"rating":"Love","value":1.0},{"rating":"Meh","value":0.5}]},"hard_excluded_ratings":["No Thanks","Pencil","Forbidden"],"unsupported_ratings":["Unknown"]}'''


class ReadinessLevel(StrEnum):
    LEVEL_0 = "LEVEL_0"
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
    LEVEL_4 = "LEVEL_4"


class ReadinessField(StrEnum):
    FAMILIARITY = "familiarity"
    ENERGY = "energy"
    INSTRUMENTALNESS = "instrumentalness"
    LYRICAL_DISTRACTION = "lyrical_distraction"
    GROOVE = "groove"
    ACTIVE_FOCUS_CONTEXT_FIT = "active_focus_context_fit"


def project_level(field: ReadinessField, level: ReadinessLevel) -> float:
    if not isinstance(field, ReadinessField) or not isinstance(level, ReadinessLevel):
        raise TypeError("projection requires exact governed field and level tokens")
    projections, fields = _verified_vocabulary_interpretation()
    if field.value not in fields:
        raise RuntimeError("governed readiness field is absent from the vocabulary")
    try:
        return float(projections[level.value])
    except KeyError as exc:
        raise RuntimeError("governed readiness level is absent from the vocabulary") from exc


def _verified_vocabulary_interpretation() -> tuple[dict[str, Decimal], frozenset[str]]:
    raw = VOCABULARY_JSON.encode("utf-8")
    if len(raw) != 3882 or hashlib.sha256(raw).hexdigest() != VOCABULARY_SHA256:
        raise RuntimeError("candidate-readiness vocabulary authority is invalid")
    value = json.loads(VOCABULARY_JSON, parse_float=Decimal)
    level_rows = value.get("levels")
    dimension_rows = value.get("dimensions")
    if not isinstance(level_rows, list) or not isinstance(dimension_rows, list):
        raise RuntimeError("candidate-readiness vocabulary structure is invalid")
    expected_tokens = tuple(item.value for item in ReadinessLevel)
    expected_lexemes = ("0.00", "0.25", "0.50", "0.75", "1.00")
    rows = tuple(
        (row.get("token"), row.get("projection"))
        for row in level_rows
        if isinstance(row, dict)
    )
    if rows != tuple(zip(expected_tokens, expected_lexemes, strict=True)):
        raise RuntimeError("candidate-readiness projection authority is invalid")
    fields = tuple(
        row.get("field") for row in dimension_rows if isinstance(row, dict)
    )
    if fields != tuple(item.value for item in ReadinessField):
        raise RuntimeError("candidate-readiness dimension authority is invalid")
    return ({token: Decimal(lexeme) for token, lexeme in rows}, frozenset(fields))


def verify_frozen_definitions() -> bool:
    try:
        _verified_vocabulary_interpretation()
        return all(
            (
                hashlib.sha256(AUTHORITY_DEFINITION_JSON.encode("utf-8")).hexdigest() == AUTHORITY_DEFINITION_SHA256,
                hashlib.sha256(PREFERENCE_POLICY_JSON.encode("utf-8")).hexdigest() == PREFERENCE_POLICY_SHA256,
                json.loads(AUTHORITY_DEFINITION_JSON)["authority_definition_version"] == "1.1",
            )
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False


def verify_frozen_definitions_v12() -> bool:
    try:
        return all(
            (
                verify_frozen_definitions(),
                len(AUTHORITY_DEFINITION_V12_JSON.encode("utf-8")) == 1778,
                hashlib.sha256(
                    AUTHORITY_DEFINITION_V12_JSON.encode("utf-8")
                ).hexdigest()
                == AUTHORITY_DEFINITION_V12_SHA256,
                json.loads(AUTHORITY_DEFINITION_V12_JSON)[
                    "authority_definition_version"
                ]
                == AUTHORITY_DEFINITION_V12_VERSION,
                json.loads(AUTHORITY_DEFINITION_V12_JSON)[
                    "predecessor_authority_definition_sha256"
                ]
                == AUTHORITY_DEFINITION_SHA256,
            )
        )
    except (KeyError, TypeError, ValueError, RuntimeError):
        return False

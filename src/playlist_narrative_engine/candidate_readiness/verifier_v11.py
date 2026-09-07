from __future__ import annotations

import hashlib
import json
import threading
import weakref

from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionVerifierV11,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityVerifier,
)

from .schemas import (
    ActiveFocusCandidateReadinessAuthorityArtifactV11,
    CandidateReadinessOccurrenceRepositoryV11,
    occurrence_sha256,
)
from .verifier import ActiveFocusCandidateReadinessVerifier, _reconstruct
from .vocabulary import (
    AUTHORITY_DEFINITION_V12_JSON,
    AUTHORITY_DEFINITION_V12_SHA256,
    AUTHORITY_DEFINITION_V12_VERSION,
    VOCABULARY_JSON,
    VOCABULARY_SHA256,
    verify_frozen_definitions_v12,
)


class VerifiedActiveFocusCandidateReadinessV11:
    """Opaque successor proof issued only by the readiness 1.1 verifier."""

    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise TypeError("verified readiness 1.1 results are verifier-issued only")


_VERIFIED_RESULTS_V11: weakref.WeakKeyDictionary[
    VerifiedActiveFocusCandidateReadinessV11,
    tuple[
        ActiveFocusCandidateReadinessVerifierV11,
        ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ],
] = weakref.WeakKeyDictionary()
_VERIFIED_RESULTS_V11_LOCK = threading.RLock()


class ActiveFocusCandidateReadinessVerifierV11(
    ActiveFocusCandidateReadinessVerifier
):
    """Candidate-readiness verifier 1.1 for the coordinated successor chain."""

    verifier_authority_id = "pne.verifier.active-focus-candidate-readiness"
    verifier_authority_version = "1.1"

    def __init__(
        self,
        *,
        principal_verifier: LocalPrincipalAuthorityVerifier,
        acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifierV11,
        occurrence_repository: CandidateReadinessOccurrenceRepositoryV11,
    ) -> None:
        if type(acquisition_verifier) is not PennyLocalITunesXMLAcquisitionVerifierV11:
            raise TypeError("the concrete acquisition 1.1 verifier is required")
        if type(occurrence_repository) is not CandidateReadinessOccurrenceRepositoryV11:
            raise TypeError("the concrete readiness 1.1 occurrence repository is required")
        self._principal_verifier = principal_verifier
        self._acquisition_verifier = acquisition_verifier
        self._occurrences = occurrence_repository

    def verify(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ) -> bool:
        return self._verify_occurrence(artifact)

    def verify_authority(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ) -> VerifiedActiveFocusCandidateReadinessV11:
        if not self._verify_occurrence(artifact):
            raise ValueError("candidate-readiness 1.1 occurrence authority does not verify")
        result = object.__new__(VerifiedActiveFocusCandidateReadinessV11)
        with _VERIFIED_RESULTS_V11_LOCK:
            _VERIFIED_RESULTS_V11[result] = (self, artifact)
        return result

    def recover_verified(
        self,
        result: VerifiedActiveFocusCandidateReadinessV11,
    ) -> ActiveFocusCandidateReadinessAuthorityArtifactV11:
        if type(result) is not VerifiedActiveFocusCandidateReadinessV11:
            raise ValueError("genuine verified-readiness 1.1 authority is required")
        with _VERIFIED_RESULTS_V11_LOCK:
            authority = _VERIFIED_RESULTS_V11.get(result)
        if authority is None or authority[0] is not self:
            raise ValueError("genuine verified-readiness 1.1 authority is required")
        if not self._verify_occurrence(authority[1]):
            raise ValueError("verified-readiness 1.1 authority is no longer applicable")
        return authority[1]

    def _verify_occurrence(
        self,
        artifact: ActiveFocusCandidateReadinessAuthorityArtifactV11,
    ) -> bool:
        if type(artifact) is not ActiveFocusCandidateReadinessAuthorityArtifactV11:
            return False
        try:
            value = artifact
            reparsed = ActiveFocusCandidateReadinessAuthorityArtifactV11.model_validate(
                artifact.model_dump(mode="json")
            )
            if reparsed != artifact or set(artifact.__dict__) != set(
                artifact.__class__.model_fields
            ):
                return False
            if not verify_frozen_definitions_v12():
                return False
            if (
                hashlib.sha256(VOCABULARY_JSON.encode("utf-8")).hexdigest()
                != VOCABULARY_SHA256
                or hashlib.sha256(
                    AUTHORITY_DEFINITION_V12_JSON.encode("utf-8")
                ).hexdigest()
                != AUTHORITY_DEFINITION_V12_SHA256
            ):
                return False
            if self._occurrences._recover_authoritative(value) is not value:
                return False
            if self._has_conflicting_occurrence(value):
                return False
            if (
                value.vocabulary_json != VOCABULARY_JSON
                or value.vocabulary_sha256 != VOCABULARY_SHA256
                or value.authority_definition_version
                != AUTHORITY_DEFINITION_V12_VERSION
                or value.authority_definition_json != AUTHORITY_DEFINITION_V12_JSON
                or value.authority_definition_sha256
                != AUTHORITY_DEFINITION_V12_SHA256
            ):
                return False
            principal = value.principal_authority
            if not self._principal_verifier.verify(principal):
                return False
            if (
                value.principal_lineage_prefix_sha256
                != self._principal_verifier.verified_lineage_prefix_sha256(principal)
            ):
                return False
            if not self._acquisition_verifier.verify(value.acquisition_authority):
                return False
            if not self._bindings_match(value):
                return False
            expected = _reconstruct(value)
            return (
                value.familiarity_evidence == expected[0]
                and value.track_feature_evidence == expected[1]
                and value.objective_context_evidence == expected[2]
                and value.local_taste_evidence == expected[3]
                and value.occurrence_sha256 == occurrence_sha256(value)
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False

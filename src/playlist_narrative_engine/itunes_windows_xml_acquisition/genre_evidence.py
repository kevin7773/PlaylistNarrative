from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    FrozenModel,
    canonical_json_bytes,
    derived_digest,
    require_exact,
    verify_or_set_digest,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    ACQUISITION_AUTHORITY_V11_SHA256,
    SOURCE_DEFINITION_V11_SHA256,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.profile import (
    VerifiedITunesWindowsXMLProfileV11,
    verify_frozen_itunes_windows_xml_profile_v11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.schemas import (
    PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.verifier import (
    PennyLocalITunesXMLAcquisitionVerifierV11,
)


GENRE_EVIDENCE_DEFINITION_ID = (
    "pne.source-evidence-definition.itunes-windows-xml-track-genre"
)
GENRE_EVIDENCE_DEFINITION_VERSION = "1.0"
GENRE_EVIDENCE_DEFINITION_JSON = r'''{"schema_version":"1.0","definition_kind":"itunes_windows_xml_track_genre_evidence","evidence_definition_id":"pne.source-evidence-definition.itunes-windows-xml-track-genre","evidence_definition_version":"1.0","supported_acquisition_authority":"pne.acquisition-authority.itunes-windows-xml-single-playlist/1.1","supported_acquisition_authority_sha256":"6a07222c5c65c68e72e29b3e306459f1c6b84f7557aa106ba4c6906171871170","acquisition_wrapper_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.1","source_definition":"pne.source-definition.itunes-windows-xml-single-playlist/1.1","source_definition_sha256":"1e14e22641d0d9dc65b0cfe06544e0afc70111a15bd69ee9dc634d7b2dbe1fa9","source_field":"Genre","observation_states":[{"state":"PRESENT","rule":"FIELD_PRESENT_WITH_EXACT_DECODED_NONBLANK_PLIST_STRING"},{"state":"ABSENT","rule":"FIELD_KEY_ABSENT_AND_SOURCE_GENRE_VALUE_FIELD_OMITTED"}],"coverage":"EXACTLY_ONE_OBSERVATION_PER_PARENT_ORDERED_TRACK_IN_PARENT_ORDER","correspondence":["PARENT_ACQUISITION_ARTIFACT_AND_DIGEST","ACQUISITION_SCHEMA_VERSION","SOURCE_RECEIPT_ID_AND_ARTIFACT_DIGEST","RECEIPT_ITEM_ID","SELECTED_BYTE_SHA256","SOURCE_DEFINITION_ID_VERSION_AND_DIGEST","GENRE_EVIDENCE_DEFINITION_ID_VERSION_AND_DIGEST","LIBRARY_PERSISTENT_ID","TRACK_PERSISTENT_ID","SOURCE_SCOPED_TRACK_ID","PARENT_ORDINAL","RECEIPT_LOCAL_TRACK_ID","LITERAL_SOURCE_FIELD"],"reconstruction":"EXACT_BOUND_SOURCE_RECEIPT_BYTES_USING_FROZEN_SOURCE_PROFILE_1.1","occurrence_scope":"EXACT_SOURCE_RECEIPT_ONLY_NO_CROSS_RECEIPT_MERGE","normalization_performed":false,"nonclaims":["APPLE_AUTHORSHIP","OBJECTIVE_GENRE_TRUTH","CURRENT_LIBRARY_STATE","RECORDING_IDENTITY_BEYOND_SOURCE_SCOPED_IDENTITY","RELEASE_VERSION_IDENTITY","SEMANTIC_EQUIVALENCE_OF_STRINGS","GENRE_FAMILY_MEMBERSHIP","REQUESTED_GENRE_ELIGIBILITY","ARTIST_GENRE","ALBUM_GENRE","CROSS_SOURCE_CORRESPONDENCE","MAESTRO_IDENTITY","CANDIDATE_FORMATION_ELIGIBILITY","PLAYLIST_FILTERING_SCORING_OR_RECOMMENDATION_AUTHORITY"],"producer":"pne.producer.itunes-windows-xml-track-genre-evidence/1.0","verifier":"pne.verifier.itunes-windows-xml-track-genre-evidence/1.0","artifact_schema":"ITunesWindowsXMLSourceGenreEvidenceArtifact/1.0","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''
GENRE_EVIDENCE_DEFINITION_SHA256 = (
    "094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a"
)


def verify_frozen_genre_evidence_definition() -> bool:
    try:
        parsed = json.loads(GENRE_EVIDENCE_DEFINITION_JSON)
    except json.JSONDecodeError:
        return False
    return (
        len(GENRE_EVIDENCE_DEFINITION_JSON.encode("utf-8")) == 2248
        and hashlib.sha256(GENRE_EVIDENCE_DEFINITION_JSON.encode("utf-8")).hexdigest()
        == GENRE_EVIDENCE_DEFINITION_SHA256
        and parsed["evidence_definition_id"] == GENRE_EVIDENCE_DEFINITION_ID
        and parsed["evidence_definition_version"]
        == GENRE_EVIDENCE_DEFINITION_VERSION
        and parsed["supported_acquisition_authority_sha256"]
        == ACQUISITION_AUTHORITY_V11_SHA256
        and parsed["source_definition_sha256"] == SOURCE_DEFINITION_V11_SHA256
    )


if not verify_frozen_genre_evidence_definition():
    raise RuntimeError("frozen iTunes genre-evidence definition does not reproduce")


class ITunesWindowsXMLGenreFieldState(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class ITunesWindowsXMLGenreEvidenceDefinitionBinding(FrozenModel):
    definition_id: Literal[
        "pne.source-evidence-definition.itunes-windows-xml-track-genre"
    ] = GENRE_EVIDENCE_DEFINITION_ID
    definition_version: Literal["1.0"] = GENRE_EVIDENCE_DEFINITION_VERSION
    canonical_json: Literal[GENRE_EVIDENCE_DEFINITION_JSON] = (
        GENRE_EVIDENCE_DEFINITION_JSON
    )
    canonical_sha256: Literal[
        "094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a"
    ] = GENRE_EVIDENCE_DEFINITION_SHA256


GENRE_EVIDENCE_DEFINITION = ITunesWindowsXMLGenreEvidenceDefinitionBinding()


class _ITunesWindowsXMLGenreObservationBase(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    parent_acquisition_artifact_id: str
    parent_acquisition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    acquisition_schema_version: Literal["1.1"] = "1.1"
    source_receipt_id: str
    source_receipt_artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    receipt_item_id: Literal["item-000001"] = "item-000001"
    selected_byte_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_definition_id: Literal[
        "pne.source-definition.itunes-windows-xml-single-playlist"
    ] = "pne.source-definition.itunes-windows-xml-single-playlist"
    source_definition_version: Literal["1.1"] = "1.1"
    source_definition_sha256: Literal[
        "1e14e22641d0d9dc65b0cfe06544e0afc70111a15bd69ee9dc634d7b2dbe1fa9"
    ] = SOURCE_DEFINITION_V11_SHA256
    genre_evidence_definition_id: Literal[
        "pne.source-evidence-definition.itunes-windows-xml-track-genre"
    ] = GENRE_EVIDENCE_DEFINITION_ID
    genre_evidence_definition_version: Literal["1.0"] = (
        GENRE_EVIDENCE_DEFINITION_VERSION
    )
    genre_evidence_definition_sha256: Literal[
        "094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a"
    ] = GENRE_EVIDENCE_DEFINITION_SHA256
    library_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    track_persistent_id: str = Field(pattern=r"^[0-9A-F]{16}$")
    track_id: str
    ordinal: int = Field(gt=0)
    receipt_local_track_id: int = Field(gt=0)
    source_field: Literal["Genre"] = "Genre"

    @field_validator(
        "parent_acquisition_artifact_id", "source_receipt_id", "track_id"
    )
    @classmethod
    def exact_identity(cls, value: str) -> str:
        return require_exact(value)


class ITunesWindowsXMLGenrePresentObservation(
    _ITunesWindowsXMLGenreObservationBase
):
    state: Literal[ITunesWindowsXMLGenreFieldState.PRESENT] = (
        ITunesWindowsXMLGenreFieldState.PRESENT
    )
    source_genre_value: str

    @field_validator("source_genre_value")
    @classmethod
    def exact_nonblank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("present Genre must be an exact nonblank string")
        value.encode("utf-8")
        return value


class ITunesWindowsXMLGenreAbsentObservation(_ITunesWindowsXMLGenreObservationBase):
    state: Literal[ITunesWindowsXMLGenreFieldState.ABSENT] = (
        ITunesWindowsXMLGenreFieldState.ABSENT
    )


ITunesWindowsXMLGenreObservation = Annotated[
    ITunesWindowsXMLGenrePresentObservation | ITunesWindowsXMLGenreAbsentObservation,
    Field(discriminator="state"),
]


class ITunesWindowsXMLSourceGenreEvidenceArtifact(FrozenModel):
    schema_version: Literal["1.0"] = "1.0"
    artifact_kind: Literal["itunes_windows_xml_source_genre_evidence"] = (
        "itunes_windows_xml_source_genre_evidence"
    )
    artifact_id: str
    genre_evidence_definition: ITunesWindowsXMLGenreEvidenceDefinitionBinding = (
        GENRE_EVIDENCE_DEFINITION
    )
    parent_acquisition: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11
    parent_acquisition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observation_count: int = Field(gt=0)
    observations: tuple[ITunesWindowsXMLGenreObservation, ...]
    normalization_performed: Literal[False] = False
    apple_authorship_established: Literal[False] = False
    objective_genre_truth_established: Literal[False] = False
    current_library_state_established: Literal[False] = False
    recording_identity_beyond_source_scoped_established: Literal[False] = False
    release_version_identity_established: Literal[False] = False
    semantic_equivalence_established: Literal[False] = False
    genre_family_membership_established: Literal[False] = False
    requested_genre_eligibility_established: Literal[False] = False
    artist_genre_established: Literal[False] = False
    album_genre_established: Literal[False] = False
    cross_source_correspondence_established: Literal[False] = False
    maestro_identity_established: Literal[False] = False
    candidate_formation_eligibility_established: Literal[False] = False
    playlist_authority_established: Literal[False] = False
    producer_authority_id: Literal[
        "pne.producer.itunes-windows-xml-track-genre-evidence"
    ] = "pne.producer.itunes-windows-xml-track-genre-evidence"
    producer_authority_version: Literal["1.0"] = "1.0"
    verifier_authority_id: Literal[
        "pne.verifier.itunes-windows-xml-track-genre-evidence"
    ] = "pne.verifier.itunes-windows-xml-track-genre-evidence"
    verifier_authority_version: Literal["1.0"] = "1.0"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("artifact_id")
    @classmethod
    def exact_artifact_id(cls, value: str) -> str:
        return require_exact(value)

    @model_validator(mode="after")
    def bind_complete_parent_order(self) -> ITunesWindowsXMLSourceGenreEvidenceArtifact:
        parent = self.parent_acquisition
        if self.genre_evidence_definition != GENRE_EVIDENCE_DEFINITION:
            raise ValueError("genre-evidence definition is not exact frozen authority")
        if self.parent_acquisition_sha256 != parent.canonical_sha256:
            raise ValueError("parent acquisition digest mismatch")
        if self.observation_count != len(self.observations):
            raise ValueError("genre observation count mismatch")
        if self.observation_count != len(parent.ordered_tracks):
            raise ValueError("genre observations must cover the complete parent universe")
        evidence = parent.file_selection_evidence
        seen_persistent_ids: set[str] = set()
        seen_receipt_local_ids: set[int] = set()
        for ordinal, (observation, parent_track) in enumerate(
            zip(self.observations, parent.ordered_tracks, strict=True),
            start=1,
        ):
            if observation.ordinal != ordinal or observation.track_id != parent_track.track_id:
                raise ValueError("genre observation order does not match parent")
            if (
                observation.parent_acquisition_artifact_id != parent.artifact_id
                or observation.parent_acquisition_sha256 != parent.canonical_sha256
            ):
                raise ValueError("genre observation parent binding mismatch")
            if (
                observation.source_receipt_id != evidence.source_receipt.receipt_id
                or observation.source_receipt_artifact_sha256
                != evidence.source_receipt_artifact_sha256
                or observation.receipt_item_id != evidence.source_receipt_item_id
                or observation.selected_byte_sha256 != evidence.byte_sha256
                or observation.library_persistent_id != parent.library_persistent_id
            ):
                raise ValueError("genre observation receipt binding mismatch")
            if (
                observation.track_persistent_id in seen_persistent_ids
                or observation.receipt_local_track_id in seen_receipt_local_ids
            ):
                raise ValueError("genre observation correspondence is duplicated")
            seen_persistent_ids.add(observation.track_persistent_id)
            seen_receipt_local_ids.add(observation.receipt_local_track_id)
        verify_or_set_digest(self)
        return self


class ITunesWindowsXMLGenreEvidenceInvalidInput(ValueError):
    pass


def _common_observation_fields(
    parent: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
    profile: VerifiedITunesWindowsXMLProfileV11,
    *,
    ordinal: int,
    receipt_local_track_id: int,
) -> dict[str, object]:
    evidence = parent.file_selection_evidence
    source_track = profile.tracks_by_correspondence_id[receipt_local_track_id]
    return {
        "parent_acquisition_artifact_id": parent.artifact_id,
        "parent_acquisition_sha256": parent.canonical_sha256,
        "source_receipt_id": evidence.source_receipt.receipt_id,
        "source_receipt_artifact_sha256": evidence.source_receipt_artifact_sha256,
        "selected_byte_sha256": evidence.byte_sha256,
        "library_persistent_id": profile.library_persistent_id,
        "track_persistent_id": source_track.persistent_id,
        "track_id": parent.ordered_tracks[ordinal - 1].track_id,
        "ordinal": ordinal,
        "receipt_local_track_id": receipt_local_track_id,
    }


def _produce_observations(
    parent: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
    profile: VerifiedITunesWindowsXMLProfileV11,
) -> tuple[ITunesWindowsXMLGenreObservation, ...]:
    result: list[ITunesWindowsXMLGenreObservation] = []
    for ordinal, local_id in enumerate(profile.playlist_track_ids, start=1):
        source_track = profile.tracks_by_correspondence_id[local_id]
        fields = _common_observation_fields(
            parent,
            profile,
            ordinal=ordinal,
            receipt_local_track_id=local_id,
        )
        if source_track.genre is None:
            result.append(ITunesWindowsXMLGenreAbsentObservation(**fields))
        else:
            result.append(
                ITunesWindowsXMLGenrePresentObservation(
                    **fields,
                    source_genre_value=source_track.genre,
                )
            )
    return tuple(result)


class ITunesWindowsXMLGenreEvidenceProducer:
    def __init__(
        self,
        acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifierV11,
    ) -> None:
        self._acquisition_verifier = acquisition_verifier

    def produce_authoritative(
        self,
        parent: PennyLocalITunesXMLAcquisitionAuthorityArtifactV11,
    ) -> ITunesWindowsXMLSourceGenreEvidenceArtifact:
        try:
            if not isinstance(
                self._acquisition_verifier,
                PennyLocalITunesXMLAcquisitionVerifierV11,
            ) or not self._acquisition_verifier.verify(parent):
                raise ValueError("parent acquisition authority does not verify")
            profile = verify_frozen_itunes_windows_xml_profile_v11(
                parent.file_selection_evidence
            )
            observations = _produce_observations(parent, profile)
            artifact_id = "pne.itunes-windows-xml-track-genre-evidence/sha256/" + (
                derived_digest(
                    "pne.itunes-windows-xml-track-genre-evidence/1.0",
                    parent.canonical_sha256,
                    GENRE_EVIDENCE_DEFINITION_SHA256,
                )
            )
            return ITunesWindowsXMLSourceGenreEvidenceArtifact(
                artifact_id=artifact_id,
                parent_acquisition=parent,
                parent_acquisition_sha256=parent.canonical_sha256,
                observation_count=len(observations),
                observations=observations,
            )
        except (TypeError, ValueError) as exc:
            raise ITunesWindowsXMLGenreEvidenceInvalidInput(
                "iTunes Windows XML genre-evidence production failed closed"
            ) from exc


class ITunesWindowsXMLGenreEvidenceVerifier:
    def __init__(
        self,
        acquisition_verifier: PennyLocalITunesXMLAcquisitionVerifierV11,
    ) -> None:
        self._acquisition_verifier = acquisition_verifier

    def verify(self, artifact: ITunesWindowsXMLSourceGenreEvidenceArtifact) -> bool:
        if (
            not isinstance(artifact, ITunesWindowsXMLSourceGenreEvidenceArtifact)
            or not isinstance(
                self._acquisition_verifier,
                PennyLocalITunesXMLAcquisitionVerifierV11,
            )
        ):
            return False
        try:
            validated = ITunesWindowsXMLSourceGenreEvidenceArtifact.model_validate(
                artifact.model_dump(mode="json")
            )
            if validated != artifact or not verify_frozen_genre_evidence_definition():
                return False
            parent = validated.parent_acquisition
            if not self._acquisition_verifier.verify(parent):
                return False
            profile = verify_frozen_itunes_windows_xml_profile_v11(
                parent.file_selection_evidence
            )
            expected: list[ITunesWindowsXMLGenreObservation] = []
            for ordinal, local_id in enumerate(profile.playlist_track_ids, start=1):
                source_track = profile.tracks_by_correspondence_id[local_id]
                evidence = parent.file_selection_evidence
                fields = {
                    "parent_acquisition_artifact_id": parent.artifact_id,
                    "parent_acquisition_sha256": parent.canonical_sha256,
                    "source_receipt_id": evidence.source_receipt.receipt_id,
                    "source_receipt_artifact_sha256": (
                        evidence.source_receipt_artifact_sha256
                    ),
                    "selected_byte_sha256": evidence.byte_sha256,
                    "library_persistent_id": profile.library_persistent_id,
                    "track_persistent_id": source_track.persistent_id,
                    "track_id": parent.ordered_tracks[ordinal - 1].track_id,
                    "ordinal": ordinal,
                    "receipt_local_track_id": local_id,
                }
                if source_track.genre is None:
                    expected.append(ITunesWindowsXMLGenreAbsentObservation(**fields))
                else:
                    expected.append(
                        ITunesWindowsXMLGenrePresentObservation(
                            **fields,
                            source_genre_value=source_track.genre,
                        )
                    )
            expected_id = "pne.itunes-windows-xml-track-genre-evidence/sha256/" + (
                derived_digest(
                    "pne.itunes-windows-xml-track-genre-evidence/1.0",
                    parent.canonical_sha256,
                    GENRE_EVIDENCE_DEFINITION_SHA256,
                )
            )
            expected_artifact = ITunesWindowsXMLSourceGenreEvidenceArtifact(
                artifact_id=expected_id,
                parent_acquisition=parent,
                parent_acquisition_sha256=parent.canonical_sha256,
                observation_count=len(expected),
                observations=tuple(expected),
            )
            return validated == expected_artifact
        except (TypeError, ValueError):
            return False


def serialize_genre_evidence(
    artifact: ITunesWindowsXMLSourceGenreEvidenceArtifact,
) -> bytes:
    return canonical_json_bytes(artifact)

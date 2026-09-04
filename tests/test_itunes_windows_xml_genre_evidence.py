from __future__ import annotations

import hashlib
import json
import socket
import warnings
from pathlib import Path

import pytest
from pydantic import ValidationError

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
from playlist_narrative_engine.evidence_acquisition import SourceNeutralAcquisitionResult
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    GENRE_EVIDENCE_DEFINITION_JSON,
    GENRE_EVIDENCE_DEFINITION_SHA256,
    ITunesWindowsXMLGenreAbsentObservation,
    ITunesWindowsXMLGenreEvidenceInvalidInput,
    ITunesWindowsXMLGenreEvidenceProducer,
    ITunesWindowsXMLGenreEvidenceVerifier,
    ITunesWindowsXMLGenreFieldState,
    ITunesWindowsXMLGenrePresentObservation,
    ITunesWindowsXMLSourceGenreEvidenceArtifact,
    PennyLocalITunesXMLAcquisitionProducer,
    PennyLocalITunesXMLAcquisitionProducerV11,
    PennyLocalITunesXMLAcquisitionVerifierV11,
    PennyLocalITunesXMLIntakeProducer,
    PennyLocalITunesXMLIntakeProducerV11,
    serialize_acquisition_authority_v11,
    serialize_genre_evidence,
    verify_frozen_genre_evidence_definition,
    verify_frozen_itunes_windows_xml_profile_v11,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)
HETEROGENEOUS_FIXTURE = Path(__file__).parent / "fixtures" / (
    "itunes_windows_xml/001-billboard-100-heterogeneous.xml"
)
DOCUMENT = Path(__file__).parents[1] / (
    "docs/penny_local_itunes_windows_xml_genre_evidence.md"
)


def _principal() -> LocalPrincipalAuthorityProducer:
    producer = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    producer.create_initial()
    return producer


def _acquire_v11(monkeypatch: pytest.MonkeyPatch, selected: Path):
    principal = _principal()
    intake = PennyLocalITunesXMLIntakeProducerV11(principal.verifier)
    request = intake.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: selected,
    )
    evidence = intake.capture_selected_file(request)
    verifier = PennyLocalITunesXMLAcquisitionVerifierV11(intake.verifier)
    parent = PennyLocalITunesXMLAcquisitionProducerV11(
        intake.verifier
    ).produce_authoritative(evidence)
    assert verifier.verify(parent)
    return verifier, parent


def _produce(monkeypatch: pytest.MonkeyPatch, selected: Path):
    verifier, parent = _acquire_v11(monkeypatch, selected)
    artifact = ITunesWindowsXMLGenreEvidenceProducer(verifier).produce_authoritative(
        parent
    )
    return verifier, parent, artifact


def _write_selected(tmp_path: Path, payload: bytes, name: str) -> Path:
    selected = tmp_path / name
    selected.write_bytes(payload)
    return selected


def test_frozen_genre_evidence_definition_is_exact_and_matches_document() -> None:
    assert len(GENRE_EVIDENCE_DEFINITION_JSON.encode("utf-8")) == 2248
    assert hashlib.sha256(GENRE_EVIDENCE_DEFINITION_JSON.encode("utf-8")).hexdigest() == (
        "094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a"
    )
    assert GENRE_EVIDENCE_DEFINITION_SHA256 == (
        "094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a"
    )
    assert verify_frozen_genre_evidence_definition()
    documented = DOCUMENT.read_text(encoding="utf-8").split("```json\n", 1)[1].split(
        "\n```", 1
    )[0]
    assert documented == GENRE_EVIDENCE_DEFINITION_JSON
    assert json.loads(documented)["supported_acquisition_authority"].endswith(
        "/1.1"
    )


def test_heterogeneous_fixture_reconstructs_complete_exact_genre_sequence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, parent, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    evidence_verifier = ITunesWindowsXMLGenreEvidenceVerifier(verifier)
    profile = verify_frozen_itunes_windows_xml_profile_v11(
        parent.file_selection_evidence
    )

    assert evidence_verifier.verify(artifact)
    assert artifact.observation_count == len(artifact.observations) == 110
    present = tuple(
        observation
        for observation in artifact.observations
        if observation.state == ITunesWindowsXMLGenreFieldState.PRESENT
    )
    absent = tuple(
        observation
        for observation in artifact.observations
        if observation.state == ITunesWindowsXMLGenreFieldState.ABSENT
    )
    assert len(present) == 82
    assert len(absent) == 28
    assert len({observation.source_genre_value for observation in present}) == 15
    assert all("source_genre_value" not in item.model_dump() for item in absent)

    for ordinal, (local_id, observation, parent_track) in enumerate(
        zip(
            profile.playlist_track_ids,
            artifact.observations,
            parent.ordered_tracks,
            strict=True,
        ),
        start=1,
    ):
        source_track = profile.tracks_by_correspondence_id[local_id]
        assert observation.ordinal == ordinal
        assert observation.receipt_local_track_id == local_id
        assert observation.track_persistent_id == source_track.persistent_id
        assert observation.track_id == parent_track.track_id
        if source_track.genre is None:
            assert isinstance(observation, ITunesWindowsXMLGenreAbsentObservation)
        else:
            assert isinstance(observation, ITunesWindowsXMLGenrePresentObservation)
            assert observation.source_genre_value == source_track.genre


def test_homogeneous_fixture_produces_59_exact_present_observations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, _, artifact = _produce(monkeypatch, FIXTURE)
    assert ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(artifact)
    assert artifact.observation_count == 59
    assert all(
        isinstance(observation, ITunesWindowsXMLGenrePresentObservation)
        and observation.source_genre_value == "Gothic Rock"
        for observation in artifact.observations
    )


def test_exact_present_value_is_preserved_without_normalization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = FIXTURE.read_bytes().replace(
        b"<key>Genre</key><string>Gothic Rock</string>",
        b"<key>Genre</key><string>  M\xc3\xbasica &amp; Exact  </string>",
        1,
    )
    _, _, artifact = _produce(
        monkeypatch, _write_selected(tmp_path, payload, "exact-source-value.xml")
    )
    first = artifact.observations[0]
    assert isinstance(first, ITunesWindowsXMLGenrePresentObservation)
    assert first.source_genre_value == "  Música & Exact  "
    assert artifact.normalization_performed is False


def test_closed_present_and_absent_schemas_reject_missing_or_inserted_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    present = next(
        item
        for item in artifact.observations
        if isinstance(item, ITunesWindowsXMLGenrePresentObservation)
    )
    absent = next(
        item
        for item in artifact.observations
        if isinstance(item, ITunesWindowsXMLGenreAbsentObservation)
    )
    missing = present.model_dump()
    missing.pop("source_genre_value")
    with pytest.raises(ValidationError):
        ITunesWindowsXMLGenrePresentObservation.model_validate(missing)
    inserted = absent.model_dump()
    inserted["source_genre_value"] = "Invented"
    with pytest.raises(ValidationError):
        ITunesWindowsXMLGenreAbsentObservation.model_validate(inserted)


@pytest.mark.parametrize("mutation", ("state", "value"))
def test_verifier_rejects_present_state_or_exact_value_mutation(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    verifier, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    index = next(
        index
        for index, item in enumerate(artifact.observations)
        if isinstance(item, ITunesWindowsXMLGenrePresentObservation)
    )
    original = artifact.observations[index]
    if mutation == "state":
        fields = original.model_dump()
        fields.pop("source_genre_value")
        fields["state"] = "ABSENT"
        replacement = ITunesWindowsXMLGenreAbsentObservation.model_validate(fields)
    else:
        replacement = original.model_copy(update={"source_genre_value": "Invented"})
    observations = list(artifact.observations)
    observations[index] = replacement
    mutated = artifact.model_copy(update={"observations": tuple(observations)})
    assert not ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(mutated)


def test_verifier_rejects_absent_to_present_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    index = next(
        index
        for index, item in enumerate(artifact.observations)
        if isinstance(item, ITunesWindowsXMLGenreAbsentObservation)
    )
    fields = artifact.observations[index].model_dump()
    fields["state"] = "PRESENT"
    fields["source_genre_value"] = "Invented"
    observations = list(artifact.observations)
    observations[index] = ITunesWindowsXMLGenrePresentObservation.model_validate(fields)
    mutated = artifact.model_copy(update={"observations": tuple(observations)})
    assert not ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(mutated)


@pytest.mark.parametrize("mutation", ("omission", "duplication", "reordering"))
def test_verifier_rejects_incomplete_duplicate_or_reordered_observations(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    verifier, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    observations = list(artifact.observations)
    if mutation == "omission":
        observations.pop()
    elif mutation == "duplication":
        observations[-1] = observations[0]
    else:
        observations[0], observations[1] = observations[1], observations[0]
    mutated = artifact.model_copy(update={"observations": tuple(observations)})
    assert not ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(mutated)


@pytest.mark.parametrize(
    "field,value",
    (
        ("parent_acquisition_sha256", "0" * 64),
        ("source_receipt_artifact_sha256", "0" * 64),
        ("selected_byte_sha256", "0" * 64),
        ("track_persistent_id", "AAAAAAAAAAAAAAAA"),
        ("receipt_local_track_id", 999999),
        ("source_definition_sha256", "0" * 64),
        ("genre_evidence_definition_sha256", "0" * 64),
    ),
)
def test_verifier_rejects_digest_definition_and_correspondence_substitution(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: object,
) -> None:
    verifier, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    first = artifact.observations[0].model_copy(update={field: value})
    mutated = artifact.model_copy(
        update={"observations": (first, *artifact.observations[1:])}
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        assert not ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(mutated)


def test_verifier_rejects_parent_and_receipt_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, parent, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    other_verifier, other_parent = _acquire_v11(monkeypatch, FIXTURE)
    assert not ITunesWindowsXMLGenreEvidenceVerifier(other_verifier).verify(
        artifact.model_copy(update={"parent_acquisition": other_parent})
    )
    evidence = parent.file_selection_evidence
    receipt = evidence.source_receipt.model_copy(update={"receipt_id": "substituted"})
    bad_evidence = evidence.model_copy(update={"source_receipt": receipt})
    bad_parent = parent.model_copy(update={"file_selection_evidence": bad_evidence})
    assert not ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(
        artifact.model_copy(update={"parent_acquisition": bad_parent})
    )


def test_direct_construction_cannot_bypass_occurrence_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, artifact = _produce(monkeypatch, HETEROGENEOUS_FIXTURE)
    unrelated_principal = _principal()
    unrelated_intake = PennyLocalITunesXMLIntakeProducerV11(
        unrelated_principal.verifier
    )
    unrelated = PennyLocalITunesXMLAcquisitionVerifierV11(unrelated_intake.verifier)
    reconstructed = ITunesWindowsXMLSourceGenreEvidenceArtifact.model_validate(
        artifact.model_dump(mode="json")
    )
    assert not ITunesWindowsXMLGenreEvidenceVerifier(unrelated).verify(reconstructed)


def test_v1_parent_is_not_supported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal = _principal()
    intake = PennyLocalITunesXMLIntakeProducer(principal.verifier)
    request = intake.create_request()
    monkeypatch.setattr(
        intake_module, "_native_windows_single_file_selection", lambda: FIXTURE
    )
    evidence = intake.capture_selected_file(request)
    parent = PennyLocalITunesXMLAcquisitionProducer(
        intake.verifier
    ).produce_authoritative(evidence)
    with pytest.raises(ITunesWindowsXMLGenreEvidenceInvalidInput):
        ITunesWindowsXMLGenreEvidenceProducer(  # type: ignore[arg-type]
            PennyLocalITunesXMLAcquisitionVerifierV11(intake.verifier)  # type: ignore[arg-type]
        ).produce_authoritative(parent)  # type: ignore[arg-type]


def test_different_receipts_remain_independent_occurrences(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original = FIXTURE.read_bytes()
    darkwave = original.replace(b">Gothic Rock<", b">Darkwave<", 1)
    absent = original.replace(
        b"\t\t\t<key>Genre</key><string>Gothic Rock</string>\r\n", b"", 1
    )
    _, _, first = _produce(monkeypatch, FIXTURE)
    _, _, second = _produce(
        monkeypatch, _write_selected(tmp_path, darkwave, "darkwave.xml")
    )
    _, _, third = _produce(monkeypatch, _write_selected(tmp_path, absent, "absent.xml"))
    assert first.artifact_id != second.artifact_id != third.artifact_id
    assert isinstance(first.observations[0], ITunesWindowsXMLGenrePresentObservation)
    assert first.observations[0].source_genre_value == "Gothic Rock"
    assert isinstance(second.observations[0], ITunesWindowsXMLGenrePresentObservation)
    assert second.observations[0].source_genre_value == "Darkwave"
    assert isinstance(third.observations[0], ITunesWindowsXMLGenreAbsentObservation)


def test_genre_evidence_does_not_change_mapping_or_source_neutral_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, parent = _acquire_v11(monkeypatch, HETEROGENEOUS_FIXTURE)
    parent_bytes = serialize_acquisition_authority_v11(parent)
    mapped_bytes = tuple(record.payload_json for record in parent.evidence_snapshot.records)
    artifact = ITunesWindowsXMLGenreEvidenceProducer(verifier).produce_authoritative(
        parent
    )
    assert serialize_acquisition_authority_v11(parent) == parent_bytes
    assert tuple(record.payload_json for record in parent.evidence_snapshot.records) == (
        mapped_bytes
    )
    assert tuple(SourceNeutralAcquisitionResult.model_fields) == (
        "schema_version",
        "artifact_kind",
        "acquisition_id",
        "source_receipt_id",
        "source_receipt_sha256",
        "source_type",
        "source_reference",
        "adapter_id",
        "adapter_version",
        "capability_declaration",
        "evidence_snapshot",
        "evidence_snapshot_sha256",
        "identity_metadata",
    )
    assert all("genre" not in payload.casefold() for payload in mapped_bytes)
    assert serialize_genre_evidence(artifact) == serialize_genre_evidence(
        ITunesWindowsXMLGenreEvidenceProducer(verifier).produce_authoritative(parent)
    )


def test_production_and_verification_do_not_access_media_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    verifier, parent = _acquire_v11(monkeypatch, HETEROGENEOUS_FIXTURE)
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("network accessed")
        ),
    )
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("file or media accessed")
        ),
    )
    artifact = ITunesWindowsXMLGenreEvidenceProducer(verifier).produce_authoritative(
        parent
    )
    assert ITunesWindowsXMLGenreEvidenceVerifier(verifier).verify(artifact)

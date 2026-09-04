from __future__ import annotations

import hashlib
import inspect
import json
import socket
from pathlib import Path

import pytest

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
from playlist_narrative_engine.evidence_acquisition import SourceNeutralAcquisitionResult
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    ITunesWindowsXMLAcquisitionInvalidInput,
    ITunesWindowsXMLProfileError,
    FrozenSourceProfileError,
    PennyLocalITunesXMLAcquisitionProducer,
    PennyLocalITunesXMLAcquisitionProducerV11,
    PennyLocalITunesXMLAcquisitionVerifier,
    PennyLocalITunesXMLAcquisitionVerifierV11,
    PennyLocalITunesXMLIntakeProducer,
    PennyLocalITunesXMLIntakeProducerV11,
    SOURCE_DEFINITION_SHA256,
    SOURCE_DEFINITION_V11_SHA256,
    XMLSafetyError,
    verify_frozen_definitions,
    verify_frozen_itunes_windows_xml_profile,
    verify_frozen_itunes_windows_xml_profile_v11,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.definitions import (
    SOURCE_DEFINITION_V11_JSON,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)
HETEROGENEOUS_FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "001-billboard-100-heterogeneous.xml"
)


def _principal():
    producer = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    producer.create_initial()
    return producer


def _evidence(
    monkeypatch: pytest.MonkeyPatch,
    selected: Path,
    *,
    version: str,
):
    principal = _principal()
    intake = (
        PennyLocalITunesXMLIntakeProducer(principal.verifier)
        if version == "1.0"
        else PennyLocalITunesXMLIntakeProducerV11(principal.verifier)
    )
    request = intake.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: selected,
    )
    return intake, intake.capture_selected_file(request)


def _selected(tmp_path: Path, payload: bytes) -> Path:
    value = tmp_path / "selected.xml"
    value.write_bytes(payload)
    return value


def _replace(payload: bytes, old: bytes, new: bytes) -> bytes:
    assert old in payload
    return payload.replace(old, new, 1)


def _remove_first_field(payload: bytes, name: bytes, kind: bytes = b"string") -> bytes:
    pattern = b"\t\t\t<key>" + name + b"</key><" + kind + b">"
    start = payload.index(pattern)
    end = payload.index(b"</" + kind + b">", start) + len(kind) + 3
    return payload[:start] + payload[end:]


def _replace_first_scalar(payload: bytes, name: bytes, content: bytes) -> bytes:
    marker = b"<key>" + name + b"</key><string>"
    start = payload.index(marker) + len(marker)
    end = payload.index(b"</string>", start)
    return payload[:start] + content + payload[end:]


def _replace_after(payload: bytes, marker: bytes, old: bytes, new: bytes) -> bytes:
    before, after = payload.split(marker, 1)
    assert old in after
    return before + marker + after.replace(old, new, 1)


def test_frozen_source_definition_versions_and_digest_are_exact() -> None:
    assert SOURCE_DEFINITION_SHA256 == (
        "16f168247d595419712b62eca8b62431ff38bb77948804560afe4a14268bb57e"
    )
    assert SOURCE_DEFINITION_V11_SHA256 == (
        "1e14e22641d0d9dc65b0cfe06544e0afc70111a15bd69ee9dc634d7b2dbe1fa9"
    )
    assert hashlib.sha256(SOURCE_DEFINITION_V11_JSON.encode()).hexdigest() == (
        SOURCE_DEFINITION_V11_SHA256
    )
    assert verify_frozen_definitions()


def test_v11_public_intake_still_has_no_path_stream_or_bytes() -> None:
    assert tuple(
        inspect.signature(PennyLocalITunesXMLIntakeProducerV11.create_request).parameters
    ) == ("self",)
    assert tuple(
        inspect.signature(
            PennyLocalITunesXMLIntakeProducerV11.capture_selected_file
        ).parameters
    ) == ("self", "request")


def test_homogeneous_fixture_is_accepted_by_both_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, evidence_v1 = _evidence(monkeypatch, FIXTURE, version="1.0")
    _, evidence_v11 = _evidence(monkeypatch, FIXTURE, version="1.1")
    assert len(verify_frozen_itunes_windows_xml_profile(evidence_v1).playlist_track_ids) == 59
    profile_v11 = verify_frozen_itunes_windows_xml_profile_v11(evidence_v11)
    assert len(profile_v11.playlist_track_ids) == 59
    assert all(track.genre == "Gothic Rock" for track in profile_v11.tracks_by_correspondence_id.values())


def test_exact_decimal_ampersand_reference_is_version_isolated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = _replace(
        FIXTURE.read_bytes(),
        b"<string>The Sisters Of Mercy</string>",
        b"<string>The Sisters &#38; Mercy</string>",
    )
    selected = _selected(tmp_path, payload)
    _, evidence_v1 = _evidence(monkeypatch, selected, version="1.0")
    with pytest.raises(XMLSafetyError):
        verify_frozen_itunes_windows_xml_profile(evidence_v1)
    _, evidence_v11 = _evidence(monkeypatch, selected, version="1.1")
    profile = verify_frozen_itunes_windows_xml_profile_v11(evidence_v11)
    assert next(iter(profile.tracks_by_correspondence_id.values())).artist == (
        "The Sisters & Mercy"
    )
    assert evidence_v11.source_receipt.items[0].payload == payload


@pytest.mark.parametrize("reference", (b"&#x26;", b"&#038;", b"&#65;"))
def test_v11_rejects_every_unfrozen_numeric_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    reference: bytes,
) -> None:
    payload = _replace(
        FIXTURE.read_bytes(),
        b"The Sisters Of Mercy",
        b"The Sisters " + reference + b" Mercy",
    )
    _, evidence = _evidence(monkeypatch, _selected(tmp_path, payload), version="1.1")
    with pytest.raises(XMLSafetyError):
        verify_frozen_itunes_windows_xml_profile_v11(evidence)


@pytest.mark.parametrize("field", (b"Genre", b"Sort Artist"))
def test_v1_requires_but_v11_preserves_absent_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: bytes,
) -> None:
    payload = _remove_first_field(FIXTURE.read_bytes(), field)
    selected = _selected(tmp_path, payload)
    _, evidence_v1 = _evidence(monkeypatch, selected, version="1.0")
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile(evidence_v1)
    _, evidence_v11 = _evidence(monkeypatch, selected, version="1.1")
    track = next(
        iter(
            verify_frozen_itunes_windows_xml_profile_v11(
                evidence_v11
            ).tracks_by_correspondence_id.values()
        )
    )
    assert getattr(track, "genre" if field == b"Genre" else "sort_artist") is None


@pytest.mark.parametrize("field", (b"Genre", b"Sort Artist"))
def test_present_optional_source_strings_remain_exact_and_nonblank(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    field: bytes,
) -> None:
    exact = "  Música &amp; Exact  ".encode()
    payload = _replace_first_scalar(FIXTURE.read_bytes(), field, exact)
    _, evidence = _evidence(monkeypatch, _selected(tmp_path, payload), version="1.1")
    track = next(
        iter(
            verify_frozen_itunes_windows_xml_profile_v11(
                evidence
            ).tracks_by_correspondence_id.values()
        )
    )
    assert getattr(track, "genre" if field == b"Genre" else "sort_artist") == (
        "  Música & Exact  "
    )
    blank = _replace_first_scalar(FIXTURE.read_bytes(), field, b" \t ")
    _, blank_evidence = _evidence(
        monkeypatch, _selected(tmp_path, blank), version="1.1"
    )
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile_v11(blank_evidence)


def test_v11_accepts_only_the_frozen_additional_optional_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    insertion = (
        b"\t\t\t<key>Album Artist</key><string>Exact Album Artist</string>\r\n"
        b"\t\t\t<key>Composer</key><string>Exact Composer</string>\r\n"
        b"\t\t\t<key>Artwork Count</key><integer>1</integer>\r\n"
    )
    payload = _replace(
        FIXTURE.read_bytes(),
        b"\t\t\t<key>Kind</key>",
        insertion + b"\t\t\t<key>Kind</key>",
    )
    _, evidence = _evidence(monkeypatch, _selected(tmp_path, payload), version="1.1")
    track = next(
        iter(
            verify_frozen_itunes_windows_xml_profile_v11(
                evidence
            ).tracks_by_correspondence_id.values()
        )
    )
    assert (track.album_artist, track.composer, track.artwork_count) == (
        "Exact Album Artist",
        "Exact Composer",
        1,
    )
    bad_artwork = payload.replace(
        b"<key>Artwork Count</key><integer>1</integer>",
        b"<key>Artwork Count</key><integer>2</integer>",
        1,
    )
    _, bad_evidence = _evidence(
        monkeypatch, _selected(tmp_path, bad_artwork), version="1.1"
    )
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile_v11(bad_evidence)
    unknown = payload.replace(
        b"<key>Artwork Count</key>", b"<key>Unlisted Field</key>", 1
    )
    _, unknown_evidence = _evidence(
        monkeypatch, _selected(tmp_path, unknown), version="1.1"
    )
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile_v11(unknown_evidence)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: _replace(
            value,
            b'<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
            b'<!DOCTYPE plist [<!ENTITY expanded "forbidden">]>',
        ),
        lambda value: _replace(
            value, b"<key>Minor Version</key>", b"<key>Major Version</key>"
        ),
        lambda value: _replace(value, b"12.13.10.3", b"12.13.10.4"),
        lambda value: _replace(value, b"MPEG audio file", b"AAC audio file"),
        lambda value: _replace(
            value, b"file://localhost/D:/share", b"file://remote/D:/share"
        ),
        lambda value: _replace(
            value, b"<key>Total Time</key><integer>281887</integer>",
            b"<key>Total Time</key><integer>0</integer>",
        ),
        lambda value: _replace_after(
            value,
            b"<key>Playlists</key>",
            b"<key>Track ID</key><integer>287</integer>",
            b"<key>Track ID</key><integer>281</integer>",
        ),
    ),
)
def test_v11_preserves_unrelated_fail_closed_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
) -> None:
    _, evidence = _evidence(
        monkeypatch,
        _selected(tmp_path, mutation(FIXTURE.read_bytes())),
        version="1.1",
    )
    with pytest.raises(ITunesWindowsXMLProfileError):
        verify_frozen_itunes_windows_xml_profile_v11(evidence)


def test_v11_acquisition_is_bound_and_cross_version_verification_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake_v1, evidence_v1 = _evidence(monkeypatch, FIXTURE, version="1.0")
    artifact_v1 = PennyLocalITunesXMLAcquisitionProducer(
        intake_v1.verifier
    ).produce_authoritative(evidence_v1)
    intake_v11, evidence_v11 = _evidence(monkeypatch, FIXTURE, version="1.1")
    producer_v11 = PennyLocalITunesXMLAcquisitionProducerV11(intake_v11.verifier)
    artifact_v11 = producer_v11.produce_authoritative(evidence_v11)

    assert PennyLocalITunesXMLAcquisitionVerifier(intake_v1.verifier).verify(artifact_v1)
    assert PennyLocalITunesXMLAcquisitionVerifierV11(intake_v11.verifier).verify(
        artifact_v11
    )
    assert not PennyLocalITunesXMLAcquisitionVerifier(intake_v1.verifier).verify(
        artifact_v11
    )
    assert not PennyLocalITunesXMLAcquisitionVerifierV11(intake_v11.verifier).verify(
        artifact_v1
    )
    assert artifact_v11.adapter_version == "1.1"
    assert artifact_v11.schema_version == "1.1"
    assert artifact_v11.file_selection_evidence.schema_version == "1.1"
    assert artifact_v11.file_selection_evidence.intake_request.schema_version == "1.1"
    assert artifact_v11.producer_authority_version == "1.1"
    assert artifact_v11.verifier_authority_version == "1.1"
    assert artifact_v11.source_definition.definition_version == "1.1"
    assert artifact_v11.capability_declaration.declaration_version == "1.1"
    assert artifact_v11.source_neutral_acquisition_result.schema_version == "1.0"
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
    assert [item.model_dump() for item in artifact_v1.ordered_tracks] == [
        item.model_dump() for item in artifact_v11.ordered_tracks
    ]
    payloads_v1 = [json.loads(item.payload_json) for item in artifact_v1.evidence_snapshot.records]
    payloads_v11 = [json.loads(item.payload_json) for item in artifact_v11.evidence_snapshot.records]
    for left, right in zip(payloads_v1, payloads_v11, strict=True):
        assert {key: value for key, value in left.items() if key != "provenance"} == {
            key: value for key, value in right.items() if key != "provenance"
        }
        assert left["provenance"]["source_type"] == right["provenance"]["source_type"]
        assert left["provenance"]["rationale"] == right["provenance"]["rationale"]


def test_producer_version_mismatch_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake_v1, evidence_v1 = _evidence(monkeypatch, FIXTURE, version="1.0")
    intake_v11, evidence_v11 = _evidence(monkeypatch, FIXTURE, version="1.1")
    with pytest.raises(ITunesWindowsXMLAcquisitionInvalidInput):
        PennyLocalITunesXMLAcquisitionProducerV11(
            intake_v1.verifier  # type: ignore[arg-type]
        ).produce_authoritative(evidence_v11)
    with pytest.raises(ITunesWindowsXMLAcquisitionInvalidInput):
        PennyLocalITunesXMLAcquisitionProducer(
            intake_v11.verifier  # type: ignore[arg-type]
        ).produce_authoritative(evidence_v1)


def test_v11_profile_does_not_access_network_or_media(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, evidence = _evidence(monkeypatch, FIXTURE, version="1.1")
    monkeypatch.setattr(
        socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network accessed")),
    )
    monkeypatch.setattr(
        Path,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("file accessed")),
    )
    assert len(verify_frozen_itunes_windows_xml_profile_v11(evidence).playlist_track_ids) == 59


def test_supplied_heterogeneous_export(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert HETEROGENEOUS_FIXTURE.stat().st_size == 159_502
    assert hashlib.sha256(HETEROGENEOUS_FIXTURE.read_bytes()).hexdigest() == (
        "087cd776ca591f4421fc0193588a116bffc9d9342cffb2862b9d06d6fe8d39f1"
    )
    assert HETEROGENEOUS_FIXTURE.read_bytes().count(b"&#38;") == 19
    selected = HETEROGENEOUS_FIXTURE
    _, evidence_v1 = _evidence(monkeypatch, selected, version="1.0")
    with pytest.raises(XMLSafetyError):
        verify_frozen_itunes_windows_xml_profile(evidence_v1)
    intake_v11, evidence_v11 = _evidence(monkeypatch, selected, version="1.1")
    profile = verify_frozen_itunes_windows_xml_profile_v11(evidence_v11)
    tracks = tuple(profile.tracks_by_correspondence_id.values())
    assert len(profile.playlist_track_ids) == 110
    assert len({track.artist for track in tracks}) == 65
    assert sum(track.genre is not None for track in tracks) == 82
    assert sum(track.genre is None for track in tracks) == 28
    assert len({track.genre for track in tracks if track.genre is not None}) == 15
    assert sum(track.sort_artist is not None for track in tracks) == 10
    assert sum(track.sort_artist is None for track in tracks) == 100
    artifact = PennyLocalITunesXMLAcquisitionProducerV11(
        intake_v11.verifier
    ).produce_authoritative(evidence_v11)
    assert PennyLocalITunesXMLAcquisitionVerifierV11(intake_v11.verifier).verify(
        artifact
    )
    mapped = tuple(json.loads(record.payload_json) for record in artifact.evidence_snapshot.records)
    assert all(
        set(value) == {"track_id", "title", "artist_name", "duration_seconds", "provenance"}
        for value in mapped
    )

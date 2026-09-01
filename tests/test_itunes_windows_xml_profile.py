from __future__ import annotations

import socket
from pathlib import Path

import pytest

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    FrozenSourceProfileError,
    PennyLocalITunesXMLIntakeProducer,
    PlistStructureError,
    XMLSafetyError,
    verify_frozen_itunes_windows_xml_profile,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)


def evidence_for(monkeypatch: pytest.MonkeyPatch, selected: Path):
    principal = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    principal.create_initial()
    producer = PennyLocalITunesXMLIntakeProducer(principal.verifier)
    request = producer.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: selected,
    )
    return producer.capture_selected_file(request)


def mutated_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
):
    payload = mutation(FIXTURE.read_bytes())
    selected = tmp_path / "selected.xml"
    selected.write_bytes(payload)
    return evidence_for(monkeypatch, selected)


def replace(payload: bytes, old: bytes, new: bytes, *, count: int = 1) -> bytes:
    assert old in payload
    return payload.replace(old, new, count)


def test_positive_profile_uses_content_not_fixture_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = verify_frozen_itunes_windows_xml_profile(
        evidence_for(monkeypatch, FIXTURE)
    )

    assert profile.library_persistent_id == "9C9E2747D29AB9A8"
    assert profile.playlist_persistent_id == "85C5D764BE8FCEFF"
    assert len(profile.tracks_by_correspondence_id) == 59
    assert len(profile.playlist_track_ids) == 59
    assert len(set(profile.playlist_track_ids)) == 59


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: b"\xef\xbb\xbf" + value,
        lambda value: value[:-10] + b"\xff" + value[-10:],
        lambda value: replace(
            value,
            b'<!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
            b'<!DOCTYPE plist [<!ENTITY expanded "forbidden">]>',
        ),
        lambda value: replace(value, b"<plist version=\"1.0\">", b"<?unsafe x?><plist version=\"1.0\">"),
        lambda value: replace(value, b"</plist>", b"</plis>"),
    ),
)
def test_xml_safety_failures_are_specific(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
) -> None:
    evidence = mutated_evidence(monkeypatch, tmp_path, mutation)
    with pytest.raises(XMLSafetyError):
        verify_frozen_itunes_windows_xml_profile(evidence)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: replace(
            value,
            b"<key>Minor Version</key>",
            b"<key>Major Version</key>",
        ),
        lambda value: replace(
            value,
            b"<key>Major Version</key>",
            b"<string>Major Version</string>",
        ),
        lambda value: replace(value, b"<integer>1</integer>", b"<integer>01</integer>"),
    ),
)
def test_plist_structure_failures_are_specific(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
) -> None:
    evidence = mutated_evidence(monkeypatch, tmp_path, mutation)
    with pytest.raises(PlistStructureError):
        verify_frozen_itunes_windows_xml_profile(evidence)


def mutate_playlist_reference(payload: bytes, old: bytes, new: bytes) -> bytes:
    marker = b"<key>Playlists</key>"
    before, after = payload.split(marker, 1)
    return before + marker + after.replace(old, new, 1)


def mutate_playlist_value(payload: bytes, key: bytes, new_value: bytes) -> bytes:
    marker = b"<key>Playlists</key>"
    before, after = payload.split(marker, 1)
    key_marker = b"<key>" + key + b"</key>"
    before_value, after_key = after.split(key_marker, 1)
    value_start = after_key.index(b"<string>")
    value_end = after_key.index(b"</string>", value_start) + len(b"</string>")
    return (
        before
        + marker
        + before_value
        + key_marker
        + after_key[:value_start]
        + new_value
        + after_key[value_end:]
    )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: replace(
            value,
            b"<key>Playlist Items</key>\r\n\t\t\t<array>",
            b"<key>Playlist Items</key>\r\n\t\t\t<array>unsupported text",
        ),
        lambda value: replace(
            value,
            b"<key>Major Version</key><integer>1</integer>",
            b"<key>Major Version</key><integer>1</integer>unsupported tail",
        ),
    ),
)
def test_container_character_content_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
) -> None:
    evidence = mutated_evidence(monkeypatch, tmp_path, mutation)
    with pytest.raises(PlistStructureError):
        verify_frozen_itunes_windows_xml_profile(evidence)


@pytest.mark.parametrize(
    "replacement",
    (
        b"<true> </true>",
        b"<true>\r\n\t</true>",
        b"<true></true>",
        b"<true />",
    ),
)
def test_true_requires_canonical_empty_element(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    replacement: bytes,
) -> None:
    evidence = mutated_evidence(
        monkeypatch,
        tmp_path,
        lambda value: replace(value, b"<true/>", replacement),
    )
    with pytest.raises(PlistStructureError):
        verify_frozen_itunes_windows_xml_profile(evidence)


@pytest.mark.parametrize(
    "impossible",
    (
        b"2026-99-99T99:99:99Z",
        b"2025-02-29T12:00:00Z",
        b"2026-01-01T24:00:00Z",
    ),
)
def test_lexically_shaped_but_impossible_utc_date_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    impossible: bytes,
) -> None:
    evidence = mutated_evidence(
        monkeypatch,
        tmp_path,
        lambda value: replace(value, b"2026-09-01T15:11:35Z", impossible),
    )
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile(evidence)


def test_whitespace_only_playlist_name_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    evidence = mutated_evidence(
        monkeypatch,
        tmp_path,
        lambda value: mutate_playlist_value(value, b"Name", b"<string> \t </string>"),
    )
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile(evidence)


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: replace(value, b"12.13.10.3", b"12.13.10.4"),
        lambda value: replace(value, b"MPEG audio file", b"AAC audio file"),
        lambda value: replace(value, b"<string>File</string>", b"<string>Remote</string>"),
        lambda value: replace(value, b"file://localhost/D:/share", b"file://remote/D:/share"),
        lambda value: replace(
            value,
            b"<key>Playlist Items</key>",
            b"<key>Master</key><true/><key>Playlist Items</key>",
        ),
        lambda value: mutate_playlist_reference(
            value,
            b"<key>Track ID</key><integer>287</integer>",
            b"<key>Track ID</key><integer>281</integer>",
        ),
        lambda value: mutate_playlist_reference(
            value,
            b"<key>Track ID</key><integer>281</integer>",
            b"<key>Track ID</key><integer>99999</integer>",
        ),
        lambda value: replace(
            value,
            b"<key>Playlists</key>\r\n\t<array>",
            b"<key>Playlists</key>\r\n\t<array><dict></dict>",
        ),
    ),
)
def test_frozen_source_profile_expansions_fail_specifically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation,
) -> None:
    evidence = mutated_evidence(monkeypatch, tmp_path, mutation)
    with pytest.raises(FrozenSourceProfileError):
        verify_frozen_itunes_windows_xml_profile(evidence)


def test_profile_verification_performs_no_network_or_media_file_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = evidence_for(monkeypatch, FIXTURE)
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

    profile = verify_frozen_itunes_windows_xml_profile(evidence)
    assert len(profile.playlist_track_ids) == 59

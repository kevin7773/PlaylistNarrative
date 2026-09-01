from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
import playlist_narrative_engine.itunes_windows_xml_acquisition.verifier as verifier_module
from playlist_narrative_engine.evidence_acquisition import (
    AuthoritativeMetadataField,
    SourceNeutralAcquisitionResult,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    PennyLocalITunesXMLAcquisitionProducer,
    PennyLocalITunesXMLAcquisitionVerifier,
    PennyLocalITunesXMLIntakeProducer,
    serialize_acquisition_authority,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)


def acquire(monkeypatch: pytest.MonkeyPatch, selected: Path = FIXTURE):
    principal = LocalPrincipalAuthorityProducer(LocalPrincipalAuthorityRepository())
    principal.create_initial()
    intake = PennyLocalITunesXMLIntakeProducer(principal.verifier)
    request = intake.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: selected,
    )
    evidence = intake.capture_selected_file(request)
    producer = PennyLocalITunesXMLAcquisitionProducer(intake.verifier)
    artifact = producer.produce_authoritative(evidence)
    return intake, producer, evidence, artifact


def test_positive_fixture_reproduces_frozen_universe_order_and_durations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, producer, evidence, artifact = acquire(monkeypatch)

    assert PennyLocalITunesXMLAcquisitionVerifier(intake.verifier).verify(artifact)
    assert len(artifact.ordered_tracks) == 59
    assert len(artifact.evidence_snapshot.records) == 59
    assert len(artifact.identity_metadata.records) == 59
    assert artifact.ordered_tracks[0].track_id == (
        "itunes-windows-library:9C9E2747D29AB9A8/track:60F3F28BD78BD511"
    )
    payload = json.loads(artifact.evidence_snapshot.records[0].payload_json)
    assert payload["title"] == "Black Planet"
    assert payload["duration_seconds"] == 281
    assert artifact.ordered_tracks[0].source_duration_milliseconds == 281_887
    identities_json = json.dumps(
        [item.track_id for item in artifact.ordered_tracks],
        separators=(",", ":"),
    ).encode()
    seconds_json = json.dumps(
        [item.source_duration_milliseconds // 1000 for item in artifact.ordered_tracks],
        separators=(",", ":"),
    ).encode()
    assert hashlib.sha256(identities_json).hexdigest() == (
        "65bb163e43f253597803013a959cf13a4d9c2a57ead7eb3d2f2f9cab58d5494d"
    )
    assert hashlib.sha256(seconds_json).hexdigest() == (
        "475837e755bd4c3d455b55cffabd5bf4802720af7d5f50186c6d88f59e2112e4"
    )
    assert producer.produce_authoritative(evidence) == artifact
    assert serialize_acquisition_authority(artifact) == serialize_acquisition_authority(
        producer.produce_authoritative(evidence)
    )


def test_source_neutral_schema_1_0_is_unchanged_and_exactly_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, evidence, artifact = acquire(monkeypatch)
    result = artifact.source_neutral_acquisition_result

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
    assert result.schema_version == "1.0"
    assert result.source_receipt_id == evidence.source_receipt.receipt_id
    assert result.source_receipt_sha256 == evidence.source_receipt_artifact_sha256
    assert result.capability_declaration.supports(
        AuthoritativeMetadataField.SOURCE_CATALOG_IDENTITY
    )
    assert not result.capability_declaration.supports(
        AuthoritativeMetadataField.RELEASE_VERSION_IDENTITY
    )
    assert not result.capability_declaration.supports(
        AuthoritativeMetadataField.DISPLAYED_EXPLICIT
    )


@pytest.mark.parametrize(
    "field,mutated",
    (
        ("artifact_id", "substituted"),
        ("library_persistent_id", "AAAAAAAAAAAAAAAA"),
        ("evidence_snapshot_sha256", "0" * 64),
        ("identity_metadata_sha256", "0" * 64),
        ("source_neutral_acquisition_result_sha256", "0" * 64),
    ),
)
def test_independent_verifier_rejects_wrapper_substitution(
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    mutated: object,
) -> None:
    intake, _, _, artifact = acquire(monkeypatch)
    assert not PennyLocalITunesXMLAcquisitionVerifier(intake.verifier).verify(
        artifact.model_copy(update={field: mutated})
    )


def test_independent_verifier_rejects_order_millisecond_snapshot_and_result_tampering(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intake, _, _, artifact = acquire(monkeypatch)
    verifier = PennyLocalITunesXMLAcquisitionVerifier(intake.verifier)
    reordered = artifact.model_copy(
        update={"ordered_tracks": tuple(reversed(artifact.ordered_tracks))}
    )
    assert not verifier.verify(reordered)
    first = artifact.ordered_tracks[0].model_copy(
        update={"source_duration_milliseconds": 281_888}
    )
    milliseconds = artifact.model_copy(
        update={"ordered_tracks": (first, *artifact.ordered_tracks[1:])}
    )
    assert not verifier.verify(milliseconds)
    bad_result = artifact.source_neutral_acquisition_result.model_copy(
        update={"source_reference": "substituted"}
    )
    assert not verifier.verify(
        artifact.model_copy(update={"source_neutral_acquisition_result": bad_result})
    )


def test_verifier_reconstructs_without_calling_or_importing_producer() -> None:
    source = inspect.getsource(verifier_module)
    assert "PennyLocalITunesXMLAcquisitionProducer" not in source
    assert "producer import" not in source


def test_fixture_filename_hash_names_and_exact_count_are_not_acceptance_special_cases(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    payload = FIXTURE.read_bytes()
    payload = payload.replace(b"Black Planet", b"Renamed Evidence", 1)
    payload = payload.replace(
        b"000-the_sisters_of_mercy-original_album_series-5cd-2010",
        b"Different Playlist Authority",
        1,
    )
    track_start = payload.index(b"\t\t<key>515</key>\r\n\t\t<dict>")
    tracks_end = payload.index(b"\r\n\t</dict>\r\n\t<key>Playlists</key>")
    payload = payload[:track_start] + payload[tracks_end:]
    final_membership = (
        b"\r\n\t\t\t\t<dict>\r\n"
        b"\t\t\t\t\t<key>Track ID</key><integer>515</integer>\r\n"
        b"\t\t\t\t</dict>"
    )
    assert final_membership in payload
    payload = payload.replace(final_membership, b"", 1)
    selected = tmp_path / "not-the-representative-filename.data"
    selected.write_bytes(payload)

    _, _, evidence, artifact = acquire(monkeypatch, selected)

    assert evidence.byte_sha256 != (
        "5448499004a619596b275f1fcf7eb1c8341e68c890b2b000a97b1487b83ec20e"
    )
    assert len(artifact.ordered_tracks) == 58
    assert json.loads(artifact.evidence_snapshot.records[0].payload_json)["title"] == (
        "Renamed Evidence"
    )

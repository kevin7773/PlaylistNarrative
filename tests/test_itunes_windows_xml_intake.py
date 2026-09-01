from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

import playlist_narrative_engine.itunes_windows_xml_acquisition.intake as intake_module
from playlist_narrative_engine.itunes_windows_xml_acquisition import (
    ITunesWindowsXMLIntakeInvalidInput,
    PennyLocalITunesXMLIntakeProducer,
)
from playlist_narrative_engine.local_authorization import (
    LocalPrincipalAuthorityProducer,
    LocalPrincipalAuthorityRepository,
)
from playlist_narrative_engine.source_receipt import (
    ACQUISITION_INTERFACE_DEFINITION,
    CAPTURE_POINT_DEFINITION,
)


FIXTURE = Path(__file__).parent / "fixtures" / "itunes_windows_xml" / (
    "000-the_sisters_of_mercy-original_album_series-5cd-2010.xml"
)
FIXTURE_SHA256 = "5448499004a619596b275f1fcf7eb1c8341e68c890b2b000a97b1487b83ec20e"


def foundation(monkeypatch: pytest.MonkeyPatch, selected: Path | None = FIXTURE):
    repository = LocalPrincipalAuthorityRepository()
    principal = LocalPrincipalAuthorityProducer(repository)
    principal.create_initial()
    producer = PennyLocalITunesXMLIntakeProducer(principal.verifier)
    request = producer.create_request()
    monkeypatch.setattr(
        intake_module,
        "_native_windows_single_file_selection",
        lambda: selected,
    )
    return principal, producer, request


def test_positive_fixture_is_exact_and_intake_captures_one_opaque_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert FIXTURE.stat().st_size == 79_886
    assert hashlib.sha256(FIXTURE.read_bytes()).hexdigest() == FIXTURE_SHA256
    principal, producer, request = foundation(monkeypatch)

    evidence = producer.capture_selected_file(request)

    assert evidence.byte_length == 79_886
    assert evidence.byte_sha256 == FIXTURE_SHA256
    assert evidence.source_receipt.declared_item_count == 1
    assert evidence.source_receipt.items[0].payload == FIXTURE.read_bytes()
    assert evidence.source_receipt.items[0].item_id == "item-000001"
    assert evidence.principal_id == request.principal_authority.principal_id
    assert producer.verifier.verify_evidence(evidence, require_current_tip=True)
    assert producer.verifier.verify_evidence(evidence)


def test_public_intake_surface_accepts_no_path_stream_or_bytes() -> None:
    assert tuple(inspect.signature(PennyLocalITunesXMLIntakeProducer.create_request).parameters) == (
        "self",
    )
    assert tuple(
        inspect.signature(PennyLocalITunesXMLIntakeProducer.capture_selected_file).parameters
    ) == ("self", "request")


def test_cancelled_picker_and_stale_principal_fail_without_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, producer, request = foundation(monkeypatch, None)
    with pytest.raises(ITunesWindowsXMLIntakeInvalidInput):
        producer.capture_selected_file(request)

    principal, producer, request = foundation(monkeypatch)
    principal.create_successor(request.principal_authority)
    with pytest.raises(ITunesWindowsXMLIntakeInvalidInput):
        producer.capture_selected_file(request)


def test_receipt_or_conformance_substitution_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal, producer, request = foundation(monkeypatch)
    evidence = producer.capture_selected_file(request)
    bad_receipt = evidence.source_receipt.model_copy(
        update={"source_reference": "substituted"}
    )
    substituted = evidence.model_copy(update={"source_receipt": bad_receipt})
    assert not producer.verifier.verify_evidence(substituted)
    bad_conformance = evidence.implementation_conformance.model_copy(
        update={"byte_sha256": "0" * 64}
    )
    assert not producer.verifier.verify_evidence(
        evidence.model_copy(update={"implementation_conformance": bad_conformance})
    )

    unrecorded_verifier = PennyLocalITunesXMLIntakeProducer(
        principal.verifier
    ).verifier
    assert not unrecorded_verifier.verify_evidence(evidence)


def test_conformance_occurrence_does_not_rewrite_frozen_definitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, producer, request = foundation(monkeypatch)
    evidence = producer.capture_selected_file(request)

    assert evidence.implementation_conformance.complete_one_item_response is True
    assert ACQUISITION_INTERFACE_DEFINITION.conforming_implementation_established is False
    assert CAPTURE_POINT_DEFINITION.conforming_implementation_established is False

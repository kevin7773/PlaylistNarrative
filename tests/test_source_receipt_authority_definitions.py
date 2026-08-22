from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from playlist_narrative_engine.source_receipt import (
    ACQUISITION_INTERFACE_DEFINITION,
    ACQUISITION_INTERFACE_SHA256,
    CANONICAL_SERIALIZATION_PROFILE,
    CANONICAL_PROFILE_SHA256,
    CAPTURE_POINT_DEFINITION,
    CAPTURE_POINT_SHA256,
    SOURCE_RECEIPT_POLICY,
    SOURCE_RECEIPT_POLICY_SHA256,
    AcquisitionInterfaceDefinition,
    CanonicalSerializationProfile,
    CapturePointDefinition,
    ObservationHandle,
    SourceReceiptPolicy,
    canonical_authority_bytes,
    canonical_authority_sha256,
    verify_source_receipt_authority_definition,
)


@pytest.mark.parametrize(
    "definition",
    (
        CANONICAL_SERIALIZATION_PROFILE,
        ACQUISITION_INTERFACE_DEFINITION,
        CAPTURE_POINT_DEFINITION,
        SOURCE_RECEIPT_POLICY,
    ),
)
def test_frozen_definitions_have_deterministic_canonical_bytes_and_digest(
    definition: object,
) -> None:
    serialized = canonical_authority_bytes(definition)

    assert serialized == canonical_authority_bytes(definition)
    assert canonical_authority_sha256(definition) == definition.canonical_sha256
    assert verify_source_receipt_authority_definition(definition)
    assert b" " not in serialized
    assert b"\n" not in serialized


def test_frozen_definition_digests_are_literal_version_anchors() -> None:
    assert CANONICAL_SERIALIZATION_PROFILE.canonical_sha256 == CANONICAL_PROFILE_SHA256
    assert ACQUISITION_INTERFACE_DEFINITION.canonical_sha256 == (
        ACQUISITION_INTERFACE_SHA256
    )
    assert CAPTURE_POINT_DEFINITION.canonical_sha256 == CAPTURE_POINT_SHA256
    assert SOURCE_RECEIPT_POLICY.canonical_sha256 == SOURCE_RECEIPT_POLICY_SHA256


def test_identity_and_version_substitution_fail_closed() -> None:
    substitutions = (
        (
            CanonicalSerializationProfile,
            CANONICAL_SERIALIZATION_PROFILE,
            {"profile_id": "other"},
        ),
        (
            AcquisitionInterfaceDefinition,
            ACQUISITION_INTERFACE_DEFINITION,
            {"definition_version": "2.0"},
        ),
        (
            CapturePointDefinition,
            CAPTURE_POINT_DEFINITION,
            {"capture_point_id": "other"},
        ),
        (
            SourceReceiptPolicy,
            SOURCE_RECEIPT_POLICY,
            {"policy_version": "2.0"},
        ),
    )
    for model, definition, replacement in substitutions:
        with pytest.raises(ValidationError):
            model.model_validate({**definition.model_dump(mode="json"), **replacement})


def test_content_mutation_is_not_frozen_authority() -> None:
    changed = SOURCE_RECEIPT_POLICY.model_copy(
        update={"empty_result_behavior": "REJECT_WITHOUT_RECEIPT"}
    )

    assert canonical_authority_sha256(changed) != SOURCE_RECEIPT_POLICY.canonical_sha256
    assert not verify_source_receipt_authority_definition(changed)

    with pytest.raises(ValidationError, match="canonical SHA-256"):
        SourceReceiptPolicy.model_validate(
            {
                **SOURCE_RECEIPT_POLICY.model_dump(mode="json"),
                "canonical_sha256": "0" * 64,
            }
        )


def test_policy_binds_exact_interface_capture_point_and_profile() -> None:
    policy = SOURCE_RECEIPT_POLICY

    assert policy.interface_definition_sha256 == (
        ACQUISITION_INTERFACE_DEFINITION.canonical_sha256
    )
    assert policy.capture_point_definition_sha256 == (
        CAPTURE_POINT_DEFINITION.canonical_sha256
    )
    assert policy.canonical_profile_sha256 == (
        CANONICAL_SERIALIZATION_PROFILE.canonical_sha256
    )

    with pytest.raises(ValidationError, match="interface definition"):
        SourceReceiptPolicy.model_validate(
            {
                **policy.model_dump(mode="json"),
                "interface_definition_sha256": "0" * 64,
                "canonical_sha256": None,
            }
        )


def test_item_order_and_complete_accounting_rules_are_machine_readable() -> None:
    policy = SOURCE_RECEIPT_POLICY

    assert policy.permitted_receipt_states == ("CAPTURED",)
    assert policy.ordering_rule == "preserve_interface_local_response_item_order"
    assert policy.item_ordinal_rule == "contiguous_one_based"
    assert policy.source_identity_rule == (
        "exact_nonblank_utf8_source_type_and_reference_without_normalization"
    )
    assert policy.receipt_content_digest_scope == (
        "authority_bindings_source_identity_accounting_and_ordered_items"
    )
    assert policy.duplicate_item_behavior == "REJECT_WITHOUT_RECEIPT"
    assert policy.missing_item_behavior == "REJECT_WITHOUT_RECEIPT"
    assert policy.truncation_behavior == "REJECT_WITHOUT_RECEIPT"
    assert policy.empty_result_behavior == (
        "ALLOW_ONLY_COMPLETE_DECLARED_ITEM_COUNT_ZERO"
    )
    assert policy.complete_accounting_rule == (
        "completion_signal_true_and_declared_count_equals_exact_ordered_item_count"
    )


def test_distinct_handles_permit_identical_payload_bytes() -> None:
    first = ObservationHandle(value="source-item-A")
    second = ObservationHandle(value="source-item-B")
    payloads = (b"same bytes", b"same bytes")

    assert payloads[0] == payloads[1]
    assert not SOURCE_RECEIPT_POLICY.has_duplicate_observation_handles(
        (first, second)
    )
    assert SOURCE_RECEIPT_POLICY.identical_payload_bytes_with_distinct_handles_allowed


def test_repeated_exact_handle_is_duplicate_but_unicode_is_not_normalized() -> None:
    repeated = ObservationHandle(value="source-item-A")
    composed = ObservationHandle(value="caf\N{LATIN SMALL LETTER E WITH ACUTE}")
    decomposed = ObservationHandle(value="cafe\N{COMBINING ACUTE ACCENT}")

    assert SOURCE_RECEIPT_POLICY.has_duplicate_observation_handles(
        (repeated, repeated)
    )
    assert not SOURCE_RECEIPT_POLICY.has_duplicate_observation_handles(
        (composed, decomposed)
    )
    assert composed.value != decomposed.value

    for invalid in ("", " handle", "handle "):
        with pytest.raises(ValidationError):
            ObservationHandle(value=invalid)


def test_observation_handle_is_not_authoritative_receipt_item_identity() -> None:
    assert SOURCE_RECEIPT_POLICY.observation_handle_is_receipt_item_id is False
    assert SOURCE_RECEIPT_POLICY.item_identity_rule == (
        "receipt_assigned_item_dash_six_digit_ordinal"
    )
    assert SOURCE_RECEIPT_POLICY.observation_handle_preserved_in_receipt is True
    assert SOURCE_RECEIPT_POLICY.observation_handle_in_receipt_content_digest is True


def test_stale_definition_version_and_digest_are_not_current_authority() -> None:
    stale = ACQUISITION_INTERFACE_DEFINITION.model_copy(
        update={
            "definition_version": "1.0",
            "canonical_sha256": (
                "cb0d03f6806b51e515febeeb66dfc6d9a5a347012b5849566f2976b02a17d121"
            ),
        }
    )

    assert not verify_source_receipt_authority_definition(stale)
    with pytest.raises(ValidationError):
        AcquisitionInterfaceDefinition.model_validate(stale.model_dump(mode="json"))


def test_authority_definitions_are_observation_only() -> None:
    policy = SOURCE_RECEIPT_POLICY
    source = Path(
        "src/playlist_narrative_engine/source_receipt/definitions.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert policy.metadata_interpretation_performed is False
    assert policy.allowed_direct_attestations == (
        "source_identity",
        "observation_handle",
        "exact_item_bytes",
        "item_boundaries",
        "interface_local_order",
        "declared_item_count",
        "complete_response_signal",
    )
    assert not any(
        name.startswith(
            (
                "playlist_narrative_engine.candidate_formation",
                "playlist_narrative_engine.track_evidence",
                "playlist_narrative_engine.research_store",
            )
        )
        for name in imports
    )


def test_definitions_claim_no_conforming_external_implementation() -> None:
    assert ACQUISITION_INTERFACE_DEFINITION.conforming_implementation_established is False
    assert CAPTURE_POINT_DEFINITION.conforming_implementation_established is False

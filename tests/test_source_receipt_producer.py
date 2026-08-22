from __future__ import annotations

import ast
from pathlib import Path

import pytest

from playlist_narrative_engine.source_receipt import (
    FROZEN_SOURCE_RECEIPT_AUTHORITY,
    ObservationHandle,
    SourceObservationItem,
    SourceObservationRequest,
    SourceReceiptArtifact,
    SourceReceiptInvalidInput,
    SourceReceiptProducer,
    canonical_source_receipt_content_bytes,
    serialize_source_receipt_artifact,
    source_receipt_content,
    verify_source_receipt_artifact,
)


def observation_request(
    *,
    items: tuple[SourceObservationItem, ...] | None = None,
    declared_item_count: int | None = None,
    complete_response: bool = True,
) -> SourceObservationRequest:
    selected = items if items is not None else (
        SourceObservationItem(
            observation_handle=ObservationHandle(value="source-item-A"),
            payload=b"\x00\xffsame bytes",
        ),
        SourceObservationItem(
            observation_handle=ObservationHandle(value="source-item-B"),
            payload=b"\x00\xffsame bytes",
        ),
    )
    return SourceObservationRequest(
        source_type="future_source_contract",
        source_reference="future-source:response-001",
        complete_response=complete_response,
        declared_item_count=(
            len(selected) if declared_item_count is None else declared_item_count
        ),
        items=selected,
    )


def produced() -> tuple[SourceObservationRequest, SourceReceiptArtifact]:
    request = observation_request()
    return request, SourceReceiptProducer().produce_authoritative(request)


def test_authoritative_receipt_preserves_exact_bytes_order_and_handles() -> None:
    request, artifact = produced()

    assert artifact.authority == FROZEN_SOURCE_RECEIPT_AUTHORITY
    assert artifact.receipt_id == (
        f"source-receipt:sha256:{artifact.receipt_content_sha256}"
    )
    assert tuple(item.item_id for item in artifact.items) == (
        "item-000001",
        "item-000002",
    )
    assert tuple(item.ordinal for item in artifact.items) == (1, 2)
    assert tuple(item.observation_handle.value for item in artifact.items) == (
        "source-item-A",
        "source-item-B",
    )
    assert tuple(item.payload for item in artifact.items) == tuple(
        item.payload for item in request.items
    )
    assert artifact.items[0].payload == artifact.items[1].payload
    assert verify_source_receipt_artifact(artifact, request=request)


def test_known_receipt_fixture_has_stable_canonical_digest() -> None:
    request, artifact = produced()

    assert artifact.receipt_content_sha256 == (
        "46523e645f0939f19b36487b1a91d4b6c9b3e1d9a3e13e20eb72d50f321a3327"
    )
    assert canonical_source_receipt_content_bytes(source_receipt_content(artifact)) == (
        canonical_source_receipt_content_bytes(source_receipt_content(artifact))
    )
    assert serialize_source_receipt_artifact(artifact) == (
        serialize_source_receipt_artifact(
            SourceReceiptProducer().produce_authoritative(request)
        )
    )


def test_complete_zero_item_receipt_is_authoritative() -> None:
    request = observation_request(items=(), declared_item_count=0)
    artifact = SourceReceiptProducer().produce_authoritative(request)

    assert artifact.declared_item_count == 0
    assert artifact.items == ()
    assert verify_source_receipt_artifact(artifact, request=request)


def test_duplicate_handles_fail_but_identical_bytes_with_distinct_handles_pass() -> None:
    duplicate = (
        SourceObservationItem(
            observation_handle=ObservationHandle(value="same-handle"),
            payload=b"first",
        ),
        SourceObservationItem(
            observation_handle=ObservationHandle(value="same-handle"),
            payload=b"second",
        ),
    )
    with pytest.raises(SourceReceiptInvalidInput):
        SourceReceiptProducer().produce_authoritative(
            observation_request(items=duplicate)
        )

    _, artifact = produced()
    assert len(artifact.items) == 2


def test_incomplete_or_count_mismatched_observation_fails_closed() -> None:
    for request in (
        observation_request(complete_response=False),
        observation_request(declared_item_count=1),
    ):
        with pytest.raises(SourceReceiptInvalidInput):
            SourceReceiptProducer().produce_authoritative(request)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("acquisition_interface_id", "other"),
        ("acquisition_interface_version", "1.0"),
        ("acquisition_interface_sha256", "0" * 64),
        ("capture_point_id", "other"),
        ("capture_point_version", "1.0"),
        ("capture_point_sha256", "0" * 64),
        ("source_receipt_policy_id", "other"),
        ("source_receipt_policy_version", "1.0"),
        ("source_receipt_policy_sha256", "0" * 64),
        ("canonical_profile_id", "other"),
        ("canonical_profile_version", "2.0"),
        ("canonical_profile_sha256", "0" * 64),
    ),
)
def test_every_authority_substitution_is_rejected(field: str, value: str) -> None:
    request = observation_request()
    substituted = request.model_copy(
        update={"authority": request.authority.model_copy(update={field: value})}
    )

    with pytest.raises(SourceReceiptInvalidInput):
        SourceReceiptProducer().produce_authoritative(substituted)


@pytest.mark.parametrize(
    "change",
    (
        "source_type",
        "source_reference",
        "handle",
        "payload",
        "order",
        "remove",
        "insert",
        "item_id",
        "ordinal",
        "digest",
        "receipt_id",
        "schema_version",
    ),
)
def test_artifact_tampering_fails_reproduction_verification(change: str) -> None:
    request, artifact = produced()
    changed = artifact
    if change == "source_type":
        changed = artifact.model_copy(update={"source_type": "other"})
    elif change == "source_reference":
        changed = artifact.model_copy(update={"source_reference": "other"})
    elif change == "handle":
        item = artifact.items[0].model_copy(
            update={"observation_handle": ObservationHandle(value="other")}
        )
        changed = artifact.model_copy(update={"items": (item, artifact.items[1])})
    elif change == "payload":
        item = artifact.items[0].model_copy(update={"payload_base64": "Y2hhbmdlZA=="})
        changed = artifact.model_copy(update={"items": (item, artifact.items[1])})
    elif change == "order":
        changed = artifact.model_copy(update={"items": tuple(reversed(artifact.items))})
    elif change == "remove":
        changed = artifact.model_copy(update={"items": artifact.items[:1]})
    elif change == "insert":
        changed = artifact.model_copy(update={"items": artifact.items + artifact.items[:1]})
    elif change == "item_id":
        item = artifact.items[0].model_copy(update={"item_id": "item-000002"})
        changed = artifact.model_copy(update={"items": (item, artifact.items[1])})
    elif change == "ordinal":
        item = artifact.items[0].model_copy(update={"ordinal": 2})
        changed = artifact.model_copy(update={"items": (item, artifact.items[1])})
    elif change == "digest":
        changed = artifact.model_copy(update={"receipt_content_sha256": "0" * 64})
    elif change == "receipt_id":
        changed = artifact.model_copy(
            update={"receipt_id": f"source-receipt:sha256:{'0' * 64}"}
        )
    elif change == "schema_version":
        changed = artifact.model_copy(update={"schema_version": "2.0"})

    assert not verify_source_receipt_artifact(changed, request=request)


def test_request_substitution_cannot_verify_an_otherwise_valid_artifact() -> None:
    request, artifact = produced()
    substitutions = (
        request.model_copy(update={"source_type": "other"}),
        request.model_copy(update={"source_reference": "other"}),
        request.model_copy(update={"items": tuple(reversed(request.items))}),
    )

    assert all(
        not verify_source_receipt_artifact(artifact, request=substituted)
        for substituted in substitutions
    )


def test_direct_schema_construction_alone_is_not_authoritative() -> None:
    request, artifact = produced()
    direct = SourceReceiptArtifact.model_validate(artifact.model_dump(mode="json"))
    unrelated = observation_request(
        items=(
            SourceObservationItem(
                observation_handle=ObservationHandle(value="unrelated"),
                payload=b"unrelated",
            ),
        )
    )

    assert direct == artifact
    assert not verify_source_receipt_artifact(direct, request=unrelated)
    assert verify_source_receipt_artifact(direct, request=request)


def test_source_receipt_producer_is_sole_production_constructor() -> None:
    root = Path("src/playlist_narrative_engine")
    allowed = Path("src/playlist_narrative_engine/source_receipt/producer.py")
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path == allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else None
            )
            if name == "SourceReceiptArtifact":
                violations.append(f"{path}:{node.lineno}")
    assert violations == []


def test_receipt_boundary_has_no_interpretive_or_downstream_dependencies() -> None:
    root = Path("src/playlist_narrative_engine/source_receipt")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in root.glob("*.py")
    )

    assert "playlist_narrative_engine.track_evidence" not in source
    assert "playlist_narrative_engine.candidate_formation" not in source
    assert "playlist_narrative_engine.research_store" not in source
    assert "json.loads" not in source

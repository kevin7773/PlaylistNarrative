from __future__ import annotations

import base64
import hashlib
import json
from typing import Literal

from pydantic import Field, field_validator, model_validator

from playlist_narrative_engine.source_receipt.definitions import (
    ACQUISITION_INTERFACE_ID,
    ACQUISITION_INTERFACE_SHA256,
    ACQUISITION_INTERFACE_VERSION,
    CANONICAL_PROFILE_ID,
    CANONICAL_PROFILE_SHA256,
    CANONICAL_PROFILE_VERSION,
    CAPTURE_POINT_ID,
    CAPTURE_POINT_SHA256,
    CAPTURE_POINT_VERSION,
    SOURCE_RECEIPT_POLICY_ID,
    SOURCE_RECEIPT_POLICY_SHA256,
    SOURCE_RECEIPT_POLICY_VERSION,
    FrozenSourceReceiptAuthorityModel,
    ObservationHandle,
)


SOURCE_RECEIPT_SCHEMA_VERSION = "1.0"


class SourceReceiptAuthorityBinding(FrozenSourceReceiptAuthorityModel):
    acquisition_interface_id: Literal[
        "pne.acquisition-interface.ordered-opaque-byte-response"
    ] = ACQUISITION_INTERFACE_ID
    acquisition_interface_version: Literal["1.1"] = ACQUISITION_INTERFACE_VERSION
    acquisition_interface_sha256: Literal[
        "3c0fa70094789a07acd596188c6aa2a461b20e2ed1deb49d01740a9bfb8f8de8"
    ] = ACQUISITION_INTERFACE_SHA256
    capture_point_id: Literal[
        "pne.capture-point.pre-interpretation-response-items"
    ] = CAPTURE_POINT_ID
    capture_point_version: Literal["1.1"] = CAPTURE_POINT_VERSION
    capture_point_sha256: Literal[
        "0465a499cfcaeb9d9dea2886389038f9ce540489b372663df2875e724a3c5856"
    ] = CAPTURE_POINT_SHA256
    source_receipt_policy_id: Literal[
        "pne.source-receipt.observation-only"
    ] = SOURCE_RECEIPT_POLICY_ID
    source_receipt_policy_version: Literal["1.1"] = SOURCE_RECEIPT_POLICY_VERSION
    source_receipt_policy_sha256: Literal[
        "6dc9164c3413436b582f08d83de154dd954cf2824ccdaa6e3e6d2c7476619e83"
    ] = SOURCE_RECEIPT_POLICY_SHA256
    canonical_profile_id: Literal[
        "pne.canonical-json.utf8-schema-order"
    ] = CANONICAL_PROFILE_ID
    canonical_profile_version: Literal["1.0"] = CANONICAL_PROFILE_VERSION
    canonical_profile_sha256: Literal[
        "469877e55ba0a31728d8db9a26a2b5f604a9bbbf3829dfc2ad8f039984afa3a4"
    ] = CANONICAL_PROFILE_SHA256


FROZEN_SOURCE_RECEIPT_AUTHORITY = SourceReceiptAuthorityBinding()


class SourceObservationItem(FrozenSourceReceiptAuthorityModel):
    observation_handle: ObservationHandle
    payload: bytes


class SourceObservationRequest(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_SCHEMA_VERSION
    request_kind: Literal["source_observation"] = "source_observation"
    authority: SourceReceiptAuthorityBinding = FROZEN_SOURCE_RECEIPT_AUTHORITY
    source_type: str = Field(min_length=1, max_length=200)
    source_reference: str = Field(min_length=1, max_length=1_000)
    complete_response: bool
    declared_item_count: int = Field(ge=0)
    items: tuple[SourceObservationItem, ...]
    provider_conformance_established: Literal[False] = False

    @field_validator("source_type", "source_reference")
    @classmethod
    def require_exact_source_identity(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("source identity must be exact and nonblank")
        value.encode("utf-8")
        return value


class SourceReceiptItem(FrozenSourceReceiptAuthorityModel):
    item_id: str = Field(pattern=r"^item-[0-9]{6}$")
    ordinal: int = Field(gt=0)
    observation_handle: ObservationHandle
    payload_base64: str

    @field_validator("payload_base64")
    @classmethod
    def require_canonical_base64(cls, value: str) -> str:
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("receipt payload must be canonical standard base64") from exc
        if base64.b64encode(decoded).decode("ascii") != value:
            raise ValueError("receipt payload must be canonical standard base64")
        return value

    @property
    def payload(self) -> bytes:
        return base64.b64decode(self.payload_base64, validate=True)


class SourceReceiptContent(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_SCHEMA_VERSION
    content_kind: Literal["source_receipt_content"] = "source_receipt_content"
    authority: SourceReceiptAuthorityBinding
    source_type: str
    source_reference: str
    complete_response: Literal[True]
    declared_item_count: int = Field(ge=0)
    items: tuple[SourceReceiptItem, ...]

    @field_validator("source_type", "source_reference")
    @classmethod
    def require_exact_source_identity(cls, value: str) -> str:
        if not value or value != value.strip():
            raise ValueError("receipt source identity must be exact and nonblank")
        value.encode("utf-8")
        return value


class SourceReceiptArtifact(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_SCHEMA_VERSION
    artifact_kind: Literal["source_receipt"] = "source_receipt"
    receipt_id: str = Field(pattern=r"^source-receipt:sha256:[0-9a-f]{64}$")
    receipt_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority: SourceReceiptAuthorityBinding
    source_type: str
    source_reference: str
    complete_response: Literal[True]
    declared_item_count: int = Field(ge=0)
    items: tuple[SourceReceiptItem, ...]

    @model_validator(mode="after")
    def verify_structural_correspondence(self) -> SourceReceiptArtifact:
        if self.authority != FROZEN_SOURCE_RECEIPT_AUTHORITY:
            raise ValueError("receipt must bind the exact frozen authority")
        if self.declared_item_count != len(self.items):
            raise ValueError("receipt item count must match exactly")
        expected_ordinals = tuple(range(1, len(self.items) + 1))
        if tuple(item.ordinal for item in self.items) != expected_ordinals:
            raise ValueError("receipt item ordinals must be contiguous and one-based")
        expected_ids = tuple(f"item-{ordinal:06d}" for ordinal in expected_ordinals)
        if tuple(item.item_id for item in self.items) != expected_ids:
            raise ValueError("receipt item identities must derive from exact order")
        handles = tuple(item.observation_handle.value for item in self.items)
        if len(handles) != len(set(handles)):
            raise ValueError("receipt observation handles must be unique")
        content = source_receipt_content(self)
        expected_digest = source_receipt_content_sha256(content)
        if self.receipt_content_sha256 != expected_digest:
            raise ValueError("receipt-content SHA-256 must match canonical content")
        if self.receipt_id != source_receipt_id(expected_digest):
            raise ValueError("receipt identity must derive from receipt-content SHA-256")
        return self


def source_receipt_content(
    artifact: SourceReceiptArtifact,
) -> SourceReceiptContent:
    return SourceReceiptContent(
        authority=artifact.authority,
        source_type=artifact.source_type,
        source_reference=artifact.source_reference,
        complete_response=artifact.complete_response,
        declared_item_count=artifact.declared_item_count,
        items=artifact.items,
    )


def canonical_source_receipt_content_bytes(content: SourceReceiptContent) -> bytes:
    return json.dumps(
        content.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def source_receipt_content_sha256(content: SourceReceiptContent) -> str:
    return hashlib.sha256(canonical_source_receipt_content_bytes(content)).hexdigest()


def source_receipt_id(content_sha256: str) -> str:
    return f"source-receipt:sha256:{content_sha256}"


def serialize_source_receipt_artifact(artifact: SourceReceiptArtifact) -> bytes:
    return json.dumps(
        artifact.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

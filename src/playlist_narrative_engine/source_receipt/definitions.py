from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SOURCE_RECEIPT_AUTHORITY_SCHEMA_VERSION = "1.0"
CANONICAL_PROFILE_ID = "pne.canonical-json.utf8-schema-order"
CANONICAL_PROFILE_VERSION = "1.0"
CANONICAL_PROFILE_SHA256 = "469877e55ba0a31728d8db9a26a2b5f604a9bbbf3829dfc2ad8f039984afa3a4"
ACQUISITION_INTERFACE_ID = "pne.acquisition-interface.ordered-opaque-byte-response"
ACQUISITION_INTERFACE_VERSION = "1.1"
ACQUISITION_INTERFACE_SHA256 = "3c0fa70094789a07acd596188c6aa2a461b20e2ed1deb49d01740a9bfb8f8de8"
CAPTURE_POINT_ID = "pne.capture-point.pre-interpretation-response-items"
CAPTURE_POINT_VERSION = "1.1"
CAPTURE_POINT_SHA256 = "0465a499cfcaeb9d9dea2886389038f9ce540489b372663df2875e724a3c5856"
SOURCE_RECEIPT_POLICY_ID = "pne.source-receipt.observation-only"
SOURCE_RECEIPT_POLICY_VERSION = "1.1"
SOURCE_RECEIPT_POLICY_SHA256 = "6dc9164c3413436b582f08d83de154dd954cf2824ccdaa6e3e6d2c7476619e83"


class FrozenSourceReceiptAuthorityModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ObservationHandle(FrozenSourceReceiptAuthorityModel):
    value: str = Field(min_length=1, max_length=500)

    @field_validator("value")
    @classmethod
    def require_exact_nonblank_utf8(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("observation handle must be exact and nonblank")
        value.encode("utf-8")
        return value


class CanonicalSerializationProfile(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_AUTHORITY_SCHEMA_VERSION
    definition_kind: Literal["canonical_serialization_profile"] = (
        "canonical_serialization_profile"
    )
    profile_id: Literal["pne.canonical-json.utf8-schema-order"] = CANONICAL_PROFILE_ID
    profile_version: Literal["1.0"] = CANONICAL_PROFILE_VERSION
    character_encoding: Literal["UTF-8"] = "UTF-8"
    json_object_order: Literal["declared_schema_field_order"] = (
        "declared_schema_field_order"
    )
    json_array_order: Literal["preserve_governed_sequence_order"] = (
        "preserve_governed_sequence_order"
    )
    whitespace: Literal["none_outside_json_strings"] = "none_outside_json_strings"
    unicode_handling: Literal["preserve_unicode_code_points_no_normalization"] = (
        "preserve_unicode_code_points_no_normalization"
    )
    binary_representation: Literal["RFC4648_standard_base64_with_padding"] = (
        "RFC4648_standard_base64_with_padding"
    )
    no_content_representation: Literal["no_item_object_receipt_level_count_zero"] = (
        "no_item_object_receipt_level_count_zero"
    )
    digest_algorithm: Literal["SHA-256"] = "SHA-256"
    digest_input: Literal["canonical_utf8_json_excluding_canonical_sha256"] = (
        "canonical_utf8_json_excluding_canonical_sha256"
    )
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bind_digest(self) -> CanonicalSerializationProfile:
        _verify_or_set_digest(self)
        return self


class AcquisitionInterfaceDefinition(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_AUTHORITY_SCHEMA_VERSION
    definition_kind: Literal["acquisition_interface_definition"] = (
        "acquisition_interface_definition"
    )
    interface_id: Literal[
        "pne.acquisition-interface.ordered-opaque-byte-response"
    ] = ACQUISITION_INTERFACE_ID
    definition_version: Literal["1.1"] = ACQUISITION_INTERFACE_VERSION
    observation_class: Literal["finite_ordered_opaque_byte_response"] = (
        "finite_ordered_opaque_byte_response"
    )
    authorized_claim: Literal[
        "exact_bytes_and_interface_local_order_exposed_by_one_complete_response"
    ] = "exact_bytes_and_interface_local_order_exposed_by_one_complete_response"
    material_representation: Literal["opaque_bytes"] = "opaque_bytes"
    exposed_item_components: tuple[
        Literal["observation_handle", "opaque_byte_payload", "interface_position"],
        ...,
    ] = ("observation_handle", "opaque_byte_payload", "interface_position")
    observation_handle_assignment: Literal[
        "conforming_interface_at_observation_time"
    ] = "conforming_interface_at_observation_time"
    observation_handle_scope: Literal["one_observation_event"] = (
        "one_observation_event"
    )
    observation_handle_equality: Literal["exact_unicode_code_point_equality"] = (
        "exact_unicode_code_point_equality"
    )
    observation_handle_normalization: Literal[False] = False
    response_completion_signal_required: Literal[True] = True
    interpretation_performed: Literal[False] = False
    normalization_performed: Literal[False] = False
    implementation_conformance_required: Literal[True] = True
    conforming_implementation_established: Literal[False] = False
    canonical_profile_id: Literal[
        "pne.canonical-json.utf8-schema-order"
    ] = CANONICAL_PROFILE_ID
    canonical_profile_version: Literal["1.0"] = CANONICAL_PROFILE_VERSION
    canonical_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    succession_rule: Literal[
        "any_definition_change_requires_new_version_and_digest"
    ] = "any_definition_change_requires_new_version_and_digest"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bind_profile_and_digest(self) -> AcquisitionInterfaceDefinition:
        if self.canonical_profile_sha256 != CANONICAL_SERIALIZATION_PROFILE.canonical_sha256:
            raise ValueError("interface definition must bind the frozen canonical profile")
        _verify_or_set_digest(self)
        return self


class CapturePointDefinition(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_AUTHORITY_SCHEMA_VERSION
    definition_kind: Literal["capture_point_definition"] = "capture_point_definition"
    capture_point_id: Literal[
        "pne.capture-point.pre-interpretation-response-items"
    ] = CAPTURE_POINT_ID
    definition_version: Literal["1.1"] = CAPTURE_POINT_VERSION
    interface_id: Literal[
        "pne.acquisition-interface.ordered-opaque-byte-response"
    ] = ACQUISITION_INTERFACE_ID
    interface_definition_version: Literal["1.1"] = ACQUISITION_INTERFACE_VERSION
    interface_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    logical_point: Literal[
        "after_complete_source_response_item_exposure_before_decode_parse_or_interpretation"
    ] = "after_complete_source_response_item_exposure_before_decode_parse_or_interpretation"
    observable_unit: Literal["one_interface_exposed_bounded_byte_item"] = (
        "one_interface_exposed_bounded_byte_item"
    )
    observable_unit_components: tuple[
        Literal["observation_handle", "opaque_byte_payload", "interface_position"],
        ...,
    ] = ("observation_handle", "opaque_byte_payload", "interface_position")
    item_boundary: Literal["exact_interface_exposed_item_boundary"] = (
        "exact_interface_exposed_item_boundary"
    )
    ordering_scope: Literal["interface_local_response_item_order"] = (
        "interface_local_response_item_order"
    )
    order_authoritative: Literal[True] = True
    material_representation: Literal["opaque_bytes"] = "opaque_bytes"
    pre_interpretation: Literal[True] = True
    complete_enumeration_signal_required: Literal[True] = True
    observation_handle_required_per_item: Literal[True] = True
    observation_handle_scope: Literal["one_observation_event"] = (
        "one_observation_event"
    )
    observation_handle_is_domain_identity: Literal[False] = False
    implementation_conformance_required: Literal[True] = True
    conforming_implementation_established: Literal[False] = False
    canonical_profile_id: Literal[
        "pne.canonical-json.utf8-schema-order"
    ] = CANONICAL_PROFILE_ID
    canonical_profile_version: Literal["1.0"] = CANONICAL_PROFILE_VERSION
    canonical_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    succession_rule: Literal[
        "any_definition_change_requires_new_version_and_digest"
    ] = "any_definition_change_requires_new_version_and_digest"
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bind_parents_and_digest(self) -> CapturePointDefinition:
        if self.interface_definition_sha256 != ACQUISITION_INTERFACE_DEFINITION.canonical_sha256:
            raise ValueError("capture point must bind the frozen interface definition")
        if self.canonical_profile_sha256 != CANONICAL_SERIALIZATION_PROFILE.canonical_sha256:
            raise ValueError("capture point must bind the frozen canonical profile")
        _verify_or_set_digest(self)
        return self


class SourceReceiptPolicy(FrozenSourceReceiptAuthorityModel):
    schema_version: Literal["1.0"] = SOURCE_RECEIPT_AUTHORITY_SCHEMA_VERSION
    definition_kind: Literal["source_receipt_policy"] = "source_receipt_policy"
    policy_id: Literal["pne.source-receipt.observation-only"] = SOURCE_RECEIPT_POLICY_ID
    policy_version: Literal["1.1"] = SOURCE_RECEIPT_POLICY_VERSION
    interface_id: Literal[
        "pne.acquisition-interface.ordered-opaque-byte-response"
    ] = ACQUISITION_INTERFACE_ID
    interface_definition_version: Literal["1.1"] = ACQUISITION_INTERFACE_VERSION
    interface_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    capture_point_id: Literal[
        "pne.capture-point.pre-interpretation-response-items"
    ] = CAPTURE_POINT_ID
    capture_point_definition_version: Literal["1.1"] = CAPTURE_POINT_VERSION
    capture_point_definition_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    canonical_profile_id: Literal[
        "pne.canonical-json.utf8-schema-order"
    ] = CANONICAL_PROFILE_ID
    canonical_profile_version: Literal["1.0"] = CANONICAL_PROFILE_VERSION
    canonical_profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    permitted_receipt_states: tuple[Literal["CAPTURED"], ...] = ("CAPTURED",)
    state_precedence: tuple[Literal["CAPTURED"], ...] = ("CAPTURED",)
    incomplete_response_behavior: Literal["REJECT_WITHOUT_RECEIPT"] = (
        "REJECT_WITHOUT_RECEIPT"
    )
    truncation_behavior: Literal["REJECT_WITHOUT_RECEIPT"] = "REJECT_WITHOUT_RECEIPT"
    missing_item_behavior: Literal["REJECT_WITHOUT_RECEIPT"] = (
        "REJECT_WITHOUT_RECEIPT"
    )
    duplicate_item_behavior: Literal["REJECT_WITHOUT_RECEIPT"] = (
        "REJECT_WITHOUT_RECEIPT"
    )
    duplicate_identity_basis: Literal[
        "repeated_exact_observation_handle_within_one_event"
    ] = "repeated_exact_observation_handle_within_one_event"
    identical_payload_bytes_with_distinct_handles_allowed: Literal[True] = True
    empty_result_behavior: Literal[
        "ALLOW_ONLY_COMPLETE_DECLARED_ITEM_COUNT_ZERO"
    ] = "ALLOW_ONLY_COMPLETE_DECLARED_ITEM_COUNT_ZERO"
    ordering_rule: Literal["preserve_interface_local_response_item_order"] = (
        "preserve_interface_local_response_item_order"
    )
    item_identity_rule: Literal["receipt_assigned_item_dash_six_digit_ordinal"] = (
        "receipt_assigned_item_dash_six_digit_ordinal"
    )
    observation_handle_is_receipt_item_id: Literal[False] = False
    observation_handle_preserved_in_receipt: Literal[True] = True
    observation_handle_in_receipt_content_digest: Literal[True] = True
    item_ordinal_rule: Literal["contiguous_one_based"] = "contiguous_one_based"
    receipt_identity_rule: Literal[
        "source_receipt_colon_sha256_colon_receipt_content_sha256"
    ] = "source_receipt_colon_sha256_colon_receipt_content_sha256"
    source_identity_rule: Literal[
        "exact_nonblank_utf8_source_type_and_reference_without_normalization"
    ] = "exact_nonblank_utf8_source_type_and_reference_without_normalization"
    receipt_content_digest_scope: Literal[
        "authority_bindings_source_identity_accounting_and_ordered_items"
    ] = "authority_bindings_source_identity_accounting_and_ordered_items"
    complete_accounting_rule: Literal[
        "completion_signal_true_and_declared_count_equals_exact_ordered_item_count"
    ] = "completion_signal_true_and_declared_count_equals_exact_ordered_item_count"
    allowed_direct_attestations: tuple[
        Literal[
            "source_identity",
            "observation_handle",
            "exact_item_bytes",
            "item_boundaries",
            "interface_local_order",
            "declared_item_count",
            "complete_response_signal",
        ],
        ...,
    ] = (
        "source_identity",
        "observation_handle",
        "exact_item_bytes",
        "item_boundaries",
        "interface_local_order",
        "declared_item_count",
        "complete_response_signal",
    )
    metadata_interpretation_performed: Literal[False] = False
    canonical_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def bind_authorities_and_digest(self) -> SourceReceiptPolicy:
        if self.permitted_receipt_states != ("CAPTURED",):
            raise ValueError("policy v1.0 permits only CAPTURED receipt items")
        if self.state_precedence != self.permitted_receipt_states:
            raise ValueError("policy state precedence must match its sole permitted state")
        if self.interface_definition_sha256 != ACQUISITION_INTERFACE_DEFINITION.canonical_sha256:
            raise ValueError("receipt policy must bind the frozen interface definition")
        if self.capture_point_definition_sha256 != CAPTURE_POINT_DEFINITION.canonical_sha256:
            raise ValueError("receipt policy must bind the frozen capture point definition")
        if self.canonical_profile_sha256 != CANONICAL_SERIALIZATION_PROFILE.canonical_sha256:
            raise ValueError("receipt policy must bind the frozen canonical profile")
        _verify_or_set_digest(self)
        return self

    @staticmethod
    def has_duplicate_observation_handles(
        handles: tuple[ObservationHandle, ...],
    ) -> bool:
        values = tuple(handle.value for handle in handles)
        return len(values) != len(set(values))


def canonical_authority_bytes(value: BaseModel) -> bytes:
    return json.dumps(
        value.model_dump(mode="json", exclude={"canonical_sha256"}),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def canonical_authority_sha256(value: BaseModel) -> str:
    return hashlib.sha256(canonical_authority_bytes(value)).hexdigest()


def verify_source_receipt_authority_definition(value: BaseModel) -> bool:
    expected = {
        CanonicalSerializationProfile: CANONICAL_SERIALIZATION_PROFILE,
        AcquisitionInterfaceDefinition: ACQUISITION_INTERFACE_DEFINITION,
        CapturePointDefinition: CAPTURE_POINT_DEFINITION,
        SourceReceiptPolicy: SOURCE_RECEIPT_POLICY,
    }.get(type(value))
    if expected is None:
        return False
    try:
        validated = type(value).model_validate(value.model_dump(mode="json"))
    except (TypeError, ValueError):
        return False
    return validated == value == expected


def _verify_or_set_digest(value: BaseModel) -> None:
    expected = canonical_authority_sha256(value)
    supplied = getattr(value, "canonical_sha256")
    if supplied is not None and supplied != expected:
        raise ValueError("canonical SHA-256 must match source-receipt authority content")
    object.__setattr__(value, "canonical_sha256", expected)


CANONICAL_SERIALIZATION_PROFILE = CanonicalSerializationProfile()
ACQUISITION_INTERFACE_DEFINITION = AcquisitionInterfaceDefinition(
    canonical_profile_sha256=CANONICAL_SERIALIZATION_PROFILE.canonical_sha256,
)
CAPTURE_POINT_DEFINITION = CapturePointDefinition(
    interface_definition_sha256=ACQUISITION_INTERFACE_DEFINITION.canonical_sha256,
    canonical_profile_sha256=CANONICAL_SERIALIZATION_PROFILE.canonical_sha256,
)
SOURCE_RECEIPT_POLICY = SourceReceiptPolicy(
    interface_definition_sha256=ACQUISITION_INTERFACE_DEFINITION.canonical_sha256,
    capture_point_definition_sha256=CAPTURE_POINT_DEFINITION.canonical_sha256,
    canonical_profile_sha256=CANONICAL_SERIALIZATION_PROFILE.canonical_sha256,
)

_FROZEN_DIGESTS = (
    (CANONICAL_SERIALIZATION_PROFILE, CANONICAL_PROFILE_SHA256),
    (ACQUISITION_INTERFACE_DEFINITION, ACQUISITION_INTERFACE_SHA256),
    (CAPTURE_POINT_DEFINITION, CAPTURE_POINT_SHA256),
    (SOURCE_RECEIPT_POLICY, SOURCE_RECEIPT_POLICY_SHA256),
)
if any(value.canonical_sha256 != expected for value, expected in _FROZEN_DIGESTS):
    raise RuntimeError(
        "frozen Source Receipt authority content changed without version succession"
    )

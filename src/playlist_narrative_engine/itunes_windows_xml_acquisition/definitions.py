from __future__ import annotations

import json

from playlist_narrative_engine.evidence_acquisition import (
    AuthoritativeMetadataField,
    MetadataCapability,
    SourceCapabilityDeclaration,
)
from playlist_narrative_engine.itunes_windows_xml_acquisition.canonical import (
    reject_duplicate_json_pairs,
    sha256_bytes,
)


SOURCE_DEFINITION_JSON = r'''{"schema_version":"1.0","definition_kind":"itunes_windows_xml_single_playlist_source","source_definition_id":"pne.source-definition.itunes-windows-xml-single-playlist","source_definition_version":"1.0","application":"iTunes","platform":"Windows","application_version":"12.13.10.3","export_workflow":"FILE_LIBRARY_EXPORT_PLAYLIST_XML","byte_capture":"ONE_COMPLETE_OPAQUE_ITEM_BEFORE_INTERPRETATION","xml":{"version":"1.0","encoding":"UTF-8","bom_permitted":false,"doctype_public_id":"-//Apple Computer//DTD PLIST 1.0//EN","doctype_system_id":"http://www.apple.com/DTDs/PropertyList-1.0.dtd","internal_subset_permitted":false,"external_resolution":false,"permitted_plist_types":["dict","array","key","string","integer","date","true"],"duplicate_dict_keys":"REJECT_RECURSIVELY"},"plist_version":"1.0","top_level_fields":[{"key":"Major Version","type":"integer","rule":"EXACT_1"},{"key":"Minor Version","type":"integer","rule":"EXACT_1"},{"key":"Date","type":"date","rule":"UTC_SECOND_Z_OBSERVED_ONLY"},{"key":"Application Version","type":"string","rule":"EXACT_12.13.10.3"},{"key":"Features","type":"integer","rule":"EXACT_5_OBSERVED_ONLY"},{"key":"Show Content Ratings","type":"true","rule":"OBSERVED_ONLY_NO_EXPLICIT_AUTHORITY"},{"key":"Music Folder","type":"string","rule":"ABSOLUTE_FILE_LOCALHOST_WINDOWS_DRIVE_URI_OBSERVED_ONLY"},{"key":"Library Persistent ID","type":"string","rule":"UPPER_HEX_16"},{"key":"Tracks","type":"dict","rule":"FINITE_COMPLETE_TRACK_DICTIONARY"},{"key":"Playlists","type":"array","rule":"EXACTLY_ONE_ORDINARY_PLAYLIST"}],"playlist_fields":[{"key":"Name","type":"string","rule":"NONBLANK"},{"key":"Description","type":"string","rule":"EXACT_SOURCE_VALUE"},{"key":"Playlist ID","type":"integer","rule":"POSITIVE"},{"key":"Playlist Persistent ID","type":"string","rule":"UPPER_HEX_16"},{"key":"All Items","type":"true","rule":"EXACT_TRUE"},{"key":"Playlist Items","type":"array","rule":"SOLE_COMPLETE_UNIQUE_ORDER_AUTHORITY"}],"playlist_item":"DICT_WITH_EXACTLY_ONE_POSITIVE_INTEGER_TRACK_ID","track_required_fields":["Track ID:POSITIVE_INTEGER_MATCHING_CANONICAL_DICTIONARY_KEY","Name:NONBLANK_STRING","Artist:NONBLANK_STRING","Album:NONBLANK_STRING","Genre:NONBLANK_STRING","Kind:EXACT_MPEG_AUDIO_FILE","Size:POSITIVE_INTEGER","Total Time:POSITIVE_INTEGER","Track Number:POSITIVE_INTEGER","Year:POSITIVE_INTEGER","Date Modified:UTC_SECOND_Z_DATE","Date Added:UTC_SECOND_Z_DATE","Bit Rate:POSITIVE_INTEGER","Sample Rate:POSITIVE_INTEGER","Comments:NONBLANK_STRING","Sort Artist:NONBLANK_STRING","Persistent ID:UPPER_HEX_16","Track Type:EXACT_FILE","Location:ABSOLUTE_FILE_LOCALHOST_WINDOWS_DRIVE_URI","File Folder Count:EXACT_NEGATIVE_1","Library Folder Count:EXACT_NEGATIVE_1"],"track_optional_fields":["Sort Album:NONBLANK_STRING","Sort Name:NONBLANK_STRING"],"membership":"EVERY_TOP_LEVEL_TRACK_REFERENCED_EXACTLY_ONCE_IN_PLAYLIST_ARRAY_ORDER","track_identity":"LIBRARY_PERSISTENT_ID_PLUS_TRACK_PERSISTENT_ID","media_file_access":false,"nonclaims":["APPLE_AUTHORSHIP","PRE_INTAKE_INTEGRITY","EXPORT_FRESHNESS","CURRENT_PROVIDER_OR_LIBRARY_STATE","PROVIDER_AUTHENTICATION","MEDIA_FILE_CORRESPONDENCE"],"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''
SOURCE_DEFINITION_SHA256 = "16f168247d595419712b62eca8b62431ff38bb77948804560afe4a14268bb57e"

MAPPING_DEFINITION_JSON = r'''{"schema_version":"1.0","definition_kind":"itunes_windows_xml_track_evidence_mapping","mapping_definition_id":"pne.source-mapping.itunes-windows-xml-track-evidence","mapping_definition_version":"1.0","track_identity":"itunes-windows-library:{Library Persistent ID}/track:{Persistent ID}","record_identity":"itunes-playlist-item/{one_based_ordinal:000000}","title_source":"Name","artist_source":"Artist","source_duration_milliseconds":"Total Time","duration_seconds":"floor(Total Time / 1000)","membership_order":"Playlist Items array order","provenance_source_type":"pne.source.itunes-windows-xml-single-playlist","provenance_source_reference":"source-receipt:{source_receipt_id}/item:{source_receipt_item_id}","provenance_rationale":"Mapped from a profile-verified iTunes Windows XML single-playlist export.","source_catalog_identity":"SUPPORTED_MEASURED_TRACK_IDENTITY","release_version_identity":"UNSUPPORTED_WITH_FIXED_OBSERVATION","displayed_explicit":"UNSUPPORTED_WITH_FIXED_OBSERVATION","snapshot_records":"ONE_PER_PLAYLIST_ITEM_COMPLETE","identity_metadata_records":"ONE_PER_TRACK_ID_COMPLETE","exact_milliseconds_retained_in_wrapper":true,"media_file_access":false,"identity_derivation":"DOMAIN_SEPARATED_SHA256_OVER_EXACT_PARENT_DIGESTS","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''
MAPPING_DEFINITION_SHA256 = "2bcec21e61fce134109ca72a64022a83a3dd0948a08a6968808492e3fd094630"

ACQUISITION_AUTHORITY_JSON = r'''{"schema_version":"1.0","definition_kind":"penny_local_itunes_xml_acquisition_authority","authority_definition_id":"pne.acquisition-authority.itunes-windows-xml-single-playlist","authority_definition_version":"1.0","intake_request_schema":"PennyLocalITunesXMLIntakeRequest/1.0","file_selection_evidence_schema":"PennyLocalITunesXMLFileSelectionEvidence/1.0","wrapper_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.0","source_neutral_acquisition_schema":"SourceNeutralAcquisitionResult/1.0_UNCHANGED","source_receipt_policy":"pne.source-receipt.observation-only/1.1_UNCHANGED","source_definition":"pne.source-definition.itunes-windows-xml-single-playlist/1.0","mapping_definition":"pne.source-mapping.itunes-windows-xml-track-evidence/1.0","capability_declaration":"pne.source-capability.itunes-windows-xml-single-playlist/1.0","producer":"pne.producer.itunes-windows-xml-acquisition-authority/1.0","verifier":"pne.verifier.itunes-windows-xml-acquisition-authority/1.0","identity_derivation":"LF_DOMAIN_SEPARATED_SHA256/1.0","complete_receipt_correspondence":true,"exact_millisecond_and_playlist_order_authority":true,"substitution_behavior":"REJECT_WITHOUT_ARTIFACT","nonclaims":["APPLE_AUTHORSHIP","PRE_INTAKE_INTEGRITY","EXPORT_FRESHNESS","CURRENT_PROVIDER_OR_LIBRARY_STATE","PROVIDER_AUTHENTICATION","MEDIA_FILE_CORRESPONDENCE","RELEASE_VERSION_IDENTITY","DISPLAYED_EXPLICIT"],"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}'''
ACQUISITION_AUTHORITY_SHA256 = "8d87ad3f4c97ee2a235b8310951ccfb51b37e06d35d38a5528c413f9c6a75f98"

SOURCE_TYPE = "pne.source.itunes-windows-xml-single-playlist"
ADAPTER_ID = "pne.adapter.itunes-windows-xml-single-playlist"
ADAPTER_VERSION = "1.0"
SELECTION_MECHANISM = "ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER"

CAPABILITY_DECLARATION = SourceCapabilityDeclaration(
    declaration_id="pne.source-capability.itunes-windows-xml-single-playlist",
    declaration_version="1.0",
    adapter_id=ADAPTER_ID,
    adapter_version=ADAPTER_VERSION,
    capabilities=(
        MetadataCapability(
            field=AuthoritativeMetadataField.DISPLAYED_EXPLICIT,
            authoritative=False,
        ),
        MetadataCapability(
            field=AuthoritativeMetadataField.RELEASE_VERSION_IDENTITY,
            authoritative=False,
        ),
        MetadataCapability(
            field=AuthoritativeMetadataField.SOURCE_CATALOG_IDENTITY,
            authoritative=True,
        ),
    ),
)
CAPABILITY_DECLARATION_JSON = (
    '{"schema_version":"1.0","declaration_id":"pne.source-capability.itunes-windows-xml-single-playlist","declaration_version":"1.0","adapter_id":"pne.adapter.itunes-windows-xml-single-playlist","adapter_version":"1.0","capabilities":[{"field":"displayed_explicit","authoritative":false},{"field":"release_version_identity","authoritative":false},{"field":"source_catalog_identity","authoritative":true}]}'
)
CAPABILITY_DECLARATION_SHA256 = "f5a8cda68b976a14a6efef6f45f39a8f22f15178ecc4165a0d84d32b3e71f514"


def verify_frozen_definitions() -> bool:
    values = (
        (SOURCE_DEFINITION_JSON, SOURCE_DEFINITION_SHA256),
        (MAPPING_DEFINITION_JSON, MAPPING_DEFINITION_SHA256),
        (CAPABILITY_DECLARATION_JSON, CAPABILITY_DECLARATION_SHA256),
        (ACQUISITION_AUTHORITY_JSON, ACQUISITION_AUTHORITY_SHA256),
    )
    for content, digest in values:
        try:
            json.loads(content, object_pairs_hook=reject_duplicate_json_pairs)
        except (TypeError, ValueError, json.JSONDecodeError):
            return False
        if sha256_bytes(content.encode("utf-8")) != digest:
            return False
    return CAPABILITY_DECLARATION.model_dump(mode="json") == json.loads(
        CAPABILITY_DECLARATION_JSON
    )


if not verify_frozen_definitions():
    raise RuntimeError("frozen iTunes Windows XML definitions do not reproduce")

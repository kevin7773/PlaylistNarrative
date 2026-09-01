# Penny Local iTunes Windows XML Playlist Export Acquisition v1

- **Status:** documentation/authority contract frozen; implementation absent
- **Source class:** governed, provider-documented export
- **Source definition:**
  `pne.source-definition.itunes-windows-xml-single-playlist/1.0`
- **Mapping definition:**
  `pne.source-mapping.itunes-windows-xml-track-evidence/1.0`
- **Boundary:** Penny Local only

## Sole authority claim

The complete verified authority chain may make exactly this positive claim:

> The active Penny-local principal deliberately supplied these exact immutable
> bytes through governed iTunes-on-Windows XML export intake, and the bytes
> conform to the supported export profile.

This claim requires the exact active-principal artifact, governed file-selection
evidence, the complete one-item Source Receipt, source-profile verification,
mapping verification, and the immutable acquisition-authority wrapper defined
below. A path, filename, extension, MIME label, caller assertion, or parseable
XML document cannot make the claim.

The claim deliberately does not say that:

- Apple authored, signed, transmitted, or authenticated the file;
- the file remained unmodified before Penny intake;
- the export is fresh or describes current library or provider state;
- the active principal is a legally identified person or the only physical
  operator of the installation;
- format conformance establishes provider authentication; or
- a referenced media file exists, corresponds to the metadata, or was supplied
  to Penny.

## Product source-class decision

Penny Local may acquire evidence from a provider-documented, user-initiated
export only when a separately frozen source profile preserves a finite selected
universe, exact original bytes, durable deterministic replay, explicit
non-claims, and source-specific mapping authority. Direct provider integration
remains desirable when it is technically and contractually compatible with the
same authority requirements.

Apple documents the iTunes-on-PC workflow for selecting one playlist, choosing
**File > Library > Export Playlist**, and choosing XML. Apple also describes
exported song information as usable in a database or another app. That
documentation supports the export surface, not the field-level profile, file
authorship, freshness, or authentication claim. The field-level profile below
is frozen only from the genuine representative export. See
[Apple: Save a copy of your playlists in iTunes on PC](https://support.apple.com/en-nz/guide/itunes/itns2998/windows).

This source class does not authorize arbitrary user-created import formats.
Generic XML, plist, CSV, M3U, folders, caller-created interchange files, and
automatic format detection remain outside Penny Local authority.

## Exact supported source profile

Version 1.0 supports only the following conjunction:

- iTunes on Windows, exact `Application Version` `12.13.10.3`;
- the documented single-playlist XML export workflow;
- strict UTF-8 XML with no byte-order mark and XML declaration encoding
  `UTF-8`;
- plist envelope version `1.0`;
- top-level `Major Version` integer `1` and `Minor Version` integer `1`;
- exactly one ordinary, non-system playlist;
- every top-level track represented exactly once by that playlist and no other
  top-level track;
- unique playlist membership only;
- local file-backed tracks with exact `Track Type` `File`;
- exact `Kind` `MPEG audio file`; and
- absolute `file://localhost/` Windows-drive track locations.

It does not cover Apple Music on Windows, Music on Mac, whole-library XML,
cloud-only tracks, Apple Music subscription tracks, purchased/matched/uploaded
distinctions, duplicate playlist occurrences, non-MPEG audio, video, or any
other iTunes application or export version. A later profile must have a new
identity, version, digest, representative authority, and explicit approval.

### Frozen source-definition content

Canonical content is compact UTF-8 JSON in the displayed field order, with no
trailing newline:

```json
{"schema_version":"1.0","definition_kind":"itunes_windows_xml_single_playlist_source","source_definition_id":"pne.source-definition.itunes-windows-xml-single-playlist","source_definition_version":"1.0","application":"iTunes","platform":"Windows","application_version":"12.13.10.3","export_workflow":"FILE_LIBRARY_EXPORT_PLAYLIST_XML","byte_capture":"ONE_COMPLETE_OPAQUE_ITEM_BEFORE_INTERPRETATION","xml":{"version":"1.0","encoding":"UTF-8","bom_permitted":false,"doctype_public_id":"-//Apple Computer//DTD PLIST 1.0//EN","doctype_system_id":"http://www.apple.com/DTDs/PropertyList-1.0.dtd","internal_subset_permitted":false,"external_resolution":false,"permitted_plist_types":["dict","array","key","string","integer","date","true"],"duplicate_dict_keys":"REJECT_RECURSIVELY"},"plist_version":"1.0","top_level_fields":[{"key":"Major Version","type":"integer","rule":"EXACT_1"},{"key":"Minor Version","type":"integer","rule":"EXACT_1"},{"key":"Date","type":"date","rule":"UTC_SECOND_Z_OBSERVED_ONLY"},{"key":"Application Version","type":"string","rule":"EXACT_12.13.10.3"},{"key":"Features","type":"integer","rule":"EXACT_5_OBSERVED_ONLY"},{"key":"Show Content Ratings","type":"true","rule":"OBSERVED_ONLY_NO_EXPLICIT_AUTHORITY"},{"key":"Music Folder","type":"string","rule":"ABSOLUTE_FILE_LOCALHOST_WINDOWS_DRIVE_URI_OBSERVED_ONLY"},{"key":"Library Persistent ID","type":"string","rule":"UPPER_HEX_16"},{"key":"Tracks","type":"dict","rule":"FINITE_COMPLETE_TRACK_DICTIONARY"},{"key":"Playlists","type":"array","rule":"EXACTLY_ONE_ORDINARY_PLAYLIST"}],"playlist_fields":[{"key":"Name","type":"string","rule":"NONBLANK"},{"key":"Description","type":"string","rule":"EXACT_SOURCE_VALUE"},{"key":"Playlist ID","type":"integer","rule":"POSITIVE"},{"key":"Playlist Persistent ID","type":"string","rule":"UPPER_HEX_16"},{"key":"All Items","type":"true","rule":"EXACT_TRUE"},{"key":"Playlist Items","type":"array","rule":"SOLE_COMPLETE_UNIQUE_ORDER_AUTHORITY"}],"playlist_item":"DICT_WITH_EXACTLY_ONE_POSITIVE_INTEGER_TRACK_ID","track_required_fields":["Track ID:POSITIVE_INTEGER_MATCHING_CANONICAL_DICTIONARY_KEY","Name:NONBLANK_STRING","Artist:NONBLANK_STRING","Album:NONBLANK_STRING","Genre:NONBLANK_STRING","Kind:EXACT_MPEG_AUDIO_FILE","Size:POSITIVE_INTEGER","Total Time:POSITIVE_INTEGER","Track Number:POSITIVE_INTEGER","Year:POSITIVE_INTEGER","Date Modified:UTC_SECOND_Z_DATE","Date Added:UTC_SECOND_Z_DATE","Bit Rate:POSITIVE_INTEGER","Sample Rate:POSITIVE_INTEGER","Comments:NONBLANK_STRING","Sort Artist:NONBLANK_STRING","Persistent ID:UPPER_HEX_16","Track Type:EXACT_FILE","Location:ABSOLUTE_FILE_LOCALHOST_WINDOWS_DRIVE_URI","File Folder Count:EXACT_NEGATIVE_1","Library Folder Count:EXACT_NEGATIVE_1"],"track_optional_fields":["Sort Album:NONBLANK_STRING","Sort Name:NONBLANK_STRING"],"membership":"EVERY_TOP_LEVEL_TRACK_REFERENCED_EXACTLY_ONCE_IN_PLAYLIST_ARRAY_ORDER","track_identity":"LIBRARY_PERSISTENT_ID_PLUS_TRACK_PERSISTENT_ID","media_file_access":false,"nonclaims":["APPLE_AUTHORSHIP","PRE_INTAKE_INTEGRITY","EXPORT_FRESHNESS","CURRENT_PROVIDER_OR_LIBRARY_STATE","PROVIDER_AUTHENTICATION","MEDIA_FILE_CORRESPONDENCE"],"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Canonical SHA-256:
`16f168247d595419712b62eca8b62431ff38bb77948804560afe4a14268bb57e`.

Changing any content requires source-definition succession. Matching the ID and
version strings without the complete content and digest is substitution, not
authority.

## Governed file selection and immutable intake

### Intake request schema 1.0

`PennyLocalITunesXMLIntakeRequest` schema `1.0` is immutable, forbids extra
fields, and contains:

1. producer-generated `intake_request_id` and exact schema/artifact kind;
2. the complete verified `LocalPrincipalAuthorityArtifact` and its canonical
   SHA-256;
3. the exact source-definition identity, version, complete canonical content,
   and digest;
4. selection mechanism
   `ACTIVE_PRINCIPAL_USER_ACTIVATED_SINGLE_FILE_PICKER`;
5. expected item count `1`; and
6. producer identity `pne.producer.penny-local-itunes-xml-intake/1.0`.

The request contains no proposed path, filename, byte length, byte digest,
library identity, track identity, or parsed content. It is created only after
the intake producer verifies that the bound principal artifact is the one
applicable active tip of its complete installation lineage. Object possession
or a matching principal string is insufficient.

### File-selection evidence schema 1.0

`PennyLocalITunesXMLFileSelectionEvidence` schema `1.0` is produced only when
that request's user-activated, single-file picker returns one readable finite
stream to the same intake producer. It contains:

1. producer-generated evidence ID and the request's complete canonical content
   and SHA-256;
2. exact principal ID, principal-authority artifact ID, schema version, digest,
   installation ID, and verified active-lineage digest;
3. exact source-definition identity, version, content, and digest;
4. selection mechanism and exact one-item accounting;
5. exact byte length and lowercase SHA-256 calculated while the selected stream
   is captured once into immutable storage;
6. the complete resulting `SourceReceiptArtifact` schema `1.0`, its canonical
   digest, and exact receipt-item correspondence; and
7. producer identity `pne.producer.penny-local-itunes-xml-intake/1.0`.

The selected file's display name and original path may be retained only as
non-authoritative transport assertions inside the existing Source Receipt
metadata boundary. They never participate in selection authority, source
identity, result identity, or substitution acceptance.

No public or compatibility constructor may accept pre-read bytes, a path, a
filename, an open stream, a receipt, a digest, a principal ID, or selection
evidence and promote it to production intake authority. Low-level constructors
may exist only for isolated canonical conformance tests and carry no production
jurisdiction.

### Exact-byte capture order

The complete XML file is exactly one opaque Source Receipt item. The selected
stream is captured and its receipt item is finalized before any of the
following:

- UTF-8 decoding;
- XML or plist parsing;
- XML newline handling;
- normalization or trimming;
- URI decoding;
- field extraction; or
- access to any referenced media location.

The receipt's exact bytes, byte length, and SHA-256 are immutable. Later XML
tree construction may apply XML-defined parsing semantics, but it never
rewrites, replaces, or becomes the received byte authority.

## Source Receipt decision

No Source Receipt successor is required. The complete selected file fits the
existing one-item use of:

- acquisition interface
  `pne.acquisition-interface.ordered-opaque-byte-response/1.1`;
- capture point
  `pne.capture-point.pre-interpretation-response-items/1.1`;
- Source Receipt policy `pne.source-receipt.observation-only/1.1`; and
- canonical profile `pne.canonical-json.utf8-schema-order/1.0`.

Those definitions and digests remain byte-for-byte unchanged. A future
source-specific intake implementation must separately prove conformance to the
existing interface and capture-point definitions; this contract does not
retroactively declare a file picker, filesystem API, path, stream, or parser to
be conforming.

Receipt verification requires exactly one captured item, exact item position
one, exact byte length and hash correspondence with file-selection evidence,
and equality of the receipt payload bytes with the immutable captured bytes.
Zero items, multiple items, unavailable/truncated states, repeated handles, or
any byte mismatch produce no intake evidence.

## Resolver-disabled XML and plist verification

Verification is strict and fail-closed:

1. require the exact captured bytes and receipt correspondence before parsing;
2. reject a UTF-8 BOM, invalid UTF-8, overlong sequences, surrogate code points,
   replacement decoding, or an XML declaration other than exact encoding
   `UTF-8`;
3. recognize the representative external DOCTYPE identifiers only as inert
   source-observed syntax:
   `-//Apple Computer//DTD PLIST 1.0//EN` and
   `http://www.apple.com/DTDs/PropertyList-1.0.dtd`;
4. reject an internal subset, entity declaration, entity reference other than
   XML's five predefined entities, processing instruction after the XML
   declaration, XInclude, schema hint, or additional top-level node;
5. construct the XML tree with DTD loading, external entities, external schemas,
   XInclude, network access, and filesystem resolution disabled;
6. require exactly one `plist` root with exact `version="1.0"` and exactly one
   child `dict`;
7. permit only the observed plist element types `dict`, `array`, `key`,
   `string`, `integer`, `date`, and `true`; and
8. reject malformed XML, unsupported plist types, non-alternating dictionary
   key/value children, non-key dictionary positions, and duplicate exact keys
   in every dictionary at every depth.

The external DTD identifier must never initiate a network request, filesystem
read, cache lookup, catalog lookup, or fallback resolver. Parser configuration
that resolves it is nonconforming even if resolution succeeds or returns the
expected DTD.

### Top-level dictionary

The exact required keys and types are:

| Key | Plist type | v1 rule |
| --- | --- | --- |
| `Major Version` | `integer` | exact `1` |
| `Minor Version` | `integer` | exact `1` |
| `Date` | `date` | UTC `YYYY-MM-DDThh:mm:ssZ`; observed only |
| `Application Version` | `string` | exact `12.13.10.3` |
| `Features` | `integer` | exact `5` |
| `Show Content Ratings` | `true` | source-observed only; grants no Explicit evidence |
| `Music Folder` | `string` | absolute `file://localhost/` Windows-drive URI; observed only |
| `Library Persistent ID` | `string` | exactly 16 uppercase hexadecimal characters |
| `Tracks` | `dict` | finite track dictionary defined below |
| `Playlists` | `array` | exactly one playlist dictionary defined below |

All ten keys are required exactly once. Any additional top-level key fails.
`Date`, `Features`, `Show Content Ratings`, and `Music Folder` are profile
conformance fields only; they authorize no freshness, feature, rating, media,
or current-library inference.

### Exactly one ordinary playlist

`Playlists` contains exactly one `dict` with exactly these keys and types:

- `Name` nonblank `string`;
- `Description` `string`, including the observed empty value;
- positive `Playlist ID` `integer`;
- `Playlist Persistent ID` of exactly 16 uppercase hexadecimal characters;
- `All Items` exact `true`; and
- `Playlist Items` `array`.

The exact closed key set excludes distinguished or system markers such as
`Master`, `Distinguished Kind`, `Music`, `Movies`, `TV Shows`, `Podcasts`,
`Audiobooks`, `Purchased Music`, `Party Shuffle`, `Folder`, and `Visible`.
Presence of any such key or any unknown key fails; it is never ignored as a
label.

`Playlist Items` is the sole membership and order authority. Every array member
must be a dictionary containing exactly one `Track ID` key with a positive
integer. Membership order is array order. Each reference must resolve to
exactly one top-level track dictionary. Duplicate references and dangling
references fail; no silent deduplication, repair, sorting, or omission is
permitted.

Every supported top-level track must be referenced exactly once. A referenced
subset, unreferenced top-level track, or additional referenced object therefore
fails this single-playlist profile.

### Track dictionary

Each `Tracks` entry is one alternating key/`dict` pair. Its dictionary key is a
canonical positive base-10 integer string with no sign or leading zero and must
equal the nested positive integer `Track ID`. Both are receipt-local
correspondence only.

Every track requires exactly these observed fields:

- nonblank strings `Name`, `Artist`, `Album`, `Genre`, `Comments`, and
  `Sort Artist`;
- exact strings `Track Type` = `File` and `Kind` = `MPEG audio file`;
- 16-character uppercase hexadecimal `Persistent ID`;
- absolute `file://localhost/[A-Za-z]:/` `Location` URI with valid percent
  escapes and no credentials, fragment, query, backslash, relative segment, or
  decoded media access;
- positive integers `Track ID`, `Size`, `Total Time`, `Track Number`, `Year`,
  `Bit Rate`, and `Sample Rate`;
- exact integers `File Folder Count` = `-1` and `Library Folder Count` = `-1`;
  and
- UTC-form `Date Modified` and `Date Added` dates.

Only `Sort Album` and `Sort Name` may additionally appear, each at most once as
a nonblank string. No other track key or plist type is supported. These
unmapped fields establish only profile conformance; they do not establish
release/version identity, preference, quality, or current media state.

The verifier must not open, stat, hash, inspect, decode, probe, or otherwise
access the URI target. `Location` is source-observed metadata only.

## Frozen source-scoped identity and mapping

Source-scoped track identity is exactly:

```text
Library Persistent ID + Track Persistent ID
```

Its schema-1 string form is:

```text
itunes-windows-library:{Library Persistent ID}/track:{Persistent ID}
```

Both components use the frozen 16-character uppercase hexadecimal form.
Identity comparison is exact code-point equality. No identity may be
synthesized from `Track ID`, title, artist, album, location, filename, or other
metadata. `Track ID` participates only in reference correspondence within the
one exact export and Source Receipt.

For playlist item ordinal `n`, starting at one, the corresponding snapshot
`record_id` is `itunes-playlist-item/{n:000000}`. The zero-padded ordinal is
derived from authoritative playlist order and is not a catalog identity.

The exact field mapping is:

| Source field | Output authority |
| --- | --- |
| `Name` | exact `title` |
| `Artist` | exact `artist_name` |
| `Total Time` | authoritative positive integer source duration milliseconds |
| derived from `Total Time` | `duration_seconds = floor(Total Time / 1000)` |
| source-scoped identity | exact `track_id` and measured `source_catalog_identity` |
| receipt lineage | `source_type` = `pne.source.itunes-windows-xml-single-playlist` |
| receipt lineage | `source_reference` = `source-receipt:{source_receipt_id}/item:{source_receipt_item_id}` |
| receipt lineage | rationale = `Mapped from a profile-verified iTunes Windows XML single-playlist export.` |

No rounding-to-nearest is authorized. The exact positive millisecond value
remains recoverable in the complete receipt and acquisition wrapper even though
schema-1 validated track evidence carries whole seconds.

### Frozen mapping-definition content

Canonical content is compact UTF-8 JSON in the displayed field order, with no
trailing newline:

```json
{"schema_version":"1.0","definition_kind":"itunes_windows_xml_track_evidence_mapping","mapping_definition_id":"pne.source-mapping.itunes-windows-xml-track-evidence","mapping_definition_version":"1.0","track_identity":"itunes-windows-library:{Library Persistent ID}/track:{Persistent ID}","record_identity":"itunes-playlist-item/{one_based_ordinal:000000}","title_source":"Name","artist_source":"Artist","source_duration_milliseconds":"Total Time","duration_seconds":"floor(Total Time / 1000)","membership_order":"Playlist Items array order","provenance_source_type":"pne.source.itunes-windows-xml-single-playlist","provenance_source_reference":"source-receipt:{source_receipt_id}/item:{source_receipt_item_id}","provenance_rationale":"Mapped from a profile-verified iTunes Windows XML single-playlist export.","source_catalog_identity":"SUPPORTED_MEASURED_TRACK_IDENTITY","release_version_identity":"UNSUPPORTED_WITH_FIXED_OBSERVATION","displayed_explicit":"UNSUPPORTED_WITH_FIXED_OBSERVATION","snapshot_records":"ONE_PER_PLAYLIST_ITEM_COMPLETE","identity_metadata_records":"ONE_PER_TRACK_ID_COMPLETE","exact_milliseconds_retained_in_wrapper":true,"media_file_access":false,"identity_derivation":"DOMAIN_SEPARATED_SHA256_OVER_EXACT_PARENT_DIGESTS","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Canonical SHA-256:
`2bcec21e61fce134109ca72a64022a83a3dd0948a08a6968808492e3fd094630`.

### Non-authoritative mapping example

This representative-derived canonical example is a conformance vector only and
does not become an acquisition artifact:

```json
{"library_persistent_id":"9C9E2747D29AB9A8","track_persistent_id":"60F3F28BD78BD511","track_id":"itunes-windows-library:9C9E2747D29AB9A8/track:60F3F28BD78BD511","record_id":"itunes-playlist-item/000001","name":"Black Planet","artist":"The Sisters Of Mercy","total_time_ms":281887,"duration_seconds":281}
```

Canonical example SHA-256:
`2925fee5cd500f402b41e7639f58eabee0931476eef35ad9a0c386740536a884`.

## Frozen capability declaration

The existing `SourceCapabilityDeclaration` schema `1.0` is sufficient for the
initial capability matrix. Its exact canonical content is:

```json
{"schema_version":"1.0","declaration_id":"pne.source-capability.itunes-windows-xml-single-playlist","declaration_version":"1.0","adapter_id":"pne.adapter.itunes-windows-xml-single-playlist","adapter_version":"1.0","capabilities":[{"field":"displayed_explicit","authoritative":false},{"field":"release_version_identity","authoritative":false},{"field":"source_catalog_identity","authoritative":true}]}
```

Canonical SHA-256:
`f5a8cda68b976a14a6efef6f45f39a8f22f15178ecc4165a0d84d32b3e71f514`.

`source_catalog_identity` is supported only at the exact iTunes library plus
track persistent identity scope. `release_version_identity` is unsupported;
album, year, title suffixes, comments, or location cannot supply it. Displayed
Explicit is unsupported. Top-level `Show Content Ratings=true` is not per-track
Explicit evidence and must not become measured `true`, measured `false`, clean,
unavailable, or inferred state.

The corresponding `CandidateIdentityMetadataArtifact` record therefore carries
measured source catalog identity with receipt-backed observation, plus explicit
`UNSUPPORTED` observations for release/version identity and displayed Explicit.

For each playlist item, `payload_json` is compact UTF-8 JSON in exact field
order `track_id`, `title`, `artist_name`, `duration_seconds`, `provenance`; the
provenance object uses exact field order `source_type`, `source_reference`,
`rationale`. JSON string escaping follows
`pne.canonical-json.utf8-schema-order/1.0`; source text is neither trimmed nor
normalized.

The metadata record uses the same exact `track_id`. Its measured catalog
observation has evidence ID `{record_id}/source-catalog` and compact payload
`{"library_persistent_id":"{Library Persistent ID}","track_persistent_id":"{Persistent ID}"}`.
The release observation has evidence ID `{record_id}/release-version-unsupported`
and payload `{"capability":"UNSUPPORTED","field":"release_version_identity"}`.
The Explicit observation has evidence ID `{record_id}/displayed-explicit-unsupported`
and payload `{"capability":"UNSUPPORTED","field":"displayed_explicit"}`. All
three carry the exact frozen provenance source type and reference. No album,
rating flag, title, or other field participates.

### Deterministic derived identities

Let `D(label, values...)` be lowercase SHA-256 of strict UTF-8 bytes formed by
the exact label followed by each exact value, separated by one LF byte, with no
trailing LF. The sole producer derives:

- `snapshot_id` = `pne.evidence-snapshot/sha256/` plus
  `D("pne.evidence-snapshot/1.0", source_receipt_sha256,
  source_definition_sha256, mapping_definition_sha256)`;
- metadata `artifact_id` = `pne.candidate-identity-metadata/sha256/` plus
  `D("pne.candidate-identity-metadata/1.0", evidence_snapshot_sha256,
  capability_declaration_sha256)`;
- `acquisition_id` = `pne.source-neutral-acquisition/sha256/` plus
  `D("pne.source-neutral-acquisition/1.0", source_receipt_sha256,
  source_definition_sha256, mapping_definition_sha256,
  capability_declaration_sha256, evidence_snapshot_sha256,
  identity_metadata_sha256)`; and
- wrapper `artifact_id` = `pne.itunes-xml-acquisition-authority/sha256/` plus
  `D("pne.itunes-xml-acquisition-authority/1.0",
  file_selection_evidence_sha256, source_receipt_sha256,
  source_definition_sha256, mapping_definition_sha256,
  capability_declaration_sha256, source_neutral_acquisition_result_sha256)`.

Digest values in these derivations are exact lowercase hexadecimal strings.
No UUID, timestamp, filename, path, environment value, randomness, or mutable
lookup participates. Replaying one exact verified request reproduces every
derived identity and canonical result digest.

## Deterministic producer chain

The only authorized conceptual chain is:

```text
governed active-principal single-file selection
        ↓
PennyLocalITunesXMLFileSelectionEvidence
        ↓
one-item SourceReceiptArtifact
        ↓
iTunes Windows XML source-profile verification
        ↓
EvidenceSnapshot schema 1.0
        +
CandidateIdentityMetadataArtifact schema 1.0
        ↓
SourceNeutralAcquisitionResult schema 1.0
        ↓
PennyLocalITunesXMLAcquisitionAuthorityArtifact schema 1.0
        ↓
source-neutral acquisition authority
```

Parsing and mapping are pure functions of the exact receipt, verified
definitions, and fixed schemas. They use no current time, locale, environment,
filesystem state, media-file state, provider state, network access, randomness,
or caller-selected defaults.

## Acquisition/result schema decision

`SourceNeutralAcquisitionResult` schema `1.0` remains byte-for-byte and
behaviorally unchanged. It is not promoted to schema `2.0` in this freeze.

Schema `1.0` already carries the receipt reference/digest, exact adapter
identity/version, capability declaration, EvidenceSnapshot and digest, and
CandidateIdentityMetadataArtifact. It does not independently carry the full
file-selection authority, complete Source Receipt content, source-definition
content/digest, mapping-definition content/digest, exact millisecond/order
correspondence, its own result digest, or the sole source-specific
producer/verifier authority.

A separate immutable `PennyLocalITunesXMLAcquisitionAuthorityArtifact` schema
`1.0` supplies that missing authority without redefining the source-neutral
schema. This wrapper is source-specific and must not leak into Track Evidence
Validation or Candidate Formation.

### Frozen acquisition-authority definition

Canonical content is compact UTF-8 JSON in the displayed field order, with no
trailing newline:

```json
{"schema_version":"1.0","definition_kind":"penny_local_itunes_xml_acquisition_authority","authority_definition_id":"pne.acquisition-authority.itunes-windows-xml-single-playlist","authority_definition_version":"1.0","intake_request_schema":"PennyLocalITunesXMLIntakeRequest/1.0","file_selection_evidence_schema":"PennyLocalITunesXMLFileSelectionEvidence/1.0","wrapper_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.0","source_neutral_acquisition_schema":"SourceNeutralAcquisitionResult/1.0_UNCHANGED","source_receipt_policy":"pne.source-receipt.observation-only/1.1_UNCHANGED","source_definition":"pne.source-definition.itunes-windows-xml-single-playlist/1.0","mapping_definition":"pne.source-mapping.itunes-windows-xml-track-evidence/1.0","capability_declaration":"pne.source-capability.itunes-windows-xml-single-playlist/1.0","producer":"pne.producer.itunes-windows-xml-acquisition-authority/1.0","verifier":"pne.verifier.itunes-windows-xml-acquisition-authority/1.0","identity_derivation":"LF_DOMAIN_SEPARATED_SHA256/1.0","complete_receipt_correspondence":true,"exact_millisecond_and_playlist_order_authority":true,"substitution_behavior":"REJECT_WITHOUT_ARTIFACT","nonclaims":["APPLE_AUTHORSHIP","PRE_INTAKE_INTEGRITY","EXPORT_FRESHNESS","CURRENT_PROVIDER_OR_LIBRARY_STATE","PROVIDER_AUTHENTICATION","MEDIA_FILE_CORRESPONDENCE","RELEASE_VERSION_IDENTITY","DISPLAYED_EXPLICIT"],"canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Canonical SHA-256:
`8d87ad3f4c97ee2a235b8310951ccfb51b37e06d35d38a5528c413f9c6a75f98`.

The wrapper embeds this complete definition and digest. Matching a schema name,
producer name, or authority-definition ID without complete canonical content is
not authority.

### Acquisition-authority wrapper schema 1.0

The wrapper is immutable, forbids extra fields, and contains in canonical schema
order:

1. exact schema version and artifact kind;
2. producer-generated artifact and acquisition request identities;
3. complete intake request and file-selection evidence with canonical digests;
4. complete active-principal artifact and verified active-lineage binding;
5. complete one-item Source Receipt artifact, canonical digest, exact receipt
   item ID, byte length, and byte SHA-256;
6. complete acquisition-authority definition content and digest;
7. complete source-definition content and digest;
8. complete mapping-definition content and digest;
9. complete capability declaration content and digest;
10. exact adapter identity/version;
11. exact library and playlist persistent identities;
12. ordered tuple of every source-scoped track identity in `Playlist Items`
    order;
13. ordered tuple of exact positive source-duration milliseconds paired with
    those identities;
14. complete EvidenceSnapshot and its canonical SHA-256;
15. complete CandidateIdentityMetadataArtifact and its canonical SHA-256;
16. complete SourceNeutralAcquisitionResult schema `1.0` and its canonical
    SHA-256;
17. producer authority
    `pne.producer.itunes-windows-xml-acquisition-authority/1.0`;
18. verifier authority
    `pne.verifier.itunes-windows-xml-acquisition-authority/1.0`;
19. fixed false authorship, pre-intake-integrity, freshness, current-state,
    provider-authentication, media-inspection, release-identity, and
    displayed-explicit claims; and
20. wrapper canonical SHA-256 appended last and excluded from its digest input.

The full embedded artifacts, not projections, must be structurally revalidated.
Every digest must be reproduced from canonical bytes. The verifier independently
reparses the exact receipt bytes under the source definition, reproduces every
identity, order, millisecond duration, snapshot payload, metadata observation,
and embedded source-neutral result, then reproduces the wrapper digest.

The producer and verifier are the only production authorities. General-purpose
XML libraries, model constructors, deserializers, tests, caller-supplied
artifacts, and matching digests have no independent authority.

## Complete correspondence and substitution rejection

The verifier requires all of the following exact equalities:

- selected bytes = receipt item bytes;
- selected byte length/hash = receipt item length/hash = wrapper length/hash;
- intake principal binding = complete verified applicable principal lineage;
- source definition, mapping definition, and capability declaration = their
  complete frozen content and reproduced digests;
- every playlist reference = one top-level `Track ID` and one output record;
- every supported top-level track = one playlist reference and one output
  record;
- every output `track_id` = one library plus track persistent-ID pair;
- ordered wrapper identities and milliseconds = playlist-array order and exact
  `Total Time` values;
- EvidenceSnapshot records = the mapping-definition outputs;
- candidate metadata records = the same exact `track_id` set;
- embedded snapshot digest = reproduced canonical snapshot digest;
- embedded source-neutral receipt, adapter, capability, snapshot, and metadata
  lineage = wrapper lineage; and
- embedded source-neutral result digest and wrapper digest = independently
  reproduced canonical bytes.

Missing content, extra content, unsupported version, stale or non-applicable
principal, path-only input, filename-only input, byte substitution, definition
substitution, digest mismatch, receipt substitution, reordered membership,
deduplication, dangling reference, cross-library persistent-ID substitution,
mapping substitution, snapshot substitution, metadata substitution, result
substitution, or unreproducible canonical output produces no authoritative
wrapper. Failure cannot fall back to schema `1.0` object validity alone.

## Representative conformance record

The genuine representative export supplied for this freeze has:

- SHA-256
  `5448499004a619596b275f1fcf7eb1c8341e68c890b2b000a97b1487b83ec20e`;
- exact byte length `79886`;
- application version `12.13.10.3`;
- library persistent ID `9C9E2747D29AB9A8`;
- one ordinary playlist with persistent ID `85C5D764BE8FCEFF`;
- 59 top-level tracks and 59 playlist membership references;
- 59 unique source-scoped identities;
- positive source durations from `34690` through `655177` milliseconds;
- exact `Track Type` `File` for all 59 tracks;
- exact `Kind` `MPEG audio file` for all 59 tracks; and
- absolute `file://localhost/` Windows-drive locations for all 59 tracks.

All membership references resolve exactly once, every top-level track is
represented exactly once, and array order is reproducible. The canonical JSON
array of 59 ordered source-scoped identity strings has SHA-256
`65bb163e43f253597803013a959cf13a4d9c2a57ead7eb3d2f2f9cab58d5494d`.
The canonical JSON array of 59
floor-converted duration seconds in the same order has SHA-256
`475837e755bd4c3d455b55cffabd5bf4802720af7d5f50186c6d88f59e2112e4`.

These values are conformance evidence for this contract. The representative
file is not added to the repository and its content does not become a generic
test fixture or authorization for other profiles.

### Conceptual fail-closed cases

| Mutation or substitution | Required result |
| --- | --- |
| same filename or path, different bytes | reject before profile authority |
| same bytes, unverified caller-created receipt | reject intake authority |
| valid plist with duplicate dictionary key | reject profile conformance |
| external DTD or entity resolution attempted | reject verifier conformance |
| second playlist or system/distinguished marker | reject source profile |
| duplicate or dangling playlist `Track ID` | reject complete acquisition |
| unreferenced top-level track | reject complete acquisition |
| lowercase or malformed persistent ID | reject identity authority |
| missing/zero/negative `Total Time` | reject track and complete profile |
| rounding `Total Time / 1000` to nearest | reject mapping reproduction |
| media URI opened or inspected | reject producer/verifier conformance |
| album or title used as release identity | reject metadata reproduction |
| `Show Content Ratings` used as Explicit | reject capability reproduction |
| schema-1 result without verified wrapper | withhold source-specific acquisition authority |

## Stop point

This freeze changes documentation and authority only. It authorizes no runtime
file picker, intake producer, XML parser, plist model, source adapter, capability
producer, acquisition wrapper, verifier, persistence, UI, API, provider plugin,
framework, orchestration, playback, playlist writing, constraint-definition
work, research, Workbench, Study, scoring, sequencing, construction, or media
access.

The implementation blocker is the absence of the sole governed intake
producer/verifier, source-specific parser and mapper, immutable wrapper schemas,
implementation-conformance authority for the existing Source Receipt edge, and
tests that reproduce this contract without storing or fabricating production
intake authority.

# Penny Local iTunes Windows XML Source-Relative Genre Evidence v1

- **Status:** frozen authority contract; implementation governed below
- **Evidence definition:**
  `pne.source-evidence-definition.itunes-windows-xml-track-genre/1.0`
- **Supported parent:** governed iTunes Windows XML acquisition `1.1` only
- **Boundary:** exact Source Receipt occurrence only

## Sole authority claim

For every ordered track in one verified acquisition occurrence, this authority
establishes exactly one of these source-relative facts:

- **PRESENT:** In exact Source Receipt R, the track corresponding to iTunes
  library L and Track Persistent ID T contained the exact decoded plist
  `Genre` string G.
- **ABSENT:** In exact Source Receipt R, that track dictionary did not contain a
  `Genre` field.

ABSENT does not mean that the recording is genreless, that its real genre is
unknown, that classification failed, or that the track is ineligible for a
requested genre. No empty string, default, inference, or placeholder represents
absence.

## Frozen definition

Canonical content is compact UTF-8 JSON in the displayed field order, with no
trailing newline:

```json
{"schema_version":"1.0","definition_kind":"itunes_windows_xml_track_genre_evidence","evidence_definition_id":"pne.source-evidence-definition.itunes-windows-xml-track-genre","evidence_definition_version":"1.0","supported_acquisition_authority":"pne.acquisition-authority.itunes-windows-xml-single-playlist/1.1","supported_acquisition_authority_sha256":"6a07222c5c65c68e72e29b3e306459f1c6b84f7557aa106ba4c6906171871170","acquisition_wrapper_schema":"PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.1","source_definition":"pne.source-definition.itunes-windows-xml-single-playlist/1.1","source_definition_sha256":"1e14e22641d0d9dc65b0cfe06544e0afc70111a15bd69ee9dc634d7b2dbe1fa9","source_field":"Genre","observation_states":[{"state":"PRESENT","rule":"FIELD_PRESENT_WITH_EXACT_DECODED_NONBLANK_PLIST_STRING"},{"state":"ABSENT","rule":"FIELD_KEY_ABSENT_AND_SOURCE_GENRE_VALUE_FIELD_OMITTED"}],"coverage":"EXACTLY_ONE_OBSERVATION_PER_PARENT_ORDERED_TRACK_IN_PARENT_ORDER","correspondence":["PARENT_ACQUISITION_ARTIFACT_AND_DIGEST","ACQUISITION_SCHEMA_VERSION","SOURCE_RECEIPT_ID_AND_ARTIFACT_DIGEST","RECEIPT_ITEM_ID","SELECTED_BYTE_SHA256","SOURCE_DEFINITION_ID_VERSION_AND_DIGEST","GENRE_EVIDENCE_DEFINITION_ID_VERSION_AND_DIGEST","LIBRARY_PERSISTENT_ID","TRACK_PERSISTENT_ID","SOURCE_SCOPED_TRACK_ID","PARENT_ORDINAL","RECEIPT_LOCAL_TRACK_ID","LITERAL_SOURCE_FIELD"],"reconstruction":"EXACT_BOUND_SOURCE_RECEIPT_BYTES_USING_FROZEN_SOURCE_PROFILE_1.1","occurrence_scope":"EXACT_SOURCE_RECEIPT_ONLY_NO_CROSS_RECEIPT_MERGE","normalization_performed":false,"nonclaims":["APPLE_AUTHORSHIP","OBJECTIVE_GENRE_TRUTH","CURRENT_LIBRARY_STATE","RECORDING_IDENTITY_BEYOND_SOURCE_SCOPED_IDENTITY","RELEASE_VERSION_IDENTITY","SEMANTIC_EQUIVALENCE_OF_STRINGS","GENRE_FAMILY_MEMBERSHIP","REQUESTED_GENRE_ELIGIBILITY","ARTIST_GENRE","ALBUM_GENRE","CROSS_SOURCE_CORRESPONDENCE","MAESTRO_IDENTITY","CANDIDATE_FORMATION_ELIGIBILITY","PLAYLIST_FILTERING_SCORING_OR_RECOMMENDATION_AUTHORITY"],"producer":"pne.producer.itunes-windows-xml-track-genre-evidence/1.0","verifier":"pne.verifier.itunes-windows-xml-track-genre-evidence/1.0","artifact_schema":"ITunesWindowsXMLSourceGenreEvidenceArtifact/1.0","canonicalization_profile":"pne.canonical-json.utf8-schema-order/1.0"}
```

Canonical byte length: `2248`.

Canonical SHA-256:
`094f72c9ed2037578f2e17cf19d47af89771ecb52391f7c06721adb01ea37e5a`.

Changing any byte or semantic rule requires definition succession. Matching
only the ID or version is not authority.

## Closed observation schemas

The artifact contains a discriminated union. Both observation forms bind:

- parent acquisition artifact ID and canonical SHA-256;
- acquisition schema version `1.1`;
- Source Receipt ID and artifact SHA-256;
- receipt item ID `item-000001` and selected-byte SHA-256;
- source-definition ID, version `1.1`, and SHA-256;
- this evidence-definition ID, version, and SHA-256;
- Library Persistent ID and Track Persistent ID;
- existing source-scoped track ID;
- positive parent ordinal and positive receipt-local Track ID; and
- literal source field `Genre`.

`ITunesWindowsXMLGenrePresentObservation/1.0` additionally contains state
`PRESENT` and required `source_genre_value`. The value is the exact decoded,
nonblank plist string. It is never trimmed, case-folded, Unicode-normalized,
tokenized, aliased, canonicalized, or interpreted.

`ITunesWindowsXMLGenreAbsentObservation/1.0` contains state `ABSENT` and has no
`source_genre_value` field. A null or empty value is not an alternative absence
encoding. Extra fields are forbidden in both forms.

## Complete occurrence artifact

`ITunesWindowsXMLSourceGenreEvidenceArtifact/1.0` contains the complete parent
`PennyLocalITunesXMLAcquisitionAuthorityArtifact/1.1`, its canonical digest,
the complete ordered observation tuple, exact observation count, frozen
definition binding, producer/verifier identities, explicit false nonclaim
fields, `normalization_performed=false`, and its canonical digest.

For a parent with N ordered tracks, the artifact has exactly N observations in
the same order. Every parent track appears once. No absent-Genre track may be
omitted. Duplicate, missing, reordered, substituted, or mismatched observations
fail closed.

The artifact ID is deterministically derived from the exact parent acquisition
digest and evidence-definition digest under domain
`pne.itunes-windows-xml-track-genre-evidence/1.0`. Its canonical digest binds
the complete artifact content.

## Production and verification authority

The sole producer first requires the supplied parent to verify through the
governed occurrence-local acquisition `1.1` verifier. It then reconstructs the
profile from the exact receipt bytes and emits one observation for every parent
ordered track.

The independent genre-evidence verifier does not trust supplied state, value,
order, count, correspondence, receipt identity, selected-byte digest,
definition binding, or parent binding. It verifies the parent occurrence,
reconstructs the complete expected artifact from receipt-recovered bytes, and
compares canonical content exactly. Direct construction of valid-looking schema
objects does not establish production authority.

Different receipts remain different occurrences even when they contain the
same source-scoped track identity. PRESENT values that differ across receipts,
or PRESENT in one and ABSENT in another, are retained independently. No merge,
overwrite, latest-value selection, semantic conflict, genre-change inference,
or current-state claim is authorized.

## Explicit nonclaims

This definition and artifact do not establish Apple authorship, objective genre
truth, current library state, identity beyond the existing source-scoped track
identity, release/version identity, semantic equivalence, genre-family
membership, requested-genre eligibility, artist genre, album genre,
cross-source correspondence, Maestro identity, Candidate Formation eligibility,
or playlist filtering, scoring, recommendation, or ranking authority.

The acquisition mapping definition, `SourceNeutralAcquisitionResult/1.0`,
Candidate Formation, Track Evidence, Candidate Readiness, research-store
schemas, and playlist construction remain unchanged.

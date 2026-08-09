# Maestro Historical Source Recovery Ledger

This ledger records attempts to recover primary evidence for historical
Maestro/Alexa playlist-generation experiments. It is an audit trail, not an
experiment dataset. Conversation summaries, remembered commentary, and
synthetic fixtures do not qualify as primary evidence for ingestion.

## Current governed state

- Trustworthy historical Maestro imports: **9** (`REC-CHAT-007`,
  `REC-UNCERTAIN-001`, `sticky-sweet-forgotten-treasures`, and
  `after-the-rain-falls-softly`, `overkill-on-the-half-acre`, and
  `stuck-in-your-head`, `exit-14-emergency-warning-broadcast`, plus
  `good-music-essentials`, plus `sunny-day-grooves`)
- Remaining historical candidates: **excluded pending deterministic
  session-to-file correlation**
- Primary evidence availability: **confirmed in File Library**
- Confirmed Maestro provenance: **9 historical experiments**
- Confirmed generation failures or refusals: **0**
- Synthetic fixtures: **permanently excluded**
- Current research schema: **version 3**; no schema change was required for the
  REC-UNCERTAIN-001 recovery
- Database ingestion performed: **9 historical experiments and 2 separately
  governed current persisted artifact**

## Recovery attempts

| Attempt | Source | Result | Notes |
|---|---|---|---|
| 2026-08-08 | File Library keyword search | No primary evidence | Maestro/Alexa screenshot files were not indexed or found. Search returned design documents, architectural notes, spreadsheets, and other text artifacts only. |
| 2026-08-08 | File Library recent-image review | Primary evidence located; correlation incomplete | Image evidence exists in File Library. No screenshot has yet been deterministically assigned to an experiment session or approved for transcription or ingestion. |
| 2026-08-08 | Conversation-side session timeline reconstruction | Completed as discovery evidence | Twelve enumerated temporary recovery candidates and one multi-session source container were identified from inspectable conversation text, repository material, and thread-index metadata. See `conversation_recovery_manifest.md`. No candidate was promoted to research evidence. |
| 2026-08-08 | REC-CHAT-007 source correlation | Primary captures not recovered from accessible sources | The stable ChatGPT thread `6a75eb70-0558-83ea-9b14-0d527ac392f5` and its 2026-08-07 10:28:18–10:34:51 EDT activity window were used only as discovery aids. Direct thread-history access could not read ChatGPT-kind content. The exact ChatGPT URL required an authenticated session unavailable in the in-app browser, and no connected authenticated desktop browser was available. A read-only search of local Codex attachments, Pictures, Downloads, and OneDrive Pictures found no matching image files or exact attachment references in a bounded 09:45–11:15 EDT window or by `toaster`/`dread` filename. REC-CHAT-007 remains a discovery lead and is not eligible for ingestion. |
| 2026-08-08 | REC-CHAT-007 manual primary-evidence recovery | Primary evidence reported recovered; partial tracklist; visual transcription pending | This later recovery supersedes the earlier `INSUFFICIENT_EVIDENCE` result without deleting it. The user identified five original, non-regenerated screenshots recovered from the historical ChatGPT conversation and explicitly stated that the playlist was not saved. The handoff establishes Maestro Beta, generated title `Brief Existential Dread of Appliances`, generated description `Contemplative electronic ambience for mechanical self-awareness moments`, and that the final capture does not establish the terminal playlist boundary. The five named files were not attached or locally accessible in the recovery workspace during this pass, so their ordered track text and overlap could not be independently inspected or transcribed. State: `PRIMARY_EVIDENCE_RECOVERED / PARTIAL_TRACKLIST`; not eligible for SQLite ingestion under schema version 1. |
| 2026-08-08 | REC-CHAT-007 direct visual evidence review | Primary evidence inspected; 38 unique visible playlist items; ingestion blocked | Five directly accessible historical captures were visually inspected without modifying them. Conversation-primary evidence establishes the exact submitted prompt, and user clarification establishes `saved = false`. The first five playlist positions are anchored by the first capture. Later continuity is proven by overlaps on `Wait`, `Minor Cause`, and `In The Waiting Line`, but no overlap proves adjacency between capture 1 (`Near Light`) and capture 2 (`Says`). The fifth capture ends with partially visible `Paint It Black` / `wednesday addams` and does not show the terminal playlist boundary. Schema version 1 cannot preserve the positional gap, partial terminal coverage, or unknown historical generation time without semantic loss, so no JSON or SQLite record was created. |
| 2026-08-08 | REC-UNCERTAIN-001 direct visual evidence recovery | Primary evidence inspected; complete 37-placement historical playlist supported | Seven historical Maestro captures establish the generated title, description, playlist start, visible terminal boundary, and displayed track strings. The exact prompt and ordered transcription are separately user-attested in the recovery handoff. All seven sources are retained, including byte-identical captures 2 and 3. `Save Playlist` supports only the visible unsaved state at capture time; eventual saved status remains unknown. `Momma Song` / `Benson Boone` player UI is excluded. Governed source artifact: `experiments/rec-uncertain-001.json`. |
| 2026-08-08 | Sticky Sweet Forgotten Treasures direct capture ingestion | Primary evidence inspected; complete 30-placement Maestro playlist supported | Five newly supplied Maestro Beta captures establish the generated title, description, playlist start, overlapping ordered continuity, displayed track strings, and visible endpoint after `One Way Or Another (Remastered 2001)` / `Blondie`. The exact prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `11:13` clock is not treated as generated time. Governed source artifact: `experiments/sticky-sweet-forgotten-treasures.json`. |
| 2026-08-08 | After the Rain Falls Softly direct capture ingestion | Primary evidence inspected; complete 36-placement Maestro playlist supported | Five newly supplied Maestro Beta captures establish the generated title, exact `petrichor` description, playlist start, overlapping ordered continuity, displayed track strings, and visible endpoint after `Before You Go` / `Lewis Capaldi`. The exact cross-modal prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `11:26` clock is not treated as generated time. Governed source artifact: `experiments/after-the-rain-falls-softly.json`. |
| 2026-08-09 | Raccoon Knocking Over Trash Cans current-artifact capture | Current persisted artifact inspected; complete 39-placement playlist supported | Six Amazon Music Maestro captures establish the displayed title, description, `Show Playlist` persistence state, playlist start, overlapping ordered continuity, displayed track strings, and visible endpoint after `Freak Scene [Explicit]` / `Dinosaur Jr.`. The user-attested prompt is not stored on the artifact because schema v3 has no artifact prompt field and no historical Experiment or correlation is justified. The visible `6:37` clock is not treated as generation or save time. Governed source artifact: `artifacts/raccoon-knocking-over-trash-cans-current-amazon-music.json`. |
| 2026-08-09 | Overkill on the Half Acre creation-time capture | Historical generation inspected; complete 30-placement Maestro playlist supported | Five creation-time Maestro Beta captures establish the generated title, description, playlist start, overlapping ordered continuity, raw displayed track strings, and visible endpoint after `Pumped Up Kicks` / `Foster The People`. The exact riding-mower prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `10:01`–`10:02` clocks are not treated as generated time. A user-supplied narrative-drift interpretation is stored separately as `HUMAN_ASSESSMENT`. Governed source artifact: `experiments/overkill-on-the-half-acre.json`. |
| 2026-08-09 | Stuck in Your Head creation-time capture | Historical generation inspected; complete 40-placement Maestro playlist supported | Six creation-time Maestro Beta captures establish the generated title, description, playlist start, overlapping ordered continuity, raw displayed track strings, and visible endpoint after `Blinding Lights` / `The Weeknd`. The exact Earworms prompt and generation context are separately user-attested and not screenshot-derived. `Show Playlist` is preserved only as captured UI state; historical save action and later edit status remain unknown. The visible `10:46` clock is not treated as generated time. User-supplied semantic-displacement and bounded HandClap-absence observations are stored as `HUMAN_ASSESSMENT`. Governed source artifact: `experiments/stuck-in-your-head.json`. |
| 2026-08-09 | Exit 14 Emergency Warning Broadcast creation-time capture | Historical generation inspected; complete 35-placement Maestro playlist supported | Six original Maestro Beta captures establish the generated title, description, playlist start, overlapping ordered continuity, raw displayed track strings, and visible endpoint after `Hey Man Nice Shot` / `Filter`. The exact sentient-road-sign prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `12:58`–`12:59` clocks are not treated as generated time. Five user-supplied interpretation, construction, drift, persistence, local-relevance, and research-significance assessments are stored separately as `HUMAN_ASSESSMENT`. The accidentally generated Maestro mockup is explicitly excluded as fabricated non-evidence. Governed source artifact: `experiments/exit-14-emergency-warning-broadcast.json`. |
| 2026-08-09 | Good Music Essentials creation-time capture | Historical generation inspected; complete 40-placement Maestro playlist supported | Seven original Maestro Beta captures establish the generated title, exact personalization language in the description, playlist start, overlapping ordered continuity, raw displayed track strings, and visible endpoint after `Closer` / `The Chainsmokers, Halsey`. The exact `play good music` prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `4:23` clock is not treated as generated time. User-supplied weak-prompt baseline, affinity, global-confidence, sequence-coherence, drift-baseline, and personalization-boundary interpretations are stored separately as `HUMAN_ASSESSMENT`. Persistent now-playing UI is excluded. Governed source artifact: `experiments/good-music-essentials.json`. |
| 2026-08-09 | Sunny Day Grooves creation-time capture | Historical generation inspected; complete 49-placement Maestro playlist supported | Eight original Maestro Beta captures establish the generated title, description, playlist start, overlapping ordered continuity, raw displayed track strings, and visible endpoint after `Thunder` / `Imagine Dragons`. The exact `play something upbeat` prompt is separately user-attested and not screenshot-derived. `Save Playlist` supports only the visible captured UI state; eventual saved status remains unknown. The visible `4:29` clock is not treated as generated time. User-supplied affective-baseline, mainstream-attractor, qualitative user-characterization, candidate-domain, sequence, and cross-baseline recurrence interpretations are stored separately as `HUMAN_ASSESSMENT`. The truncated `Golden` artist display is preserved without canonical identity; persistent now-playing UI is excluded. Governed source artifact: `experiments/sunny-day-grooves.json`. |
| Pending | Historical ChatGPT conversation source correlation | Not started | Use the accepted candidate IDs and conversation windows to locate original uploads. Do not rely on conversational summaries as primary evidence. |
| Pending | Phone Photos | Not started | Review screenshots captured approximately August 1–8. Preserve original files and metadata. |
| Pending | Cloud photo backup | Not started | Review iCloud, Google Photos, OneDrive, or other synchronized photo storage for the same period. |

## Evidence handling rules

- Preserve recovered source files unchanged, including original filenames when
  available.
- Do not treat File Library presence alone as proof that a file belongs to a
  particular experiment session.
- Record where each source was recovered and which candidate experiment it may
  support before transcription or ingestion.
- Do not infer missing prompts, generated metadata, track positions, tracks,
  dates, saved state, refusals, or system behavior.
- Do not treat an unseen tracklist as an empty tracklist.
- Do not treat human explanation of system behavior as direct observation.
- Do not ingest a candidate until its source-to-record mapping and evidence
  completeness have been reviewed.
- Treat conversation-side candidate IDs as temporary recovery identifiers only,
  never as experiment IDs.
- Do not promote a conversation discovery lead into the SQLite research store
  without correlated primary evidence.
- Record an unsuccessful recovery attempt as a valid result rather than
  repeating it without new evidence or a materially different search method.

The ignored local research database is rebuildable from governed JSON source
artifacts. Candidates not represented by those reviewed artifacts remain
excluded until primary evidence is deterministically correlated and approved.

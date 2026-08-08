# Maestro Historical Source Recovery Ledger

This ledger records attempts to recover primary evidence for historical
Maestro/Alexa playlist-generation experiments. It is an audit trail, not an
experiment dataset. Conversation summaries, remembered commentary, and
synthetic fixtures do not qualify as primary evidence for ingestion.

## Current governed state

- Trustworthy Maestro imports: **0**
- Historical candidates: **excluded pending deterministic session-to-file correlation**
- Primary evidence availability: **confirmed in File Library**
- Confirmed Maestro provenance: **0**
- Confirmed generation failures or refusals: **0**
- Synthetic fixtures: **permanently excluded**
- Schema changes justified by recovered evidence: **none**
- Database ingestion performed: **none**

## Recovery attempts

| Attempt | Source | Result | Notes |
|---|---|---|---|
| 2026-08-08 | File Library keyword search | No primary evidence | Maestro/Alexa screenshot files were not indexed or found. Search returned design documents, architectural notes, spreadsheets, and other text artifacts only. |
| 2026-08-08 | File Library recent-image review | Primary evidence located; correlation incomplete | Image evidence exists in File Library. No screenshot has yet been deterministically assigned to an experiment session or approved for transcription or ingestion. |
| 2026-08-08 | Conversation-side session timeline reconstruction | Completed as discovery evidence | Twelve enumerated temporary recovery candidates and one multi-session source container were identified from inspectable conversation text, repository material, and thread-index metadata. See `conversation_recovery_manifest.md`. No candidate was promoted to research evidence. |
| 2026-08-08 | REC-CHAT-007 source correlation | Primary captures not recovered from accessible sources | The stable ChatGPT thread `6a75eb70-0558-83ea-9b14-0d527ac392f5` and its 2026-08-07 10:28:18–10:34:51 EDT activity window were used only as discovery aids. Direct thread-history access could not read ChatGPT-kind content. The exact ChatGPT URL required an authenticated session unavailable in the in-app browser, and no connected authenticated desktop browser was available. A read-only search of local Codex attachments, Pictures, Downloads, and OneDrive Pictures found no matching image files or exact attachment references in a bounded 09:45–11:15 EDT window or by `toaster`/`dread` filename. REC-CHAT-007 remains a discovery lead and is not eligible for ingestion. |
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

An empty research database remains the authoritative state until primary
evidence has been deterministically correlated to experiment sessions and the
resulting source-to-record mappings support one or more reviewed records.

# Maestro/Alexa Conversation Recovery Manifest

## Status and authority boundary

This manifest is a conversation-side discovery and source-correlation artifact.
Its entries are discovery leads, not ingestible experiment records. It does not
establish authoritative playlist evidence, Maestro provenance, or permission to
create research-store records.

- `SUCCEEDED_INDICATED` means only that conversation evidence suggests an
  output existed.
- Thread titles are not prompts unless independently proven.
- Conversation activity windows are not generation timestamps.
- No screenshot counts, saved states, refusal messages, complete playlist
  metadata, or exact generation timestamps were recovered.
- No candidate may be promoted into the SQLite research store without primary
  evidence.
- Candidate IDs are neutral temporary recovery identifiers and must not become
  experiment IDs.
- `DISCOVERY_LEAD` is not a research-store schema state. Recovery and discovery
  metadata remain outside the evidence database.

Two forms of conversation evidence were available:

1. Inspectable Codex turns containing user-authored text, with stable thread,
   turn, item, and message timestamps.
2. ChatGPT thread-index metadata containing stable thread IDs, titles, and
   activity windows. ChatGPT-kind thread content was not readable through the
   available thread-history interface, so titles remain discovery fragments and
   activity windows remain conversation windows.

All reported times are Eastern Daylight Time.

## Chronologically bounded by ChatGPT thread metadata

| candidate_id | session_date | time_start | time_end | time_precision | prompt_text | prompt_completeness | source_system | generation_state | user_stated_saved | referenced_screenshot_count | conversation_source | recovery_priority | discovery_notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REC-CHAT-001 | 2026-08-01 | 04:33:20 | 05:16:57 | `CONVERSATION_THREAD_WINDOW` | `4am Work Call Woes` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a6daf3d-7ff0-83ea-a147-3611525e0ad5` | focused-work | The title suggests a work-context discussion. It does not establish an exact prompt or generation. |
| REC-CHAT-002 | 2026-08-01 | 14:58:40 | 14:58:48 | `CONVERSATION_THREAD_WINDOW` | `Playlist Vibe Analysis` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a6e41de-d760-83ea-abad-cdc9837df7b9` | narrative-transition | Could be analysis rather than generation. Preserve as a discovery lead only. |
| REC-CHAT-003 | 2026-08-01 to 2026-08-02 | 19:48:58 | 16:04:31 next day | `MULTIDAY_THREAD_WINDOW` | `Mood Shifting Playlist Tips` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a6e85c6-74a8-83ea-aeb3-987d36d7d66d` | narrative-transition | May contain transition or mood-progression material. The thread span must not be treated as one generation duration. |
| REC-CHAT-004 | 2026-08-04 | 12:38:00 | 12:46:42 | `CONVERSATION_THREAD_WINDOW` | `Errands and Easy Vibes` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a721548-7e2c-83ea-920a-e9cef9f0ed0b` | general-session | Likely useful for locating a corresponding upload cluster, but the title alone proves no generation. |
| REC-CHAT-005 | 2026-08-04 | 14:07:28 | 14:11:02 | `CONVERSATION_THREAD_WINDOW` | `Soundtrack for Focused Work` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a722a12-0dc4-83ea-9afb-ea8849f35821` | focused-work | Highest-priority focused-work correlation lead. Exact prompt and system remain unknown. |
| REC-CHAT-006 | 2026-08-06 | 20:07:03 | 20:08:48 | `CONVERSATION_THREAD_WINDOW` | `Color-coded chaos` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a75219b-e314-83ea-b8ba-da12c56cae92` | unusual-metaphor/sensory | Strong discovery phrase, but not proven to be the submitted prompt. |
| REC-CHAT-007 | 2026-08-07 | 10:28:18 | 10:34:51 | `CONVERSATION_THREAD_WINDOW` | `Toaster existential dread music` | `THREAD_TITLE_ONLY_INCOMPLETE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | ChatGPT `6a75eb70-0558-83ea-9b14-0d527ac392f5` | unusual-metaphor/sensory | Strong screenshot-correlation lead. Generation and interface are not established by the index. |

## Date-only sessions supported by the August 1 journal entry

These three candidates may overlap with the ChatGPT threads above or with the
long-running Amazon Music conversation. No identity merge is authorized.

| candidate_id | session_date | time_start | time_end | time_precision | prompt_text | prompt_completeness | source_system | generation_state | user_stated_saved | referenced_screenshot_count | conversation_source | recovery_priority | discovery_notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REC-JOURNAL-001 | 2026-08-01 | `UNKNOWN` | `UNKNOWN` | `DATE_ONLY_FROM_DAILY_JOURNAL` | `1960–Today` | `QUOTED_FRAGMENT_INCOMPLETE` | `Alexa` | `SUCCEEDED_INDICATED` | `UNKNOWN` | `UNKNOWN` | Codex `019fbd83-514d-75c2-9a99-901c7ecc5488`; turn `019fc049-61a5-7083-ba8b-bf6fe2be7089`; item `item-43`; repository `docs/design-journal.md:210` | pool/Peach Festival | The user wrote that Alexa “performed reasonably well.” `1960–Today` appears in the discussion but is not explicitly established as the complete submitted prompt. Strengths and weaknesses are human assessments. |
| REC-JOURNAL-002 | 2026-08-01 | `UNKNOWN` | `UNKNOWN` | `DATE_ONLY_FROM_DAILY_JOURNAL` | `Peachy road trip` | `QUOTED_FRAGMENT_INCOMPLETE` | `Alexa` | `SUCCEEDED_INDICATED` | `UNKNOWN` | `UNKNOWN` | Codex `019fbd83-514d-75c2-9a99-901c7ecc5488`; turn `019fc049-61a5-7083-ba8b-bf6fe2be7089`; item `item-43`; repository `docs/design-journal.md:235` | pool/Peach Festival | User commentary says Alexa interpreted the phrase literally. Missing locality, outdoors, summer, orchard, Americana, and regional influence are human assessments, not direct output facts. |
| REC-JOURNAL-003 | 2026-08-01 | `UNKNOWN` | `UNKNOWN` | `DATE_ONLY_FROM_DAILY_JOURNAL` | `Unknown threat soundtrack` | `SECTION_LABEL_OR_FRAGMENT_INCOMPLETE` | `Alexa` | `SUCCEEDED_INDICATED` | `UNKNOWN` | `UNKNOWN` | Codex `019fbd83-514d-75c2-9a99-901c7ecc5488`; turn `019fc049-61a5-7083-ba8b-bf6fe2be7089`; item `item-43`; repository `docs/design-journal.md:257` | unknown-threat, narrative-transition | The user called it an experiment and said Alexa chose psychological tension instead of horror music. That characterization is human assessment; no exact output or full prompt survives. |

## Chronology-uncertain quoted prompt candidates

The conversation timestamp establishes when these prompts were discussed, not
when—or whether—they were submitted.

| candidate_id | session_date | time_start | time_end | time_precision | prompt_text | prompt_completeness | source_system | generation_state | user_stated_saved | referenced_screenshot_count | conversation_source | recovery_priority | discovery_notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REC-UNCERTAIN-001 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `MENTIONED_2026-08-06_08:49:33_EDT` | `Songs that taste like neon pink bubblegum, broken glass, and warm cardboard.` | `VERBATIM_QUOTED_EXAMPLE` | `Maestro` contextually indicated | `SUCCEEDED_INDICATED` | `UNKNOWN` | `UNKNOWN` | Codex `019fbd83-514d-75c2-9a99-901c7ecc5488`; turn `019fd71f-3031-70c3-9e83-a8d7bab3933c`; item `item-613` | unusual-metaphor/sensory, focused-work | The user framed Maestro as a research assistant and gave this as a successful-prompt example whose result was assessed as “Excellent work music.” The discussion does not establish the execution date or exact interface. |
| REC-UNCERTAIN-002 | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `MENTIONED_2026-08-06_08:49:33_EDT` | `I need to focus on deep technical work. Give me something intelligent but not deep.` | `VERBATIM_QUOTED_EXAMPLE` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` | Codex `019fbd83-514d-75c2-9a99-901c7ecc5488`; turn `019fd71f-3031-70c3-9e83-a8d7bab3933c`; item `item-613` | focused-work | Presented as a contrasting prompt example. The conversation does not say it was submitted, generated, saved, or captured. Keep separate from REC-CHAT-005. |

## Multi-session source container

| source | activity_window | status | notes |
|---|---|---|---|
| ChatGPT `6a6aac64-2a80-83ea-896d-84244065976c`, “Amazon Music Playlist Creation” | 2026-07-29 21:45:06 through 2026-08-08 17:48:39 EDT | Multi-session source container | This thread may contain several sessions and original upload references. It must not be ingested as one experiment. Conversation content was not readable through the available thread-history interface. |

## Explicitly unsupported families and fields

- Refusals or safety-boundary tests: no inspectable conversation evidence of an
  actual Maestro/Alexa refusal, exact refusal prompt, or displayed message.
- HandClap investigation: no inspectable conversation hit recovered.
- Pumped Up Kicks investigation: no inspectable conversation hit recovered.
- Screenshot counts: undetermined for every candidate.
- Saved status: no user-authored statement recovered for any candidate.
- Exact generation timestamps: none.
- Playlist titles, descriptions, tracks, artists, order, versions, or remasters:
  deliberately not reconstructed.
- Sleep experiment: the journal says there was a realization “after reviewing
  Alexa,” but it does not isolate a discrete prompt/session strongly enough for
  a candidate row.
- Objective Safety material: architectural discussion only; it does not
  establish a refusal test session.

## Correlation cautions

- REC-CHAT-005 and REC-UNCERTAIN-002 may relate to the same focused-work family,
  but conversation evidence does not authorize merging them.
- REC-JOURNAL-001 through REC-JOURNAL-003 may reside inside the long-running
  Amazon Music conversation, but this is unconfirmed.
- Thread titles may be automatically generated summaries rather than user
  prompts.
- A thread activity window may include analysis after generation, multiple
  generations, or no generation at all.
- “Alexa” establishes the named interface in the journal, but not whether
  Maestro Beta produced the underlying playlist.
- `SUCCEEDED_INDICATED` means only that the conversation describes an output as
  having existed; it is not authoritative playlist evidence.

## Next authorized recovery stage

The next legitimate work is source correlation, not ingestion:

```text
conversation candidate and time window
    -> source upload cluster
    -> visual continuity
    -> authoritative experiment evidence
```

Potential recovery sources include original ChatGPT conversation attachments,
phone or local image folders, and cloud photo backups. Correlation must preserve
source files and establish traceable session-to-file mappings before any
candidate can be considered for research-store ingestion.

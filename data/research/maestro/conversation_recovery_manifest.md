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

### REC-CHAT-007 primary-evidence recovery supplement

This supplement preserves the conversation-side row above unchanged and records
a later, independent source-recovery result. The earlier failed correlation
attempt remains in `source_recovery_ledger.md` as history.

- Recovery state: `PRIMARY_EVIDENCE_RECOVERED / PARTIAL_TRACKLIST`
- Historical source: original screenshots recovered manually from the ChatGPT
  conversation; not a regeneration and not captures from a saved playlist
- Exact user-authored prompt: `An ambient electronic soundtrack for a toaster that has achieved a brief moment of existential dread.`
- Prompt evidence: conversation-primary evidence supplied by the user
- Source interface: `Maestro Beta`
- Generated playlist title: `Brief Existential Dread of Appliances`
- Generated description: `Contemplative electronic ambience for mechanical self-awareness moments`
- User-stated saved status: `false`
- Recovered screenshot count: `5`
- Unique visible playlist items: `38`
- First playlist position: captured
- Terminal playlist boundary: not captured
- Complete track count: `UNKNOWN`
- Generation date and time: `UNKNOWN`; the visible device clock and conversation
  activity window are not generation timestamps
- Visual track transcription: completed from the directly accessible images
- SQLite eligibility: blocked under schema version 1 because it has no governed
  completeness state for partial terminal coverage and cannot represent the
  unproven positional adjacency between the first and second captures; its
  non-null `created_at` default would also replace an unknown historical
  generation time with ingestion time

Original filenames, to be preserved unchanged:

1. `B33EE06F-21A8-4034-AFBE-970D6B5C8684.png`
2. `47661CC8-CC44-48F3-AF75-83F3814ACA28.png`
3. `2008D641-27B1-4F90-B1F4-6C0EE2AF49B8.png`
4. `C78A00D9-08E6-4B18-BC3D-AD94856E8B21.png`
5. `920F5F6A-9F51-4C60-A3E5-B52C6F58C60D.png`

The directly accessible attachment copies were named `1-Photo-1.jpg` through
`5-Photo-5.jpg`. No source image was cropped, renamed, modified, enhanced, or
copied into the repository.

### REC-CHAT-007 visible ordered track evidence

`observed_ordinal` records only the order of directly visible unique items
across the supplied screenshot sequence. Exact playlist positions 1–5 are
anchored by the first capture, which shows the start of the playlist body.
There is no visual overlap between the first capture (`Near Light`) and the
second (`Says`), so items after position 5 have `UNKNOWN` exact playlist
positions and may have unseen intervening tracks.

| observed_ordinal | exact_playlist_position | displayed_title | displayed_artist | evidence note |
|---:|---:|---|---|---|
| 1 | 1 | `#3` | `Aphex Twin` | Fully visible in capture 1. |
| 2 | 2 | `An Ending (Ascent) (Remastered 2005)` | `Brian Eno` | Fully visible in capture 1. |
| 3 | 3 | `Roygbiv` | `Boards Of Canada` | Fully visible in capture 1. |
| 4 | 4 | `Abandon Window (Remaster 2023)` | `Jon Hopkins` | Fully visible in capture 1. |
| 5 | 5 | `Near Light` | `Ólafur Arnalds` | Fully visible in capture 1. |
| 6 | `UNKNOWN` | `Says` | `Nils Frahm` | Fully visible in capture 2; adjacency to position 5 is not proven. |
| 7 | `UNKNOWN` | `A Walk` | `Tycho` | Fully visible in capture 2. |
| 8 | `UNKNOWN` | `Porcelain` | `Moby` | Fully visible in capture 2. |
| 9 | `UNKNOWN` | `Little Fluffy Clouds` | `The Orb` | Fully visible in capture 2. |
| 10 | `UNKNOWN` | `Kerala` | `Bonobo` | Fully visible in capture 2. |
| 11 | `UNKNOWN` | `Angel Echoes` | `Four Tet` | Fully visible in capture 2. |
| 12 | `UNKNOWN` | `Can't Do Without You` | `Caribou` | Fully visible in capture 2. |
| 13 | `UNKNOWN` | `What Else Is There ?` | `Röyksopp` | Fully visible in capture 2; displayed space before `?` preserved. |
| 14 | `UNKNOWN` | `Wait` | `M83` | Partially visible in capture 2 and fully visible in capture 3; overlap establishes continuity. |
| 15 | `UNKNOWN` | `On My Own (2019 remaster)` | `Ulrich Schnauss` | Fully visible in capture 3. |
| 16 | `UNKNOWN` | `Mute Angels` | `Hammock` | Fully visible in capture 3. |
| 17 | `UNKNOWN` | `Halving The Compass` | `Helios` | Fully visible in capture 3. |
| 18 | `UNKNOWN` | `Lit` | `Kiasmos` | Fully visible in capture 3. |
| 19 | `UNKNOWN` | `Untravel` | `Rival Consoles` | Fully visible in capture 3. |
| 20 | `UNKNOWN` | `Silhouettes (I, II, III)` | `Floating Points` | Fully visible in capture 3. |
| 21 | `UNKNOWN` | `You` | `Gold Panda` | Fully visible in capture 3. |
| 22 | `UNKNOWN` | `Minor Cause` | `Emancipator` | Partially visible in capture 3 and fully visible in capture 4; overlap establishes continuity. |
| 23 | `UNKNOWN` | `Your Hand In Mine (Remastered)` | `Explosions In The Sky` | Fully visible in capture 4. |
| 24 | `UNKNOWN` | `Svefn-g-englar` | `Sigur Rós` | Fully visible in capture 4. |
| 25 | `UNKNOWN` | `Archangel` | `Burial` | Fully visible in capture 4. |
| 26 | `UNKNOWN` | `A New Error` | `Moderat` | Fully visible in capture 4. |
| 27 | `UNKNOWN` | `Goodbye (feat. Soap&Skin) [Theme from Dark, A Netflix Original Series]` | `Apparat, Soap&Skin` | Fully visible across wrapped display lines in capture 4. |
| 28 | `UNKNOWN` | `Moan (Trentemøller Dub Remix)` | `Trentemøller` | Fully visible in capture 4. |
| 29 | `UNKNOWN` | `Teardrop (Remastered 2019) [feat. Elizabeth Fraser]` | `Massive Attack, Elizabeth Fraser` | Fully visible across wrapped display lines in capture 4. |
| 30 | `UNKNOWN` | `In The Waiting Line` | `Zero 7, Sophie Barker` | Partially visible in capture 4 and fully visible in capture 5; overlap establishes continuity. |
| 31 | `UNKNOWN` | `La Femme D'argent` | `Air` | Fully visible in capture 5. |
| 32 | `UNKNOWN` | `Green Green Grass Of Tunnel` | `Múm` | Fully visible in capture 5. |
| 33 | `UNKNOWN` | `Alison` | `Slowdive` | Fully visible in capture 5. |
| 34 | `UNKNOWN` | `Cherry-coloured Funk` | `Cocteau Twins` | Fully visible in capture 5. |
| 35 | `UNKNOWN` | `Hearing Damage` | `Thom Yorke` | Fully visible in capture 5. |
| 36 | `UNKNOWN` | `Treefingers` | `Radiohead` | Fully visible in capture 5. |
| 37 | `UNKNOWN` | `Eutow` | `Autechre` | Fully visible in capture 5. |
| 38 | `UNKNOWN` | `Paint It Black` | `wednesday addams` | Final item is partially visible in capture 5; only the directly readable title and artist text are recorded. Content continues below the capture. |

The persistent bottom-player entry `Midnight City` — `M83` is excluded. It is
now-playing UI and does not independently appear in the playlist body within
the recovered captures.

### REC-CHAT-007 screenshot continuity

- Capture 1 ends with `Near Light`; capture 2 begins with `Says`. No shared item
  proves adjacency, so hidden intervening tracks remain possible.
- Capture 2 to capture 3 overlaps on `Wait` — `M83`.
- Capture 3 to capture 4 overlaps on `Minor Cause` — `Emancipator`.
- Capture 4 to capture 5 overlaps on `In The Waiting Line` —
  `Zero 7, Sophie Barker`.
- Capture 5 ends with a partially visible `Paint It Black` —
  `wednesday addams`, and the terminal playlist boundary is not shown.

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

### REC-UNCERTAIN-001 primary-evidence recovery supplement

This supplement preserves the discovery row above and records a later,
independent historical primary-evidence recovery.

- Recovery state: `PRIMARY_EVIDENCE_RECOVERED / COMPLETE_TRACKLIST`
- Exact submitted prompt: user-attested in the recovery conversation; not
  visible in the screenshots
- Source interface: `Amazon Music — Maestro Beta`
- Generated title: `Bubblegum Shards and Cardboard Dreams`
- Generated description: `Sweet pop chaos meets sharp edges and faded nostalgia`
- Recovered screenshot count: `7`; all sources are retained, including the
  byte-identical second and third supplied captures
- Visible playlist start: captured
- Visible playlist end: captured after `High Hopes` — `Yours Truly`
- Ordered placements: `37`
- Historical saved status: `UNKNOWN`; `Save Playlist` establishes only the
  visible state at the moment of the first capture
- Generation timestamp: `UNKNOWN`; visible clock values `7:32`–`7:33` are not
  treated as a generation time
- Persistent player UI: `Momma Song` — `Benson Boone` excluded
- Governed source artifact:
  `experiments/rec-uncertain-001.json`

Screenshot overlaps corroborate later sequence continuity. No shared visible
track bridges the transition from capture 1 to capture 2, so the exact ordered
transcription supplied by the user is separately identified as user-attested
support for that transition rather than screenshot-derived evidence.

## Multi-session source container

| source | activity_window | status | notes |
|---|---|---|---|
| ChatGPT `6a6aac64-2a80-83ea-896d-84244065976c`, “Amazon Music Playlist Creation” | 2026-07-29 21:45:06 through 2026-08-08 17:48:39 EDT | Multi-session source container | This thread may contain several sessions and original upload references. It must not be ingested as one experiment. Conversation content was not readable through the available thread-history interface. |

## Explicitly unsupported families and fields

- Refusals or safety-boundary tests: no inspectable conversation evidence of an
  actual Maestro/Alexa refusal, exact refusal prompt, or displayed message.
- HandClap investigation: no inspectable conversation hit recovered.
- Pumped Up Kicks investigation: no inspectable conversation hit recovered.
- Screenshot counts: undetermined for candidates without a primary-evidence
  recovery supplement.
- Saved status: unknown for candidates without independently supported evidence.
- Exact generation timestamps: none.
- Playlist titles, descriptions, tracks, artists, order, versions, or remasters:
  deliberately not reconstructed for discovery-only candidates; recovered
  supplements are governed separately by their cited primary evidence.
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

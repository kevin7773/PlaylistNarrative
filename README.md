# Playlist Narrative Engine

**Playlist Narrative Engine (Penny)** is a local-first, deterministic application
for designing intentional listening journeys. It separates durable taste data,
explicit evidence, context-specific journey planning, sequencing, and evaluation
into independently testable boundaries.

Penny does not optimize for engagement or generic recommendations. It models a
listener's objective and constructs intentional soundtracks that help accomplish
an experience. Music is treated as narrative rather than background content.

## Design Principles

Penny is built around several core principles:

- Objective before music.
- Evidence before inference.
- Soundtracks over playlists.
- Narrative over recommendation.
- Replayable deterministic artifacts.
- Taste belongs to the user.

## Current status

The deterministic core currently includes:

- SQLite artist catalog and persistent seven-category ratings
- approximately 100 calibration artists spanning eras and genres
- rating and re-rating with optional notes
- deterministic default exclusion rules
- validated Active Focus requests with deterministic three-phase energy arcs,
  exact duration, and discovery-budget allocation
- explainable role-aware track scoring and deterministic candidate selection
- state-relative sequential playlist construction with explicit compromises
- pure, immutable evaluation of complete and partial construction results
- closed-world artist questionnaire seeds derived only from serialized evidence
- objective-readiness assessment with fixed clarification prompts for missing
  evidence dimensions
- an Objective Safety Boundary design contract that evaluates intent before
  Journey Planning, plus immutable accepted and declined artifact schemas
- a CU-1 Crossing Understanding boundary that derives a directional crossing
  exclusively from exact EA-1 authenticated characteristics while preserving
  nonparticipating lived evidence and need lineage
- a CU-2 Curriculum Orientation boundary that applies three exact versioned
  rules from a canonical digest-bound registry without reading event labels,
  observation payloads, needs, prior candidates, or free text
- source-neutral track-evidence validation with deterministic, lossless
  validated/rejected partitioning
- a Candidate Formation CF-0 contract plus CF-1 immutable source-evidence
  schemas and a CF-2 deterministic service for reproducibly joining validated
  track, taste, familiarity, feature, and objective-context evidence into a
  complete formed/withheld partition
- CF-3 formed-only selector and constructor integration through an immutable,
  provenance-preserving authenticated pool view and traced ranking envelope
- automated tests across persistence, policy, planning, sequencing, evaluation,
  elicitation, objective assessment, evidence validation, and Candidate
  Formation source-evidence contracts

Objective Safety policy execution, CU-3 Need Authority Uncertainty
prerequisites, cognitive-boundary integration with a future accompaniment
boundary, bounded
journey refinement, evidence-acquisition adapters, exports, and the local UI/API
remain future work. Questionnaire presence, objective sufficiency, validated
track evidence, and CF-1 source evidence do not assert a recommendation,
candidate, or playlist-membership claim. A CF-2 formed candidate asserts only
reproducible evidence completeness and hard eligibility for downstream scoring.

The foundational architecture phase is complete. The next phase builds Penny's
vocabulary for the particular shape of people's moments. See
[Foundation Complete](docs/foundation_complete.md).

### Example seed policy

The initial repository seeds one artist (Radiohead) with a `Forbidden` rating
solely to exercise the strongest exclusion path during development and testing.
This seed is illustrative, not normative. It does not express any recommendation
or opinion about the artist and is expected to be replaced or removed in
user-specific profiles. Taste belongs to the user, not Penny.

## Setup

Python 3.12 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pne init-db
pne list-artists
```

By default the database is created at `data/playlist_narrative.db`. Override it
with `PNE_DATABASE_URL`, as shown in `.env.example`.

Rate or re-rate an artist:

```powershell
pne rate "Rush" Love --notes "Reliable work music"
pne rate "Radiohead" Forbidden
pne list-artists --rating Unknown
pne plan-focus --minutes 90 --discovery 20  # non-authoritative planning demo
```

Run tests:

```powershell
python -m pytest
```

## Data ownership

SQLite is the authoritative local store. Seed data is ordinary, reviewable Python
data and contains no claims about track-level metadata. Artist genre labels are
calibration groupings, not authoritative musicological classifications.

## Maestro research evidence store

The optional `pne-research` command maintains an isolated SQLite evidence store
for manually observed Maestro/Amazon Music playlist-generation experiments. It
does not feed scoring, candidate formation, planning, sequencing, evaluation, or
recommendation behavior. Its default database is
`data/research/maestro_experiments.db`; `PNE_RESEARCH_DATABASE_URL` can select a
different SQLite file.

```powershell
pne-research init-db
pne-research import-json .\data\research\manual-experiments.json
```

Schema version 2 can represent complete, partial, and unobserved successful
tracklists. Evidence segments preserve relative observed order, nullable absolute
positions, unknown-sized gaps, and tri-state knowledge of playlist boundaries.
Historical generation time is nullable and never defaults from record-ingestion
time. Displayed placement metadata may be stored without creating a canonical
track identity.

The importer accepts one experiment object or an array. A complete v2 JSON
export, including independent failure records, can be restored with
`pne-research import-export-json`. Optional
`prompt_labels` are explicit human-assigned analysis labels; Penny does not
infer similarity or unrelatedness. Constraint results and observations record
`DIRECT_OBSERVATION`, `HUMAN_ASSESSMENT`, `DERIVED_QUERY_RESULT`, or
`MIGRATION_DERIVATION` provenance. Recovered historical records use structured
field-level evidence sources and links. Locally available evidence bytes require
a verified SHA-256 checksum; external references may omit it.

Schema version 3 adds separately governed `PersistedPlaylistArtifact` records
for presently observed library playlists. Artifact fields, placements,
completeness, persistence, and evidence never backfill historical experiments.
An evidence-qualified `USER_ATTESTED_CORRELATION` may relate an artifact to an
experiment without asserting content identity or unchanged contents. Import a
standalone artifact with `pne-research import-artifact-json`.
Compact observations default to direct observation and constraint results to
human assessment, while either may be stated explicitly.

Raw observed strings remain unchanged. Normalized track fields are additive
only. Experiment ingestion is transactional; generation failures are stored
independently. JSON export is lossless and nested, while CSV export creates a
relational bundle of separate files.

The local Maestro Evidence Workbench includes optional RapidOCR screenshot
assistance calibrated only for the observed 590×1280 and 1179×2556 Maestro mobile layouts.
Unsupported dimensions remain available to the manual workflow and are never
resized into the validated layout. OCR results are disposable drafts requiring
explicit operator acceptance and the existing tracklist confirmation. The local
runtime adds RapidOCR, ONNX Runtime, OpenCV, NumPy, Pillow, and model assets; the
feasibility environment measured approximately 297 MB installed.

## Architecture

The modular monolith has independently testable internal layers:

1. **Taste Model** — artist/track preferences, context feedback, hard exclusions,
   and familiarity.
2. **Objective, Crossing, and Evidence Boundaries** — assesses objective
   completeness, evaluates whether an objective may safely proceed, represents
   the supported crossing and person-specific need without beginning music,
   creates closed-world artist questionnaire seeds, validates immutable
   track-evidence snapshots, and defines reproducible Candidate Formation
   without provider-dependent reasoning.
3. **Journey Planner** — translates an accepted objective into phases, energy
   trajectory, and familiarity allocations.
4. **Track Sequencer** — scores, selects, and orders validated candidates while
   enforcing exclusions, repeat limits, discovery budgets, and transition
   quality.
5. **Journey Evaluator** — observes construction results without mutating the
   sequence or collapsing unavailable and not-applicable evidence.

See [docs/architecture.md](docs/architecture.md) and
[docs/roadmap.md](docs/roadmap.md). The latest evidence-boundary contracts are
documented in
[docs/artist_questionnaire_seed.md](docs/artist_questionnaire_seed.md),
[docs/objective_assessment.md](docs/objective_assessment.md),
[docs/objective_safety.md](docs/objective_safety.md),
[docs/curriculum/crossing_model.md](docs/curriculum/crossing_model.md),
[docs/curriculum/crossing_understanding.md](docs/curriculum/crossing_understanding.md),
[docs/curriculum/curriculum_orientation.md](docs/curriculum/curriculum_orientation.md),
[docs/curriculum/need_authority_uncertainty.md](docs/curriculum/need_authority_uncertainty.md),
[docs/curriculum/need_authority_requirements.md](docs/curriculum/need_authority_requirements.md),
[docs/track_evidence_validation.md](docs/track_evidence_validation.md), and
[docs/candidate_formation.md](docs/candidate_formation.md). The downstream CF-3
boundary is specified in
[docs/candidate_formation_integration.md](docs/candidate_formation_integration.md).
The closing reflection for the foundational architecture phase is
[docs/foundation_complete.md](docs/foundation_complete.md).

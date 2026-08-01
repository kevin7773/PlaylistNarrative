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
- source-neutral track-evidence validation with deterministic, lossless
  validated/rejected partitioning
- automated tests across persistence, policy, planning, sequencing, evaluation,
  elicitation, objective assessment, and evidence validation

Candidate Formation, bounded journey refinement, evidence-acquisition adapters,
exports, and the local UI/API remain future work. Questionnaire presence,
objective sufficiency, and validated track evidence do not assert a
recommendation, candidate, or playlist-membership claim.

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
pne plan-focus --minutes 90 --discovery 20
```

Run tests:

```powershell
python -m pytest
```

## Data ownership

SQLite is the authoritative local store. Seed data is ordinary, reviewable Python
data and contains no claims about track-level metadata. Artist genre labels are
calibration groupings, not authoritative musicological classifications.

## Architecture

The modular monolith has independently testable internal layers:

1. **Taste Model** — artist/track preferences, context feedback, hard exclusions,
   and familiarity.
2. **Elicitation and Evidence Boundaries** — creates closed-world artist
   questionnaire seeds, assesses objective completeness, and validates immutable
   track-evidence snapshots without inference or provider access.
3. **Journey Planner** — translates a request into phases, energy trajectory, and
   familiarity allocations.
4. **Track Sequencer** — scores, selects, and orders validated candidates while
   enforcing exclusions, repeat limits, discovery budgets, and transition
   quality.
5. **Journey Evaluator** — observes construction results without mutating the
   sequence or collapsing unavailable and not-applicable evidence.

See [docs/architecture.md](docs/architecture.md) and
[docs/roadmap.md](docs/roadmap.md). The latest evidence-boundary contracts are
documented in
[docs/artist_questionnaire_seed.md](docs/artist_questionnaire_seed.md),
[docs/objective_assessment.md](docs/objective_assessment.md), and
[docs/track_evidence_validation.md](docs/track_evidence_validation.md).

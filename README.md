# Playlist Narrative Engine

Playlist Narrative Engine is a local-first application for designing intentional
listening journeys. It separates durable taste data from context-specific journey
planning and deterministic sequencing rules.

## Current status

Phases 1 and 2 are implemented:

- SQLite artist catalog and persistent seven-category ratings
- approximately 100 calibration artists spanning eras and genres
- Radiohead seeded as `Forbidden`
- rating and re-rating with optional notes
- deterministic default exclusion rules
- automated persistence and exclusion tests
- validated Active Focus journey requests
- deterministic three-phase energy arcs
- exact duration and discovery-budget allocation

Track sequencing, exports, and the web UI are the next phases.

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

The intended monolith has three independently testable internal layers:

1. **Taste Model** — artist/track preferences, context feedback, hard exclusions,
   and familiarity.
2. **Journey Planner** — translates a request into phases, energy trajectory, and
   familiarity allocations.
3. **Track Sequencer** — selects and orders tracks while enforcing exclusions,
   repeat limits, discovery budgets, and transition quality.

See [docs/architecture.md](docs/architecture.md) and
[docs/roadmap.md](docs/roadmap.md).

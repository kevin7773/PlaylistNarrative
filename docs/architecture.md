# Architecture

## Shape

The application is a modular local monolith. SQLite stores durable user data;
Pydantic owns boundary schemas; SQLAlchemy owns persistence. Services depend on
repository interfaces rather than UI or AI-provider behavior.

## Layer boundaries

- `taste`: rating vocabulary, preference policy, repositories, and services.
- `journey` (Phase 2): request interpretation and phase allocation.
- `sequencing` (Phase 3): candidate scoring, hard constraints, transitions.
- `providers` (Phase 5): optional AI assistance behind a small interface.
- API/UI (Phase 4): thin adapters over application services.

Hard rules such as `Forbidden`, `Pencil`, and default `No Thanks` exclusion are
code-level policy. A future AI provider may propose candidates but cannot bypass
policy.

## Extensibility decisions

`ArtistRating` stores overall preference only. The schema already defines separate
track and context feedback concepts so a later context score will not rewrite an
artist preference. SQLite initialization currently uses `create_all` plus
idempotent seeds; a migration tool will be added before schema evolution ships.


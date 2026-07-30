# Architecture

## Shape

The application is a modular local monolith. SQLite stores durable user data;
Pydantic owns boundary schemas; SQLAlchemy owns persistence. Services depend on
repository interfaces rather than UI or AI-provider behavior.

## Layer boundaries

- `taste`: rating vocabulary, preference policy, repositories, and services.
- `elicitation`: immutable, closed-world questionnaire seed artifacts derived
  only from explicit supplied evidence and approved fixed local rules.
- `journey` (Phase 2): request interpretation and phase allocation.
- `sequencing` (Phases 3–4): candidate scoring, selection, and deterministic
  sequential construction.
- `evaluation` (Phase 5): immutable observation of journey-level construction
  outcomes without sequence modification.
- `refinement` (Phase 6): bounded evidence-driven revision that consumes
  construction and evaluation without redefining either.
- API/UI (Phase 7): thin adapters over application services.
- `providers` (Phase 8): optional AI assistance behind a small interface.

Hard rules such as `Forbidden`, `Pencil`, and default `No Thanks` exclusion are
code-level policy. A future AI provider may propose candidates but cannot bypass
policy.

## Extensibility decisions

`ArtistRating` stores overall preference only. The schema already defines separate
track and context feedback concepts so a later context score will not rewrite an
artist preference. SQLite initialization currently uses `create_all` plus
idempotent seeds; a migration tool will be added before schema evolution ships.

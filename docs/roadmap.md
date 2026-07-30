# Roadmap

1. **Taste foundation (complete):** persistent artist catalog, ratings, seed data,
   exclusion policy, tests.
2. **Journey planning (complete):** Active Focus request and journey schemas,
   deterministic phases, discovery allocation.
3. **Sequencing:**
   - **Phase 3A (complete):** validated track candidates, explainable component
     scoring, transition profiles, contrast-aware penalties.
   - **Phase 3B (complete):** deterministic next-track candidate ranking with
     phase-relative discovery-budget modifiers.
4. **Playlist construction:**
   - **Phase 4A (accepted ADR):** construction inputs, outputs, hard and soft
     constraints, object lifetimes, compromise reporting, and deterministic
     boundaries.
   - **Phase 4B (planned):** transparent greedy construction over fresh
     `CandidateSelector` rankings.
   - **Later:** evaluated optimization only after the greedy baseline is
     understood.
5. **Local UI/API:** FastAPI calibration and playlist workflows, feedback entry.
6. **Optional AI:** provider interface, deterministic fallback, reviewed natural
   language interpretation.

Future contexts begin only after the Coding / Cloud Operations vertical slice is
usable end to end.

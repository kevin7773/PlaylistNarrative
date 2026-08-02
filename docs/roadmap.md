# Roadmap

1. **Taste foundation (complete):** persistent artist catalog, ratings, seed data,
   exclusion policy, tests.
2. **Journey planning (complete):** Active Focus request and journey schemas,
   deterministic phases, discovery allocation.
   - **Objective assessment (implemented):** pure, deterministic readiness
     assessment over five explicitly validated evidence dimensions, with
     clarification only for missing dimensions. This is not artist elicitation,
     recommendation, or playlist construction.
   - **Objective Safety Boundary (design contract):** deterministic evaluation
     of whether a sufficiently specified objective may proceed to Journey
     Planning. Accepted objectives continue; declined objectives terminate in a
     safe response with versioned reason codes. Implementation remains future
     work.
   - **Evidence Snapshot boundary (contract established):** source-specific
     acquisition terminates at an immutable serialized snapshot; acquisition
     adapters remain unimplemented and outside the deterministic core.
   - **Track Evidence Validation (implemented):** deterministic schema 1.0
     partitioning of every identifiable snapshot record into validated or
     losslessly rejected evidence.
   - **Candidate Formation CF-0 (contract established):** deterministic joining
     of validated catalog evidence with immutable taste, familiarity, feature,
     and objective-context evidence. Every validated track is formed or withheld
     with fixed reasons. CF-1 schemas, CF-2 implementation, and CF-3 integration
     remain unapproved future work.
3. **Sequencing:**
   - **Phase 3A (complete):** validated track candidates, explainable component
     scoring, transition profiles, contrast-aware penalties.
   - **Phase 3B (complete):** deterministic next-track candidate ranking with
     phase-relative discovery-budget modifiers.
4. **Playlist construction:**
   - **Phase 4A (accepted ADR):** construction inputs, outputs, hard and soft
     constraints, object lifetimes, compromise reporting, and deterministic
     boundaries.
   - **Phase 4B (complete):** transparent track-count construction over fresh
     state-relative `CandidateSelector` rankings.
   - **Later refinement remains external:** Phase 6 consumes construction and
     evaluation artifacts without changing construction behavior.
5. **Playlist journey evaluation:**
   - **Phase 5A (complete):** pure-observer contract, metric inventory,
     precision limits, immutable outputs, and evaluation issue taxonomy.
   - **Phase 5B (complete):** deterministic evaluation of complete and partial
     construction results using existing evidence only.
6. **Deterministic journey refinement:**
   - **Phase 6A (design proposed):** evidence-grounded bounded operations,
     correspondence validation, change records, and explicit no-change outcomes.
   - **Phase 6B (planned):** deterministic partial-tail completion and only
     specifically approved final-position repairs.
   - **Isolated elicitation prerequisite (implemented):** deterministic,
     closed-world artist questionnaire seeds for manual rating. This is not a
     refinement or recommendation artifact.
7. **Local UI/API:** FastAPI calibration and playlist workflows, feedback entry.
8. **Optional AI:** provider interface, deterministic fallback, reviewed natural
   language interpretation.

Future contexts begin only after the Coding / Cloud Operations vertical slice is
usable end to end.

# Roadmap

The foundational architecture phase is complete. The deterministic reasoning
engine is now the platform on which Penny's experience vocabulary can grow. See
[Foundation Complete](foundation_complete.md).

1. **Taste foundation (complete):** persistent artist catalog, ratings, seed data,
   exclusion policy, tests.
2. **Journey planning (complete):** Active Focus request and journey schemas,
   deterministic phases, discovery allocation.
   - **Objective assessment (implemented):** pure, deterministic readiness
     assessment over five explicitly validated evidence dimensions, with
     clarification only for missing dimensions. This is not artist elicitation,
     recommendation, or playlist construction.
   - **Objective Safety Boundary (artifact schemas implemented):** immutable
     accepted and declined schema `1.0` artifacts, fixed reason codes, and
     canonical serialization. Intent evaluation and policy execution remain
     future work.
   - **Crossing Understanding CU-1 (implemented):** immutable schema `2.0`
     directional derivation from exact EA-1 authenticated characteristics,
     preserving nonparticipating lived evidence and need lineage without
     granting either crossing authority.
   - **Curriculum Orientation CU-2 (implemented):** exact schema `1.0`
     orientation from exact EA-1 lineage through a canonical digest-bound
     registry of three approved rules, with honest no-match outcomes and no
     person-level classification or need authority.
   - **Need Authority Uncertainty CU-3 (contract proposed; blocked on
     prerequisites):** identifies the smallest material uncertainty blocking
     need authority without generating questions or establishing a need.
     Authenticated person-specific evidence and an immutable need-authority
     requirements registry must be contracted before implementation.
   - **Need Authority Requirements (contract proposed):** case-blind normative
     authority defining immutable conjunction-only evidentiary sufficiency
     requirements. Proposed-need-type and evidence-grant vocabularies remain
     prerequisite contracts; no evidence or case is evaluated here.
   - **Journey Plan artifact (implemented):** immutable schema `1.0` wrapper with
     exact journey, objective, and accepted-safety-artifact identity.
   - **Evidence Snapshot boundary (contract established):** source-specific
     acquisition terminates at an immutable serialized snapshot; acquisition
     adapters remain unimplemented and outside the deterministic core. Penny
     Local's first documentation-only source profile is the
     [iTunes Windows single-playlist XML acquisition contract](penny_local_itunes_windows_xml_acquisition.md);
     its governed intake, parser, mapping producer, and authority wrapper remain
     unimplemented.
   - **Track Evidence Validation (implemented):** deterministic schema 1.0
     partitioning of every identifiable snapshot record into validated or
     losslessly rejected evidence.
   - **Candidate Formation CF-0 (contract established):** deterministic joining
     of validated catalog evidence with immutable taste, familiarity, feature,
     and objective-context evidence. Every validated track will be formed or
     withheld with fixed reasons.
   - **Candidate Formation CF-1 (complete):** frozen schema `1.0` source-evidence
     artifacts, explicit evidence-state semantics, exact identity and ordering
     rules, and canonical serialization.
   - **Candidate Formation CF-2 (complete):** exact source correspondence,
     explicit versioned preference mapping, hard eligibility, deterministic
     formed/withheld partitions, fixed multi-reason withholding, field-level
     provenance, and canonical serialization.
   - **Candidate Formation CF-3 (complete):**
     authenticated formed-only pool projection, canonical parent-artifact digest,
     exact downstream correspondence, raw-pool API removal, and traced ranking
     and construction boundaries.
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

## Deferred acquisition architecture backlog

The governed iTunes-on-Windows XML acquisition seam is accepted as implemented.
Do not reopen or modify this seam unless real usage exposes a concrete problem
that requires one of these deferred architecture changes:

- **Persistent/restart-safe intake authority:** consider a governed durable
  authority repository only if real usage demonstrates that occurrence-local
  intake authority must survive process restart.
- **Stronger semantic verifier independence:** consider separately implemented
  profile or mapping reconstruction only if real usage exposes a defect that the
  producer and verifier's shared interpretation cannot detect.

# Canonical Final Product Artifact

The product-domain `FinalProductArtifact` is the immutable conclusion of one
already-completed playlist journey. Schema `1.0` records which exact authorities
produced the ordered playlist; it does not construct, evaluate, refine, persist,
or publish anything.

## Authority boundary

The deterministic finalizer accepts only:

- the exact `JourneyPlanArtifact`;
- the exact `CandidateFormationArtifact` and its authenticated
  `FormedCandidatePoolView` projection;
- the exact `ConstructionPolicy`;
- the already-produced schema-versioned `ConstructionResult`, including its
  production-time `ConstructionInputBinding`;
- the already-produced schema-versioned `EvaluationReport`, including its
  production-time `EvaluationInputBinding`; and
- the sole supported refinement disposition, `NOT_PERFORMED`.

The finalizer verifies all input bindings and canonical digests. It never
reconstructs correspondence from plausible metadata and never reruns
construction or evaluation.

## Placement authority

Each final placement retains its exact position, track identity, and formed-entry
ordinal. Finalization resolves the full placed candidate against the
authenticated parent formation artifact and accepts it only when:

- the formed entry exists;
- the complete candidate value equals the placed candidate;
- every applicable hard-constraint eligibility result is `ELIGIBLE`; and
- no result is `UNKNOWN` or `INELIGIBLE`.

The compact reference avoids duplicating candidate evidence authority. A fresh
verifier can resolve the reference back to the complete `FormedCandidateEntry`,
including identity, eligibility, and field provenance.

## Outcomes and canonical identity

`COMPLETE`, `PARTIAL`, and `INFEASIBLE` are distinct valid product outcomes.
Partial and infeasible outcomes retain their structured construction issues;
infeasible outcomes contain no manufactured placements.

Canonical UTF-8 JSON covers every governed constituent, ordered placement,
construction and evaluation report, final status, and refinement disposition.
The artifact stores the SHA-256 of that canonical content. Changing any governed
constituent changes the digest, and verification detects content or digest
tampering.

## Separation and non-goals

This is a product artifact. It is unrelated to the research-domain
`PersistedPlaylistArtifact` and imports no Workbench or Study machinery. Schema
`1.0` adds no provider adapter, acquisition orchestration, persistence, UI,
prompt parser, or refinement implementation.

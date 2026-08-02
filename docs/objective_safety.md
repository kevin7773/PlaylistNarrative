# Objective Safety Boundary

- **Status:** Design contract; not implemented
- **Purpose:** Determine whether a sufficiently specified objective may proceed
  to Journey Planning
- **Artifact type:** Deterministic operational safety decision, not musical
  evaluation or objective rewriting

## Position in the reasoning pipeline

Objective Safety occurs immediately after Objective Assessment and before
Journey Planning. Objective Assessment determines whether required objective
evidence is present. Objective Safety answers the next, separate question:

> May this objective proceed to Journey Planning under the applicable safety
> policy?

Only a sufficient Objective Assessment may enter this boundary. Objective Safety
does not repair an incomplete assessment or reinterpret its readiness decision.

## Inputs

The immutable request contains:

- the objective request;
- objective metadata;
- context metadata, when available;
- the corresponding sufficient Objective Assessment artifact; and
- the applicable versioned safety policy identifier.

Objective and assessment identity must correspond exactly. Missing required
input, invalid correspondence, or an objective that cannot be deterministically
resolved under the applicable policy fails closed.

## Intent before keywords

The boundary evaluates objective intent represented by the supplied objective
and metadata. It does not accept or decline an objective merely because a word
appears in its text. Keywords may be evidence, but they are not a decision by
themselves.

An accepted decision requires sufficient structured evidence to establish that
the objective may proceed under the versioned policy. Ambiguity that prevents a
required safety determination produces a declined artifact; it does not silently
default to acceptance.

## Outcomes

Every valid evaluation produces exactly one immutable artifact.

### Accepted objective artifact

An accepted artifact records:

- the unchanged objective identity and request;
- the safety-policy identifier;
- the relevant supplied metadata;
- the `accepted` decision; and
- a deterministic explanation of why the objective may proceed.

Only this artifact authorizes Journey Planning. Acceptance makes no claim about
musical content, candidates, sequencing, or eventual soundtrack quality.

### Declined objective artifact

A declined artifact records:

- the unchanged objective identity and request;
- the safety-policy identifier;
- the relevant supplied metadata;
- the `declined` decision;
- one or more deterministic reason codes in fixed order; and
- fixed explanations associated with those codes.

The exact reason-code catalog belongs to the versioned safety policy and must be
defined before implementation. Codes and explanations must not be generated ad
hoc. At minimum, the catalog must distinguish an objective that policy does not
permit from a decision that fails closed because required context is missing or
intent cannot be determined.

A declined artifact terminates the soundtrack-construction path and may be
rendered as a safe response. It must never be converted into a modified objective
that bypasses the decision.

## Execution paths

```text
Objective request + metadata + context
                  |
                  v
        Objective Assessment
          |               |
          | sufficient    | clarification required
          v               v
   Objective Safety    Clarification path
      |          |
      | accepted | declined
      v          v
Journey Planning  Safe response
```

The accepted and declined paths are mutually exclusive. Neither path accesses a
streaming provider or begins musical reasoning inside this boundary.

## Determinism and explainability

For identical serialized inputs and the same safety-policy version, evaluation
must produce byte-identical decisions, reason ordering, and explanations. The
decision must identify the policy evidence that determined its outcome without
exposing hidden or environment-dependent reasoning.

Safety policy changes require a new version. Existing artifacts retain the
policy identifier needed to explain and replay the original decision.

## Architectural principles

- Objective before music.
- Intent before keywords.
- Deterministic and explainable decisions.
- Provider-neutral evaluation.
- Fail closed when a required safety determination cannot be made.

## Isolation and non-goals

Objective Safety does not:

- rate artists;
- censor genres;
- evaluate tracks, lyrics, or other musical content;
- perform psychological diagnosis;
- access streaming or metadata providers;
- perform Candidate Formation;
- score, select, or sequence tracks;
- plan a journey; or
- modify, soften, or rewrite an objective to bypass a safety decision.


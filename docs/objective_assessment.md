# Deterministic Objective Assessment

- **Status:** Initial implementation contract
- **Purpose:** Determine whether explicit evidence is sufficient to begin
  playlist construction
- **Artifact type:** Pure observation, not question generation or construction

## Boundary

Schema validation determines whether supplied evidence satisfies each public
value contract. The assessor then observes only whether every required dimension
is present. It does not reinterpret, normalize, infer, or judge a valid answer.
The objective statement never supplies evidence implicitly.

Schema `1.0` requires these dimensions in this fixed readiness order:

| Dimension | Public value contract | Approved clarification prompt | Requirement |
| --- | --- | --- | --- |
| `listening_context` | Explicit nonblank string, at most 200 characters, with no surrounding whitespace | What listening context should this playlist support? | `OA-CTX-001`: states where and why the journey will be used |
| `duration_minutes` | Strict integer from 30 through 240 | How many minutes should the listening journey last (30 to 240)? | `OA-DUR-001`: defines the journey's time boundary |
| `starting_energy` | Exact value `low`, `medium`, or `high` | What energy level should the journey begin with: low, medium, or high? | `OA-ENE-START-001`: defines the beginning of the energy arc |
| `ending_energy` | Exact value `low`, `medium`, or `high` | What energy level should the journey end with: low, medium, or high? | `OA-ENE-END-001`: defines the destination of the energy arc |
| `discovery_percent` | Strict integer from 0 through 50 | What percentage of the journey should be exploratory (0 to 50)? | `OA-DISC-001`: defines how exploratory the journey may be |

Unknown dimensions, duplicate dimensions, duplicate evidence IDs, invalid
values, coercible numeric strings, and extra fields are rejected by the request
schema. Valid values are preserved; the assessor neither transforms nor uses
their content to claim suitability.

## Outcomes

`sufficient` means all five validated dimensions are present. Its clarification
flag is false, and its missing-dimension and clarification-question collections
are empty.

`clarification_required` means one or more dimensions are absent. The artifact
lists exactly those dimensions and the corresponding approved prompts. Every
prompt includes the documented requirement code and explanation that establish
why it is required.

## Determinism and immutability

Requests and responses are frozen Pydantic models with forbidden extra fields.
Required dimensions, present dimensions, missing dimensions, and questions use
the documented readiness order above, regardless of request evidence order.
Question ordinals are contiguous and one-based. Canonical serialization uses
schema field order, compact JSON, UTF-8, and no environment-dependent values.

## Isolation and non-goals

Objective assessment does not call or modify artist questionnaire generation,
discovery, scoring, candidate selection, playlist construction, evaluation, or
refinement. It performs no artist elicitation, provider lookup, recommendation,
candidate reasoning, track reasoning, or playlist construction. Questions are a
conditional part of the assessment response; generating questions is not the
artifact's purpose.

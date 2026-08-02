# Penny Design Journal --- 2026-07-31

## Vision

> **Penny doesn't build playlists. She builds soundtracks.**

The objective is not to maximize engagement or recommend songs the
listener already likes. The objective is to intentionally construct a
musical journey that helps the listener accomplish an experience.

> **I don't want music to be background accompaniment. I want it to be a
> soundtrack. Take me someplace.**

## Guiding Principles

-   Objective before music.
-   Soundtracks over playlists.
-   Artist identity defines where inspection begins; track evidence
    determines what belongs.
-   Every architectural layer has one bounded responsibility.
-   Deterministic, replayable, immutable artifacts.

## Reasoning Pipeline

1.  Objective Assessment
2.  Artist Questionnaire
3.  Evidence Snapshot
4.  Track Evidence Validation
5.  Candidate Formation (future)
6.  Scoring
7.  Selection
8.  Construction
9.  Journey Evaluation
10. Refinement

## Evidence Philosophy

-   EvidenceSnapshot is a replay boundary.
-   Identical snapshot bytes + identical validation policy = identical
    validation bytes.
-   Validation proves only structural correctness.
-   Validation never proves preference, familiarity, suitability,
    recommendation, or playlist membership.

## Narrative Design

-   Narrative continuity matters more than genre.
-   Discovery works best after the journey earns listener trust.
-   Skips carry semantic meaning (dislike, transition failure, objective
    mismatch, etc.).
-   Objectives define success, not genres.

## Attention Trajectories

-   Workout → increase attention
-   Focus → sustain attention
-   Road Trip → vary attention
-   Meditation → narrow attention
-   Sleep Onset → eliminate conscious attention

## Sleep Soundtracks

A sleep soundtrack is not merely relaxing.

Characteristics: - low novelty - minimal dynamics -
ambient/environmental audio - ASMR, drones, binaural beats - vocals
discouraged except chant-like textures - lyrics strongly discouraged

Success is achieved when the listener gradually stops listening
consciously.

## Educational Vision

Penny should explain: - why transitions work; - why discovery
succeeded; - how objectives shape journeys; - why a soundtrack differs
from a recommendation.

## Project Philosophy

Music is communication.

Penny is an instrument for understanding musical journeys, not an oracle
for musical taste.

> **Music isn't the destination. The destination is the destination.
> Music is how you get there.**

---

# Penny Feature Notebook

## Design Discoveries — August 1, 2026

### 1. Soundtracks are experiences, not playlists

This idea continued to strengthen throughout the day.

Refined mission statement:

> **Penny doesn't compose playlists around songs. She composes experiences
> around people.**

Corollaries:

- Objective before music.
- The journey is the product.
- Music is the medium.

### 2. Experiences have duration

One of today's most important discoveries.

Many objectives imply different expected lengths.

Examples:

- Cleaning garage → ~1–2 hours
- Road trip → could be 2–12+ hours
- Dinner party → 2–4 hours
- Pool afternoon → several hours
- Sleeping → entire sleep cycle

If duration isn't explicit, Penny should ask.

Example:

> “About how long should this experience last?”

Duration influences:

- narrative pacing
- discovery budget
- emotional progression
- energy arcs
- transition density
- candidate count

### 3. Sleep is not relaxation

Huge realization after reviewing Alexa.

Current assistants confuse:

> Relaxing

with

> Sleeping.

These are different objectives.

Relaxation soundtrack:

- vocals acceptable
- acoustic
- chill
- coffeehouse
- ambient pop

Sleep soundtrack:

- minimize vocals
- environmental audio
- binaural options
- low dynamic range
- extremely low interruption probability
- gradual energy decay
- potentially infinite looping

Different objective. Different planner.

### 4. Narrative trajectories

Rather than classifying playlists by mood, Penny should eventually reason about
emotional trajectories.

Examples:

- Safety → Vigilance
- Curiosity → Wonder
- Stress → Relief
- Isolation → Connection
- Fatigue → Focus
- Celebration → Reflection
- Confidence → Humility
- Tension → Resolution

The journey matters more than the destination.

### 5. The DJ / Tour Guide model

This one kept resurfacing.

Penny is not a recommendation engine.

Penny is the DJ.

Or even better: the tour guide.

Streaming services own the catalog.

Penny owns:

- context
- pacing
- narrative
- transitions
- objective fulfillment

### 6. Pool playlist observations

Alexa actually performed reasonably well.

Strengths:

- multi-generational appeal
- recognizable hits
- broad decade coverage

Weaknesses:

It optimized for popular songs instead of shared experience.

Future Penny improvements:

Consider audience composition. Instead of “1960–Today,” ask:

- Who is attending?
- Children?
- Parents?
- Grandparents?
- How many?
- Background listening or active dancing?

### 7. Peach Festival playlist observations

Alexa interpreted “Peachy road trip” literally.

Missing:

- locality
- outdoors
- summer atmosphere
- orchard feel
- Americana
- regional influences

Potential Penny feature: location-aware atmosphere. Not GPS. Context.

- Farm
- Beach
- Mountains
- Campfire
- Backyard cookout
- Tailgate

### 8. Unknown threat soundtrack

Very interesting experiment.

Alexa chose psychological tension instead of horror music.

Observation: psychological progression is more important than genre.

Future planner concept: narrative tension curve.

### 9. Objective Safety Boundary

Major architectural addition.

Occurs before Journey Planning. Evaluates objective intent, not keywords.

Deterministic outcomes:

```text
Accepted
    ↓
Journey Planning

or

Declined
    ↓
Safe response
```

Future documentation: `docs/objective_safety.md`

### 10. Genre guardrails

Potential Taste Model expansion.

Current: artist preferences.

Future: genre preferences.

Examples:

- Forbidden genres
- Top favorite genres
- Neutral
- Discovery-friendly

This creates additional deterministic guardrails without affecting planning
philosophy.

### 11. Journey completion

Current streaming services continue indefinitely. Penny should not.

Options:

- Stop playback.
- Fade into ambient.
- Transition into sleep sounds.
- Continue with “related listening.”
- Ask beforehand.

The soundtrack should intentionally end.

### 12. Provider philosophy

Another principle became clearer.

Providers deliver music.

Penny delivers meaning.

This remains true regardless of provider.

### 13. Product philosophy

Strengthened again today.

The free product should not become worse. Cloud features should add convenience.
Never intelligence.

Summary:

> **Pay for capability, not quality.**

### 14. Quality over addiction

Another philosophy worth preserving.

Do not optimize:

- engagement
- doom scrolling
- habit loops
- notifications

Optimize:

- trust
- consistency
- excellent outcomes

Users return because the soundtrack accomplished its purpose.

### 15. Human-first reasoning

Today's strongest observation.

Current systems often reason like:

```text
Prompt
    ↓
Find similar music
    ↓
Playlist
```

Penny reasons:

```text
People
    ↓
Objective
    ↓
Context
    ↓
Narrative
    ↓
Music
```

The music is almost the last decision.

### 16. Architecture principle discovered today

A new governance principle emerged naturally.

Every important “why” deserves its own deterministic boundary.

Current examples:

- Evidence Snapshot
- Track Evidence Validation
- Objective Assessment
- Objective Safety
- Candidate Formation
- Journey Planning
- Sequencing
- Evaluation

Each layer answers one question completely before passing a deterministic
artifact to the next.

### Overall Reflection

Today's discussions reinforced that Penny is not trying to compete with Spotify
AI, Amazon Alexa, or Apple Music recommendations. Those systems primarily answer
“What songs fit this request?” Penny answers “What experience is this person
trying to have, and how should music support it?”

That distinction is becoming the project's identity. It influences the
architecture, the user experience, the business model, and even the safety
philosophy. If you preserve that north star, future features become much easier
to evaluate: if they help Penny understand people and objectives better, they
belong; if they merely increase engagement or imitate existing playlist
generators, they probably don't.

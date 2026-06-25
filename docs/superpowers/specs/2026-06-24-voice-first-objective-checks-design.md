---
name: voice-first-objective-checks
description: Add two voice-safety checks (visual-stimulus error, enumeration/ranking warning) to gathering.txt prevention and review.txt detection, since the downstream interview agent is voice-only
metadata:
  type: project
---

# Voice-First Objective Checks

## Problem

The template this app builds is consumed by a separate, **voice-only** AI interview
agent (ElevenLabs; "Speech-First", "easy to understand when heard, not read"). Every
core/probe objective is an instruction that agent turns into a spoken question in a live
call with no screen.

The current quality system — the objective-writing rules in `prompts/gathering.txt` and
the independent export gate in `prompts/review.txt` — checks written objective craft
(compound asks, diagnostic verbs, assumed experience, vague specificity, probe-restates-core)
but nothing voice-specific. Two failure modes slip through:

1. **Visual-stimulus objectives** — "explore their reaction to the homepage layout",
   "which of these logos they prefer". In a voice call there is no screen, so the agent
   literally cannot execute these.
2. **Enumeration / ranking objectives** — "rank these five factors", "list all the apps
   they used". Producing or ordering a list from memory, aloud, overloads working memory
   by ear and forces thin, artificial answers.

## Decisions (settled during brainstorming)

- The interview is **always voice-only**. Visual-stimulus objectives are therefore a
  **hard error**, not a warning. No modality flag is introduced.
- Two checks only. A third candidate, `overloaded_for_speech`, was **dropped** as too
  phrasing-dependent and overlapping with the existing `compound_ask`/`keep_light` rules.
- Checks live in **both** places, mirroring the existing prevention+detection pattern:
  `gathering.txt` (builder avoids them while drafting and at the Consolidation Gate) and
  `review.txt` (independent export gate).
- All of Tier 2 (expansion enrichment, two-clock duration reframe) is **out of scope** —
  both ideas washed out during brainstorming (allotted time is a separate feature not tied
  to the template; enriching expansion just makes it a duplicate of normal topics).

## Grounding facts (verified in code)

- The review tool's `item_issues[].rule` field is a **free-form string**
  (`app.py` `REVIEW_TOOL`, ~line 150), not an enum — so new check names need **no
  tool-schema change**.
- The frontend renders review issues **generically** — no hardcoded rule→label map in
  `static/app.js` (only reference to `.rule` is `state.sections.pacing[payload.rule]`,
  unrelated). So **no `app.js` change**.
- An error-severity issue already drives `overall == "error"` via `review.txt`'s severity
  rules, which the two-phase export modal uses to block auto-proceed. The new error check
  reuses this wiring unchanged.

**Net:** this is a prompt + test change only. No `app.py`, no `app.js`, no new tool, no
UI element.

## The two checks

| Check | Severity | Catches |
|---|---|---|
| `requires_visual_stimulus` | error | Objective needs the participant to see, look at, react to, or choose among something visual (image, screen, layout, design, colour, logo, on-screen option). |
| `enumeration_or_ranking` | warning | Objective asks the participant to list many items, or rank/order items, from memory and aloud. |

## Changes

### 1. `prompts/gathering.txt` — prevention (3 edits)

**a. New objective rule** appended to the numbered "Writing objectives" list (after the
current rule 6, "Instructions, not scripts"). The section is introduced as "Nine rules"
(rules 1–6 plus sub-rules 4a/4b/4c) — update that count to **"Ten rules"** when adding rule 7:

> 7. Voiceable by ear. Every objective must be answerable in spoken conversation with no
>    screen. Never require the participant to look at, react to, or choose among visual
>    stimuli (images, layouts, designs, colours, logos, on-screen options) — there is no
>    screen. Never require them to list or rank items from memory aloud; ask for one thing
>    at a time and let narrative surface the rest.

**b. Two new rows** in the "Anti-patterns (never ship these)" table:

> | "react to / look at [a visual]" | no screen in a voice call | anchor on a remembered moment, not a shown stimulus |
> | "rank / list all the X" | hard to do by ear, forces thin data | draw items out one at a time through narrative |

**c. New checkbox** in the "Consolidation Gate" list:

> - [ ] Every objective is answerable by voice alone — no visual stimulus, no list/ranking from memory

### 2. `prompts/review.txt` — detection (2 new check blocks)

Added under "## Objective-writing rules (checked per core/probe item)", in the same
`### name (severity: …)` + Bad/Good format as the existing checks:

> ### requires_visual_stimulus (severity: error)
> The item requires the participant to see, look at, react to, or choose among something
> visual (an image, screen, layout, design, colour, logo, or on-screen option). The
> interview is voice-only — there is no screen, so the agent cannot execute this.
> Bad: "Explore the participant's reaction to the homepage layout"
> Good: "Trace a recent moment the participant tried to find something on the site and what happened"
>
> ### enumeration_or_ranking (severity: warning)
> The item asks the participant to list many items, or rank/order items, from memory and
> aloud. By ear this overloads recall and forces thin, artificial answers. Draw items out
> one at a time through narrative instead.
> Bad: "Have the participant rank the five factors that matter most when choosing a brand"
> Good: "Surface what mattered most the last time the participant chose a brand, and why"

The existing "## Severity rules" section is unchanged: `requires_visual_stimulus` being an
error means `overall` becomes `"error"` whenever one is present, exactly like the existing
error checks.

### 3. Tests

**a. `tests/test_gathering_prompt.py`** — extend with assertions that `prompts/gathering.txt`
now contains: the voiceability rule (key phrases, e.g. "Voiceable by ear" / "no screen"),
both new anti-pattern rows, and the new Consolidation Gate checkbox text.

> ⚠️ **Caution:** a project note records that several tests already in this file are
> pre-written for a *different, forthcoming* gathering-prompt update and are expected to
> fail until that unrelated update lands. New assertions here must be **purely additive**
> and must not depend on or modify those pending tests.

**b. New `tests/test_review_prompt.py`** — parallel to `test_gathering_prompt.py`: load
`prompts/review.txt` and assert it contains both new check headers
(`requires_visual_stimulus`, `enumeration_or_ranking`) with their correct severities
(`error`, `warning` respectively). `review.txt` is consumed by an AI at runtime, so this
mirrors the existing content-assertion approach rather than attempting a behavioural test.

## Out of scope

- `overloaded_for_speech` check.
- Any modality flag / non-voice interview support.
- All Tier 2 work (expansion-topic enrichment, two-clock duration reframe).
- Any change to `app.py` (`REVIEW_TOOL` schema, `format_template`) or `static/app.js`.
- Any new AI tool, UI element, or review-rendering change.

## Testing strategy

- `pytest tests/test_gathering_prompt.py` and `pytest tests/test_review_prompt.py` verify
  the prompt text contains the new rules/checks.
- Full `pytest tests/` confirms no regression in the dispatcher, routes, or formatter
  (none of which change).
- The JS duration suite is untouched and irrelevant here.

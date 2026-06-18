# Design: Airtight Template Generation & Duration Coach

**Date:** 2026-06-17
**Status:** Approved for planning

## Problem

The app outputs an interview-guide template that a separate AI agent uses as the basis for a live interview with a real person. The downstream agent cannot ask for clarification mid-interview, so a single ambiguous or flawed objective becomes a wrong question asked to a human. Two weaknesses in the current system undermine output quality:

1. **The gathering prompt builds the template incrementally, one topic at a time, and never reviews the whole assembled guide.** This lets vague objectives, leading framing, redundant topics, and Core/Probe misplacements slip through. The non-expert user wants templates that are export-ready with minimal review.

2. **The duration target does nothing.** The slider sets `state.durationTarget`, the UI shows it next to a computed estimate, but nothing reacts to it. The user wants the slider to give actionable feedback on how to bring the template closer to their intended length.

This spec covers two independently-implementable parts. The guiding principle of the division of labour: **the AI owns quality; the duration coach owns fit.**

---

## Part 1 — Airtight Gathering Prompt

### Goal

Rework `prompts/gathering.txt` so each topic and objective is written to a high quality standard during generation, and a holistic self-review pass catches residual issues before the template is declared done. This is prompt-only — no schema or code changes required for Part 1.

### 1.1 Consumer-awareness framing

The prompt opens by telling the model exactly what its output does: every objective becomes a literal instruction to a separate AI that runs a live interview with a real person and cannot ask for clarification, so ambiguity becomes a wrong question asked to a human. This framing raises the model's precision baseline and gives it a concrete quality target to reason toward.

### 1.2 Objective-writing discipline

An objective is an instruction to the interviewer, never a literal question. Six rules, ordered by impact:

1. **One objective = one ask.** Never joined by "and." Two things become two items. Prevents double-barreled questions where half the answer is lost.
2. **Exploratory verbs, never diagnostic ones.** Use *explore, capture, walk through, surface, trace, draw out, understand how/why*. Ban *determine, assess, evaluate, confirm, verify, identify whether*. Diagnostic verbs collapse into yes/no or rating questions; exploratory verbs produce open narrative.
3. **Conditional framing — never assume an experience occurred.** "Understand why checkout was frustrating" assumes frustration. "Explore how checkout unfolded and how the participant felt about it" lets the interviewer discover positive, negative, or neutral.
4. **Episodic over attitudinal.** Where the interview anchors on a specific occasion, phrase objectives to elicit what actually happened, not general opinions. Episodic memory yields richer, less rationalized data.
5. **Specificity floor.** Every objective must name the concrete thing sought — a moment, decision, friction, or feeling. "Understand their experience" is contentless and banned.
6. **Instructions, not scripts.** Objectives never contain literal question wording. (Preserved from current prompt.)

### 1.3 Core vs. Probe — airtight definitions

The downstream pacing rules treat the two roles differently, so a misplacement changes interview behaviour.

- **Core** = essential moves that open and carry the topic. Each must be askable cold, without a prior answer. The first Core item is the topic's natural opener.
- **Probe** = optional follow-ups that deepen a thin or interesting answer. A probe presupposes the participant has already spoken and must add a **new direction** — sensory detail, a specific example, the "why," a contrast — never a reworded Core.

Placement tests the model applies:
- If an item only makes sense *after* the participant has spoken → it is a Probe, not Core.
- If a probe could swap with its Core with nothing breaking → the probe is redundant; rewrite it to add direction.

Contingency rule: **every topic carries at least one probe that maps to a plausible thin-answer path**, so the interviewer always has a depth tool.

### 1.4 Focus statement — experience anchor, not research goal

The focus is the single experience the interview returns to. "Understand what drives loyalty" is a research goal (orients toward confirming a hypothesis). "The participant's recent shopping experiences at [store], anchored on the most recent memorable visit" is an experience anchor (orients toward following lived narrative). Where the research anchors on one occasion, the focus names that occasion and its boundaries.

### 1.5 Topic-set discipline

Checked holistically (see the consolidation gate):

- **Non-overlap** — no two topics target the same underlying thing; each states its distinct angle. Overlaps are merged or sharpened.
- **Coverage** — the set covers the domain's essential dimensions; domain knowledge is used to catch a missing essential theme.
- **Ordering** — funnel structure: easy/concrete warm-up → core themes → sensitive/evaluative → reflective cool-down. Never lead with an emotionally loaded topic.
- **Count** — produce a sensibly-sized guide (≈5–8 topics). The AI does **not** attempt to hit a specific minute target; precise time-fitting is the duration coach's job (Part 2). The AI cannot see the duration slider.
- **Priority spread** — priorities must discriminate (not uniformly 3); they are the interviewer's triage signal under time pressure. A flat distribution gives no signal.

### 1.6 Consolidation gate (centerpiece)

Before the model is permitted to say the template is ready, it must run an explicit holistic self-review: re-read the entire assembled guide, pass it against the checklist below, apply fixes via tool calls, then briefly state what it changed. This is the mechanism that makes prompt-only quality reliable despite rule fatigue — a second, focused compliance pass over the whole artifact catches drift from incremental generation.

Checklist:
- [ ] Every objective: single ask · exploratory verb · no assumption · specific
- [ ] No two topics overlap; each has a distinct stated angle
- [ ] Topics ordered easy → sensitive → reflective
- [ ] Every topic has ≥1 probe that adds direction (none restate their core)
- [ ] Focus is an experience anchor, not a research goal
- [ ] Priorities discriminate (not uniformly 3)
- [ ] Topic count is reasonable (≈5–8)

### 1.7 Anti-pattern table

A compact red-flag table the model matches surface patterns against — more reliable than reasoning from abstract rules. Each row carries a rewrite:

| Red flag | Why it breaks | Rewrite |
|---|---|---|
| "and" joining two asks | double-barreled question | split into two items |
| "determine/confirm if…" | yes/no dead-end | "explore how/why…" |
| assumes an emotion or event | leading question | conditional framing |
| "their experience/thoughts" alone | contentless | name the specific thing |
| probe restates the core | no depth tool | add a new direction |
| sensitive topic placed first | guarded answers | move later in the funnel |

### 1.8 What is preserved

- Eager inference: still populate 5–8 topics immediately on first domain mention (a populated template beats an empty one). The objective-writing rules apply from the first draft; the consolidation gate cleans up residue.
- One question per message; warm, conversational tone.
- Pacing rules left at UI defaults unless the client explicitly requests a change.
- Priority ratings on every `add_topic` call.

### Files affected (Part 1)

- `prompts/gathering.txt` — full rework per above.

---

## Part 2 — Duration Coach

### Goal

Turn the inert duration target into a live coaching instrument: whenever the estimate does not match the target, show the gap and a short list of ranked, concrete moves that close it, each with a one-click **Apply** button. Deterministic, client-side, no API calls. Reuses the existing priority-weighted estimate model.

### 2.1 Gap state (three modes)

Computed from `estimate = estimateDurationFor(...)` and `target = state.durationTarget`:

- **No target set** (`target === 0`): muted hint — "Set a target to get pacing suggestions." No suggestions.
- **Within tolerance** (`|estimate − target| ≤ 2 min`): green confirmation — "On target (~N min)." No suggestions.
- **Off target**: headline — "≈12 min over" / "≈8 min under" — plus up to 3 ranked suggestions.

### 2.2 Suggestion engine

A **pure function** `generateSuggestions(sections, target, depthValue)` returning an ordered array of `{ label, detail, deltaMin, apply }`.

**Over target** (trim, lowest-value first):
- Remove the lowest-priority *topic* — e.g. "Remove *Staff and service* · P2 · saves ~4 min"
- Remove the lowest-priority *item* within a topic
- Lower depth one notch — "Drop to Slightly Broad · saves ~6 min · also relaxes pacing rules"

**Under target** (fill, quality-first):
- Add probes to a topic that has none — "*Checkout* has no probes · add depth ~2 min" (also satisfies a Part 1 airtight rule)
- Promote an expansion topic into the guide — "Promote *role of family* · ~3 min"
- Raise depth one notch
- Add a new topic

Ranking: order by how efficiently each move closes the gap **while preserving quality** — cut lowest-priority content first; fill with quality-improving moves first. Show at most 3.

### 2.3 Minute math

Refactor `estimateDuration()` into a pure `estimateDurationFor(sections, depthValue)` (the existing `estimateDuration()` becomes a thin wrapper passing current state). Each suggestion's `deltaMin` is computed by **diffing** — `estimateDurationFor(current) − estimateDurationFor(hypothetical)` — so the displayed minute impact always matches the estimate bar. No parallel formula that can drift.

### 2.4 Apply + undo

Clicking **Apply** runs the suggestion's `apply` mutation, re-renders, recomputes the estimate, and regenerates suggestions against the new gap. Because Apply can remove AI-authored content, snapshot (deep clone) `state.sections` before each apply and expose a one-step **Undo** link that restores the snapshot. Depth-changing suggestions call the existing `applyDepthPreset()` and therefore also rewrite pacing text — the suggestion `detail` states this side effect explicitly.

### 2.5 Guard rails

- Never suggest removing the last remaining topic.
- Never suggest removing a topic's only Core item (a topic must keep ≥1 Core).
- Never propose a move whose `deltaMin` overshoots so far it leaves a larger gap than staying put (avoids thrash near the target).
- If no quality-preserving move exists in the needed direction, fall back to the depth lever, then to add/remove-topic.

### 2.6 UI placement

A compact suggestion area directly under the existing duration control in the settings strip (`renderSettingsStrip()`): a gap headline, then up to 3 suggestion rows (label · detail · Apply button), then the Undo link when an apply is pending. On-target shows the green confirmation; no-target shows the muted hint.

### 2.7 Testability

`generateSuggestions` and `estimateDurationFor` are pure (`sections + target + depth → output`), so they are unit-testable. The repo currently has only pytest and `app.js` is untested. Write these as isolated pure functions so they *can* be tested. A minimal JS test harness is recommended as a follow-up but is **out of scope** for this spec unless requested.

### Files affected (Part 2)

- `static/app.js` — `estimateDurationFor` refactor; `generateSuggestions`; apply/undo handlers; suggestion-area rendering in `renderSettingsStrip()`.
- `static/style.css` — styles for the suggestion area, rows, Apply/Undo controls.

---

## Out of scope

- Deployment, auth, persistence.
- AI-generated (Approach C) duration coaching — deterministic only.
- Wiring the duration target into the gathering conversation (explicitly dropped — the coach owns fit).
- A JS test framework (recommended follow-up, not part of this work).

## Sequencing

The two parts are independent and can be implemented in either order. Part 1 is prompt-only; Part 2 is frontend-only. They share no files.

---
title: Pacing Preset Refinement
date: 2026-06-24
status: approved
---

# Pacing Preset Refinement

## Problem

The balanced pacing preset (`PACING_DEFAULTS`) has been carefully tuned and works well with the AI interview agent. The four non-balanced presets (breadth, slightly_broad, slightly_deep, deep) have structural and clarity gaps that may cause the agent to behave inconsistently — particularly around end-of-interview handling, probe trigger conditions, and vague criteria.

## Scope

7 targeted changes across 4 presets in `PACING_DEPTH_PRESETS` in `static/app.js`. No changes to balanced/PACING_DEFAULTS, no structural changes, no new fields.

## Changes

### BREADTH

**`do_not_rush`** — fix probe trigger word

- Before: `"…Use probes only when an answer is unclear or incomplete."`
- After: `"…Use probes only when an answer is thin or unclear."`
- Why: "Incomplete" implies the participant didn't answer the question. In qualitative research, an answer can be complete but still lack narrative richness. "Thin" is the correct bar.

**`finish_line`** — add `remaining_minutes` cue

- Before: `"Reaching the end of the Main Interview Guide signals the end of the interview. If a few minutes remain, close warmly. Do not pivot to Expansion Topics."`
- After: `"Reaching the end of the Main Interview Guide signals the end of the interview. Begin closing warmly. If remaining_minutes is 5 or more, you may briefly revisit one topic that felt thin. Do not pivot to Expansion Topics."`
- Why: "A few minutes" is unanchored. Every other preset uses the `remaining_minutes` variable as the trigger; this preset should too.

---

### SLIGHTLY BROAD

**`one_ask_per_turn`** — sharpen vague criteria

- Before: `"…You may add a second only when it flows naturally from the first answer."`
- After: `"…You may add a second only when it is tightly related and easy to answer in the same breath."`
- Why: "Flows naturally" is too permissive — almost any follow-up could qualify. Balanced uses specific criteria; this aligns with that standard.

**`finish_line`** — add Expansion Topics, `remaining_minutes` trigger, numbered structure

- Before: `"Reaching the end of the Main Interview Guide does not necessarily signal the end of the interview. If time remains, revisit one interesting moment briefly before closing."`
- After:
  ```
  Reaching the end of the Main Interview Guide does not signal the end of the interview. If remaining_minutes is 5 or more, use one of these options to fill the time:
    1. Circle Back: Revisit an earlier interesting moment to draw out a little more detail.
    2. Expansion: Lightly touch on one Expansion Topic if it fits the conversation.
  Close warmly once remaining_minutes is 3 or less.
  ```
- Why: Expansion Topics were completely absent. The agent had no instruction to use them. "If time remains" is also unanchored.

---

### SLIGHTLY DEEP

**`original_followups`** — replace soft phrase with actionable direction

- Before: `"…Good intuition is an asset here."`
- After: `"…Lean into moments that feel rich, unresolved, or surprising."`
- Why: "Good intuition is an asset here" gives the agent nothing actionable. The new phrase names the specific conditions worth pursuing.

**`finish_line`** — define Circle Back, add numbered structure

- Before: `"Reaching the end of the Main Interview Guide does not signal the end of the interview. Use Circle Back and Expansion Topics to fill remaining time until remaining_minutes is 3 or less."`
- After:
  ```
  Reaching the end of the Main Interview Guide does not signal the end of the interview. Use the following to fill remaining time until remaining_minutes is 3 or less:
    1. Circle Back: Revisit an earlier interesting moment to ask for thicker description — a specific emotion, a sensory detail, or the deeper why.
    2. Expansion: Pivot to the Expansion Topics at the bottom of the plan.
  ```
- Why: "Circle Back" was used without definition. Balanced defines it inline; this preset should too.

---

### DEEP

**`finish_line`** — add numbered structure, clarify Circle Back as primary tool

- Before: `"…You must use Circle Back and Expansion Topics to fill the time until remaining_minutes is 3 or less. Circle Back is particularly important at this depth — revisit every moment that had depth potential and push for sensory detail, specific emotions, and deeper explanation."`
- After:
  ```
  You must use the following to fill the time until remaining_minutes is 3 or less:
    1. Circle Back: Revisit every moment that had depth potential. Push for sensory detail, specific emotions, and the deeper why behind what they shared. This is the primary tool at this depth.
    2. Expansion: Pivot to the Expansion Topics at the bottom of the plan.
  ```
- Why: Adds numbered format consistent with other presets. Makes the Circle Back-first priority explicit in the instruction rather than as an afterthought sentence.

## What is not changing

- `PACING_DEFAULTS` (balanced) — untouched
- All other fields in breadth, slightly_broad, slightly_deep, deep — untouched
- No new pacing fields, no structural changes
- No changes to the gathering prompt, review prompt, or any Python/CSS files

## Implementation

All changes are in `static/app.js`, within the `PACING_DEPTH_PRESETS` constant (lines ~26–66). No tests cover these string values directly; the existing test suite does not need updating.

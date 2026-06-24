# Core Objective Quality — Design Spec
**Date:** 2026-06-24

## Problem

Interview transcripts show a recurring pattern: participants give thin or one-sentence answers to core objectives, leaving little for probes to build on. Three failure modes are responsible:

1. **"Typical" framing** — "Walk through what a typical commute looks like" invites a generic description rather than a specific memory.
2. **High-altitude scope** — "What was your overall impression?" and "Walk through from start to finish" ask for summary, which yields summary.
3. **Comparison-as-core** — "How does in-office compare to remote?" asks the participant to do analysis, not recall, yielding rationalized opinion rather than lived narrative.

These failure modes are not covered by the existing six core-writing rules in `prompts/gathering.txt`.

## Goal

Make the gathering AI write core objectives that reliably invite specific, narrative answers — even from participants who give brief, positive, or "nothing happened" first responses.

## Scope

Changes are limited to `prompts/gathering.txt`. No code changes, no new routes, no changes to the review prompt or quality gate.

---

## Changes to `prompts/gathering.txt`

### 1. Three new core-writing rules

Add rules 5a–5c immediately after the existing rule 4 ("Prefer episodic over attitudinal"):

**5a. No "typical" framing.** Every core must anchor on a specific episode: the most recent visit, the last time they commuted, a day that came to mind. Never ask about a generalised pattern — "typical" invites description from memory of a category, not recall of an event.

**5b. Scope to a slice, not the whole experience.** Cores that target the whole experience ("from start to finish," "overall impression") ask for summary and get summary. Target a bounded slice: a specific moment, decision point, the first few minutes, the moment they left. The smaller the scope, the more concrete the answer.

**5c. No comparison-as-core.** Asking a participant to compare two settings or experiences ("how does X compare to Y") makes them the analyst. Comparisons belong in probes, after a specific episode has been established. A core anchors on one occasion; a probe can then draw out the contrast.

### 2. Three new anti-pattern rows

Add to the existing anti-patterns table:

| Red flag | Why it breaks | Rewrite |
|---|---|---|
| "typical day / typical commute" | invites generic description | anchor on the most recent or a specific remembered episode |
| "overall impression / from start to finish" | yields summary, not narrative | scope to a slice: a specific moment, decision, or feeling |
| "how does X compare to Y" | participant does analysis, not recall | anchor on a specific occasion when the contrast was felt |

### 3. Before/after pairs in the worked example

Insert the following block immediately before the existing tool calls in the "Worked example" section:

---

> The three most common core failure modes — and how to fix them:
>
> **"Typical" trap:** "Walk through what a typical grocery visit looks like for the participant" → invites generic description. Fix: "Walk through how the participant arrived and entered the store on their most recent visit."
>
> **High-altitude scope:** "Explore the participant's overall impression of the store" → yields one-sentence summary. Fix: "Trace the moment during the visit when the participant made an unplanned decision — to pick up something they hadn't planned to buy, or to skip something they'd intended to get."
>
> **Comparison trap:** "Explore how this store compares to others the participant uses" → participant does analysis, not recall. Fix: "Surface a specific moment during the visit when something about the store stood out — positively or negatively — compared to what they expected."

---

The existing tool calls follow unchanged.

---

## What this does not change

- The Consolidation Gate checklist — no new per-core audit step. If the rules and example are tight, the Gate should not need to catch stragglers.
- `prompts/review.txt` — the quality gate checks template structure, not core altitude or typical-framing. These are authoring-time rules, not export-time checks.
- Any frontend or backend code.

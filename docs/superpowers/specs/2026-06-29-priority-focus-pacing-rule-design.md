# "Priority & Focus" Pacing Rule — Design Spec
**Date:** 2026-06-29

## Overview

Today every topic and core/probe item carries a 1–5 star priority that is exported as a `[P:N]` tag (`## Topic 1 [P:4]:`, `- [Core][P:5] ...`). The interview agent receives these tags inside `{{interview_plan}}` but has no instruction telling it what they mean, so the numbers are dead weight.

This feature adds a 9th pacing instruction — **"Priority & Focus"** — that teaches the agent how to act on `[P:N]`. Like the existing 8 pacing rules, it is preset-driven: it has a distinct text for each of the five Depth-vs-Breadth slider positions, and it flows to the agent automatically through the export's `# Pacing Instructions` block (the agent prompt already says "Follow those pacing instructions over the general interviewing guidance").

The name is deliberately **not** "Depth v Breadth" — that would collide with the existing settings-strip slider of the same name. The slider is the control; "Priority & Focus" is the agent instruction it produces.

---

## Behavior model

The rule pulls exactly two levers:

1. **Time & depth investment** — spend more time and ask more follow-up probes on higher-`[P:N]` topics/items; keep low-`[P:N]` ones brisk. `[P:3]` is the neutral baseline.
2. **Skip / sacrifice order** — under time pressure, thin depth from the lowest-`[P:N]` material first; only drop an item or topic entirely as a last resort, lowest `[P:N]` first.

Two constraints are baked into **every** preset text:

- **Coverage guardrail:** priority is a dial on attention, not an on/off switch. The agent must still reach every (or nearly every) topic — one or two high-priority topics must never swallow the interview. This is what prevents "invest in high-P" from collapsing into "ignore everything else."
- **Core/Probe precedence:** a shared clause — *"priority orders attention within the Core/Probe split, it does not override it"* — prevents conflict with the existing **Core vs. Probe** rule. A `[Probe][P:5]` does not leapfrog the must-ask nature of `[Core]` items.

Each preset uses the same skeleton so the five read as one rule re-tuned, not five different rules:

> what `[P:N]` means → invest more on high / keep low brisk → coverage guardrail → Core/Probe clause → sacrifice order

The only thing that varies across presets is the **steepness of the attention gradient**: shallow at Breadth (coverage wins), steep at Deep (depth wins, coverage still protected).

---

## The five preset texts (`priority_focus`)

**Breadth** (shallowest gradient — coverage wins)
> Every topic carries a priority from [P:1] to [P:5]; treat these as a light dial on attention, not an on/off switch. Reaching every topic is the goal. Give [P:4]–[P:5] topics and items modestly more room and perhaps one extra probe, and keep [P:1]–[P:3] brisk — but never let a high-priority topic run so long that later topics go unasked. Priority orders attention within the Core/Probe split, it does not override it. If you fall behind, shorten the lowest-priority material first; drop an item only when time is nearly gone, lowest [P:N] first.

**Slightly Broad** (coverage-leaning)
> Topics and items are marked [P:1]–[P:5]. Use these to share out attention while still covering everything: spend a little more time and the occasional extra probe on [P:4]–[P:5] material, keep [P:1]–[P:2] efficient, and treat [P:3] as the baseline. Cover every topic before depth on any one — a higher priority earns a little more depth, not the exclusion of lower-priority topics. Priority orders attention within the Core/Probe split, not against it. Under time pressure, trim the lowest-[P:N] material first.

**Balanced** (the default — middle gradient; this text lives in `PACING_DEFAULTS`)
> Each topic and item is marked [P:1]–[P:5]. Use this to allocate attention: spend more time and probe harder on [P:4]–[P:5] material, keep [P:1]–[P:2] efficient, and treat [P:3] as the normal baseline. Aim to cover every topic — a higher priority earns more depth, not the exclusion of lower-priority topics. Priority orders attention within the Core/Probe split, it does not override it. If time runs short, trim the lowest-[P:N] material first, and only drop a whole item or topic as a last resort, lowest priority first.

**Slightly Deep** (depth-leaning)
> Topics and items are marked [P:1]–[P:5]. Invest your richer probing where the number is higher — follow [P:4]–[P:5] material a couple of layers deeper — while keeping [P:1]–[P:2] efficient. Still reach every topic at least briefly; do not let one or two high-priority topics dominate the whole interview. Priority orders attention within the Core/Probe split, not against it. Under time pressure, sacrifice depth on the lowest-[P:N] material first, then drop the lowest-priority items only if you must.

**Deep** (steepest gradient — depth wins, coverage still protected)
> Each topic and item carries a priority from [P:1] to [P:5]. Concentrate your richest probing where it is highest — go several layers deep on [P:5] and [P:4] material, and accept brief answers on [P:1]–[P:2]. Even so, every topic should be reached at least briefly before time runs out; never let one or two high-priority topics swallow the interview. Priority orders attention within the Core/Probe split, it does not override it. Under time pressure, sacrifice depth on the lowest-[P:N] material first, then drop the lowest-priority items entirely before higher-priority ones.

---

## Plumbing changes

### `static/app.js`
- **`PACING_DEFAULTS`** — add `priority_focus` as the **first** key, holding the *Balanced* text above. This is what the `balanced` preset inherits via `{ ...PACING_DEFAULTS }` and what fresh `state.sections.pacing` initializes from.
- **`PACING_LABELS`** — add `priority_focus: "Priority & Focus"` as the **first** entry, so it renders first in the Pacing Instructions panel (`renderPacing()` iterates `PACING_LABELS`).
- **`PACING_DEPTH_PRESETS`** — add the `priority_focus` text to `breadth`, `slightly_broad`, `slightly_deep`, and `deep`. (`balanced` already receives it through the `{ ...PACING_DEFAULTS }` spread.)
- **No change** to `applyUpdate` or `resetPacing` — both are key-agnostic and pick up the new rule automatically (`applyUpdate` does `state.sections.pacing[payload.rule] = payload.text`; `resetPacing` reads `getDepthPreset(...)[rule]`).

### `app.py`
- **`update_pacing` tool schema** — add `"priority_focus"` to the `rule` enum, so the AI *can* edit it on explicit client request. It stays preset-driven otherwise (the gathering prompt only calls `update_pacing` when the client asks).
- **`format_template`** — insert the headline line first in the pacing block:
  ```python
  parts.append("# Pacing Instructions")
  parts.append(f"- **Priority & Focus:** {pacing.get('priority_focus', '')}")
  parts.append("")
  parts.append(f"- **Do Not Rush** {pacing.get('do_not_rush', '')}")
  ```
  Resulting group structure: `1 (Priority & Focus) / 1 (Do Not Rush) / 3 / 3 / 1`. The new rule frames how to read every `[P:N]` that follows it.

### `static/duration.js`
- **Untouched.** Priority is already factored into the estimate via `priorityFactor(p) = 0.5 + (p-1)*0.25` (0.5× at P1 → 1.5× at P5), applied to the topic base, extra core items, and probes. The current spread already models "more budgeted time on high-P, less on low-P," which matches the new behavior; no retune.

### `prompts/gathering.txt`
- Add **one sentence** to the existing "Priority ratings" block noting that priorities now drive the agent's attention via the Priority & Focus pacing rule — reinforcing why a discriminating priority spread matters. Low-risk and optional; flagged here for review.

---

## Tests

| File | Change |
|---|---|
| `tests/test_tools.py` | Update the `format_template` golden-output assertions for the new headline line and regrouped pacing block. Add a check that the `priority_focus` text renders into the `# Pacing Instructions` block. |
| `tests/test_routes.py` | Add a case that `update_pacing` with `rule: "priority_focus"` dispatches to a `{section: "pacing", payload: {rule, text}}` update. |
| `tests/test_gathering_prompt.py` | Only if `gathering.txt` is touched — assert the new sentence is present. |
| `tests/duration.test.js` | No change (weighting unchanged). |

---

## Out of scope

- The downstream ElevenLabs interview-agent prompt (it consumes the export; it is not edited in this repo).
- Any change to the priority → duration weighting in `duration.js`.
- Reordering or renaming the existing 8 pacing rules.

---

## Regression notes

- A fresh template and the `balanced` preset both gain the new rule via `PACING_DEFAULTS`; every other preset gains it explicitly. There is no state in which `priority_focus` is undefined — and `format_template` defaults it to `""` defensively regardless.
- Existing exported templates produced before this change simply lacked the line; nothing downstream parses the pacing block positionally, so adding a leading rule is backward-safe.

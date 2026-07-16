# Coverage Guarantee — Design Spec
**Date:** 2026-07-16

## Problem

Same Golden Child evidence as the ordering spec, other half of the lesson.
v7.0's endgame rule was weak — "if time remains, revisit the most useful
earlier moment." Consequence: interview `4e7ccf39` (v7) **ran out of time before
reaching the advertising / proof topic and closed without it** — the single
most decision-relevant topic for an advertising-development study, lost.

v8.0 added an explicit **Closing Priority**: *"if Topic 10 (advertising) has not
been covered yet, go there now and cover its [Core] points."* Both v8 interviews
reached it. A named-topic backstop guaranteed the strategic topic was covered.

Our pacing model has the same hole v7 did. Two rules sit near this area
(`static/app.js`, `PACING_DEPTH_PRESETS`):

- **`priority_focus`** — describes what to *sacrifice* under time pressure (trim
  lowest-priority first). It never says to *protect* the must-hit topic.
- **`finish_line`** — handles reaching the end *early* (circle back / expand).

Neither handles **running out of time *before* reaching the end** — exactly the
case that killed `4e7ccf39`. And it now matters more: the ordering feature
(2026-07-16 ordering spec) deliberately positions the payoff topic *late*,
making it the topic most at risk of being cut off. Ordering positions the
payoff; this spec guarantees it is reached.

## Goal

Add a hard backstop to the endgame pacing rule: when time is nearly up and a
must-cover topic has not been reached, the interviewer jumps to it, covers its
`[Core]` points, and then closes — abandoning the current thread if needed.

## Decisions (from brainstorming)

- **Must-hit = topic priority 5.** Reuse the existing signal — the P:5
  definition already reads "must be covered in every interview regardless of
  time." No new flag, no UI. Today that promise is unenforced; this enforces it.
- **Hard jump, one topic.** Not a soft nudge, not all P:5s at once.
- **Tie-breaker = latest position in the guide.** If several P:5 topics are
  unreached, jump to the one that appears **latest**. Rationale:
  1. Position is a total order → always resolves to exactly one topic, fully
     deterministic, no secondary tie-break ever needed; an LLM applies it by eye.
  2. Composes with ordering — the payoff/evaluative topic is deliberately
     positioned late, so "latest uncovered P:5" *is* the intended payoff.
  3. Matches v8 — advertising sat late; the mechanical topics after it (brand
     battery, Golden Child) were low-priority, never P:5, so "latest P:5" lands
     on advertising, exactly what v8's hand-written rule named.
  - Assumption: mechanical late topics (recognition batteries) are not marked
    P:5. They shouldn't be; a mis-marked battery is a visible priority error the
    researcher can fix, not a silent failure.

## Non-goals

- The other deferred threads (verbatim control, short-interview ordering).
- Enforcing runtime interviewer behavior. This guarantee lives in the pacing
  rules the template *hands to* the downstream agent; we strengthen the
  instruction (as v8 did), we cannot enforce execution from the builder. Inherent
  to the architecture.

---

## Architecture

| Area | Change |
|---|---|
| `static/app.js` — `PACING_DEFAULTS.finish_line` | Prepend the coverage-backstop clause (balanced inherits this via `{...PACING_DEFAULTS}`). |
| `static/app.js` — `PACING_DEPTH_PRESETS` finish_line ×4 | Prepend the same backstop clause to `breadth`, `slightly_broad`, `slightly_deep`, `deep` (wording tuned to each voice; the backstop clause itself is uniform). |
| `prompts/gathering.txt` | One line tying the pair together: the late-positioned payoff topic must be marked P:5, because the endgame rule protects a P:5. |
| `tests/test_pacing_backstop.py` | New content-guard: read `static/app.js`, assert the backstop phrase appears in every `finish_line` (all 5 source occurrences). |

**Why extend `finish_line`, not add a 9th rule.** `finish_line` is already the
*endgame* rule; the new case is its complementary branch (running-out vs
finished-early), keyed off the same `remaining_minutes` signal, mutually
exclusive triggers. A new rule would change the pacing-rule count and the
`format_template` emission grouping (the fixed 1/3/3/1 layout at
`app.py:407–419`), and touch `PACING_DEFAULTS`, `PACING_LABELS`, all five
presets, and the `format_template` structure tests. Extending `finish_line`
changes only *rule text* — `format_template` interpolates whatever text is in
`sections.pacing['finish_line']`, so export is untouched.

---

## The backstop clause

Uniform across all five, prepended so it takes precedence over the
finished-early guidance. Contains the exact phrase **`the latest uncovered [P:5]
topic`** in every occurrence (the test keys on it):

> If time is nearly up and any [P:5] topic has not yet been reached, go straight
> to **the latest uncovered [P:5] topic**, cover its [Core] points, then begin
> closing — even if it means leaving the current thread.

### Resulting `finish_line` texts

**`PACING_DEFAULTS` (balanced):**
```
If time is nearly up and any [P:5] topic has not yet been reached, go straight to the latest uncovered [P:5] topic, cover its [Core] points, then begin closing — even if it means leaving the current thread. Otherwise, reaching the end of the Main Interview Guide does not signal the end of the interview. If you finish those topics early, you must utilize the following two options to fill the time until remaining_minutes is 3 or less:
  1. Circle Back: Revisit an earlier interesting moment to ask for "thicker" description (sensory details, specific emotions, or a deeper "why").
  2. Expansion: Pivot to the Expansion Topics at the bottom of this plan.
```

**`breadth`:**
```
If time is nearly up and any [P:5] topic has not yet been reached, go straight to the latest uncovered [P:5] topic, cover its [Core] points, then close warmly — even if it means leaving the current thread. Otherwise, reaching the end of the Main Interview Guide signals the end of the interview: begin closing warmly. If remaining_minutes is 5 or more, you may briefly revisit one topic that felt thin. Do not pivot to Expansion Topics.
```

**`slightly_broad`:**
```
If time is nearly up and any [P:5] topic has not yet been reached, go straight to the latest uncovered [P:5] topic, cover its [Core] points, then begin closing — even if it means leaving the current thread. Otherwise, reaching the end of the Main Interview Guide does not signal the end of the interview. If remaining_minutes is 5 or more, use one of these options to fill the time:
  1. Circle Back: Revisit an earlier interesting moment to draw out a little more detail.
  2. Expansion: Lightly touch on one Expansion Topic if it fits the conversation.
Close warmly once remaining_minutes is 3 or less.
```

**`slightly_deep`:**
```
If time is nearly up and any [P:5] topic has not yet been reached, go straight to the latest uncovered [P:5] topic, cover its [Core] points, then begin closing — even if it means leaving the current thread. Otherwise, reaching the end of the Main Interview Guide does not signal the end of the interview. Use the following to fill remaining time until remaining_minutes is 3 or less:
  1. Circle Back: Revisit an earlier interesting moment to ask for thicker description — a specific emotion, a sensory detail, or the deeper why.
  2. Expansion: Pivot to the Expansion Topics at the bottom of the plan.
```

**`deep`:**
```
If time is nearly up and any [P:5] topic has not yet been reached, go straight to the latest uncovered [P:5] topic, cover its [Core] points, then begin closing — even if it means leaving the current thread. Otherwise, reaching the end of the Main Interview Guide does not signal the end of the interview. You must use the following to fill the time until remaining_minutes is 3 or less:
  1. Circle Back: Revisit every moment that had depth potential. Push for sensory detail, specific emotions, and the deeper why behind what they shared. This is the primary tool at this depth.
  2. Expansion: Pivot to the Expansion Topics at the bottom of the plan.
```

The backstop is **uniform** (not softened at breadth): a hard guarantee should
not weaken with depth. Only the finished-early half varies by preset, unchanged
from today.

---

## Builder nudge (`prompts/gathering.txt`)

The guarantee only protects the payoff if the payoff is actually a P:5. Add one
line where ordering / priority guidance lives, connecting the two features:

> The topic you position late as the payoff (claims, proof, concept reaction)
> should be marked priority 5 — the interviewer's endgame rule guarantees a
> [P:5] topic is reached before closing, so P:5 is what protects that
> late-positioned topic from being cut off when time runs short.

Placed adjacent to the ordering bullet added by the ordering spec, so the two
read as a pair. No other builder change; the existing priority-discrimination
guidance already pushes the payoff toward P:5.

---

## Data flow (unchanged)

The depth slider → `applyDepthPreset()` overwrites `state.sections.pacing` with
the chosen preset (now carrying the backstop). Export → `format_template()`
interpolates `pacing['finish_line']` into the exported guide. The downstream
interviewer agent reads it. No mechanism changes — only the rule text the agent
receives.

## Testing

- **`tests/test_pacing_backstop.py`** (new; pytest, no API key needed — pure file
  read, consistent with the suite):
  ```python
  import os

  APP_JS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "app.js")

  def _app_js():
      with open(APP_JS, encoding="utf-8") as f:
          return f.read()

  def test_every_finish_line_has_coverage_backstop():
      text = _app_js()
      # One occurrence per source finish_line: PACING_DEFAULTS + 4 explicit
      # presets (balanced spreads from defaults, so no 6th).
      assert text.count("the latest uncovered [P:5] topic") == 5

  def test_backstop_names_the_p5_jump():
      text = _app_js()
      assert "[P:5] topic has not yet been reached" in text
  ```
- **Existing suites unchanged.** `format_template`'s tests
  (`tests/test_tools.py:109,143,214`) use dummy pacing values (`"H"`), so preset
  text edits don't touch them. No existing assertion targets the real
  `finish_line` text.
- **Rationale for a pytest content-guard** (not a node test): the preset text
  lives in `static/app.js`, which is DOM-coupled and not a clean importable
  module like `duration.js`. A text read from the existing pytest suite adds no
  new tooling or run command; a second node suite would.

## Build phases

1. **Pacing text** — edit `finish_line` in `PACING_DEFAULTS` + the 4 explicit
   presets; add `tests/test_pacing_backstop.py`. Green suite.
2. **Builder nudge** — add the one-line P:5/payoff connection to
   `gathering.txt`. (Optional companion assertion in
   `tests/test_gathering_prompt.py` if desired.)

## What is unchanged

- `format_template`, the pacing-rule count and grouping, `PACING_LABELS`,
  `update_pacing`, the depth-preset overwrite mechanism.
- The `priority_focus` rule and the priority system (reused, not modified).
- The ordering feature (this composes with it; no edits to it).

# Priority-Assignment Guidance in the Gathering Prompt — Design Spec
**Date:** 2026-06-29

## Overview

The gathering AI assigns a 1–5 priority to every topic and every core/probe item when it calls `add_topic`. The prompt already defines what each level *means* (the "Priority ratings" block at `prompts/gathering.txt:117`) and the Consolidation Gate already checks that "priorities discriminate (not all 3s)." What the prompt lacks is a *decision procedure* — something that helps the AI confidently choose 5 vs 4 vs 3 for a given item at call time, rather than reasoning from the rubric definitions each turn.

This is a **proactive quality improvement**, not a fix for an observed defect. There is no reported problem with current priority assignment; the goal is more calibrated, reliably discriminating spreads.

The change is **prompt-only**. No code, no corpus, no new tools, no schema changes. It touches `prompts/gathering.txt` and adds assertions to `tests/test_gathering_prompt.py`.

This is the surviving outcome of a brainstorm that started at "implement RAG in the priority slider." We considered and rejected two heavier paths: (1) enriching the `corpus/` coverage entries with per-dimension priority tiers that flow through the existing `<grounding>` block, and (2) using star ratings to drive RAG selection. Both were rejected — the gathering model (Sonnet) already knows which dimensions matter for a domain, so a corpus-tier signal would mostly annotate what the model infers anyway, at the cost of a corpus migration and `retrieve.py` schema changes. A prompt edit captures the consistency benefit far more cheaply.

---

## What changes

### Change 1 — "How to choose" decision procedure

In the **Priority ratings** block (`prompts/gathering.txt:117-125`), after the 1–5 rubric and before/with the existing "Set topic priority by how central…" sentence, add a concrete decision test:

> **How to choose:** Imagine the interview must end at the 70% mark. What would you protect at all costs? Those are your 5s. What would you skip without a second thought? Those are your 1–2s. Most items fall in between — force the spread, don't cluster at 3.

This gives the AI a single mental operation to run per item (a forced-triage thought experiment) instead of matching against five abstract definitions. It reinforces, rather than replaces, the existing rubric and the Consolidation Gate's discrimination check.

**No probe cap.** An earlier draft included a guardrail capping probe priority at 3. It was removed by design decision: a probe that maps to a high-value thin-answer path can be critically important depending on how the conversation unfolds, so probes stay fully flexible. The existing rubric line — "set item priority by how important that objective is within its topic" — already lets a critical probe earn a 4 or 5 on its own merits.

### Change 2 — Annotate the worked example with priority reasoning

The grocery-store worked example (`prompts/gathering.txt:95-100`) already shows `add_topic` calls carrying priority values, but gives no reason for those specific numbers. Add a brief reasoning annotation after the tool calls — explaining *why* each priority was chosen — so the AI has a concrete pattern to imitate. For example: topic 2 ("Finding what they came for") is a 5 because it is the core purpose of the visit; arrival is a 4 because it sets context but isn't the point of the research; the probes are 3 because they only matter if the core reveals friction.

The annotation must phrase probe values as *role-specific to this example*, not as a general rule that probes are lower — consistent with the no-cap decision above. Worked examples are the most heavily used teaching device in this prompt (see the extensive objective-writing examples), and LLMs imitate annotated examples more reliably than they apply abstract rules; this is the highest-leverage part of the change.

---

## What stays unchanged

- The 1–5 rubric definitions (5 Critical … 1 Minimal) — correct as written.
- The "Set topic priority by how central the theme is… set item priority by how important that objective is within its topic" guidance.
- The downstream-use sentence noting priorities feed the "Priority & Focus" pacing rule.
- The Consolidation Gate's "Priorities discriminate (not all 3s)" check.
- All code: `app.py`, `static/app.js`, `static/duration.js`, `retrieve.py`, the `corpus/`, and every tool schema.

---

## Tests

| File | Change |
|---|---|
| `tests/test_gathering_prompt.py` | Add assertion(s) that the "How to choose" decision procedure text is present in the prompt (substring check on a distinctive phrase, e.g. the 70%-mark triage test), matching the existing string-assertion style. Add an assertion that the worked example carries priority reasoning. |

No other suite is affected — there is no code change for `tests/test_tools.py`, `tests/test_routes.py`, `tests/test_retrieve.py`, or `tests/duration.test.js` to cover.

The assertions must key on phrasing distinctive enough not to match incidentally elsewhere in the prompt, but not so verbatim that ordinary copy-edits to the prompt break the test. Prefer a short, stable anchor phrase over matching a whole sentence.

---

## Out of scope

- Any RAG / corpus change (the rejected alternative). Coverage entries keep their flat `dimensions` string arrays.
- Using priority values to drive RAG selection.
- Changing the priority → duration weighting in `static/duration.js` (`priorityFactor`).
- The downstream interview-agent prompt that consumes the export.
- Any change to how priority is rendered, exported, or stored.

---

## Risks & regression notes

- **Prompt bloat / dilution.** The gathering prompt is already long. Both additions are short (one decision test, one annotation block) and live inside sections that already cover their topic, so they extend rather than introduce structure. Net addition is a handful of lines.
- **Over-steering toward extremes.** The "protect at all costs / skip without a second thought" framing could push the model toward a bimodal 5/1 spread. The "most items fall in between" clause is the counterweight; the worked-example annotation models a realistic 5/4/3 mix to reinforce the middle.
- **No behavioral test of model output.** The tests verify the prompt *contains* the guidance, not that the model produces better spreads — consistent with how `test_gathering_prompt.py` already works (it asserts on prompt content, not model behavior). Validation of actual spread quality is manual/qualitative, as with prior prompt-craft changes in this repo.

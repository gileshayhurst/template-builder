# Pacing Preset Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply 7 targeted string fixes to the non-balanced pacing presets in `PACING_DEPTH_PRESETS` to improve clarity and consistency with the well-tested balanced preset.

**Architecture:** All changes are string edits inside one constant (`PACING_DEPTH_PRESETS`) in `static/app.js`. No new files, no structural changes, no test changes needed (the test suite does not cover pacing strings).

**Tech Stack:** Vanilla JS (`static/app.js`)

---

## Files

- Modify: `static/app.js` — lines 26–66, inside `PACING_DEPTH_PRESETS`

---

### Task 1: Apply all 7 pacing string fixes

**Files:**
- Modify: `static/app.js`

**Reference — current state of `PACING_DEPTH_PRESETS` (lines 25–67):**

```js
const PACING_DEPTH_PRESETS = {
  breadth: {
    do_not_rush: "Keep the conversation moving. If a participant gives a brief answer and the response is clear, accept it and move on. Use probes only when an answer is unclear or incomplete.",
    core_vs_probe: "Treat [Core] points as must-ask items. Skip most [Probe] points unless they arise naturally. Prioritise covering all topics over depth in any one area.",
    one_ask_per_turn: "Each turn should contain exactly one question. Do not combine follow-up questions or add sub-questions.",
    keep_light: "Keep questions short and easy to answer. Avoid anything that requires extended reflection.",
    follow_signals: "When something interesting emerges, note it briefly and return immediately to the guide. Do not follow tangents.",
    original_followups: "Stick closely to the interview guide. Only ask questions not in the guide when explicitly necessary to clarify something.",
    selective_probing: "Use probes sparingly. Prefer moving to the next topic over dwelling on the current one.",
    finish_line: "Reaching the end of the Main Interview Guide signals the end of the interview. If a few minutes remain, close warmly. Do not pivot to Expansion Topics."
  },
  slightly_broad: {
    do_not_rush: "Keep the conversation flowing. Use probes when an answer seems incomplete, but do not linger. Accept brief answers for straightforward questions.",
    core_vs_probe: "Treat [Core] points as priorities. Use [Probe] points selectively — when an answer is thin or a topic clearly needs more colour.",
    one_ask_per_turn: "Each turn should usually contain one main question. You may add a second only when it flows naturally from the first answer.",
    keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
    follow_signals: "When something specific or emotional emerges, follow it with one brief follow-up, then return to the guide.",
    original_followups: "You may ask original follow-up questions when they would clearly deepen understanding. Keep them brief.",
    selective_probing: "Use follow-up probes selectively. Prefer coverage over depth when time is limited.",
    finish_line: "Reaching the end of the Main Interview Guide does not necessarily signal the end of the interview. If time remains, revisit one interesting moment briefly before closing."
  },
  balanced: { ...PACING_DEFAULTS },
  slightly_deep: {
    do_not_rush: "If a participant gives brief answers, use [Probe] points to unlock more detail. Take time on answers that hint at something richer.",
    core_vs_probe: "Treat [Core] points as priorities and [Probe] points as important tools. Use most probes unless time pressure is significant.",
    one_ask_per_turn: "Each turn should usually contain one main question. You may combine a second when it is tightly related, easy to answer in the same thought, and not from a different part of the story.",
    keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
    follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it — ask a clarifying or deepening question — then return to the guide.",
    original_followups: "Ask original follow-up questions when they would help uncover better insight. Good intuition is an asset here.",
    selective_probing: "Use probes thoughtfully. When an answer feels thin or opens a door, follow it. Do not skip probes by default.",
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. Use Circle Back and Expansion Topics to fill remaining time until remaining_minutes is 3 or less."
  },
  deep: {
    do_not_rush: "Prioritize depth over coverage. If the participant gives brief answers, use every available [Probe] point to unlock detail. Never accept a thin answer when a richer one is possible.",
    core_vs_probe: "Treat both [Core] and [Probe] points as essential. Use all probes unless the participant has already addressed them or time is critically short.",
    one_ask_per_turn: "Each turn should contain one focused question. You may add a tightly related follow-up when it deepens the current answer rather than changing the subject.",
    keep_light: "Keep individual questions focused and clear, but do not shy away from questions that require genuine reflection or pause.",
    follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it fully. Ask multiple deepening questions before returning to the guide. These moments often yield the richest insight.",
    original_followups: "Actively ask original follow-up questions not in the guide whenever they would surface deeper understanding. Treat the guide as a floor, not a ceiling.",
    selective_probing: "Use every relevant probe. Probes are not optional tools — they are the primary mechanism for achieving depth. Only skip a probe if the participant has already fully addressed it.",
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. You must use Circle Back and Expansion Topics to fill the time until remaining_minutes is 3 or less. Circle Back is particularly important at this depth — revisit every moment that had depth potential and push for sensory detail, specific emotions, and deeper explanation."
  }
};
```

---

- [ ] **Step 1: Fix `breadth.do_not_rush` — change "unclear or incomplete" to "thin or unclear"**

In `static/app.js`, replace:
```
    do_not_rush: "Keep the conversation moving. If a participant gives a brief answer and the response is clear, accept it and move on. Use probes only when an answer is unclear or incomplete.",
```
With:
```
    do_not_rush: "Keep the conversation moving. If a participant gives a brief answer and the response is clear, accept it and move on. Use probes only when an answer is thin or unclear.",
```

- [ ] **Step 2: Fix `breadth.finish_line` — add `remaining_minutes` cue**

Replace:
```
    finish_line: "Reaching the end of the Main Interview Guide signals the end of the interview. If a few minutes remain, close warmly. Do not pivot to Expansion Topics."
```
With:
```
    finish_line: "Reaching the end of the Main Interview Guide signals the end of the interview. Begin closing warmly. If remaining_minutes is 5 or more, you may briefly revisit one topic that felt thin. Do not pivot to Expansion Topics."
```

- [ ] **Step 3: Fix `slightly_broad.one_ask_per_turn` — sharpen "flows naturally"**

Replace:
```
    one_ask_per_turn: "Each turn should usually contain one main question. You may add a second only when it flows naturally from the first answer.",
```
With:
```
    one_ask_per_turn: "Each turn should usually contain one main question. You may add a second only when it is tightly related and easy to answer in the same breath.",
```

- [ ] **Step 4: Fix `slightly_broad.finish_line` — add Expansion Topics, `remaining_minutes`, numbered structure**

Replace:
```
    finish_line: "Reaching the end of the Main Interview Guide does not necessarily signal the end of the interview. If time remains, revisit one interesting moment briefly before closing."
```
With:
```
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. If remaining_minutes is 5 or more, use one of these options to fill the time:\n  1. Circle Back: Revisit an earlier interesting moment to draw out a little more detail.\n  2. Expansion: Lightly touch on one Expansion Topic if it fits the conversation.\nClose warmly once remaining_minutes is 3 or less.",
```

- [ ] **Step 5: Fix `slightly_deep.original_followups` — replace vague phrase with actionable direction**

Replace:
```
    original_followups: "Ask original follow-up questions when they would help uncover better insight. Good intuition is an asset here.",
```
With:
```
    original_followups: "Ask original follow-up questions when they would help uncover better insight. Lean into moments that feel rich, unresolved, or surprising.",
```

- [ ] **Step 6: Fix `slightly_deep.finish_line` — define Circle Back, add numbered structure**

Replace:
```
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. Use Circle Back and Expansion Topics to fill remaining time until remaining_minutes is 3 or less."
```
With:
```
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. Use the following to fill remaining time until remaining_minutes is 3 or less:\n  1. Circle Back: Revisit an earlier interesting moment to ask for thicker description — a specific emotion, a sensory detail, or the deeper why.\n  2. Expansion: Pivot to the Expansion Topics at the bottom of the plan.",
```

- [ ] **Step 7: Fix `deep.finish_line` — add numbered structure, clarify Circle Back as primary tool**

Replace:
```
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. You must use Circle Back and Expansion Topics to fill the time until remaining_minutes is 3 or less. Circle Back is particularly important at this depth — revisit every moment that had depth potential and push for sensory detail, specific emotions, and deeper explanation."
```
With:
```
    finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. You must use the following to fill the time until remaining_minutes is 3 or less:\n  1. Circle Back: Revisit every moment that had depth potential. Push for sensory detail, specific emotions, and the deeper why behind what they shared. This is the primary tool at this depth.\n  2. Expansion: Pivot to the Expansion Topics at the bottom of the plan."
```

- [ ] **Step 8: Verify the file still parses**

Run:
```
node -e "const fs=require('fs'); const src=fs.readFileSync('static/app.js','utf8'); console.log('parse ok');"
```
Expected output: `parse ok`

If you get a syntax error, re-read the file around lines 25–67 and find the malformed string. Common causes: mismatched quotes, trailing comma missing or extra, unclosed backtick.

- [ ] **Step 9: Commit**

```bash
git add static/app.js
git commit -m "fix: refine non-balanced pacing preset instructions for agent compatibility"
```

# Airtight Templates & Duration Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the gathering AI produce export-ready, airtight interview topics, and turn the inert duration slider into a live coach that suggests concrete, one-click moves to hit the target length.

**Architecture:** Part 1 is a full rewrite of `prompts/gathering.txt` (prompt-only) guarded by a content-presence test. Part 2 extracts the duration math into a new DOM-free `static/duration.js` module (testable with Node's built-in runner), adds a pure suggestion engine, and renders a suggestion area with Apply/Undo in the settings strip. The two parts share no files and can be built in either order.

**Tech Stack:** Python/Flask, vanilla JS (classic `<script>` globals, no bundler), `node:test` for JS unit tests, pytest for Python.

**Spec:** `docs/superpowers/specs/2026-06-17-airtight-templates-and-duration-coach-design.md`

**Division of labour:** the AI owns *quality*; the duration coach owns *fit*.

---

## PART 1 — Airtight Gathering Prompt

### Task 1: Rewrite the gathering prompt

**Files:**
- Create: `tests/test_gathering_prompt.py`
- Modify: `prompts/gathering.txt` (full rewrite)

- [ ] **Step 1: Write the failing test**

Create `tests/test_gathering_prompt.py`. It asserts the prompt contains the structural anchors that encode each airtight rule, so the rules can't silently disappear later.

```python
import os

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "gathering.txt"
)


def _prompt_text():
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().lower()


def test_prompt_has_consumer_framing():
    assert "live interview with a real person" in _prompt_text()


def test_prompt_has_objective_rules():
    text = _prompt_text()
    assert "one objective = one ask" in text
    assert "exploratory verbs" in text
    assert "determine" in text          # banned-verb list present
    assert "specificity floor" in text


def test_prompt_has_core_probe_definitions():
    text = _prompt_text()
    assert "askable cold" in text
    assert "new direction" in text


def test_prompt_has_focus_anchor_rule():
    assert "experience anchor" in _prompt_text()


def test_prompt_has_consolidation_gate():
    text = _prompt_text()
    assert "consolidation gate" in text
    assert "no two topics overlap" in text


def test_prompt_has_anti_pattern_table():
    text = _prompt_text()
    assert "red flag" in text
    assert "double-barreled" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_gathering_prompt.py -v`
Expected: FAIL — the current prompt lacks these anchors (e.g. `assert "consolidation gate" in text` fails).

- [ ] **Step 3: Rewrite the prompt**

Replace the **entire** contents of `prompts/gathering.txt` with the text below. Every anchor the test checks appears verbatim.

```
You are a research design consultant helping a client build a qualitative interview guide template.

## What your output does (read this first)

Everything you put in this template is handed to a SEPARATE AI agent that will conduct a live interview with a real person. That agent follows your objectives literally and CANNOT ask you for clarification mid-interview. A vague, compound, or leading objective therefore becomes a flawed question asked to a real human, and the data is lost. Precision is the whole job.

Your goal is to understand the client's research goals and build a complete, airtight interview template, using both what the client tells you AND your own general knowledge of the topic domain.

## Your approach
- Open with: "Tell me about the research experience you want to explore. What's the topic, and who will you be interviewing?"
- Ask ONE question at a time. Never combine multiple questions in one message.
- After EACH client message, before asking your next question, call every tool you can justify. Use inference freely — topics can always be refined or removed.
- Fill sections incrementally — never wait until the end to call tools.
- Before declaring the template ready, run the Consolidation Gate (below). Only then say: "I think we have a solid template. Take a look at the right panel and let me know if you'd like to adjust anything before exporting."

## Eager inference rule
After any message that identifies a research topic or domain, immediately:
1. Call update_metadata with the best title you can infer — do not wait for confirmation.
2. Call add_topic for every obvious main theme you can predict from general knowledge — aim for 5–8 topics. These are drafts the client can refine or remove.
3. Call update_focus if the framing implies what experience to anchor on.
A populated template is always better than an empty one. The quality rules below apply to these first drafts too; the Consolidation Gate cleans up what slips through.

## Writing objectives (the core craft)
Each core/probe item is an OBJECTIVE: an instruction telling the interviewer what to accomplish — never a literal question to read aloud. Six rules:

1. One objective = one ask. Never join two asks with "and". Two things become two separate items. This prevents double-barreled questions where the participant answers one half and the other half is lost.
2. Use exploratory verbs, never diagnostic ones. Use: explore, capture, walk through, surface, trace, draw out, understand how/why. Avoid: determine, assess, evaluate, confirm, verify, identify whether. Diagnostic verbs collapse into yes/no or rating questions; exploratory verbs open up narrative.
3. Never assume an experience occurred — use conditional framing. Not "Understand why checkout was frustrating" (assumes frustration) but "Explore how checkout unfolded and how the participant felt about it" (lets them reveal positive, negative, or neutral).
4. Prefer episodic over attitudinal. Where the interview anchors on a specific occasion, phrase objectives to draw out what actually happened, not general opinions. Episodic memory yields richer, less rationalized data.
5. Specificity floor. Every objective must name the concrete thing sought — a moment, decision, friction, or feeling. "Understand their experience" is contentless and banned.
6. Instructions, not scripts. Never write the literal question wording; the interviewer phrases the actual question.

## Core vs. Probe
The downstream pacing rules treat these differently, so placement matters.
- Core = the essential moves that open and carry the topic. Each must be askable cold, with no prior answer. The first core item is the topic's natural opener.
- Probe = optional follow-ups that deepen a thin or interesting answer. A probe assumes the participant has already spoken, and must add a NEW direction — a sensory detail, a specific example, the "why", a contrast — never a reworded core.
Placement tests:
- If an item only makes sense AFTER the participant has spoken, it is a probe, not a core.
- If a probe could swap with its core and nothing would break, the probe is redundant — rewrite it to add direction.
Every topic must carry at least one probe that maps to a plausible thin-answer path, so the interviewer always has a depth tool.

## Interview focus
The focus is the single experience the interview returns to — an experience anchor, not a research goal. Not "Understand what drives loyalty" (a goal that pushes the interviewer to confirm a hypothesis) but "The participant's recent visits to [store], anchored on the most recent memorable one" (an anchor that follows lived narrative). Where the research centres on one occasion, name that occasion and its boundaries.

## Topic set (checked holistically in the Consolidation Gate)
- Non-overlap: no two topics target the same underlying thing. Each must have a distinct angle. Merge or sharpen overlaps.
- Coverage: cover the domain's essential dimensions; use domain knowledge to catch a missing essential theme.
- Ordering: follow the funnel — easy/concrete warm-up first, then core themes, then sensitive/evaluative, then a reflective close. Never lead with an emotionally loaded topic.
- Count: aim for roughly 5–8 topics. Do NOT try to hit a specific interview length — the client fine-tunes length with the duration controls in the UI.
- Priority spread: priorities must discriminate. Not everything is a 3. Priorities are the interviewer's triage signal under time pressure; a flat distribution gives no signal.

## Consolidation Gate (run before declaring the template ready)
Re-read the ENTIRE assembled guide and check it against this list, applying fixes via tool calls, then briefly tell the client what you changed:
- [ ] Every objective: single ask, exploratory verb, no assumption, specific
- [ ] No two topics overlap; each has a distinct angle
- [ ] Topics ordered easy to sensitive to reflective
- [ ] Every topic has at least one probe that adds direction; no probe restates its core
- [ ] Focus is an experience anchor, not a research goal
- [ ] Priorities discriminate (not all 3s)
- [ ] Topic count is reasonable (≈5–8)

## Anti-patterns (never ship these)
| Red flag | Why it breaks | Rewrite |
| "and" joining two asks | double-barreled question | split into two items |
| "determine/confirm if…" | yes/no dead-end | "explore how/why…" |
| assumes an emotion or event | leading question | use conditional framing |
| "their experience/thoughts" alone | contentless | name the specific thing |
| probe restates the core | no depth tool | add a new direction |
| sensitive topic placed first | guarded answers | move it later in the funnel |

## Worked example
If the client says "I want a comprehensive interview about my grocery store," immediately call:
- update_metadata: title = "Grocery Store Experience"
- add_topic: index=1, title="Arrival and first impressions", priority=4, core=[{"text":"Walk through how the participant arrived and entered the store on their most recent visit.","priority":4}], probe=[{"text":"Capture what first caught their attention on the way in.","priority":3}]
- add_topic: index=2, title="Finding what they came for", priority=5, core=[{"text":"Trace how the participant looked for the items they came to buy.","priority":5}], probe=[{"text":"Surface any moment an item was hard to locate and what they did next.","priority":3}]
- add_topic: index=3, title="Checkout", priority=4, core=[{"text":"Walk through how the checkout unfolded, from joining the queue to leaving.","priority":4}], probe=[{"text":"Draw out anything that felt smooth or frustrating, if anything stood out.","priority":3}]
Then ask your clarifying question. Note the objectives: single ask, exploratory verbs, conditional framing, and every topic has a directional probe.

## Sections to fill (rough order)
1. update_metadata — as soon as any topic or domain is mentioned
2. update_focus — once you know what experience to anchor on
3. add_topic — pre-populate from domain knowledge immediately, then refine
4. update_expansion — near the end, after main topics are established
5. update_pacing — ONLY if the client explicitly requests a change; otherwise leave UI defaults
6. remove_topic — if the client asks to drop a topic

## Questions to cover (one per message)
- Should the interview anchor on one specific recent occasion, or explore more broadly?
- Who will be interviewed?
- Any themes to add, remove, or adjust from the draft?
- What secondary areas could fill time if the interview finishes early? (Expansion topics)
- Any special pacing preferences? (Most clients use defaults — only ask if they raise it)

## Priority ratings
Every add_topic call must include a priority (1–5) for the topic and for each core and probe item:
- 5 Critical: must be covered in every interview regardless of time
- 4 High: important, normally covered
- 3 Medium: standard relevance; use when unsure
- 2 Low: useful if time permits
- 1 Minimal: rarely needed; for completeness
Set topic priority by how central the theme is to the research goal; set item priority by how important that objective is within its topic. Never omit priority.

## Rules
- Never ask more than one question per message.
- Always call tools before your next question — never batch tools at the end.
- Be warm and conversational — this is a collaborative design session, not a form.
```

- [ ] **Step 4: Run the new test to verify it passes**

Run: `pytest tests/test_gathering_prompt.py -v`
Expected: PASS (all six tests green).

- [ ] **Step 5: Run the full suite to confirm no regression**

Run: `pytest tests/ -v`
Expected: PASS — the existing `tests/test_tools.py` is unaffected (no code changed).

- [ ] **Step 6: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "feat: rework gathering prompt for airtight objectives + consolidation gate"
```

---

### Task 2: Manual smoke test of the gathering conversation

**Files:** none (verification only)

- [ ] **Step 1: Start the app**

Run (PowerShell, not Bash): `python main.py`
The browser opens at `localhost:5000`.

- [ ] **Step 2: Run a sample conversation**

Type: "I want to interview recent customers about their experience at my coffee shop."
Confirm:
- 5–8 topics populate immediately.
- Each objective is a single ask using an exploratory verb (explore/walk through/capture/etc.), with no "and"-joined compound asks and no assumed emotions.
- Every topic has at least one probe that adds a new direction.

- [ ] **Step 3: Trigger the consolidation gate**

Continue until the AI says the template is ready. Confirm it explicitly states what it changed during a final review pass (e.g. merging an overlap, reordering, sharpening an objective) before declaring done.

- [ ] **Step 4: Stop the app**

Find the PID: `netstat -ano | Select-String ':5000.*LISTENING'`
Then: `Stop-Process -Id <PID> -Force`

No commit (verification task).

---

## PART 2 — Duration Coach

### Task 3: Extract the duration math into a testable module

**Files:**
- Create: `static/duration.js`
- Create: `tests/duration.test.js`

The estimate logic currently lives inline in `static/app.js` (`priorityFactor`, `estimateDuration`) and reads global `state`. We move the pure math into a DOM-free module so it can be unit-tested and reused by the suggestion engine. The module works as a browser global (`window.DurationEngine`) and as a Node CommonJS module (`module.exports`).

- [ ] **Step 1: Write the failing test**

Create `tests/duration.test.js`. Expected values are computed from the existing formula (`priorityFactor(p) = 0.5 + (p-1)*0.25`; depth factor `0.65`→`1.8`; base `+0.5`; expansion `+0.2` each; focus `+0.5`; clamp `[2,90]`; round).

```javascript
const { test } = require('node:test');
const assert = require('node:assert');
const D = require('../static/duration.js');

test('priorityFactor scales 0.5 .. 1.5', () => {
  assert.strictEqual(D.priorityFactor(1), 0.5);
  assert.strictEqual(D.priorityFactor(3), 1.0);
  assert.strictEqual(D.priorityFactor(5), 1.5);
  assert.strictEqual(D.priorityFactor(undefined), 1.0); // defaults to 3
});

test('estimateDurationFor matches known values across depths', () => {
  const sections = {
    topics: [
      { priority: 4, core: [{ priority: 4 }, { priority: 3 }], probe: [{ priority: 2 }] },
      { priority: 5, core: [{ priority: 5 }], probe: [] },
    ],
    expansion: ['a', 'b'],
    focus: 'x',
  };
  assert.strictEqual(D.estimateDurationFor(sections, 50), 4);  // factor 1.0
  assert.strictEqual(D.estimateDurationFor(sections, 100), 7); // factor 1.8
  assert.strictEqual(D.estimateDurationFor(sections, 0), 3);   // factor 0.65
});

test('estimateDurationFor returns floor of 2 for empty topics', () => {
  assert.strictEqual(D.estimateDurationFor({ topics: [], expansion: [], focus: '' }, 50), 2);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test tests/duration.test.js`
Expected: FAIL — `Cannot find module '../static/duration.js'`.

- [ ] **Step 3: Create the module**

Create `static/duration.js`:

```javascript
// Pure, DOM-free duration math + suggestion engine.
// Loaded in the browser as window.DurationEngine (classic script, before app.js),
// and required directly in Node tests.
(function () {
  const TOLERANCE = 2; // minutes; within this band the template is "on target"

  function priorityFactor(p) {
    return 0.5 + ((p ?? 3) - 1) * 0.25;
  }

  function depthFactorFor(v) {
    return v < 50 ? 1.0 - ((50 - v) / 50) * 0.35 : 1.0 + ((v - 50) / 50) * 0.8;
  }

  // Clamped but UN-rounded estimate. Suggestion deltas use this so sub-minute
  // moves are compared honestly before rounding.
  function estimateRawFor(sections, depthValue) {
    const topics = (sections && sections.topics) || [];
    if (topics.length === 0) return 2;
    let raw = 0;
    for (const t of topics) {
      raw += 0.8 * priorityFactor(t.priority ?? 3);
      const core = t.core || [];
      for (let i = 1; i < core.length; i++) raw += 0.2 * priorityFactor(core[i].priority ?? 3);
      for (const p of (t.probe || [])) raw += 0.1 * priorityFactor(p.priority ?? 3);
    }
    raw += 0.5;
    raw += ((sections.expansion || []).length) * 0.2;
    if (sections.focus) raw += 0.5;
    raw *= depthFactorFor(depthValue);
    return Math.min(90, Math.max(2, raw));
  }

  // Rounded estimate — what the bar displays.
  function estimateDurationFor(sections, depthValue) {
    return Math.round(estimateRawFor(sections, depthValue));
  }

  const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor };
  if (typeof window !== 'undefined') window.DurationEngine = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `node --test tests/duration.test.js`
Expected: PASS (3 tests, all assertions green).

- [ ] **Step 5: Commit**

```bash
git add static/duration.js tests/duration.test.js
git commit -m "feat: extract pure duration math into testable duration.js module"
```

---

### Task 4: Wire app.js to the module

**Files:**
- Modify: `templates/index.html:48` (add script tag)
- Modify: `static/app.js:82-113` (replace `priorityFactor` + `estimateDuration` with a wrapper)

- [ ] **Step 1: Load the module before app.js**

In `templates/index.html`, the body currently ends with `<script src="/static/app.js"></script>`. Add the duration module immediately before it so the global is set first:

```html
  <script src="/static/duration.js"></script>
  <script src="/static/app.js"></script>
```

- [ ] **Step 2: Replace the inline math in app.js**

In `static/app.js`, delete the entire `priorityFactor` function (lines 82–84) and the entire `estimateDuration` function (lines 86–113), and replace both with this single wrapper:

```javascript
function estimateDuration() {
  return DurationEngine.estimateDurationFor(state.sections, state.depthSliderValue);
}
```

Leave `durationViewModel`, `getDepthPreset`, `applyDepthPreset`, and everything else unchanged — `durationViewModel` already calls `estimateDuration()`, which now delegates to the module. `priorityFactor` is not referenced anywhere else in app.js.

- [ ] **Step 3: Verify the existing Python suite still passes**

Run: `pytest tests/ -v`
Expected: PASS (unaffected — no Python changed).

- [ ] **Step 4: Manual check that the estimate still works**

Run `python main.py`. Build a couple of topics via chat. Confirm the "Est: N min" label and the amber estimate bar still update as topics are added and as the depth slider moves (behaviour identical to before the refactor). Stop the app (`Stop-Process` per Task 2).

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/app.js
git commit -m "refactor: app.js uses DurationEngine for the duration estimate"
```

---

### Task 5: Build the suggestion engine

**Files:**
- Modify: `static/duration.js` (add `applySuggestion`, `generateSuggestions`, update exports)
- Modify: `tests/duration.test.js` (add engine tests)

The engine is pure: `generateSuggestions(sections, target, depthValue)` returns up to 3 ranked descriptor objects `{ type, label, detail, deltaMin, ... }`. `applySuggestion(sections, depthValue, s)` returns a deep-cloned `{ sections, depthValue }` with the move applied — used both to compute deltas here and to perform the real mutation in app.js. Depth moves carry a `toValue`; their pacing side effect is handled in app.js, not here (pacing text does not affect the estimate).

Quality-cost ranking (`_cls`, lower = more quality-preserving, ranked first):
- Over target: drop a probe (0) → drop a non-opening core point (2) → remove a whole topic (3) → reduce depth (4).
- Under target: add probes to a topic that has none (0) → promote an expansion topic (1) → increase depth (2) → add a topic (3).

Within a tier, lower `_cut` (the priority of what's cut) ranks first, then whichever lands closest to the target. Moves that round to 0 minutes, or that overshoot the target by more than doing nothing, are dropped.

- [ ] **Step 1: Write the failing tests**

Add to `tests/duration.test.js` (expected values are computed from the formula in Task 3):

```javascript
test('over target: removes the lowest-priority topic first', () => {
  const sections = {
    topics: [
      { title: 'Keep1', priority: 5, core: [{ priority: 5 }], probe: [] },
      { title: 'Keep2', priority: 5, core: [{ priority: 5 }], probe: [] },
      { title: 'Drop',  priority: 2, core: [{ priority: 2 }], probe: [] },
    ],
    expansion: [], focus: '',
  };
  // est at depth 100 = 6 min; target 2 -> 4 min over.
  const s = D.generateSuggestions(sections, 2, 100);
  assert.ok(s.length > 0);
  assert.strictEqual(s[0].type, 'remove_topic');
  assert.strictEqual(s[0].topicPos, 2);          // the P2 "Drop" topic
  assert.strictEqual(s[0].deltaMin, -1);
  assert.match(s[0].label, /Drop/);
  assert.match(s[0].detail, /saves/);
});

test('under target: suggests positive moves, none with zero delta', () => {
  const sections = {
    topics: [
      { title: 'T1', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T2', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T3', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T4', priority: 3, core: [{ priority: 3 }], probe: [] },
      { title: 'T5', priority: 3, core: [{ priority: 3 }], probe: [] },
    ],
    expansion: ['E1', 'E2'], focus: 'x',
  };
  // est at depth 25 = 4 min; target 20 -> well under.
  const s = D.generateSuggestions(sections, 20, 25);
  assert.ok(s.length > 0);
  assert.ok(s.every((c) => c.deltaMin > 0));
  assert.strictEqual(s[0].type, 'raise_depth');
  assert.strictEqual(s[0].toValue, 50);
  assert.strictEqual(s[0].deltaMin, 1);
});

test('on target returns no suggestions', () => {
  const sections = { topics: [{ priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  const est = D.estimateDurationFor(sections, 50);
  assert.deepStrictEqual(D.generateSuggestions(sections, est, 50), []);
});

test('no target returns no suggestions', () => {
  const sections = { topics: [{ priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  assert.deepStrictEqual(D.generateSuggestions(sections, 0, 50), []);
});

test('never removes the last remaining topic', () => {
  const sections = { topics: [{ title: 'Solo', priority: 5, core: [{ priority: 5 }], probe: [] }], expansion: [], focus: '' };
  const s = D.generateSuggestions(sections, 2, 100);
  assert.ok(s.every((c) => c.type !== 'remove_topic'));
});

test('applySuggestion is pure (does not mutate input)', () => {
  const sections = { topics: [{ title: 'A', priority: 3, core: [{ priority: 3 }], probe: [] }, { title: 'B', priority: 3, core: [{ priority: 3 }], probe: [] }], expansion: [], focus: '' };
  const before = JSON.stringify(sections);
  D.applySuggestion(sections, 50, { type: 'remove_topic', topicPos: 0 });
  assert.strictEqual(JSON.stringify(sections), before);
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/duration.test.js`
Expected: FAIL — `D.generateSuggestions is not a function`.

- [ ] **Step 3: Implement the engine**

In `static/duration.js`, add the following functions inside the IIFE, immediately after `estimateDurationFor`:

```javascript
  function clone(sections) {
    return typeof structuredClone === 'function'
      ? structuredClone(sections)
      : JSON.parse(JSON.stringify(sections));
  }

  function maxIndex(topics) {
    return topics.reduce((m, t) => Math.max(m, t.index || 0), 0);
  }

  // Apply a sections-mutating suggestion, returning a fresh clone.
  // Depth moves (lower_depth/raise_depth) are handled by the caller; for delta
  // computation they are simulated via estimateRawFor(sections, toValue).
  function applySuggestion(sections, depthValue, s) {
    const next = clone(sections);
    const topics = next.topics || (next.topics = []);
    if (s.type === 'remove_topic') {
      topics.splice(s.topicPos, 1);
    } else if (s.type === 'remove_item') {
      topics[s.topicPos][s.itemType].splice(s.itemIndex, 1);
    } else if (s.type === 'add_probes') {
      const t = topics[s.topicPos];
      t.probe = t.probe || [];
      for (let i = 0; i < s.count; i++) t.probe.push({ text: '', priority: 3 });
    } else if (s.type === 'promote_expansion') {
      const title = (next.expansion || [])[s.expansionIndex];
      next.expansion.splice(s.expansionIndex, 1);
      topics.push({ index: maxIndex(topics) + 1, title, priority: 3, core: [{ text: '', priority: 3 }], probe: [] });
    } else if (s.type === 'add_topic') {
      topics.push({ index: maxIndex(topics) + 1, title: '', priority: 3, core: [{ text: '', priority: 3 }], probe: [] });
    }
    return { sections: next, depthValue };
  }

  function candidateDelta(sections, depthValue, baseRaw, c) {
    if (c.type === 'lower_depth' || c.type === 'raise_depth') {
      return Math.round(estimateRawFor(sections, c.toValue) - baseRaw);
    }
    const r = applySuggestion(sections, depthValue, c);
    return Math.round(estimateRawFor(r.sections, depthValue) - baseRaw);
  }

  function generateSuggestions(sections, target, depthValue) {
    if (!target || target <= 0) return [];
    const est = estimateDurationFor(sections, depthValue);
    const gap = est - target;
    if (Math.abs(gap) <= TOLERANCE) return [];

    const baseRaw = estimateRawFor(sections, depthValue);
    const topics = sections.topics || [];
    let cands = [];

    if (gap > 0) {
      // OVER target — trim, least valuable first.
      topics.forEach((t, ti) => {
        (t.probe || []).forEach((p, ii) => cands.push({
          type: 'remove_item', topicPos: ti, itemType: 'probe', itemIndex: ii,
          _cls: 0, _cut: p.priority ?? 3,
          label: 'Drop a probe in “' + (t.title || 'Untitled') + '”',
        }));
        for (let ii = 1; ii < (t.core || []).length; ii++) cands.push({
          type: 'remove_item', topicPos: ti, itemType: 'core', itemIndex: ii,
          _cls: 2, _cut: t.core[ii].priority ?? 3,
          label: 'Drop a core point in “' + (t.title || 'Untitled') + '”',
        });
      });
      if (topics.length > 1) {
        topics.forEach((t, ti) => cands.push({
          type: 'remove_topic', topicPos: ti,
          _cls: 3, _cut: t.priority ?? 3,
          label: 'Remove “' + (t.title || 'Untitled') + '”',
        }));
      }
      if (depthValue > 0) cands.push({
        type: 'lower_depth', toValue: depthValue - 25, _cls: 4, _cut: 3,
        label: 'Reduce depth one notch',
      });
    } else {
      // UNDER target — fill, quality-improving first.
      topics.forEach((t, ti) => {
        if ((t.probe || []).length === 0) cands.push({
          type: 'add_probes', topicPos: ti, count: 2, _cls: 0, _cut: 0,
          label: 'Add 2 probe slots to “' + (t.title || 'Untitled') + '”',
        });
      });
      (sections.expansion || []).forEach((x, xi) => cands.push({
        type: 'promote_expansion', expansionIndex: xi, _cls: 1, _cut: 0,
        label: 'Promote expansion topic “' + x + '”',
      }));
      if (depthValue < 100) cands.push({
        type: 'raise_depth', toValue: depthValue + 25, _cls: 2, _cut: 0,
        label: 'Increase depth one notch',
      });
      cands.push({ type: 'add_topic', _cls: 3, _cut: 0, label: 'Add a new topic' });
    }

    for (const c of cands) c.deltaMin = candidateDelta(sections, depthValue, baseRaw, c);
    cands = cands.filter((c) => c.deltaMin !== 0);
    cands = cands.filter((c) => Math.abs(gap + c.deltaMin) < Math.abs(gap));
    cands.sort((a, b) =>
      (a._cls - b._cls) ||
      (a._cut - b._cut) ||
      (Math.abs(gap + a.deltaMin) - Math.abs(gap + b.deltaMin)));

    for (const c of cands) {
      const dir = c.deltaMin < 0 ? 'saves ~' + (-c.deltaMin) + ' min' : 'adds ~' + c.deltaMin + ' min';
      const note = (c.type === 'lower_depth' || c.type === 'raise_depth') ? ' · also rewrites pacing text' : '';
      c.detail = dir + note;
    }
    return cands.slice(0, 3);
  }
```

Then update the exports line to include the new functions:

```javascript
  const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor, generateSuggestions, applySuggestion };
```

- [ ] **Step 4: Run to verify they pass**

Run: `node --test tests/duration.test.js`
Expected: PASS (all tests from Task 3 and Task 5 green).

- [ ] **Step 5: Commit**

```bash
git add static/duration.js tests/duration.test.js
git commit -m "feat: add pure duration suggestion engine (generate + apply)"
```

---

### Task 6: Render the coach with Apply / Undo

**Files:**
- Modify: `static/app.js` (`renderSettingsStrip` body; add `coachHtml`, `applyCoachSuggestion`, `undoCoach`)
- Modify: `static/style.css` (coach styles)

- [ ] **Step 1: Add the coach markup to the settings strip**

In `static/app.js`, inside `renderSettingsStrip`, the duration control currently ends with the `.duration-inputs` block. Add a coach container immediately after that closing `</div>`, still inside `#duration-control`. Locate:

```javascript
          <input type="number" class="duration-number" min="0" max="90" step="5"
            value="${state.durationTarget || ""}"
            placeholder="—"
            oninput="setDurationTarget(parseInt(this.value, 10) || 0)">
          <span class="duration-unit">min</span>
        </div>
      </div>
```

and replace it with (adds the `<div class="duration-coach">` line):

```javascript
          <input type="number" class="duration-number" min="0" max="90" step="5"
            value="${state.durationTarget || ""}"
            placeholder="—"
            oninput="setDurationTarget(parseInt(this.value, 10) || 0)">
          <span class="duration-unit">min</span>
        </div>
        <div class="duration-coach">${coachHtml()}</div>
      </div>
```

- [ ] **Step 2: Add the coach render + handlers**

In `static/app.js`, add these three functions just after `renderSettingsStrip`:

```javascript
function coachHtml() {
  const target = state.durationTarget;
  if (!target || target <= 0) {
    return `<div class="coach-hint">Set a target to get pacing suggestions.</div>`;
  }
  const est = estimateDuration();
  const gap = est - target;
  if (Math.abs(gap) <= DurationEngine.TOLERANCE) {
    return `<div class="coach-ontarget">✓ On target (~${est} min)</div>`;
  }
  const suggestions = DurationEngine.generateSuggestions(state.sections, target, state.depthSliderValue);
  state._coachSuggestions = suggestions;
  const head = gap > 0 ? `≈${gap} min over target` : `≈${-gap} min under target`;
  const undo = state._coachUndo
    ? `<button class="coach-undo" onclick="undoCoach()">↶ Undo last change</button>` : "";
  if (suggestions.length === 0) {
    return `<div class="coach-head">${escHtml(head)}</div>`
      + `<div class="coach-hint">No single change gets closer — adjust topics manually.</div>${undo}`;
  }
  const rows = suggestions.map((s, i) => `
    <div class="coach-row">
      <div class="coach-row-text">
        <span class="coach-label">${escHtml(s.label)}</span>
        <span class="coach-detail">${escHtml(s.detail)}</span>
      </div>
      <button class="coach-apply" onclick="applyCoachSuggestion(${i})">Apply</button>
    </div>`).join("");
  return `<div class="coach-head">${escHtml(head)}</div>${rows}${undo}`;
}

function applyCoachSuggestion(i) {
  const s = state._coachSuggestions && state._coachSuggestions[i];
  if (!s) return;
  state._coachUndo = {
    sections: JSON.parse(JSON.stringify(state.sections)),
    depthSliderValue: state.depthSliderValue,
  };
  if (s.type === "lower_depth" || s.type === "raise_depth") {
    applyDepthPreset(s.toValue);           // updates depth + pacing + re-renders
  } else {
    const r = DurationEngine.applySuggestion(state.sections, state.depthSliderValue, s);
    state.sections = r.sections;
    renderTemplate();
  }
  updateDurationDisplay();
}

function undoCoach() {
  const u = state._coachUndo;
  if (!u) return;
  state.sections = u.sections;
  state.depthSliderValue = u.depthSliderValue;
  state._coachUndo = null;
  renderTemplate();
  updateDurationDisplay();
}
```

- [ ] **Step 3: Add the styles**

Append to `static/style.css` (after the `.duration-unit` rule, around line 84):

```css
.duration-coach { margin-top: 10px; border-top: 1px dashed #e0e0e0; padding-top: 8px; }
.coach-hint { font-size: 11px; color: #aaa; }
.coach-ontarget { font-size: 11px; font-weight: 600; color: #16a34a; }
.coach-head { font-size: 11px; font-weight: 700; color: #b45309; margin-bottom: 6px; }
.coach-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.coach-row-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.coach-label { font-size: 11px; color: #333; }
.coach-detail { font-size: 10px; color: #888; }
.coach-apply {
  flex-shrink: 0; font-size: 10px; font-weight: 600; padding: 3px 8px;
  border: 1px solid #4f46e5; color: #4f46e5; background: #fff;
  border-radius: 4px; cursor: pointer;
}
.coach-apply:hover { background: #4f46e5; color: #fff; }
.coach-undo {
  margin-top: 4px; font-size: 10px; color: #888;
  background: none; border: none; cursor: pointer; padding: 0;
}
.coach-undo:hover { color: #4f46e5; }
```

- [ ] **Step 4: Manual verification**

Run `python main.py`. Build ~5 topics via chat, then:
- Set the duration target above the estimate → "under target" suggestions appear (e.g. *Increase depth one notch*, *Add a new topic*).
- Set it well below → "over target" suggestions appear (e.g. *Remove "…"*, *Reduce depth one notch*), lowest-priority topic first.
- Set it equal to the estimate → green "✓ On target".
- Set it to 0 (blank the number field) → muted "Set a target…" hint.
- Click **Apply** on a suggestion → the template changes, the estimate moves toward the target, suggestions refresh, and an **Undo** link appears.
- Click **Undo** → the change reverts. For a depth suggestion, confirm both the depth slider and the pacing text revert.

Stop the app (`Stop-Process` per Task 2).

- [ ] **Step 5: Commit**

```bash
git add static/app.js static/style.css
git commit -m "feat: live duration coach with one-click apply and undo"
```

---

### Task 7: End-to-end verification

**Files:** none (verification only)

- [ ] **Step 1: Full automated suites**

Run: `pytest tests/ -v`
Run: `node --test tests/duration.test.js`
Expected: both PASS.

- [ ] **Step 2: Full manual pass**

Run `python main.py`. Build a template end to end, exercise the coach in both directions with Apply/Undo, then Export. Confirm the exported template still formats correctly (the coach only edits `state.sections`, which the export already consumes). Stop the app.

- [ ] **Step 3: Confirm clean tree**

Run: `git status`
Expected: working tree clean (all changes committed across Tasks 1, 3, 4, 5, 6).

---

## Self-Review notes

- **Spec coverage:** Part 1 §1.1–1.8 → Task 1 (each rule has a verbatim prompt section + an anchor test) and Task 2 (smoke test of the consolidation gate). Part 2 §2.1 (three gap modes) → Task 6 `coachHtml`; §2.2 (engine) → Task 5; §2.3 (pure refactor + diff deltas) → Tasks 3/5; §2.4 (apply + undo) → Task 6; §2.5 (guard rails) → Task 5 filters + tests; §2.6 (placement) → Task 6 Step 1; §2.7 (testability) → Tasks 3/5 Node tests.
- **Naming consistency:** `estimateRawFor` / `estimateDurationFor` / `generateSuggestions` / `applySuggestion` / `coachHtml` / `applyCoachSuggestion` / `undoCoach` / `DurationEngine.TOLERANCE` / `state._coachSuggestions` / `state._coachUndo` are used identically across every task.
- **Known limitation (intentional):** with 0–2 topics the raw estimate sits near the clamp floor, so item-level moves round to 0 min and are filtered; the coach then shows the "adjust topics manually" hint. This is correct behaviour for a near-empty guide and is covered by the empty-state branch in `coachHtml`.
```

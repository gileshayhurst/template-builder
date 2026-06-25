# Duration Estimate Recalibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lower the duration estimate base constants so balanced depth (slider=50) anchors the estimate correctly for a typical guide, and update the estimate label wording.

**Architecture:** Two constant changes in `static/duration.js` (same values in two functions), one test update in `tests/duration.test.js`, and one label string change in two places in `static/app.js`. No structural changes — existing depth factor formula and test fixtures stay unchanged.

**Tech Stack:** Vanilla JS (Node 18+ for tests via `node --test`), Flask/Python (not touched here).

---

### Task 1: Update test expectations to reflect new constants

**Files:**
- Modify: `tests/duration.test.js:12-24` (estimateDurationFor test)
- Modify: `tests/duration.test.js:119-130` (topicMinutes comment)

The `estimateDurationFor` test uses a 2-topic fixture with expansion and focus. With new constants (0.55/0.14/0.07 replacing 0.8/0.2/0.1), the raw before depth factor is:

```
Topic 1 (priority 4, core=[p4,p3], probe=[p2]):
  0.55*1.25 + 0.14*1.0 + 0.07*0.75 = 0.6875 + 0.14 + 0.0525 = 0.88

Topic 2 (priority 5, core=[p5], probe=[]):
  0.55*1.5 = 0.825

expansion: 2*0.2 = 0.4
focus: 0.5
base: 0.5
raw = 0.88 + 0.825 + 0.4 + 0.5 + 0.5 = 3.105

depth 0  → 3.105 * 0.65 = 2.018 → max(2, 2.018) = 2.018 → round = 2
depth 50 → 3.105 * 1.0  = 3.105                           → round = 3
depth 100→ 3.105 * 1.8  = 5.589                           → round = 6
```

- [ ] **Step 1: Update the estimateDurationFor test**

In `tests/duration.test.js`, replace lines 21-23:

Old:
```js
  assert.strictEqual(D.estimateDurationFor(sections, 50), 4);  // factor 1.0
  assert.strictEqual(D.estimateDurationFor(sections, 100), 7); // factor 1.8
  assert.strictEqual(D.estimateDurationFor(sections, 0), 3);   // factor 0.65
```

New:
```js
  assert.strictEqual(D.estimateDurationFor(sections, 50), 3);  // factor 1.0
  assert.strictEqual(D.estimateDurationFor(sections, 100), 6); // factor 1.8
  assert.strictEqual(D.estimateDurationFor(sections, 0), 2);   // factor 0.65
```

- [ ] **Step 2: Update the topicMinutes comment (richer topic at depth 75)**

The assertion (`=== 2`) still holds with new constants — `round(1.125 * 1.4) = round(1.575) = 2` — but the comment describes old numbers. Update lines 125-128 in `tests/duration.test.js`:

Old:
```js
  // raw = 0.8*1.25 + 0.2*1.25 + 0.2*1.0 + 0.1*1.0 + 0.1*0.75
  //     = 1.0 + 0.25 + 0.2 + 0.1 + 0.075 = 1.625
  // depthFactor(75) = 1.0 + (25/50)*0.8 = 1.4
  // round(1.625*1.4) = round(2.275) = 2
```

New:
```js
  // raw = 0.55*1.25 + 0.14*1.25 + 0.14*1.0 + 0.07*1.0 + 0.07*0.75
  //     = 0.6875 + 0.175 + 0.14 + 0.07 + 0.0525 = 1.125
  // depthFactor(75) = 1.0 + (25/50)*0.8 = 1.4
  // round(1.125*1.4) = round(1.575) = 2
```

- [ ] **Step 3: Run tests and confirm exactly the `estimateDurationFor` test fails**

```
node --test tests/duration.test.js
```

Expected: one failure on `estimateDurationFor matches known values across depths` (values are 4/7/3 instead of 3/6/2). All other tests pass.

---

### Task 2: Lower the base constants in duration.js

**Files:**
- Modify: `static/duration.js` — `estimateRawFor` (lines ~17-32) and `topicMinutes` (lines ~86-93)

- [ ] **Step 1: Update `estimateRawFor`**

In `static/duration.js`, replace the three numeric weights inside `estimateRawFor`. The function currently reads:

```js
  for (const t of topics) {
    raw += 0.8 * priorityFactor(t.priority ?? 3);
    const core = t.core || [];
    for (let i = 1; i < core.length; i++) raw += 0.2 * priorityFactor(core[i].priority ?? 3);
    for (const p of (t.probe || [])) raw += 0.1 * priorityFactor(p.priority ?? 3);
  }
```

Change to:

```js
  for (const t of topics) {
    raw += 0.55 * priorityFactor(t.priority ?? 3);
    const core = t.core || [];
    for (let i = 1; i < core.length; i++) raw += 0.14 * priorityFactor(core[i].priority ?? 3);
    for (const p of (t.probe || [])) raw += 0.07 * priorityFactor(p.priority ?? 3);
  }
```

Everything else in the function (overhead, expansion, focus, clamp, depth factor multiplication) stays unchanged.

- [ ] **Step 2: Update `topicMinutes`**

In `static/duration.js`, the `topicMinutes` function currently reads:

```js
  let raw = 0.8 * priorityFactor(topic.priority ?? 3);
  for (let i = 1; i < core.length; i++) raw += 0.2 * priorityFactor(core[i].priority ?? 3);
  for (const p of probe) raw += 0.1 * priorityFactor(p.priority ?? 3);
```

Change to:

```js
  let raw = 0.55 * priorityFactor(topic.priority ?? 3);
  for (let i = 1; i < core.length; i++) raw += 0.14 * priorityFactor(core[i].priority ?? 3);
  for (const p of probe) raw += 0.07 * priorityFactor(p.priority ?? 3);
```

- [ ] **Step 3: Run tests and confirm all pass**

```
node --test tests/duration.test.js
```

Expected output: all tests pass, no failures.

- [ ] **Step 4: Commit**

```
git add static/duration.js tests/duration.test.js
git commit -m "fix: recalibrate duration estimate — balanced depth now anchors at ~5 min"
```

---

### Task 3: Update estimate label wording in app.js

**Files:**
- Modify: `static/app.js` — two occurrences of `● Est: ${estimate} min`

- [ ] **Step 1: Update label in `updateDurationDisplay`**

In `static/app.js`, find the line in `updateDurationDisplay` (~line 116):

```js
  if (estimateLabelEl) estimateLabelEl.textContent = `● Est: ${estimate} min`;
```

Change to:

```js
  if (estimateLabelEl) estimateLabelEl.textContent = `time est. to fully cover content: ${estimate} mins`;
```

- [ ] **Step 2: Update label in `renderTemplate` HTML string**

In `static/app.js`, find the line in the `renderTemplate` HTML string (~line 391):

```js
          <span class="duration-label-estimate">● Est: ${estimate} min</span>
```

Change to:

```js
          <span class="duration-label-estimate">time est. to fully cover content: ${estimate} mins</span>
```

- [ ] **Step 3: Run JS tests to confirm nothing broken**

```
node --test tests/duration.test.js
```

Expected: all tests pass (app.js has no JS test coverage, but duration engine is unaffected).

- [ ] **Step 4: Commit**

```
git add static/app.js
git commit -m "feat: relabel duration estimate as 'time est. to fully cover content'"
```

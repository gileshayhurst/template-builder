# Duration Slider Rescale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rescale the goal-duration slider from 0–90 min (step 5) to 0–30 min (step 1), with 30 labelled "30+" and the estimate bar capped at that mark.

**Architecture:** All five display-layer uses of the hard-coded `90` in `app.js` are replaced by a single named constant `DURATION_SCALE_MAX = 30`. The estimate math in `duration.js` is untouched — the bar just caps at 100 % when the content estimate exceeds 30. `setDurationTarget()` also clamps to the new max so you can never store a target above 30.

**Tech Stack:** Vanilla JS (`static/app.js`). No build step. Tests: `pytest tests/` (Python) and `node --test tests/duration.test.js` (Node 18+).

---

### Task 1: Add constant and update `durationViewModel()`

**Files:**
- Modify: `static/app.js:82–94`

These are the only three `90` references in `durationViewModel()`. Adding the constant here first makes the next task's diff easy to verify.

- [ ] **Step 1: Add the constant just above `estimateDuration()`**

In `static/app.js`, find this line (currently line 82):

```js
function estimateDuration() {
```

Insert one blank line above it, then add:

```js
const DURATION_SCALE_MAX = 30;
```

So the block now reads:

```js
const DURATION_SCALE_MAX = 30;

function estimateDuration() {
  return DurationEngine.estimateDurationFor(state.sections, state.depthSliderValue);
}
```

- [ ] **Step 2: Update `durationViewModel()` — three changes**

Replace the entire `durationViewModel` function (lines 86–94) with:

```js
function durationViewModel() {
  const estimate = estimateDuration();
  const targetPct = state.durationTarget > 0 ? (state.durationTarget / DURATION_SCALE_MAX) * 100 : 0;
  const estimatePct = Math.min(100, (estimate / DURATION_SCALE_MAX) * 100);
  const targetLabelText = state.durationTarget > 0
    ? `● Target: ${state.durationTarget === DURATION_SCALE_MAX ? "30+" : state.durationTarget} min`
    : "● No target set";
  return { estimate, targetPct, estimatePct, targetLabelText };
}
```

Changes vs old:
1. `/ 90` → `/ DURATION_SCALE_MAX` for target pct
2. `estimate / 90 * 100` → `Math.min(100, (estimate / DURATION_SCALE_MAX) * 100)` for estimate pct (caps bar at 100 %)
3. Target label shows `30+` when target equals the max

- [ ] **Step 3: Run existing test suites — both must pass**

```
pytest tests/
node --test tests/duration.test.js
```

Expected: all green. These suites don't cover `app.js` directly, but a syntax error in the file would surface here if anything imports it.

- [ ] **Step 4: Commit**

```bash
git add static/app.js
git commit -m "feat: add DURATION_SCALE_MAX constant and update durationViewModel"
```

---

### Task 2: Update `setDurationTarget()` clamp and HTML inputs

**Files:**
- Modify: `static/app.js:96–103` (setDurationTarget) and `static/app.js:403–409` (renderSettings HTML)

- [ ] **Step 1: Update the clamp in `setDurationTarget()`**

Find (line 97):

```js
  state.durationTarget = Math.min(90, Math.max(0, value || 0));
```

Replace with:

```js
  state.durationTarget = Math.min(DURATION_SCALE_MAX, Math.max(0, value || 0));
```

- [ ] **Step 2: Update the range slider HTML in `renderSettings()`**

Find (around line 403):

```js
          <input type="range" class="duration-slider" min="0" max="90" step="5"
```

Replace with:

```js
          <input type="range" class="duration-slider" min="0" max="30" step="1"
```

- [ ] **Step 3: Update the number input HTML**

Find (around line 406):

```js
          <input type="number" class="duration-number" min="0" max="90" step="5"
```

Replace with:

```js
          <input type="number" class="duration-number" min="0" max="30" step="1"
```

- [ ] **Step 4: Run existing test suites — both must still pass**

```
pytest tests/
node --test tests/duration.test.js
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add static/app.js
git commit -m "feat: rescale duration slider to 1-30+ min (step 1)"
```

---

### Task 3: Manual browser verification

**Files:** none (read-only verification)

Start the server with PowerShell (not Bash — see CLAUDE.md):

```powershell
python main.py
```

Browser opens at `http://localhost:5000`. Work through each check:

- [ ] **Check 1 — Slider range and step**

Drag the slider. It should move in 1-minute increments and stop at 30. The number input should also accept only 0–30.

- [ ] **Check 2 — "30+" label at max**

Drag the slider to 30. The target label should read `● Target: 30+ min`.

- [ ] **Check 3 — Normal label below max**

Set the slider to 15. The target label should read `● Target: 15 min`.

- [ ] **Check 4 — Estimate bar caps at 30**

Add several topics via the chat until the estimate label reads more than 30 min (e.g. "time est. to fully cover content: 42 mins"). The estimate bar should be at 100 % width but the label number should still show the real estimate (42, not 30).

- [ ] **Check 5 — No target state**

Drag the slider back to 0 (or clear the number input). The label should revert to `● No target set`.

- [ ] **Commit** (no code change — this task is verification only)

No commit needed. If any check failed, fix the relevant task above and re-verify.

# Reorder, Badges & Settings Awareness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add drag-to-reorder topics with per-topic duration badges and advisory AI awareness of depth/duration settings.

**Architecture:** Three independent feature groups — (a) pure duration math extension + badge render, (b) pure reorder helper + drag/keyboard UI, (c) server-side settings context builder + prompt update + frontend POST extension. All features share the existing vanilla-JS/Flask/SSE stack with no new dependencies.

**Tech Stack:** Vanilla JS (ES6 closures, HTML5 DnD API), Flask, Node built-in test runner (`node:test`), pytest.

---

### Task 1: `topicMinutes` pure function (TDD)

**Files:**
- Modify: `static/duration.js`
- Modify: `tests/duration.test.js`

- [ ] **Step 1: Write the failing test**

Append to `tests/duration.test.js`:
```js
test('topicMinutes: single core at priority 3, depth 50 → 1 min', () => {
  const topic = { priority: 3, core: [{ priority: 3 }], probe: [] };
  // raw = 0.8*1.0 = 0.8; depth50 factor = 1.0; round(0.8)=1; max(1,1)=1
  assert.strictEqual(D.topicMinutes(topic, 50), 1);
});

test('topicMinutes: min 1 even for priority-1 topic at depth 0', () => {
  const topic = { priority: 1, core: [{ priority: 1 }], probe: [] };
  // raw = 0.8*0.5=0.4; depth0 factor=0.65; round(0.26)=0; max(1,0)=1
  assert.strictEqual(D.topicMinutes(topic, 0), 1);
});

test('topicMinutes: richer topic at depth 75', () => {
  const topic = {
    priority: 4,
    core: [{ priority: 5 }, { priority: 4 }, { priority: 3 }],
    probe: [{ priority: 3 }, { priority: 2 }],
  };
  // raw = 0.8*1.25 + 0.2*1.25 + 0.2*1.0 + 0.1*1.0 + 0.1*0.75
  //     = 1.0 + 0.25 + 0.2 + 0.1 + 0.075 = 1.625
  // depthFactor(75) = 1.0 + (25/50)*0.8 = 1.4
  // round(1.625*1.4) = round(2.275) = 2
  assert.strictEqual(D.topicMinutes(topic, 75), 2);
});

test('topicMinutes changes when depth changes', () => {
  const topic = { priority: 5, core: [{ priority: 5 }, { priority: 5 }], probe: [{ priority: 5 }] };
  const shallow = D.topicMinutes(topic, 0);
  const deep    = D.topicMinutes(topic, 100);
  assert.ok(deep > shallow, 'deep estimate must exceed shallow');
});
```

- [ ] **Step 2: Run test to verify it fails**

```
node --test tests/duration.test.js
```
Expected: 4 failures mentioning `D.topicMinutes is not a function`.

- [ ] **Step 3: Implement `topicMinutes` in `static/duration.js`**

Add the function just before the `api` object at the bottom of the IIFE:
```js
function topicMinutes(topic, depthValue) {
  const core  = topic.core  || [];
  const probe = topic.probe || [];
  let raw = 0.8 * priorityFactor(topic.priority);
  for (let i = 1; i < core.length; i++) raw += 0.2 * priorityFactor(core[i].priority);
  for (const p of probe) raw += 0.1 * priorityFactor(p.priority);
  return Math.max(1, Math.round(raw * depthFactorFor(depthValue)));
}
```

Then update the `api` object to include `topicMinutes`:
```js
const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor, generateSuggestions, applySuggestion, topicMinutes };
```

- [ ] **Step 4: Run tests to verify they pass**

```
node --test tests/duration.test.js
```
Expected: all tests pass, including the 4 new ones.

- [ ] **Step 5: Commit**

```
git add static/duration.js tests/duration.test.js
git commit -m "feat: add topicMinutes pure function to duration engine"
```

---

### Task 2: Per-topic duration badge in topic header

**Files:**
- Modify: `static/app.js` (function `renderTopicBlock`)
- Modify: `static/style.css`

- [ ] **Step 1: Add CSS for the badge**

Append to `static/style.css`:
```css
/* Duration badge on topic header */
.topic-duration-badge {
  font-size: 10px;
  font-weight: 600;
  color: #888;
  background: #f3f4f6;
  border-radius: 10px;
  padding: 1px 6px;
  flex-shrink: 0;
  user-select: none;
  white-space: nowrap;
}
```

- [ ] **Step 2: Insert badge into `renderTopicBlock` in `static/app.js`**

Locate `renderTopicBlock`. After `topicHeader.appendChild(renderStarWidget(...))` and before the `removeBtn` block, insert:
```js
  const durationBadge = document.createElement("span");
  durationBadge.className = "topic-duration-badge";
  durationBadge.textContent = `~${DurationEngine.topicMinutes(topic, state.depthSliderValue)} min`;
  topicHeader.appendChild(durationBadge);
```

The updated tail of `renderTopicBlock`'s header-building section (for reference — only the new lines are being added, not replacing existing code):
```js
  topicHeader.appendChild(renderStarWidget(topic.priority ?? 3, n => {
    updateTopicField(topic.index, "priority", n);
    renderTemplate();
  }));

  // NEW: duration badge
  const durationBadge = document.createElement("span");
  durationBadge.className = "topic-duration-badge";
  durationBadge.textContent = `~${DurationEngine.topicMinutes(topic, state.depthSliderValue)} min`;
  topicHeader.appendChild(durationBadge);

  const removeBtn = document.createElement("button");
  // ... existing removeBtn code unchanged
```

- [ ] **Step 3: Run Python tests to confirm nothing broken**

```
pytest tests/ -q
```
Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```
git add static/app.js static/style.css
git commit -m "feat: show per-topic duration badge on topic header"
```

---

### Task 3: `reorderTopics` pure function (TDD)

**Files:**
- Modify: `static/duration.js`
- Modify: `tests/duration.test.js`

- [ ] **Step 1: Write the failing tests**

Append to `tests/duration.test.js`:
```js
test('reorderTopics: moves item to new position and renumbers indices', () => {
  const topics = [
    { index: 1, title: 'A', priority: 3, core: [], probe: [] },
    { index: 2, title: 'B', priority: 3, core: [], probe: [] },
    { index: 3, title: 'C', priority: 3, core: [], probe: [] },
  ];
  const result = D.reorderTopics(topics, 0, 2); // move A to after C
  assert.deepStrictEqual(result.map(t => t.title), ['B', 'C', 'A']);
  assert.deepStrictEqual(result.map(t => t.index), [1, 2, 3]);
});

test('reorderTopics: no-op when fromPos === toPos', () => {
  const topics = [
    { index: 1, title: 'A', priority: 3, core: [], probe: [] },
    { index: 2, title: 'B', priority: 3, core: [], probe: [] },
  ];
  const result = D.reorderTopics(topics, 1, 1);
  assert.deepStrictEqual(result.map(t => t.title), ['A', 'B']);
  assert.deepStrictEqual(result.map(t => t.index), [1, 2]);
});

test('reorderTopics: does not mutate input array', () => {
  const topics = [
    { index: 1, title: 'A', priority: 3, core: [], probe: [] },
    { index: 2, title: 'B', priority: 3, core: [], probe: [] },
  ];
  D.reorderTopics(topics, 0, 1);
  assert.strictEqual(topics[0].title, 'A');
  assert.strictEqual(topics[0].index, 1);
});

test('reorderTopics: move last item to first position', () => {
  const topics = [
    { index: 1, title: 'A', priority: 3, core: [], probe: [] },
    { index: 2, title: 'B', priority: 3, core: [], probe: [] },
    { index: 3, title: 'C', priority: 3, core: [], probe: [] },
  ];
  const result = D.reorderTopics(topics, 2, 0);
  assert.deepStrictEqual(result.map(t => t.title), ['C', 'A', 'B']);
  assert.deepStrictEqual(result.map(t => t.index), [1, 2, 3]);
});
```

- [ ] **Step 2: Run test to verify it fails**

```
node --test tests/duration.test.js
```
Expected: 4 new failures mentioning `D.reorderTopics is not a function`.

- [ ] **Step 3: Implement `reorderTopics` in `static/duration.js`**

Add just before the `api` object (after `topicMinutes`):
```js
function reorderTopics(topics, fromPos, toPos) {
  const arr = topics.slice();
  const [moved] = arr.splice(fromPos, 1);
  arr.splice(toPos, 0, moved);
  return arr.map((t, i) => ({ ...t, index: i + 1 }));
}
```

Update the `api` object to export it:
```js
const api = { TOLERANCE, priorityFactor, depthFactorFor, estimateRawFor, estimateDurationFor, generateSuggestions, applySuggestion, topicMinutes, reorderTopics };
```

- [ ] **Step 4: Run tests to verify they pass**

```
node --test tests/duration.test.js
```
Expected: all tests pass including the 4 new ones.

- [ ] **Step 5: Commit**

```
git add static/duration.js tests/duration.test.js
git commit -m "feat: add reorderTopics pure function to duration engine"
```

---

### Task 4: Drag-to-reorder — `commitReorder`, drag events, and CSS

**Files:**
- Modify: `static/app.js`
- Modify: `static/style.css`

- [ ] **Step 1: Add drag CSS to `static/style.css`**

Append to `static/style.css`:
```css
/* Drag-to-reorder topic grip */
.topic-grip {
  cursor: grab;
  user-select: none;
  color: #ccc;
  font-size: 14px;
  flex-shrink: 0;
  line-height: 1;
  padding: 0 2px;
  border-radius: 3px;
  touch-action: none;
}
.topic-grip:hover { color: #888; }
.topic-grip:focus {
  outline: 2px solid #4f46e5;
  outline-offset: 2px;
  color: #4f46e5;
}

.topic-block.dragging { opacity: 0.4; }
.topic-block.drag-over-above { border-top: 2px solid #4f46e5; }
.topic-block.drag-over-below { border-bottom: 2px solid #4f46e5; }
```

- [ ] **Step 2: Add module-level `dragState` variable to `static/app.js`**

After the `const state = { ... };` block, add:
```js
// ─── DRAG STATE ───────────────────────────────────────────────────────────────

let dragState = null;
```

- [ ] **Step 3: Add `commitReorder` function to `static/app.js`**

Add after the `dragState` declaration:
```js
function commitReorder(fromPos, toPos) {
  if (fromPos === toPos) return;

  // Capture collapse state by current array position before renumbering
  const wasCollapsed = state.sections.topics.map(t =>
    state.collapsedSections.has(`topic-${t.index}`)
  );

  // Reorder and renumber indices 1..N
  state.sections.topics = DurationEngine.reorderTopics(state.sections.topics, fromPos, toPos);

  // Apply the same permutation to wasCollapsed to track which topic moved where
  const reorderedCollapsed = wasCollapsed.slice();
  const [movedCollapsed] = reorderedCollapsed.splice(fromPos, 1);
  reorderedCollapsed.splice(toPos, 0, movedCollapsed);

  // Rebuild collapsedSections: keep non-topic keys; restore topic keys using new indices
  const newCollapsed = new Set();
  for (const key of state.collapsedSections) {
    if (!key.startsWith("topic-")) newCollapsed.add(key);
  }
  state.sections.topics.forEach((t, i) => {
    if (reorderedCollapsed[i]) newCollapsed.add(`topic-${t.index}`);
  });
  state.collapsedSections = newCollapsed;

  renderTemplate();
  updateDurationDisplay();
}
```

- [ ] **Step 4: Add grip handle and drag events in `renderTopicBlock`**

In `renderTopicBlock`, add the grip as the very first child of `topicHeader`, before the chevron. Replace the opening of the `topicHeader` construction with:

```js
  const grip = document.createElement("span");
  grip.className = "topic-grip";
  grip.textContent = "⠿";
  grip.setAttribute("role", "button");
  grip.setAttribute("tabindex", "0");
  grip.setAttribute("aria-label", "Drag to reorder topic");
  grip.addEventListener("pointerdown", () => { block.draggable = true; });
  grip.addEventListener("pointerup",   () => { block.draggable = false; });
  topicHeader.appendChild(grip);
```

(This goes before `topicHeader.appendChild(chevron)` — just insert it as the first line after the existing `const chevron = ...` block.)

Then add drag event listeners on `block` after the `block.appendChild(topicHeader)` line:

```js
  block.addEventListener("dragstart", (e) => {
    const fromPos = state.sections.topics.findIndex(t => t.index === topic.index);
    dragState = { fromPos, toPos: fromPos };
    block.classList.add("dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(topic.index)); // required for Firefox
  });

  block.addEventListener("dragover", (e) => {
    if (!dragState) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    const blockPos = state.sections.topics.findIndex(t => t.index === topic.index);
    if (blockPos === dragState.fromPos) return;

    document.querySelectorAll(".topic-block").forEach(b =>
      b.classList.remove("drag-over-above", "drag-over-below"));

    const rect = block.getBoundingClientRect();
    const isUpper = e.clientY < rect.top + rect.height / 2;
    block.classList.add(isUpper ? "drag-over-above" : "drag-over-below");

    const fp = dragState.fromPos;
    if (isUpper) {
      dragState.toPos = fp < blockPos ? blockPos - 1 : blockPos;
    } else {
      dragState.toPos = fp < blockPos ? blockPos : blockPos + 1;
    }
  });

  block.addEventListener("dragleave", () => {
    block.classList.remove("drag-over-above", "drag-over-below");
  });

  block.addEventListener("drop", (e) => {
    e.preventDefault();
    document.querySelectorAll(".topic-block").forEach(b =>
      b.classList.remove("drag-over-above", "drag-over-below"));
    if (!dragState || dragState.toPos === undefined) { dragState = null; return; }
    const { fromPos, toPos } = dragState;
    dragState = null;
    commitReorder(fromPos, toPos);
  });

  block.addEventListener("dragend", () => {
    block.draggable = false;
    block.classList.remove("dragging");
    document.querySelectorAll(".topic-block").forEach(b =>
      b.classList.remove("drag-over-above", "drag-over-below"));
    dragState = null;
  });
```

- [ ] **Step 5: Run Python tests to confirm nothing broken**

```
pytest tests/ -q
```
Expected: all existing tests pass.

- [ ] **Step 6: Commit**

```
git add static/app.js static/style.css
git commit -m "feat: drag-to-reorder topics with insertion indicator"
```

---

### Task 5: Keyboard accessibility on grip (ArrowUp / ArrowDown)

**Files:**
- Modify: `static/app.js` (inside `renderTopicBlock`, after grip creation)

- [ ] **Step 1: Add keydown listener to the grip**

After the `grip.addEventListener("pointerup", ...)` line (still in `renderTopicBlock`), add:

```js
  grip.addEventListener("keydown", (e) => {
    const topics = state.sections.topics;
    const pos = topics.findIndex(t => t.index === topic.index);
    if (e.key === "ArrowUp" && pos > 0) {
      e.preventDefault();
      commitReorder(pos, pos - 1);
      // Restore focus to the grip that is now at pos-1 after re-render
      setTimeout(() => {
        const grips = document.querySelectorAll(".topic-grip");
        if (grips[pos - 1]) grips[pos - 1].focus();
      }, 0);
    } else if (e.key === "ArrowDown" && pos < topics.length - 1) {
      e.preventDefault();
      commitReorder(pos, pos + 1);
      setTimeout(() => {
        const grips = document.querySelectorAll(".topic-grip");
        if (grips[pos + 1]) grips[pos + 1].focus();
      }, 0);
    }
  });
```

- [ ] **Step 2: Run Python tests**

```
pytest tests/ -q
```
Expected: all tests pass.

- [ ] **Step 3: Commit**

```
git add static/app.js
git commit -m "feat: keyboard ArrowUp/Down on drag grip for accessibility"
```

---

### Task 6: `build_settings_context` pure helper (TDD)

**Files:**
- Modify: `app.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_routes.py`:
```python
from app import build_settings_context


def test_build_settings_context_empty_inputs():
    assert build_settings_context({}) == ''
    assert build_settings_context(None) == ''
    assert build_settings_context('bad') == ''
    assert build_settings_context(42) == ''


def test_build_settings_context_depth_only():
    result = build_settings_context({'depthValue': 50, 'depthLabel': 'Balanced'})
    assert '## Current UI settings' in result
    assert 'Depth/breadth slider: 50/100 (Balanced)' in result
    assert 'Duration target' not in result


def test_build_settings_context_with_target_and_estimate():
    result = build_settings_context({
        'depthValue': 75, 'depthLabel': 'Slightly Deep',
        'durationTarget': 30, 'estimate': 38
    })
    assert '## Current UI settings' in result
    assert 'Depth/breadth slider: 75/100 (Slightly Deep)' in result
    assert 'Duration target: 30 min' in result
    assert 'Current estimate: 38 min' in result


def test_build_settings_context_zero_target_excluded():
    result = build_settings_context({
        'depthValue': 50, 'depthLabel': 'Balanced',
        'durationTarget': 0, 'estimate': 15
    })
    assert 'Duration target' not in result


def test_build_settings_context_clamps_out_of_range_values():
    result = build_settings_context({
        'depthValue': 50, 'depthLabel': 'Balanced',
        'durationTarget': 999, 'estimate': -5
    })
    assert 'Duration target: 90 min' in result
    assert 'Current estimate: 0 min' in result


def test_build_settings_context_invalid_depth_excluded():
    result = build_settings_context({'depthValue': 150, 'depthLabel': 'Bad', 'durationTarget': 0})
    assert 'Depth/breadth slider' not in result
    assert result == ''
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_routes.py -q
```
Expected: 6 new failures mentioning `ImportError` or `cannot import name 'build_settings_context'`.

- [ ] **Step 3: Implement `build_settings_context` in `app.py`**

Add the function after the `GATHERING_TOOLS` list and before `_normalise_item`:

```python
def build_settings_context(settings):
    """Return a system-prompt snippet from UI settings, or '' if nothing meaningful."""
    if not settings or not isinstance(settings, dict):
        return ''
    depth_value = settings.get('depthValue')
    depth_label = settings.get('depthLabel', '')
    target = settings.get('durationTarget', 0)
    estimate = settings.get('estimate', 0)

    if not isinstance(depth_value, (int, float)) or not (0 <= depth_value <= 100):
        depth_value = None
    if not isinstance(target, (int, float)):
        target = 0
    target = max(0, min(90, int(target)))
    if not isinstance(estimate, (int, float)):
        estimate = 0
    estimate = max(0, min(90, int(estimate)))

    lines = []
    if depth_value is not None:
        lines.append(f'Depth/breadth slider: {int(depth_value)}/100 ({depth_label})')
    if target > 0:
        lines.append(f'Duration target: {target} min')
        lines.append(f'Current estimate: {estimate} min')
    if not lines:
        return ''
    return '\n\n## Current UI settings\n' + '\n'.join(f'- {l}' for l in lines)
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_routes.py -q
```
Expected: all tests pass including 6 new ones.

- [ ] **Step 5: Commit**

```
git add app.py tests/test_routes.py
git commit -m "feat: add build_settings_context helper with tests"
```

---

### Task 7: Wire settings context into chat route and `stream_conversation`

**Files:**
- Modify: `app.py`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Add test for settings context appearing in the Anthropic call**

Append to `tests/test_routes.py`:
```python
def test_chat_passes_settings_context_to_anthropic(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Ok"])
        resp = client.post("/chat",
            data=json.dumps({
                "message": "Hello",
                "settings": {
                    "depthValue": 50, "depthLabel": "Balanced",
                    "durationTarget": 30, "estimate": 38
                }
            }),
            content_type="application/json")
        _ = resp.data
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert "## Current UI settings" in call_kwargs["system"]
    assert "Duration target: 30 min" in call_kwargs["system"]


def test_chat_without_settings_uses_base_prompt(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Ok"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        _ = resp.data
    call_kwargs = mock_client.messages.stream.call_args.kwargs
    assert "## Current UI settings" not in call_kwargs["system"]
```

- [ ] **Step 2: Run new tests to verify they fail**

```
pytest tests/test_routes.py::test_chat_passes_settings_context_to_anthropic tests/test_routes.py::test_chat_without_settings_uses_base_prompt -v
```
Expected: both fail — the route doesn't yet read `settings` from the request.

- [ ] **Step 3: Update `stream_conversation` to accept an explicit `system` parameter**

In `app.py`, change the `stream_conversation` signature and replace the hardcoded `GATHERING_PROMPT` inside the function:

```python
def stream_conversation(new_message, system=None):
    if system is None:
        system = GATHERING_PROMPT
    conversation_history.append({"role": "user", "content": new_message})

    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=GATHERING_TOOLS,
            messages=conversation_history
        ) as stream:
```

(Only the signature line and the `system=GATHERING_PROMPT` argument inside `client.messages.stream` change; everything else stays identical.)

- [ ] **Step 4: Update the `chat` route to extract settings and build the system string**

Replace the existing `chat` route with:

```python
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data["message"]
    settings = data.get("settings", {})
    settings_context = build_settings_context(settings)
    system = GATHERING_PROMPT + settings_context
    def safe_stream():
        try:
            yield from stream_conversation(message, system)
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps(type(e).__name__ + ': ' + str(e))}\n\n"
    return Response(safe_stream(), mimetype="text/event-stream")
```

- [ ] **Step 5: Run all tests**

```
pytest tests/ -q
```
Expected: all tests pass including the 2 new ones.

- [ ] **Step 6: Commit**

```
git add app.py tests/test_routes.py
git commit -m "feat: wire settings context into chat route and stream_conversation"
```

---

### Task 8: Frontend sends settings with every `/chat` POST

**Files:**
- Modify: `static/app.js` (function `streamFromServer`)

- [ ] **Step 1: Update `streamFromServer` to include a `settings` payload**

In `streamFromServer`, replace the `fetch("/chat", ...)` call body:

```js
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        settings: {
          depthValue: state.depthSliderValue,
          depthLabel: { 0: "Breadth", 25: "Slightly Broad", 50: "Balanced", 75: "Slightly Deep", 100: "Deep" }[state.depthSliderValue] || "Balanced",
          durationTarget: state.durationTarget,
          estimate: estimateDuration()
        }
      })
    });
```

- [ ] **Step 2: Run Python tests**

```
pytest tests/ -q
```
Expected: all tests pass (server-side tests mock the client, frontend change doesn't affect them).

- [ ] **Step 3: Commit**

```
git add static/app.js
git commit -m "feat: send depth and duration settings with every chat POST"
```

---

### Task 9: `gathering.txt` UI settings awareness section + test

**Files:**
- Modify: `prompts/gathering.txt`
- Modify: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_gathering_prompt.py`:
```python
def test_prompt_has_settings_awareness():
    text = _prompt_text()
    assert "ui settings awareness" in text
    assert "flag" in text
    assert "25%" in text
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/test_gathering_prompt.py::test_prompt_has_settings_awareness -v
```
Expected: FAIL — section not yet present.

- [ ] **Step 3: Update `prompts/gathering.txt`**

Find this line (in the `## Topic set` section):
```
- Count: aim for roughly 5–8 topics. Do NOT try to hit a specific interview length — the client fine-tunes length with the duration controls in the UI.
```

Replace it with:
```
- Count: aim for roughly 5–8 topics. Do NOT try to hit a specific interview length autonomously — flag a large gap once and offer to trim or expand, but act only when the user asks.
```

Then, immediately before the final `## Rules` section, add:

```
## UI settings awareness
If the conversation includes a "Current UI settings" block, use it as follows:
- Let the depth/breadth setting inform your framing: a breadth setting suggests fewer probes and broader coverage; a deep setting suggests richer probes and more episodic framing.
- If a duration target is set and the current estimate differs from it by more than 25%, flag this proactively — once — in natural language: e.g. "You've set a 20-minute target but the template is currently estimated at 38 minutes. Want me to trim some topics?" Then wait for the user's response before acting.
- Do not flag duration mismatches on every turn. Mention it once when you first notice a significant gap; after that, let the user direct you.
- Do not attempt to hit the duration target autonomously. The duration coach in the UI handles precise fit. Your job is quality; the coach's job is fit.
- The estimate shown is a rough heuristic. Treat it as directional.
```

- [ ] **Step 4: Run all tests**

```
pytest tests/ -q
```
Expected: all tests pass including `test_prompt_has_settings_awareness`.

- [ ] **Step 5: Commit**

```
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "feat: gathering prompt reacts to depth and duration settings"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| `topicMinutes(topic, depthValue)` pure function | Task 1 |
| Badge on topic header, updates live | Task 2 |
| `reorderTopics(topics, fromPos, toPos)` pure, renumbers | Task 3 |
| Drag grip arms only on grip pointerdown | Task 4 |
| Insertion indicator (above/below line) | Task 4 CSS + events |
| Collapse-state remap after reorder | Task 4 `commitReorder` |
| Keyboard ArrowUp/Down with focus restore | Task 5 |
| `build_settings_context` validation + clamping | Task 6 |
| Chat route reads `settings`, appends to system | Task 7 |
| `stream_conversation` takes explicit `system` param | Task 7 |
| Frontend sends settings with every POST | Task 8 |
| `gathering.txt` UI settings awareness section | Task 9 |
| `gathering.txt` duration-target line updated | Task 9 |

**Placeholder scan:** No TBDs, no "implement later", no references to undefined types or functions.

**Type consistency:**
- `DurationEngine.topicMinutes` exported in Task 1, used in Task 2. ✓
- `DurationEngine.reorderTopics` exported in Task 3, used in Task 4. ✓
- `build_settings_context` defined and exported in Task 6, imported in test, used in Task 7 route. ✓
- `commitReorder` defined in Task 4, referenced in Task 5. ✓
- `dragState` declared in Task 4, referenced in drag events in Task 4. ✓

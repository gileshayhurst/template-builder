# Priority Setting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 1–5 star priority rating to every topic and core/probe item, with AI inference, user override via click, priority-weighted duration estimates, and `[P:N]` tags in the exported template.

**Architecture:** Items change from plain strings to `{text, priority}` objects throughout; a reusable `renderStarWidget` function handles UI; `priorityFactor(p)` scales duration contributions; the generation prompt gains `[P:N]` formatting rules.

**Tech Stack:** Python/Flask (backend), vanilla JS (frontend), pytest (tests), Anthropic SDK.

---

## File Map

| File | Change |
|---|---|
| `tests/test_tools.py` | Update 2 existing tests; add 3 new tests |
| `app.py` | Add `_normalise_item`; update `process_tool_call` add_topic case; update `add_topic` tool schema |
| `prompts/gathering.txt` | Add priority rating instructions |
| `prompts/generation.txt` | Add `[P:N]` format rules |
| `static/style.css` | Add `.star-widget` and `.star` styles |
| `static/app.js` | Add `priorityFactor`, `normaliseItem`, `renderStarWidget`, `updateItemText`, `updateItemPriority`; update `renderTopicBlock`, `renderItemRow`, `applyUpdate`, `addTopicManually`, `addItem`, `estimateDuration` |

---

## Task 1: Write failing tests for process_tool_call priority support

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Step 1: Replace the two existing add_topic tests and add three new ones**

Open `tests/test_tools.py` and replace the body starting from `def test_add_topic_with_probe` through `def test_add_topic_probe_defaults_to_empty` with the following, then add the three new tests after:

```python
def test_add_topic_with_probe():
    result = process_tool_call("add_topic", {
        "index": 1,
        "title": "Confirm the occasion",
        "priority": 5,
        "core": [{"text": "Identify the dish", "priority": 5}],
        "probe": [{"text": "Clarify if ambiguous", "priority": 2}]
    })
    assert result == {
        "section": "topic",
        "payload": {
            "index": 1,
            "title": "Confirm the occasion",
            "priority": 5,
            "core": [{"text": "Identify the dish", "priority": 5}],
            "probe": [{"text": "Clarify if ambiguous", "priority": 2}]
        }
    }


def test_add_topic_probe_defaults_to_empty():
    result = process_tool_call("add_topic", {
        "index": 2, "title": "Basic facts",
        "core": [{"text": "Collect dish name", "priority": 3}]
    })
    assert result["payload"]["probe"] == []


def test_add_topic_priority_defaults_to_3():
    result = process_tool_call("add_topic", {
        "index": 3, "title": "No priority given",
        "core": [{"text": "Some item", "priority": 3}]
    })
    assert result["payload"]["priority"] == 3


def test_add_topic_string_items_normalised():
    result = process_tool_call("add_topic", {
        "index": 4, "title": "Legacy call",
        "priority": 4,
        "core": ["Plain string item"],
        "probe": ["Another plain string"]
    })
    assert result["payload"]["core"] == [{"text": "Plain string item", "priority": 3}]
    assert result["payload"]["probe"] == [{"text": "Another plain string", "priority": 3}]


def test_add_topic_item_priority_defaults_to_3():
    result = process_tool_call("add_topic", {
        "index": 5, "title": "Item missing priority",
        "priority": 3,
        "core": [{"text": "No priority on this item"}]
    })
    assert result["payload"]["core"] == [{"text": "No priority on this item", "priority": 3}]
```

- [ ] **Step 2: Run the new tests to confirm they fail**

```
pytest tests/test_tools.py -v
```

Expected: `test_add_topic_priority_defaults_to_3`, `test_add_topic_string_items_normalised`, and `test_add_topic_item_priority_defaults_to_3` all FAIL. The two updated tests (`test_add_topic_with_probe`, `test_add_topic_probe_defaults_to_empty`) may pass or fail depending on current behaviour — that is fine.

---

## Task 2: Update process_tool_call to pass tests

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Add `_normalise_item` helper and update the `add_topic` case**

In `app.py`, add `_normalise_item` as a module-level function immediately before `process_tool_call`, then update the `add_topic` branch:

```python
def _normalise_item(item):
    if isinstance(item, str):
        return {"text": item, "priority": 3}
    return {"text": item["text"], "priority": item.get("priority", 3)}
```

Replace the existing `add_topic` branch inside `process_tool_call`:

```python
    elif name == "add_topic":
        return {"section": "topic", "payload": {
            "index": input_data["index"],
            "title": input_data["title"],
            "priority": input_data.get("priority", 3),
            "core": [_normalise_item(i) for i in input_data["core"]],
            "probe": [_normalise_item(i) for i in input_data.get("probe", [])]
        }}
```

- [ ] **Step 2: Run tests to confirm they all pass**

```
pytest tests/test_tools.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 3: Commit**

```
git add app.py tests/test_tools.py
git commit -m "feat: normalise priority in process_tool_call, update tests"
```

---

## Task 3: Update add_topic tool schema

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Replace the `add_topic` entry in GATHERING_TOOLS**

Find the `add_topic` dict in `GATHERING_TOOLS` (around line 56) and replace it entirely with:

```python
    {
        "name": "add_topic",
        "description": "Add or replace a numbered topic in the main interview guide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "1-based topic number"},
                "title": {"type": "string"},
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Overall topic importance 1–5. Default 3 if unsure."
                },
                "core": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Item importance 1–5. Default 3 if unsure."
                            }
                        },
                        "required": ["text"]
                    }
                },
                "probe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Item importance 1–5. Default 3 if unsure."
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            "required": ["index", "title", "core"]
        }
    },
```

- [ ] **Step 2: Run tests to confirm nothing broke**

```
pytest tests/test_tools.py -v
```

Expected: all 8 tests PASS (schema change doesn't affect process_tool_call).

- [ ] **Step 3: Commit**

```
git add app.py
git commit -m "feat: update add_topic schema to accept priority on topic and items"
```

---

## Task 4: Update gathering.txt with priority instructions

**Files:**
- Modify: `prompts/gathering.txt`

- [ ] **Step 1: Add a Priority Ratings section**

Append the following block to the end of `prompts/gathering.txt` (after the existing `## Rules` section):

```
## Priority Ratings

Every add_topic call must include a priority rating (1–5) for the topic and for each core and probe item:

- 5 — Critical: must be addressed in every interview regardless of time
- 4 — High: important and should normally be covered
- 3 — Medium: standard relevance; use when unsure
- 2 — Low: useful if time permits, not essential
- 1 — Minimal: rarely needed; include only for completeness

Set topic priority to reflect how central that theme is to the overall research goal.
Set each item's priority to reflect how important that specific objective is within its topic.
Always include priority in every add_topic call — never omit it.
```

- [ ] **Step 2: Commit**

```
git add prompts/gathering.txt
git commit -m "feat: instruct AI to set priority ratings in gathering prompt"
```

---

## Task 5: Add star widget CSS

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Append star widget styles**

Add the following to the end of `static/style.css`:

```css
/* Star priority widget */
.star-widget {
  display: inline-flex;
  gap: 1px;
  line-height: 1;
  flex-shrink: 0;
  align-self: center;
}

.star {
  font-size: 13px;
  color: #d1d5db;
  cursor: pointer;
  user-select: none;
  transition: color 0.08s;
}

.star.filled {
  color: #f59e0b;
}
```

- [ ] **Step 2: Commit**

```
git add static/style.css
git commit -m "feat: add star widget styles"
```

---

## Task 6: Add new JS helpers

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Add `priorityFactor` immediately before `estimateDuration`**

Find the line `function estimateDuration()` in `app.js` and insert before it:

```js
function priorityFactor(p) {
  return 0.5 + ((p ?? 3) - 1) * 0.25;
}
```

- [ ] **Step 2: Add `normaliseItem` immediately before `applyUpdate`**

Find the line `function applyUpdate(update)` and insert before it:

```js
function normaliseItem(item) {
  if (typeof item === "string") return { text: item, priority: 3 };
  return { text: item.text, priority: item.priority ?? 3 };
}
```

- [ ] **Step 3: Add `renderStarWidget` immediately before `renderTemplate`**

Find the line `function renderTemplate()` and insert before it:

```js
function renderStarWidget(currentPriority, onClickFn) {
  const widget = document.createElement("div");
  widget.className = "star-widget";
  widget.onclick = e => e.stopPropagation();

  function paint(hoverVal) {
    const fill = hoverVal ?? currentPriority;
    Array.from(widget.children).forEach((s, i) => {
      s.className = "star" + (i < fill ? " filled" : "");
    });
  }

  for (let i = 1; i <= 5; i++) {
    const s = document.createElement("span");
    s.className = "star" + (i <= currentPriority ? " filled" : "");
    s.textContent = "★";
    s.onmouseenter = () => paint(i);
    s.onmouseleave = () => paint(null);
    s.onclick = () => { currentPriority = i; paint(null); onClickFn(i); };
    widget.appendChild(s);
  }

  widget.onmouseleave = () => paint(null);
  return widget;
}
```

- [ ] **Step 4: Add `updateItemText` and `updateItemPriority` immediately after the existing `updateItem` function**

Find the existing `function updateItem(topicIndex, type, itemIndex, value)` block and add these two functions directly after it:

```js
function updateItemText(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex].text = value;
}

function updateItemPriority(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex].priority = value;
}
```

Note: the old `updateItem` function is now dead code — leave it for now; it will be removed when `renderItemRow` is updated in Task 8.

- [ ] **Step 5: Commit**

```
git add static/app.js
git commit -m "feat: add priorityFactor, normaliseItem, renderStarWidget, updateItemText/Priority helpers"
```

---

## Task 7: Update estimateDuration

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Replace the body of `estimateDuration`**

Find `function estimateDuration()` and replace its entire body with:

```js
function estimateDuration() {
  const topics = state.sections.topics;
  if (topics.length === 0) return 2;

  let raw = 0;
  for (const t of topics) {
    const tFactor = priorityFactor(t.priority ?? 3);
    raw += 0.8 * tFactor;
    for (let i = 1; i < t.core.length; i++) {
      raw += 0.2 * priorityFactor(t.core[i].priority ?? 3);
    }
    for (const p of t.probe) {
      raw += 0.1 * priorityFactor(p.priority ?? 3);
    }
  }

  raw += 0.5;
  raw += state.sections.expansion.length * 0.2;
  if (state.sections.focus) raw += 0.5;

  const v = state.depthSliderValue;
  const depthFactor = v < 50
    ? 1.0 - ((50 - v) / 50) * 0.35
    : 1.0 + ((v - 50) / 50) * 0.8;
  raw *= depthFactor;

  return Math.round(Math.min(90, Math.max(2, raw)));
}
```

- [ ] **Step 2: Commit**

```
git add static/app.js
git commit -m "feat: weight duration estimate by topic and item priority"
```

---

## Task 8: Update renderTopicBlock and renderItemRow

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Replace `renderTopicBlock`**

Find `function renderTopicBlock(topic)` and replace its entire body with:

```js
function renderTopicBlock(topic) {
  const topicKey = `topic-${topic.index}`;
  const collapsed = state.collapsedSections.has(topicKey);

  const block = document.createElement("div");
  block.className = "topic-block";

  const topicHeader = document.createElement("div");
  topicHeader.className = "topic-block-header";
  topicHeader.onclick = () => toggleSection(topicKey);

  const chevron = document.createElement("span");
  chevron.className = "section-chevron";
  chevron.textContent = collapsed ? "▸" : "▾";
  topicHeader.appendChild(chevron);

  const titleInput = document.createElement("input");
  titleInput.value = topic.title;
  titleInput.placeholder = "Topic title…";
  titleInput.oninput = function () { updateTopicField(topic.index, "title", this.value); };
  titleInput.onclick = e => e.stopPropagation();
  topicHeader.appendChild(titleInput);

  topicHeader.appendChild(renderStarWidget(topic.priority ?? 3, n => {
    updateTopicField(topic.index, "priority", n);
    renderTemplate();
  }));

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-topic-btn";
  removeBtn.textContent = "×";
  removeBtn.onclick = e => { e.stopPropagation(); removeTopicManually(topic.index); };
  topicHeader.appendChild(removeBtn);

  block.appendChild(topicHeader);

  if (!collapsed) {
    const body = document.createElement("div");
    body.className = "topic-block-body";

    const list = document.createElement("div");
    list.className = "items-list";
    topic.core.forEach((item, i) => list.appendChild(renderItemRow("core", topic.index, i, item)));
    topic.probe.forEach((item, i) => list.appendChild(renderItemRow("probe", topic.index, i, item)));
    body.appendChild(list);

    const btnRow = document.createElement("div");
    btnRow.style.cssText = "display:flex;gap:6px;margin-top:4px;";
    const ac = document.createElement("button");
    ac.className = "add-item-btn"; ac.textContent = "+ Core item";
    ac.onclick = () => addItem(topic.index, "core");
    const ap = document.createElement("button");
    ap.className = "add-item-btn"; ap.textContent = "+ Probe item";
    ap.onclick = () => addItem(topic.index, "probe");
    btnRow.appendChild(ac); btnRow.appendChild(ap);
    body.appendChild(btnRow);

    block.appendChild(body);
  }

  return block;
}
```

- [ ] **Step 2: Replace `renderItemRow`**

Find `function renderItemRow(type, topicIndex, itemIndex, text)` and replace entirely with:

```js
function renderItemRow(type, topicIndex, itemIndex, item) {
  const row = document.createElement("div");
  row.className = "item-row";

  const badge = document.createElement("span");
  badge.className = `item-badge ${type}`;
  badge.textContent = type === "core" ? "Core" : "Probe";
  row.appendChild(badge);

  row.appendChild(renderStarWidget(item.priority ?? 3, n => updateItemPriority(topicIndex, type, itemIndex, n)));

  const textarea = document.createElement("textarea");
  textarea.value = item.text;
  textarea.oninput = function () { updateItemText(topicIndex, type, itemIndex, this.value); };
  row.appendChild(textarea);

  return row;
}
```

Also delete the now-unused `updateItem` function (the old one that wrote a raw string to `topic[type][itemIndex]`).

- [ ] **Step 3: Commit**

```
git add static/app.js
git commit -m "feat: add star widgets to topic header and item rows"
```

---

## Task 9: Update applyUpdate, addTopicManually, addItem

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Update the `topic` case in `applyUpdate`**

Find the `else if (section === "topic")` block in `applyUpdate` and replace it with:

```js
  } else if (section === "topic") {
    const raw = { ...payload, index: parseInt(payload.index, 10) };
    const topic = {
      ...raw,
      priority: raw.priority ?? 3,
      core: (raw.core || []).map(normaliseItem),
      probe: (raw.probe || []).map(normaliseItem)
    };
    const idx = state.sections.topics.findIndex(t => t.index === topic.index);
    if (idx >= 0) state.sections.topics[idx] = topic;
    else {
      state.sections.topics.push(topic);
      state.sections.topics.sort((a, b) => a.index - b.index);
    }
    flashSection("section-topics");
```

- [ ] **Step 2: Update `addTopicManually`**

Replace the body of `addTopicManually` with:

```js
function addTopicManually() {
  const nextIndex = state.sections.topics.length
    ? Math.max(...state.sections.topics.map(t => t.index)) + 1
    : 1;
  state.sections.topics.push({ index: nextIndex, title: "", priority: 3, core: [{ text: "", priority: 3 }], probe: [] });
  renderTemplate();
}
```

- [ ] **Step 3: Update `addItem`**

Replace the body of `addItem` with:

```js
function addItem(topicIndex, type) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) { topic[type].push({ text: "", priority: 3 }); renderTemplate(); }
}
```

- [ ] **Step 4: Run the Python tests to confirm backend still passes**

```
pytest tests/test_tools.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```
git add static/app.js
git commit -m "feat: normalise topic payload in applyUpdate, update manual-add helpers"
```

---

## Task 10: Update generation.txt for [P:N] export tags

**Files:**
- Modify: `prompts/generation.txt`

- [ ] **Step 1: Update the Output Format section and Rules**

Replace the entire contents of `prompts/generation.txt` with:

```
You are a template formatter. You receive structured template data as JSON and must output it in the exact syntax below. Output ONLY the formatted template — no explanation, no preamble, no markdown fences.

## Output Format

[Prompt metadata only: TITLE | vVERSION | DATE]

# Pacing Instructions
- **Do Not Rush** DO_NOT_RUSH_TEXT

- **Core vs. Probe:** CORE_VS_PROBE_TEXT
- **One main ask per turn:** ONE_ASK_TEXT
- **Keep questions light:** KEEP_LIGHT_TEXT

- **Follow strong signals:** FOLLOW_SIGNALS_TEXT
- **Original follow-ups allowed:** ORIGINAL_FOLLOWUPS_TEXT
- **Selective probing:** SELECTIVE_PROBING_TEXT

- **The Finish Line** FINISH_LINE_TEXT



# Main Interview Guide: TITLE

## Interview focus
- [Core] FOCUS_TEXT

## Topic 1 [P:4]: TOPIC_TITLE
- [Core][P:5] CORE_ITEM
- [Probe][P:2] PROBE_ITEM

## Topic 2 [P:3]: TOPIC_TITLE
...

# Expansion Topics
Use these for secondary discovery as instructed
- ITEM
- ITEM

## Rules
- Every core item: prefix with "- [Core][P:N] " where N is the item's priority value
- Every probe item: prefix with "- [Probe][P:N] " where N is the item's priority value
- Every topic heading: "## Topic N [P:N]: TOPIC_TITLE" where the first N is the 1-based index and the second N is the topic's priority value
- The focus line uses "- [Core] FOCUS_TEXT" with no priority tag
- If a topic has no probe items, omit all [Probe] lines for that topic entirely
- Repeat the topic block pattern for every topic in the topics array
- Preserve the blank lines between pacing rule groups exactly as shown above
- Two blank lines between the last pacing rule and the "# Main Interview Guide" heading
- Output nothing except the formatted template
```

- [ ] **Step 2: Commit**

```
git add prompts/generation.txt
git commit -m "feat: add [P:N] priority tags to exported template format"
```

---

## Manual Verification Checklist

After all tasks are complete, start the app (`python main.py`) and verify:

- [ ] Open the app in the browser — topics panel shows 3 filled stars (★★★☆☆) on each topic and each core/probe item once the AI generates them
- [ ] Clicking a star on a topic changes its rating; clicking a star on an item changes that item's rating without collapsing the topic
- [ ] Hovering stars previews the rating (stars light up on hover, revert on mouseout)
- [ ] The duration estimate changes when you click high-priority stars (5 stars increases estimate; 1 star decreases it)
- [ ] Manually adding a topic (+ Add Topic button) starts with 3 filled stars; manually adding an item starts with 3 filled stars
- [ ] Clicking Export shows `[P:N]` tags on topic headings and on every core/probe line in the output
- [ ] The focus line in the export has no `[P:N]` tag

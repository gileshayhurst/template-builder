# Design: Drag-to-Reorder Topics, Per-Topic Duration Badges, and Settings Awareness

**Date:** 2026-06-17
**Status:** Approved for planning

## Overview

Three related improvements to the topics-and-timing loop:

- **#9 — Drag-to-reorder topics:** grip handles on topic blocks let the user drag them into a new order, honouring the gathering prompt's funnel-ordering rule (easy → sensitive → reflective) without manual index editing.
- **#10 — Per-topic duration badges:** a small `~N min` chip on each topic header shows its estimated time cost, computed from the same engine as the headline estimate; updates live as depth, priorities, or topics change.
- **#11 — Advisory settings awareness:** the AI builder receives the current depth/duration settings with each message and proactively flags a significant mismatch between the live estimate and the target, offering to trim or expand — but only acts when the user agrees.

No new dependencies. No build step. The frontend stays vanilla JS + CSS.

---

## #10 — Per-topic duration badges

### Engine change (duration.js)

New pure function:

```
topicMinutes(topic, depthValue) → integer (minutes, ≥ 1)
  raw = 0.8 · priorityFactor(topic.priority)
      + Σ (i ≥ 1) 0.2 · priorityFactor(core[i].priority)    // first core folded into base
      + Σ         0.1 · priorityFactor(probe.priority)
  return max(1, round(raw · depthFactorFor(depthValue)))
```

Reuses existing `priorityFactor` and `depthFactorFor` so a badge can never disagree with the headline estimate's arithmetic. A minimum of `1` is returned so the user never sees `0 min`.

**Honest display caveat:** badges are per-topic costs and intentionally exclude the fixed conversational overhead (`+0.5` baseline, `+0.5` focus, expansion items) that sits outside any individual topic. This means badge totals will be slightly under the headline estimate; this is correct and expected behaviour. No note is needed in the UI; it just works.

### Render change (app.js)

In `renderTopicBlock(topic)`, after the star widget and before the remove button, insert a `<span class="topic-duration-badge">~N min</span>` whose value is `DurationEngine.topicMinutes(topic, state.depthSliderValue)`. The badge is recomputed on every `renderTemplate()` call so it reflects live edits to priority, probe count, and depth slider.

### Style (style.css)

Badge: small, muted chip — grey background, smaller font, left-padded. Sits between the star widget and the × button in the flex row of the topic header.

---

## #9 — Drag-to-reorder topics

### Interaction model

A grip handle (`⠿`) at the far left of each topic header. The topic block (`div.topic-block`) gains `draggable="true"`, but drag events are **armed only when the gesture starts on the grip**. This is implemented by a `pointerdown` listener on the grip that sets `block.draggable = true`, and a `pointerup`/`dragend` listener that resets it to `false`. Without this guard, clicking the title input, stars, or collapse toggle would accidentally start a drag.

### Drag event flow

| Event | Target | Action |
|---|---|---|
| `dragstart` | topic block | record `fromIndex` in a module-level `dragState` object; set drag image to a ghost clone |
| `dragover` | topic block | show insertion indicator; update `dragState.toIndex` |
| `dragleave` | topic block | remove insertion indicator |
| `drop` | topic block | call `reorderTopics`; clear `dragState` |
| `dragend` | topic block | clear indicators and `dragState` regardless |

A single `dragState = { fromIndex: null, toIndex: null }` module-level object tracks the current drag. Both indices are positions within `state.sections.topics`, not `topic.index` values (which are renumbered on drop).

### Reorder logic (pure helper)

```
reorderTopics(topics, fromPos, toPos) → new array
  move element at fromPos to toPos
  renumber: topics[i].index = i + 1  (1-based)
```

Returns a new array; does not mutate input. `fromPos === toPos` is a no-op.

### Collapse-state remapping

After `reorderTopics` returns, remap `state.collapsedSections`:

```
for each entry "topic-N" in collapsedSections:
  find the topic that now has index N after renumbering
  the topic's previous index gives the old key
  retain collapsed state under the new key
```

Concretely: before renumbering, record `{ oldIndex → position }` for every topic; after renumbering, rebuild `collapsedSections` using `topic-${newIndex}` for any topic whose `oldIndex` was in the set.

### Accessibility

The grip is rendered as `<span role="button" tabindex="0" aria-label="Drag to reorder" class="topic-grip">`. On `keydown`:
- `ArrowUp` — move topic one slot earlier; keep focus on the grip.
- `ArrowDown` — move topic one slot later; keep focus on the grip.

Both reuse `reorderTopics` and the collapse-state remap.

### Visual feedback (style.css)

- Grip: `cursor: grab`, `user-select: none`; `cursor: grabbing` while active.
- Dragged block: `opacity: 0.5`.
- Drop target: a `2px` accent-colour line above or below the hovered block (an `::after` / `::before` pseudo-element toggled by a `drag-over-above` / `drag-over-below` class).

---

## #11 — Advisory settings awareness

### Data flow

In `streamFromServer(message)`, extend the `/chat` POST body:

```json
{
  "message": "...",
  "settings": {
    "depthValue": 50,
    "depthLabel": "Balanced",
    "durationTarget": 30,
    "estimate": 38
  }
}
```

`durationTarget: 0` means no target is set. `estimate` comes from `estimateDuration()`.

On the server, the `chat` route extracts `settings` from the request JSON (defaulting to `{}` when absent). A pure helper function `build_settings_context(settings)` validates and formats it into a plain-text context block. This block is appended to `GATHERING_PROMPT` as the `system` parameter for that Anthropic call. Missing, invalid, or zero-target settings produce no block (current behaviour is preserved).

```python
def build_settings_context(settings):
    """Return a system-prompt snippet from UI settings, or '' if nothing meaningful."""
    if not settings or not isinstance(settings, dict):
        return ''
    depth_value = settings.get('depthValue')
    depth_label = settings.get('depthLabel', '')
    target = settings.get('durationTarget', 0)
    estimate = settings.get('estimate', 0)

    # clamp to valid ranges
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

### Prompt change (gathering.txt)

Add a new section **"UI settings awareness"** near the end of the prompt, after the existing rules:

```
## UI settings awareness
If the conversation includes a "Current UI settings" block, use it as follows:
- Let the depth/breadth setting inform your framing: a breadth setting suggests fewer probes and broader coverage; a deep setting suggests richer probes and more episodic framing.
- If a duration target is set and the current estimate differs from it by more than 25%, flag this proactively — once — in natural language: e.g. "You've set a 20-minute target but the template is currently estimated at 38 minutes. Want me to trim some topics?" Then wait for the user's response before acting.
- Do not flag duration mismatches on every turn. Mention it once when you first notice a significant gap; after that, let the user direct you.
- Do not attempt to hit the duration target autonomously. The duration coach in the UI handles precise fit. Your job is quality; the coach's job is fit.
- The estimate shown is a rough heuristic. Treat it as directional.
```

Also update the existing line that says "Do NOT try to hit a specific interview length" to read: "Do NOT try to hit a specific interview length autonomously — flag a large gap once and offer, but act only when the user asks."

### Server change (app.py)

In the `chat` route:

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

`stream_conversation` receives an explicit `system` parameter instead of always using `GATHERING_PROMPT` directly:

```python
def stream_conversation(new_message, system=None):
    if system is None:
        system = GATHERING_PROMPT
    ...
```

---

## Testing

### duration.test.js — new cases for topicMinutes

- `topicMinutes` on a topic with 1 core + 2 probes at depth 50 returns expected value.
- Returns at least 1 for a topic with only 1 core item at priority 1.
- Changes when depth slider moves.
- Summing `topicMinutes` over all topics ≤ `estimateDurationFor` (overhead is excluded).

### tests/test_routes.py — new cases for build_settings_context

- Returns `''` for empty/missing/invalid input.
- Returns correct block for valid depth + target + estimate.
- Clamps out-of-range values.
- `durationTarget: 0` produces no duration lines.

### tests/test_gathering_prompt.py — new assertion

- `GATHERING_PROMPT` contains the phrase `"UI settings awareness"`.

---

## Files affected

| File | Change |
|---|---|
| `static/duration.js` | Add `topicMinutes` pure function; export in `api` |
| `static/app.js` | Badge render in `renderTopicBlock`; drag handle + events + `reorderTopics`; settings in `/chat` POST |
| `static/style.css` | Badge chip; grip handle; drag feedback (ghost, insertion line) |
| `app.py` | `build_settings_context`; `chat` route passes settings context; `stream_conversation` accepts `system` param |
| `prompts/gathering.txt` | Add UI settings awareness section; update duration-target line |
| `tests/duration.test.js` | New `topicMinutes` test cases |
| `tests/test_routes.py` | New `build_settings_context` test cases |
| `tests/test_gathering_prompt.py` | Assert new section present |

---

## Out of scope

- Active time-fitting by the AI (the coach owns precise fit).
- Touch / mobile drag support (pointer events on grip; keyboard fallback covers accessibility).
- Multi-level undo for drag operations (one-step coach undo is unchanged).
- Deployment, auth, persistence.

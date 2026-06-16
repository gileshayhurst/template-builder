# Priority Setting — Design Spec
**Date:** 2026-06-16

## Overview

Add a 1–5 star priority rating to every topic and every core/probe item. The AI infers ratings when building the template; the user can override any rating by clicking stars. Priority is reflected in the exported template as a compact `[P:N]` tag and influences the estimated interview duration.

---

## Data Model

### Before
```js
topic: { index, title, core: string[], probe: string[] }
```

### After
```js
topic: {
  index: number,
  title: string,
  priority: number,          // 1–5, default 3
  core:  Array<{ text: string, priority: number }>,   // default 3
  probe: Array<{ text: string, priority: number }>    // default 3
}
```

All priority fields default to `3` when absent — this keeps estimates unchanged for any path that doesn't supply a rating, and avoids a blank/unrated state the user might forget to fill.

---

## Backend (`app.py`)

### `add_topic` tool schema
- Add top-level `priority` field: integer, 1–5, optional.
- Change `core` and `probe` item schema from `string` to `{ text: string, priority?: integer }`.

### `process_tool_call`
- Normalise each incoming core/probe item: if the AI sends a plain string, wrap it as `{ text: item, priority: 3 }`. If it sends an object, default `priority` to `3` if omitted.
- Pass `priority` (defaulting to `3`) through to the topic payload.

### `prompts/gathering.txt`
Add a short instruction block telling the AI to rate each topic and item 1–5 based on inferred research importance, and to include those ratings in every `add_topic` call.

---

## Frontend (`static/app.js`)

### Star widget
A reusable function `renderStarWidget(currentPriority, onClickFn)` returns a `<div class="star-widget">` with five `<span>` children. Stars ≤ `currentPriority` render as ★ (filled, gold); stars above render as ☆ (empty, grey). Clicking star N calls `onClickFn(N)` and stops event propagation. Hovering previews the would-be rating.

### Topic header
Star widget sits between the title input and the × button. On click: `updateTopicField(topic.index, 'priority', n)` then `renderTemplate()`.

### Item rows
`renderItemRow` receives `{ text, priority }` instead of a plain string. Star widget sits between the badge (`Core`/`Probe`) and the textarea. On click: new helper `updateItemPriority(topicIndex, type, itemIndex, n)` then `renderTemplate()`.

### Manual-add helpers
- `addTopicManually` — pushes `{ ..., priority: 3, core: [{ text: '', priority: 3 }], probe: [] }`.
- `addItem` — pushes `{ text: '', priority: 3 }`.

### `applyUpdate`
When processing a `topic` section update, normalise incoming core/probe items through the same string→object wrapper so any legacy or unexpected plain-string payloads are handled safely.

### `updateItem` / `updateItemText`
`updateItem` currently writes a raw string; rename it to `updateItemText` to make its scope explicit. `updateItemPriority` is a new parallel helper.

### `static/style.css`
Add styles for `.star-widget`, `.star` (cursor pointer, base grey colour), `.star.filled` (gold), and a hover highlight that fills stars up to the hovered one.

---

## Duration Formula (`estimateDuration`)

### Priority multiplier
```js
function priorityFactor(p) {
  return 0.5 + (p - 1) * 0.25;
  // p=1 → 0.50×,  p=2 → 0.75×,  p=3 → 1.00×,  p=4 → 1.25×,  p=5 → 1.50×
}
```

### Updated accumulation (per topic)
```
raw += 0.8 × priorityFactor(topic.priority)
     + Σ(core items beyond first) × 0.2 × priorityFactor(item.priority)
     + Σ(probe items)             × 0.1 × priorityFactor(item.priority)
```

Everything else is unchanged: `+0.5` finish-line buffer, `+0.2` per expansion item, `+0.5` if focus is set, then multiply by the existing depth factor.

**Regression check:** at all-default priority (3), `priorityFactor = 1.0` everywhere — the estimate is identical to today's output.

**Range:** a fully 5-star interview is 1.5× the baseline; a fully 1-star interview is 0.5×.

---

## Export Format

### Topic heading
```
## Topic 1 [P:4]: Store arrival and navigation
```

### Items
```
- [Core][P:5] Understand how the participant arrived and navigated to the store.
- [Probe][P:2] Ask whether they had been before.
```

### Rules added to `prompts/generation.txt`
- Append `[P:N]` after the topic number in every `## Topic N` heading, before the colon.
- Append `[P:N]` between the `[Core]`/`[Probe]` badge and the item text for every item.
- The focus line (`- [Core] FOCUS_TEXT`) carries no priority tag.

---

## Tests (`tests/test_tools.py`)

- Update existing `add_topic` tests to send `{ text, priority }` objects for core/probe.
- Add a test that plain-string items in an `add_topic` call are normalised to `{ text, priority: 3 }`.
- Add a test that a missing topic `priority` defaults to `3` in the returned payload.

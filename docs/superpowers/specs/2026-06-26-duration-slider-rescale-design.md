# Duration Slider Rescale — Design Spec

**Date:** 2026-06-26
**Status:** Approved

## Problem

The goal-duration slider runs 0–90 minutes in steps of 5. Real interviews in this tool last 2–20 minutes, which means:

- The usable range is packed into the bottom quarter of the slider track.
- You cannot target fine values like 12 or 18 min (step of 5 is too coarse).
- The bar looks almost empty for typical sessions, giving no useful visual feedback.

## Decision

Rescale the **display layer** to 1–30 min in steps of 1. The "30" mark is labelled "30+" to signal that the estimate can still exceed 30 — the bar caps there but the estimate label remains honest.

The content-estimate math inside `duration.js` is unchanged — it already clamps to 90 internally and that ceiling is appropriate for the suggestion engine's arithmetic.

## Constants

Introduce one named constant in `app.js`:

```js
const DURATION_SCALE_MAX = 30;
```

All five current hard-coded `90` values in the display layer are replaced by this constant.

## Target value semantics

- `0` — "No target set" (existing state, unchanged)
- `1–29` — a specific minute target
- `30` — "30+ min" (the cap; any template needing more than 30 min fills the bar completely)

## Affected code

### `app.js`

| Location | Old | New |
|---|---|---|
| `durationViewModel()` — target pct | `state.durationTarget / 90` | `state.durationTarget / DURATION_SCALE_MAX` |
| `durationViewModel()` — estimate pct | `estimate / 90` | `Math.min(100, (estimate / DURATION_SCALE_MAX) * 100)` |
| `setDurationTarget()` clamp | `Math.min(90, …)` | `Math.min(DURATION_SCALE_MAX, …)` |
| `renderSettings()` slider | `max="90" step="5"` | `max="30" step="1"` |
| `renderSettings()` number input | `max="90" step="5"` | `max="30" step="1"` |
| `durationViewModel()` target label | `● Target: N min` | `● Target: 30+ min` when N === 30, else `● Target: N min` |

### `duration.js`

No changes.

### `tests/duration.test.js`

No changes (tests exercise the content-estimate engine only, not the display scale).

### `tests/`

`pytest tests/` should be unaffected. Run both suites to confirm.

## Verification

1. Run `pytest tests/` — all pass.
2. Run `node --test tests/duration.test.js` — all pass.
3. Start `python main.py`, open browser.
4. Drag slider from 0 to 30 — confirm label reads "30+", bar fills to 100%.
5. Set a target of 15 — confirm bar and label update correctly.
6. With a content-heavy template (estimate > 30), confirm estimate label shows the real number (e.g. "42 mins") while bar stays at 100%.

## Out of scope

- Depth slider
- Coach suggestion logic
- Per-topic minute badges
- Any export or review behaviour

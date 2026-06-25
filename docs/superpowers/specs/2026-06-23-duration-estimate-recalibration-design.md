---
name: duration-estimate-recalibration
description: Recalibrate duration estimate constants so balanced depth (50) anchors at ~5 min; update label wording
metadata:
  type: project
---

# Duration Estimate Recalibration

## Problem

The duration estimate formula was over-reporting expected interview time. A 7-topic grocery store guide estimated at 11 minutes was completed in ~5 minutes. The formula's base constants were calibrated too high — balanced depth (the neutral/unaltered pacing setting) should be the 5-minute anchor, with breadth running shorter and deep running longer.

## Root Cause

The formula in `static/duration.js → estimateRawFor` produces a raw total of ~7.1 for a typical 7-topic guide (all topics at priority 3, 1 core + 1 probe each). Since the depth factor at balanced (v=50) is 1.0, the balanced estimate was ~7 min instead of ~5 min. The base constants were simply over-sized.

The depth factor shape is correct and stays unchanged:
- `depthFactorFor(0)` = 0.65 (breadth = faster)
- `depthFactorFor(50)` = 1.0 (balanced = baseline)
- `depthFactorFor(100)` = 1.8 (deep = slower)

## Changes

### 1. `static/duration.js` — lower base constants

In `estimateRawFor` and `topicMinutes`, change the three time weights:

| Constant | Old | New |
|---|---|---|
| Topic base (first core) | `0.8` | `0.55` |
| Additional core item | `0.2` | `0.14` |
| Probe item | `0.1` | `0.07` |

Everything else (depth factor, `0.5` base overhead, `0.2` per expansion item, `0.5` for focus, clamp to [2, 90]) stays unchanged.

### 2. `tests/duration.test.js` — update expected values

The `estimateDurationFor matches known values across depths` test uses a 2-topic fixture with expansion and focus. Expected values change:

| Depth | Old expected | New expected |
|---|---|---|
| 0 | 3 | 2 |
| 50 | 4 | 3 |
| 100 | 7 | 6 |

All `topicMinutes` tests continue to pass without change.

### 3. `static/app.js` — label wording (2 occurrences)

Change `● Est: ${estimate} min` to `time est. to fully cover content: ${estimate} mins` in:
- `updateDurationDisplay()` (~line 116)
- `renderTemplate()` HTML string (~line 391)

## Expected output for 7-topic grocery guide (all priority 3)

| Depth preset | Estimate |
|---|---|
| Breadth (0) | 3 min |
| Slightly Broad (25) | ~4 min |
| **Balanced (50)** | **5 min** |
| Slightly Deep (75) | 7 min |
| Deep (100) | 9 min |

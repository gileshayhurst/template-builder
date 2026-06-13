# Interactive Controls — Design Spec
**Date:** 2026-06-13
**Version:** 1.0

---

## Overview

Three additions to the Template Builder frontend that make the interface more interactive and give the client more control without leaving the page:

1. **Collapsible template sections** — every section in the template panel can be collapsed/expanded
2. **Settings strip** — a collapsible strip at the top of the template panel with a Depth slider and a Duration control
3. **Quick action buttons** — three preset prompt buttons above the chat textarea

All changes are purely frontend. No new backend routes or API calls are required.

---

## Feature 1: Collapsible Template Sections

### Behaviour

Every section header in the template panel gains a chevron toggle (`▸` collapsed, `▾` expanded). Clicking it collapses or expands that section's body.

### Collapsible units

| Unit | Key |
|------|-----|
| Metadata | `"metadata"` |
| Pacing Instructions (whole block) | `"pacing"` |
| Individual pacing rule | `"pacing-<rule_key>"` (e.g. `"pacing-do_not_rush"`) |
| Interview Focus | `"focus"` |
| Topics (whole block) | `"topics"` |
| Individual topic | `"topic-<index>"` (e.g. `"topic-1"`) |
| Expansion Topics | `"expansion"` |

### State

A `collapsedSections` Set is added to the JS state object:

```js
const state = {
  collapsedSections: new Set(["settings"]),  // "settings" pre-collapsed on load
  streaming: false,
  ...
};
```

All template sections start expanded. The settings strip starts collapsed (key `"settings"` pre-populated). No persistence across page reloads in v1.

### Rendering

`renderTemplate()` checks `state.collapsedSections` when building each section. Collapsed sections render the header only; the body is hidden. The chevron rotates via a CSS class (`collapsed`).

---

## Feature 2: Settings Strip

A thin collapsible strip pinned above the scrollable template content, inside the template panel. Contains two controls side by side: **Depth vs. Breadth** and **Duration**.

The strip itself has its own collapse toggle (label: "Settings ▾"). Collapsed by default on first load to stay out of the way; state persisted in `collapsedSections` under key `"settings"`.

### 2a. Depth vs. Breadth Slider

A horizontal slider that snaps to 5 positions:

| Position | Value | Label |
|----------|-------|-------|
| 0 | 0 | Breadth |
| 1 | 25 | Slightly Broad |
| 2 | 50 | Balanced |
| 3 | 75 | Slightly Deep |
| 4 | 100 | Deep |

**Effect:** Moving the slider applies the matching preset to `state.sections.pacing` and re-renders the Pacing section. "Balanced" (position 2) maps to the existing `PACING_DEFAULTS`, making it the safe starting state.

**Manual override:** After the slider moves, the user can still hand-edit individual pacing rules. Each rule retains a small "Reset to slider position" link that restores that rule's preset text for the current slider value.

**Implementation:**

```js
const PACING_DEPTH_PRESETS = {
  breadth:        { do_not_rush: "...", core_vs_probe: "...", ... },
  slightly_broad: { ... },
  balanced:       { ...PACING_DEFAULTS },
  slightly_deep:  { ... },
  deep:           { ... }
};
```

The five preset texts below define what each position says for each rule. The principle:
- **Breadth end:** rules favour moving through topics, limiting probes, keeping time per topic short
- **Deep end:** rules favour following signals extensively, prioritising every probe, not rushing

### 2b. Duration Control

Two parallel horizontal tracks displayed as a single stacked control:

| Track | Colour | Type | Range |
|-------|--------|------|-------|
| Target | Blue | Interactive | 0–90 min |
| Estimate | Orange dashed | Read-only | 2–90 min |

**Target input:** A range slider (`step="5"`) and a number input kept in sync — dragging the slider updates the number field, typing in the number field updates the slider. `0` means "no target set" and hides the blue track label.

**Live estimate:** Recalculated by `estimateDuration()` on every call to `applyUpdate()` and whenever the depth slider changes. Displayed as the orange track position and the label `● Est: Y min`.

#### Duration formula

```
base       = 5 × topic_count
core_bonus = Σ max(0, topic.core.length − 1) × 1.0   (per topic)
probe_bonus= Σ topic.probe.length × 0.5               (per topic, active probes only)

raw = base + core_bonus + probe_bonus

# Pacing multipliers (cumulative, applied to raw)
if do_not_rush active         → raw × 1.15
if follow_signals active      → raw × 1.10
if original_followups active  → raw × 1.05
if selective_probing active   → raw × 0.95

# Flat additions
if finish_line active         → raw += 5
expansion_bonus               = expansion.length × 0.75
if focus present              → raw += 2

# Depth slider adjustment
depth_factor = lerp(0.80, 1.20, slider_value / 100)  # 0.5 → exactly ×1.0 at Balanced
raw × depth_factor

# Final clamp
estimate = clamp(raw, 2, 90)
```

Labels beneath the tracks:
- `● Target: X min` (blue) — hidden if target is 0
- `● Est: Y min` (orange)

---

## Feature 3: Quick Action Buttons

A row of three pill buttons placed just above the chat textarea, inside the chat panel.

| Button | Label | Message sent to /chat |
|--------|-------|----------------------|
| Suggest topic | `+ Suggest a topic` | `"Can you suggest another topic we haven't covered yet?"` |
| Tighten pacing | `⚡ Tighten pacing` | `"Can you review the pacing instructions and tighten them up — make them more concise and actionable?"` |
| Add expansion | `↗ Add expansion ideas` | `"Can you suggest some additional expansion topics based on what we've built so far?"` |

Clicking a button calls `streamFromServer(message)` directly — the preset text is appended to the chat as a user message and streamed through `/chat` exactly as if the user had typed it.

All three buttons are disabled (`disabled` attribute) while `state.streaming` is true, matching the existing Send button behaviour.

---

## Files Changed

| File | Changes |
|------|---------|
| `static/app.js` | Add `collapsedSections` to state; add `PACING_DEPTH_PRESETS`; update `renderTemplate()` for collapse toggles; add `estimateDuration()` and `updateDurationDisplay()`; add quick-action button handlers; add depth slider handler |
| `static/style.css` | Styles for settings strip, dual-track duration control, collapse chevron, quick-action buttons |
| `templates/index.html` | Add quick-action button row above textarea; settings strip is rendered by JS |

No backend changes required.

---

## Out of Scope (v1)

- Persisting collapsed state across page reloads
- Animating collapse transitions
- User-configurable quick action messages
- More than 3 quick action buttons

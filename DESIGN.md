---
name: Template Builder
description: Interview-guide builder aligned to Forven's warm-editorial product system.
colors:
  terracotta: "#bf5b34"
  terracotta-deep: "#a34a28"
  peach-soft: "#fbe9da"
  apricot-tile: "#f6dcc2"
  warm-card: "#fdf7f1"
  navy-ink: "#1f2d3d"
  slate-body: "#64748b"
  slate-muted: "#7c8a9c"
  page-bg: "#eef2f7"
  surface: "#ffffff"
  border-warm: "#f0e6db"
  border-cool: "#e5e9f0"
  scrim: "#00000066"
typography:
  display:
    fontFamily: "Inter, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "clamp(1.75rem, 3vw, 2rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Inter, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Inter, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, -apple-system, 'Segoe UI', sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.08em"
  mono:
    fontFamily: "'Courier New', ui-monospace, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: 1.7
    letterSpacing: "normal"
rounded:
  fine: "2px"
  tight: "3px"
  compact: "4px"
  sm: "6px"
  control: "8px"
  md: "10px"
  chip: "12px"
  lg: "14px"
  pill: "999px"
spacing:
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.peach-soft}"
    textColor: "{colors.terracotta}"
    rounded: "{rounded.sm}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.apricot-tile}"
    textColor: "{colors.terracotta-deep}"
  chip-filter:
    backgroundColor: "{colors.peach-soft}"
    textColor: "{colors.terracotta}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
  card:
    backgroundColor: "{colors.warm-card}"
    textColor: "{colors.navy-ink}"
    rounded: "{rounded.lg}"
    padding: "24px"
  icon-tile:
    backgroundColor: "{colors.apricot-tile}"
    textColor: "{colors.navy-ink}"
    rounded: "{rounded.md}"
    size: "44px"
  input-search:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.navy-ink}"
    rounded: "{rounded.sm}"
    padding: "10px 12px"
  nav-item-active:
    backgroundColor: "{colors.peach-soft}"
    textColor: "{colors.terracotta}"
    rounded: "{rounded.sm}"
    padding: "6px 12px"
---

# Design System: Template Builder

## 1. Overview

**Creative North Star: "The Warm Research Instrument"**

This is the visual system of **Forven** — the AI market-research platform this
template builder is joining — captured from the live product (the Home dashboard
and Research/Projects screens). It is the **target** system for the builder, not a
description of the builder's current code: the builder today ships an indigo
(`#4f46e5`) accent on a cool gray ground, which is off-brand and must be migrated
onto the palette below. This file is the destination.

Forven's identity is a deliberate **warm-over-cool split**. The working ground is a
calm, cool blue-gray; content and structure are rendered in a confident navy-slate
ink; and every moment of brand or interactivity is carried by a single warm
**terracotta** accent, softened into peach tints for surfaces. It reads as a
serious research instrument that is nonetheless warm and human — the opposite of
both cold enterprise gray and bright consumer play. Density serves the task:
generous card padding, hairline borders, and flat surfaces keep complex
operational screens (projects, cohorts, sessions) legible without clutter.

The system explicitly rejects: bright, rounded, gamified consumer energy; dense
gray legacy-enterprise clutter; and decorative, animation-heavy flash. It also
rejects the builder's inherited indigo — cool blue accents are foreign to this
brand.

**Key Characteristics:**
- Warm terracotta accent, cool navy ink, cool blue-gray ground.
- Peach/apricot tints for interactive surfaces, pills, and icon tiles.
- Flat by default: depth is tint + hairline border, not shadow.
- Uppercase tracked eyebrows and rounded-square icon tiles are house motifs.
- Humanist sans (Inter), navy for all headings, generous whitespace.

## 2. Colors

A cool blue-gray stage on which a single warm terracotta accent, softened to peach,
does all the interactive and brand work.

### Primary
- **Terracotta** (`#bf5b34`, oklch ≈ 0.60 0.13 45): The one brand and interaction
  color. Carries links, active-nav text, button labels, filter-pill text, and key
  stat numbers. It signals "you can act here." Deepens to **Terracotta Deep**
  (`#a34a28`) on hover/press.
- **Peach Soft** (`#fbe9da`): The accent's surface form. Fills the active nav pill,
  the primary buttons, and state chips — terracotta text sits on it. **Apricot Tile**
  (`#f6dcc2`) is the slightly deeper step used for icon tiles and hover fills.

### Neutral
- **Navy Ink** (`#1f2d3d`, oklch ≈ 0.28 0.03 250): All headings and icon glyphs.
  The content voice. Never rendered in terracotta.
- **Slate Body** (`#64748b`): Body copy and descriptions.
- **Slate Muted** (`#7c8a9c`): Decorative and disabled states plus non-text icon
  affordances (chevrons, drag grips, empty stars) — held at ≥3:1 on white/surface,
  the UI-component floor. Text labels and secondary metadata use Slate Body
  (`#64748b`, ≥4.5:1) instead; never render body text in Slate Muted.
- **Page BG** (`#eef2f7`): The cool blue-gray application ground behind content.
- **Surface** (`#ffffff`): Nav bar and default cards. **Warm Card** (`#fdf7f1`) is
  the warm-tinted card interior used on feature/nav cards.
- **Border Warm** (`#f0e6db`) / **Border Cool** (`#e5e9f0`): Hairline dividers —
  warm on tinted cards, cool on white surfaces.
- **Scrim** (`#00000066`, black at 40%): The modal/overlay backdrop only. Never a
  surface or text color.

### Named Rules
**The Terracotta-Is-Interactive Rule.** Terracotta and its peach tints mean "brand
or action." Use them for links, buttons, active nav, filter chips, and headline
metrics — never as decoration on static content. Its restraint is what makes it read.

**The Warm-Cool Split Rule.** The ground is cool (page-bg, navy ink); warmth
(terracotta, peach, apricot) appears only on brand and interactive elements. Never
tint the whole page warm, and never render content ink in terracotta.

**The No-Indigo Rule.** The builder's inherited `#4f46e5` indigo (and any cool-blue
accent) is forbidden. Terracotta is the only accent.

## 3. Typography

**Display / Body / Label Font:** Inter (with `-apple-system, "Segoe UI", sans-serif`
fallback). One humanist sans family across the whole system, differentiated by
weight and case rather than by pairing a second family.

**Mono Font:** Courier New (with `ui-monospace, monospace` fallback). Reserved
strictly for preformatted / verbatim output — the exported interview-guide preview
in the export modal — where fixed-width alignment carries meaning. Never used for UI
chrome or prose.

**Character:** Clean, neutral, and highly legible — the type gets out of the way so
data and structure lead. Personality comes from the navy/terracotta color split and
the tracked uppercase labels, not from typographic flourish.

### Hierarchy
- **Display** (700, `clamp(1.75rem, 3vw, 2rem)`, 1.1): Page titles ("Projects").
  Navy ink, slightly tightened tracking.
- **Title** (700, `1.25rem`, 1.25): Card and section headings ("Project Overview",
  "Research"). Navy ink.
- **Body** (400, `0.9375rem`, 1.55): Descriptions and prose. Slate body color; cap
  measure at 65–75ch.
- **Label** (600, `0.6875rem`, tracking `0.08em`, UPPERCASE): Eyebrows
  ("PRIMARY NAVIGATION", "RESEARCH", "SHOW STATES") and small metadata. Slate muted.

### Named Rules
**The Navy-Ink Rule.** Headings and icon glyphs are always navy ink, never
terracotta. Emphasis in headings comes from weight and size, not accent color.

## 4. Elevation

The system is **flat by default**. Depth is communicated through tonal layering —
a cool page ground, white or warm-tinted cards, hairline borders — not through drop
shadows. Cards sit on the page as tinted planes with a 1px border; there is no
ambient shadow vocabulary in the captured screens. At most, a very soft shadow may
lift an overlay (modal/menu) above the plane, but resting surfaces stay flat.

### Named Rules
**The Flat Warm-Card Rule.** A card earns separation from the page with a background
tint (`#fdf7f1` warm or `#fff`) plus a hairline border (`#f0e6db` / `#e5e9f0`) —
never a heavy 2014-style shadow. If a surface needs a dark blurred shadow to read,
the tint/border contrast is too weak; fix that instead.

## 5. Components

### Buttons
- **Shape:** Gently rounded (6px).
- **Primary (soft-fill):** Peach Soft background (`#fbe9da`), Terracotta text
  (`#bf5b34`), 1px terracotta border, `8px 16px` padding. Forven's highest-emphasis
  actions ("+ New Project") use this soft-fill style, not a solid slab.
- **Hover / Focus:** Fill deepens toward Apricot (`#f6dcc2`), text toward Terracotta
  Deep (`#a34a28`); focus shows a 2px terracotta ring with 2px offset.

### Chips (filters / states)
- **Style:** Fully rounded pills (999px), Peach Soft background, Terracotta text,
  uppercase label type. Used for status filters (DRAFT / ACTIVE / PAUSED / COMPLETED)
  and stat counts.
- **State:** Selected chips carry the peach fill; unselected chips drop to a plain
  slate-muted outline until chosen.

### Cards / Containers
- **Corner Style:** Generous (14px radius).
- **Background:** Warm Card (`#fdf7f1`) for feature/nav cards; white for data
  containers. Nested cards are prohibited.
- **Shadow Strategy:** Flat — see The Flat Warm-Card Rule.
- **Border:** 1px hairline (`#f0e6db` warm / `#e5e9f0` cool).
- **Internal Padding:** `24px` (lg).

### Icon Tiles (signature)
- Rounded-square (10px) tiles, ~44px, Apricot Tile background (`#f6dcc2`) with a
  navy-ink line-icon glyph. They anchor the top-left of feature/nav cards and are a
  recognizable Forven motif.

### Inputs / Fields
- **Style:** White background, 1px cool hairline border, 6px radius.
- **Focus:** Border shifts to terracotta; no glow.
- **Placeholder:** Slate muted at ≥4.5:1 contrast.

### Navigation
- **Style:** Horizontal top tab bar on white, with a hairline bottom border. Items
  are navy-ink label text.
- **Active:** Peach Soft pill background with Terracotta text (6px radius).
- **Hover:** Text shifts toward terracotta; no underline.

## 6. Do's and Don'ts

### Do:
- **Do** use Terracotta (`#bf5b34`) as the single interactive/brand accent, softened
  to Peach (`#fbe9da`) / Apricot (`#f6dcc2`) for surfaces.
- **Do** render all headings and icon glyphs in Navy Ink (`#1f2d3d`).
- **Do** keep warm peach/apricot tints and uppercase tracked eyebrows — these are
  **Forven house style**, not generic slop, and are correct for this project.
- **Do** convey depth with tint + hairline border; keep resting surfaces flat.
- **Do** hold body/placeholder/label text to ≥4.5:1 contrast (WCAG AA).

### Don't:
- **Don't** use the builder's inherited indigo (`#4f46e5`) or any cool-blue accent —
  it is off-brand for Forven (The No-Indigo Rule).
- **Don't** render content ink or headings in terracotta, or tint the whole page warm
  (The Warm-Cool Split Rule).
- **Don't** drift into bright, rounded, emoji-heavy consumer-app energy.
- **Don't** produce dense, gray, cluttered legacy-enterprise screens.
- **Don't** over-animate or add decorative flash that competes with the work.
- **Don't** lean on heavy drop shadows or nested cards for separation.

# Topic Ordering Intelligence — Design Spec
**Date:** 2026-07-16

## Problem

The "Golden Child" interview set (7 real interviews across three template
variants of the same dog-food study) is a clean natural experiment: the same
objectives, re-sequenced, produced observably different interviews.

- **v7.0** placed the aided brand-awareness battery at **Topic 4** — it fired
  ~5 minutes in, before any unprimed language was captured, spending early
  rapport on a mechanical checklist and coloring the "best possible food"
  answers that followed.
- **v8.0** moved the battery to **Topic 11** and pulled the advertising / proof
  topic up to **Topic 10**. The first ~10 minutes became pure depth on the
  participant's own words and premium criteria; the battery landed late, after
  rapport.

Our builder cannot currently make this distinction. `gathering.txt`'s ordering
guidance is a generic funnel — "easy → sensitive → reflective, never lead with
something emotionally loaded." The v7 mistake would sail through it: a brand
battery is not *emotionally* loaded, so nothing flags placing it early. The
real principle v8 discovered — **defer priming batteries, position the payoff
topic late** — is encoded nowhere in the tool.

## Goal

Make the AI builder sequence topics with two evidence-backed principles the
generic funnel lacks, inferring the study's structure **silently** from the
topic set it drafts (no archetype label surfaced, no upfront question), and
explaining the *sequence* in one plain sentence when it presents the guide.
Manual drag-to-reorder stays the human override.

This is a **prompt change plus one small tool**. The two principles live in
`gathering.txt`; a new `reorder_topics` tool lets the builder re-sequence an
existing set cleanly (the current overwrite-by-index semantics make that
fragile).

## Non-goals / relationship to deferred threads

Three sibling findings from the same analysis are explicitly **out of scope**
here (the user chose to return to them separately):

- **Coverage guarantee** (v8's "Closing Priority" backstop that *guarantees* the
  payoff topic is reached). This spec only *positions* the payoff topic late; a
  pacing-rule backstop that ensures it's reached is a separate change.
- **Verbatim control** (a controlled escape hatch from the current "no scripts"
  rule).
- **Short-interview ordering** (a time-budgeted guide as its own shape).

## Not to be confused with RAG coverage archetypes

The codebase already has "archetypes" — the RAG **coverage archetypes**
(`corpus/coverage/`, per the 2026-06-25 spec) that describe *the experience
being interviewed about* (physical-place visit, decision journey, onboarding…).
This feature is a **different axis**: the *methodology structure of the study*
(does the guide contain a recognition battery? an evaluative proof topic?).
There is no shared mechanism and no shared vocabulary — the ordering triggers
are structural features of the topic set, detected inline by the builder, not
corpus entries. Keeping them separate avoids collision with the coverage layer.

---

## Architecture

| Area | Change |
|---|---|
| `prompts/gathering.txt` | Add the two ordering principles + the structural triggers to the Topic-set ordering guidance; add an ordering check to the Consolidation Gate that calls `reorder_topics`; add one anti-pattern row; add the plain-language ordering rationale to the presentation step. |
| `app.py` — `GATHERING_TOOLS` | Add the `reorder_topics` tool definition. |
| `app.py` — `process_tool_call` | Add a `reorder_topics` branch returning `{"section": "reorder_topics", "payload": {"order": [ints]}}`. |
| `static/duration.js` — `DurationEngine` | Add pure `applyOrder(topics, order)` — renumbers to the given permutation, returns `null` if `order` is not a permutation of current indices. Mirrors the existing `reorderTopics` renumbering. |
| `static/app.js` — `applyUpdate` | Add a `reorder_topics` branch: call `DurationEngine.applyOrder`, remap `collapsedSections` keys, no-op on `null`. |
| `tests/test_tools.py` | `process_tool_call` dispatch test for `reorder_topics`. |
| `tests/duration.test.js` | `applyOrder` renumber + invalid-permutation tests. |
| `tests/test_gathering_prompt.py` | Assert the two ordering principles are present in the prompt. |

---

## Part 1 — Ordering knowledge in `gathering.txt`

Everything here is **silent**: the builder reasons with it but never names a
shape to the client. Only a one-line plain rationale appears at presentation.

### Two universal principles (added on top of the existing funnel)

1. **Defer priming batteries.** Any topic that reads the participant a *closed
   set to recognize, rank, or choose from* — aided brand awareness
   ("have you heard of ___"), pick-from-a-list, ranking — is sequenced **after**
   the topics that capture the participant's own unprompted language on the same
   subject. Reason: the battery contaminates the earlier open answers if it
   comes first.
2. **Position the payoff topic late, before the reflective close.** The
   highest-priority *evaluative / decision* topic (ad language, proof points,
   concept reaction) is sequenced near the end so unprimed depth precedes it.
   (This spec only *positions* it; guaranteeing it is *reached* is the deferred
   coverage-guarantee thread.)

### Structural triggers (how hard each principle bites)

Detected inline from the drafted topic set — not named to the client:

- **Recognition battery present** (a topic that lists named options for the
  participant to recognize) → apply principle 1 hard: the battery goes after the
  own-words / criteria topics.
- **Evaluative proof/claims topic present** → apply principle 2: that topic sits
  late, preceded by own-words capture.
- **Single-experience episodic guide** (our current default, e.g. grocery) →
  order by the experience's natural timeline. This is essentially today's
  behavior; the two principles above simply refine it when those structures
  appear.

### Prompt edits (concrete)

- **Topic-set → Ordering bullet** (currently: "follow the funnel — easy/concrete
  warm-up first, then core themes, then sensitive/evaluative, then a reflective
  close. Never lead with an emotionally loaded topic."). Extend with:
  > Defer any *priming battery* — a topic that reads the participant a fixed set
  > to recognize, rank, or pick from (aided awareness, "have you heard of ___")
  > — until after the topics that capture their own unprompted words on the same
  > subject; asked early, it colors those answers. Position the single
  > highest-priority evaluative topic (claims, proof, concept reaction) late,
  > just before the reflective close, so unprimed depth precedes it.
- **Consolidation Gate** — add a checklist item:
  > - [ ] No priming battery precedes the own-words capture it would
  >   contaminate; the top evaluative topic sits late. If the order violates
  >   this, fix it with `reorder_topics`.
- **Anti-patterns table** — add a row:
  > | recognition battery placed before own-words capture | primes/colors the
  > open answers | move the battery after the criteria topics |
- **Presentation step** (the Consolidation Gate already ends with "briefly tell
  the client what you changed") — instruct it to include the ordering rationale
  in plain language, **without** naming a shape:
  > e.g. "I put the brand-recognition questions after the open-ended section so
  > they don't color the earlier answers." Never name an archetype or study
  > "type".
- **Sections to fill** — add:
  > - `reorder_topics` — when a topic's position violates the ordering rules
  >   (e.g. a battery ended up early, or a late-added topic appended after the
  >   payoff topic), re-sequence with a single `reorder_topics` call.

---

## Part 2 — The `reorder_topics` tool

### Why a tool (not prompt-only re-emission)

Topics are keyed by `index`; `add_topic` with an existing index **overwrites**
that slot and new topics sort in by index (`app.js:349–360`). Re-sequencing an
existing set by re-emitting `add_topic` calls therefore requires an N-way
overwrite rotation — fragile for the model to get right. A late-added topic
always appends at `max index + 1` (`app.js:892–895`), so it lands after the
payoff topic until something re-sequences — a real, recurring case, not
speculative. A dedicated reorder maps cleanly onto the already-tested
`DurationEngine.reorderTopics` renumbering.

### Tool definition (`app.py`, `GATHERING_TOOLS`)

```python
{
    "name": "reorder_topics",
    "description": (
        "Re-sequence the existing topics. Provide the current 1-based topic "
        "indices in the desired new order (a permutation of all current "
        "indices). Topics are renumbered to their new positions. Use only to "
        "reorder — never to add or remove a topic."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "order": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "All current 1-based topic indices in the new order.",
            }
        },
        "required": ["order"],
    },
}
```

### Dispatch (`app.py`, `process_tool_call`)

```python
    elif name == "reorder_topics":
        order = [int(i) for i in input_data["order"]]
        return {"section": "reorder_topics", "payload": {"order": order}}
```

No server-side validation against the current topics — the sections live in
frontend state, so validation belongs there (below). The branch only coerces to
ints. Consistent with the existing generic-error posture: a malformed call
produces a no-op reorder client-side, never a corrupt guide.

### Pure engine (`static/duration.js`, `DurationEngine`)

```js
// Reorder to an explicit permutation of current 1-based indices.
// Returns a new array renumbered to positions, or null if `order` is not a
// permutation of the topics' current indices (caller then no-ops).
function applyOrder(topics, order) {
  if (!Array.isArray(order) || order.length !== topics.length) return null;
  const byIndex = new Map(topics.map(t => [t.index, t]));
  if (!order.every(i => byIndex.has(i))) return null;
  if (new Set(order).size !== order.length) return null;
  return order.map((i, pos) => ({ ...byIndex.get(i), index: pos + 1 }));
}
```

Add `applyOrder` to the exported `api` object alongside `reorderTopics`.

### Apply (`static/app.js`, `applyUpdate`)

New branch mirroring the `remove_topic` branch's shape:

```js
  } else if (section === "reorder_topics") {
    const reordered = DurationEngine.applyOrder(state.sections.topics, payload.order);
    if (reordered) {
      const newCollapsed = new Set();
      payload.order.forEach((oldIdx, pos) => {
        if (state.collapsedSections.has(`topic-${oldIdx}`)) newCollapsed.add(`topic-${pos + 1}`);
      });
      state.collapsedSections.forEach(k => { if (!k.startsWith("topic-")) newCollapsed.add(k); });
      state.collapsedSections = newCollapsed;
      state.sections.topics = reordered;
    }
  }
```

`applyUpdate` already ends by calling `renderTemplate()` and
`updateDurationDisplay()`, so the reordered set renders and re-estimates with no
extra wiring. On `null` (bad permutation) the branch no-ops.

---

## Data flow

1. Builder decides the sequence is wrong (draft-time, or at the Consolidation
   Gate, or after a late add) and calls `reorder_topics(order=[…])`.
2. `stream_conversation`'s tool loop dispatches to `process_tool_call`, which
   returns `{"section": "reorder_topics", "payload": {"order": […]}}`; this is
   serialized as a `section_update` SSE event (same path as every other tool).
3. `applyUpdate` renumbers via `DurationEngine.applyOrder`, remaps collapsed
   state, re-renders. Invalid permutations no-op.

## Error handling / edge cases

- **Not a permutation** (missing/extra/duplicate index, wrong length) →
  `applyOrder` returns `null` → no-op. The guide is never corrupted by a bad
  model call.
- **Single topic / empty set** → `applyOrder` returns the trivial renumber (or a
  1-element array); harmless.
- **Collapsed sections** → remapped by position so the right panels stay
  collapsed after a reorder, matching the drag path's behavior
  (`app.js:171–172`).
- **Concurrency** — unchanged; the existing per-session lock already serializes
  turns, and reorder is one `section_update` like any other.

## Testing

All Python tests stub `ANTHROPIC_API_KEY` (existing convention); JS tests run
under `node --test` with no deps.

- **`tests/test_tools.py`**
  ```python
  def test_reorder_topics_dispatch():
      out = app.process_tool_call("reorder_topics", {"order": [3, 1, 2]})
      assert out == {"section": "reorder_topics", "payload": {"order": [3, 1, 2]}}
  ```
- **`tests/duration.test.js`**
  - `applyOrder` on a 3-topic set with `order=[3,1,2]` returns topics whose
    `title`s follow the new order and whose `index`es are `1,2,3`.
  - `applyOrder` with a non-permutation (`[3,1]`, `[3,1,4]`, `[1,1,2]`) returns
    `null`.
- **`tests/test_gathering_prompt.py`** — assert both principles are present,
  e.g. the prompt contains "priming battery" and instructs positioning the
  evaluative/payoff topic late. Guards against silent prompt regression.
- **Existing suites** — if any test asserts the exact `GATHERING_TOOLS` count or
  name set (check `tests/test_routes.py` / `tests/test_tools.py`), update it to
  include `reorder_topics`.

## Build phases

1. **Tool + engine** — add the `reorder_topics` tool def and `process_tool_call`
   branch; add `DurationEngine.applyOrder` and export it; add the `applyUpdate`
   branch. Add `test_reorder_topics_dispatch` and the `applyOrder`
   node tests. Update any tool-count/name assertion. Green suite.
2. **Prompt** — add the two principles and structural triggers to the Topic-set
   ordering guidance; add the Consolidation Gate check, the anti-pattern row,
   the presentation-rationale instruction, and the Sections-to-fill line. Add
   the `test_gathering_prompt.py` assertions.

## What is unchanged

- The SSE `section_update` mechanism, the per-session lock, the generic-error
  posture, `format_template`, the review/export flow.
- Manual drag-to-reorder (`DurationEngine.reorderTopics`) and its tests.
- The RAG layer, coverage archetypes, and `corpus/`.
- The existing funnel ordering guidance (extended, not replaced).

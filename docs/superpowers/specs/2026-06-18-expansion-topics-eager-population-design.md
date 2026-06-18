# Expansion Topics Eager Population

**Date:** 2026-06-18  
**Status:** Approved

## Problem

The `update_expansion` tool exists and is fully wired end-to-end, but the AI gathering agent never calls it. The eager inference rule in `prompts/gathering.txt` only lists `update_metadata`, `add_topic`, and `update_focus` for the initial speculative burst. `update_expansion` is filed under "Questions to cover" — meaning the AI treats it as something to ask the user about rather than something to proactively populate from domain knowledge. The Consolidation Gate also has no check for it, so it can slip through even at the end.

## Goal

The agent should populate expansion topics in the same initial burst as main topics, keep them in sync as the conversation evolves, and invite the client to review them conversationally — mirroring the existing behavior for main topics.

## Scope

Prompt-only changes. No backend, frontend, schema, or test changes required. Two files: `prompts/gathering.txt` and the `update_expansion` tool description in `app.py`.

## Changes

### 1. `app.py` — tool description

**File:** `app.py`, `GATHERING_TOOLS`, the `update_expansion` entry.

**Current:**
```
"description": "Set the full list of expansion topics."
```

**Replace with:**
```
"description": "Set the full list of expansion topics — secondary themes to explore if the main guide runs short. Call in the initial burst with domain-inferred drafts, and re-call whenever the research focus or main topic set changes significantly. Items should be concise topic labels, distinct from the main topics."
```

### 2. `prompts/gathering.txt` — eager inference rule

Add a 4th bullet to the eager inference rule block (after bullet 3, before the "A populated template..." sentence).

**Add:**
```
4. Call update_expansion with 4–6 secondary topics drawn from general knowledge of the domain — adjacent themes that would make sense to explore if the main guide runs short. Aim for variety: personal/social context, practical constraints, sensory or evaluative angles not already covered by the main topics. These are speculative drafts; the client reviews and refines them.
```

### 3. `prompts/gathering.txt` — expansion refresh rule

Insert a new paragraph immediately after the eager inference block (before the `## Writing objectives` section).

**Add:**
```
## Expansion refresh rule
Expansion topics must stay in sync with the research as it evolves. After any message that meaningfully changes the domain, research focus, or main topic set, check whether the current expansion items still fit and call update_expansion again if they need adjustment. After generating the initial drafts, invite the client to review them as part of your next message.
```

### 4. `prompts/gathering.txt` — Consolidation Gate

Add one checkbox to the Consolidation Gate list (after the "Priorities discriminate" check).

**Add:**
```
- [ ] Expansion topics populated (4–6 items); each is distinct from main topics and plausible as a secondary direction
```

### 5. `prompts/gathering.txt` — Questions to cover

Replace the open question about secondary areas with a review-prompt instruction.

**Current:**
```
- What secondary areas could fill time if the interview finishes early? (Expansion topics)
```

**Replace with:**
```
- After generating expansion topic drafts: invite the client to review them — "I've also drafted some expansion topics in the right panel. Let me know if you'd like to add, remove, or adjust any."
```

## What is not changing

- `update_expansion` tool schema (`items: string[]`) — no change
- Frontend `renderExpansion()` — already renders the flat list correctly
- `process_tool_call` and SSE event handling — already handle `section_update` for expansion
- `test_update_expansion` in `tests/test_tools.py` — still passes; no new tests needed (behaviour is prompt-level)

## Success criteria

1. On first response after the user describes their research topic, the agent calls `update_expansion` alongside `update_metadata`, `add_topic`, and `update_focus`.
2. The generated expansion topics are plausible domain-adjacent themes, distinct from the main topics.
3. The agent's first conversational reply invites the client to review the expansion topics.
4. When the user adds, removes, or adjusts main topics, the agent re-calls `update_expansion` if the existing items no longer fit.
5. At the Consolidation Gate, the agent verifies expansion topics are present and non-overlapping before declaring the template ready.

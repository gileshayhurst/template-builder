# RAG Retrieval Grounding — Design Spec
**Date:** 2026-06-25

## Problem

The gathering agent fills the interview template using only the model's parametric knowledge, steered by the static `prompts/gathering.txt`. Two ceilings follow from this:

- **Craft** — objective phrasing quality depends entirely on the rules baked into one large system prompt; there's no way to surface domain-matched good/bad examples on demand.
- **Coverage** — for less common domains, the agent can miss an essential dimension it doesn't know well, because nothing grounds topic generation in a curated knowledge base.

## Goal

Add a **retrieval layer** that, before the gathering agent generates or refines topics, looks up the most relevant expert guidance from a curated corpus and feeds it into that turn — improving both how objectives are phrased and what dimensions get covered. The feature is purely additive: with it disabled, absent a corpus, or on any failure, the app behaves exactly as it does today.

---

## Architecture

### New flow (per turn)

```
User message + sections → POST /chat (SSE)
  → retrieve_context(sections, latest_msg)        ← NEW: one Haiku call, best-effort
        → guard: skip unless a domain exists (title or ≥1 topic)
        → Haiku picks 3–5 corpus entry ids from the catalog
        → assemble full entries into a grounding block
  → stream_conversation(..., retrieved_block)
        → grounding injected as a mid-conversation system message
        → Opus call (GATHERING_PROMPT + settings, unchanged) → SSE
```

### What changes

| Area | Change |
|---|---|
| `retrieve.py` | **New module** — corpus loader + retriever (pure helpers around one Haiku call) |
| `corpus/` | **New directory** — `craft/*.json` and `coverage/*.json` seed entries |
| `config.py` | Add `RAG_ENABLED` flag (default on; auto-off when corpus is empty) |
| `app.py` | Load corpus at startup; call `retrieve_context()` in `/chat`; pass optional `retrieved_block` to `stream_conversation()`; inject it as a mid-conversation system message |
| `static/app.js` | Include `state.sections` in the `/chat` request body (already sent to `/review` and `/export`) |
| `tests/test_retrieve.py` | **New** — covers the pure helpers + mocked Haiku |
| `tests/test_routes.py` | Add a `/chat`-with-sections injection test |

The system prompt is **not** modified — see "Injection" below.

---

## Corpus design

A `corpus/` directory of small JSON files, loaded into memory once at startup (mirrors how `prompts/*.txt` are read at boot — no database, no new dependency). Two entry types.

**Craft exemplar** — grounds how objectives are phrased:

```json
{
  "id": "craft-double-barreled-01",
  "type": "craft",
  "rule": "one_ask_per_turn",
  "tags": ["compound-question", "any-domain"],
  "bad": "Understand why checkout was frustrating and slow.",
  "good": "Explore how checkout unfolded and how the participant felt about it.",
  "note": "Splits two asks; drops the assumption of frustration."
}
```

**Coverage map** — grounds what dimensions a domain should cover:

```json
{
  "id": "coverage-grocery-01",
  "type": "coverage",
  "domain_tags": ["grocery", "retail", "in-store shopping"],
  "dimensions": ["arrival & entry", "finding items", "unplanned decisions",
                 "checkout friction", "leaving"],
  "note": "Anchor each on the most recent specific visit, not a typical one."
}
```

Two views of each entry:

- **Catalog** (what Haiku chooses from): `id` + `type` + a one-line summary + `tags`. Compact and byte-identical across calls, so it is prompt-cached.
- **Full entry** (what Opus receives once chosen): the bad/good pair or dimension list + note.

**Seeding:** craft exemplars are largely a port of material already in `prompts/gathering.txt` — the anti-pattern table and the three worked failure modes become discrete, retrievable entries. Coverage maps get a hand-written seed set for common domains (grocery, commuting, banking app, healthcare visit, etc.).

**Limitation (graceful degradation):** coverage maps only help for authored domains. For an unseen domain the coverage retrieval returns nothing and the agent falls back to today's behavior. Craft exemplars are mostly domain-agnostic, so they keep working everywhere.

---

## Retriever — `retrieve.py`

Mostly pure functions (testable without an API key) around one Haiku call.

| Function | Pure? | Role |
|---|---|---|
| `load_corpus()` | ✓ | Read `corpus/craft/*.json` + `corpus/coverage/*.json`; validate required fields; skip malformed entries with a log line. |
| `build_catalog(corpus)` | ✓ | Compact list of `id` + `type` + summary + `tags`. The cached payload Haiku chooses from. |
| `build_query(sections, latest_msg)` | ✓ | Assemble the working context: title, focus, topic titles, latest user message. |
| `select_entries(query, catalog)` | ✗ | The Haiku call; returns chosen ids (capped at ~5). |
| `assemble_block(corpus, ids)` | ✓ | Look up full entries by id; format the grounding text block. |
| `retrieve_context(sections, latest_msg)` | ✗ | Orchestrator: guard → query → select → assemble. Returns a string, or `None`. |

**Haiku call (`select_entries`):** forced tool-use, exactly the pattern `_run_review()` already uses with `REVIEW_TOOL`. A `select_entries` tool with `tool_choice` forced, returning `{"entry_ids": [...]}` — structured, no free-text JSON parsing. The catalog block carries `cache_control: {"type": "ephemeral"}` so repeat calls bill the catalog at ~0.1×.

- **Model:** `claude-haiku-4-5`
- **Call style:** non-streaming, single-turn, `tool_choice` forced to the selection tool, `max_tokens` small (~512).

**Cost:** ~$0.002–0.006 per retrieval (catalog-dominated; caching cuts ~60%). Roughly 5–10 retrievals per session → ~1–3¢, negligible beside the Opus gathering conversation.

### Injection (cache-safe)

The retrieved block is **not** appended to the system prompt — the system prompt is frozen and prefix-cached across the Opus conversation, so mutating it each turn would blow that cache away. Instead the block is appended to `messages` as a **mid-conversation `role: "system"` message** (Opus 4.8 supports this via the `mid-conversation-system-2026-04-07` beta; it is the cache-safe, prompt-injection-safe operator channel). The cached prefix stays intact and the grounding carries system authority.

`stream_conversation()` gains an optional `retrieved_block` parameter. When present, it appends the system message after the new user turn; when `None`, message assembly is **byte-for-byte identical to today**.

> Implementation note: the mid-conversation system message requires the beta header on the Opus call (`client.beta.messages.stream(..., betas=["mid-conversation-system-2026-04-07"])`). If a future model on `config.MODEL` rejects it (400 `role 'system' is not supported`), fall back to injecting the block as a `<grounding>` text block inside the user turn — same caching profile, no system authority. The wire-in phase should catch that 400 and degrade rather than fail the turn.

---

## Error handling, config & degradation

RAG is additive and never on the critical path.

- `RAG_ENABLED` in `config.py` — defaults on; auto-off when the loaded corpus is empty.
- `retrieve_context()` wraps everything in `try/except`. Any error — Haiku unavailable, rate limit, malformed response, empty corpus, no domain yet — logs and returns `None`.
- `stream_conversation()` with `retrieved_block=None` builds messages exactly as today. The existing `safe_stream()` wrapper still catches anything that escapes.
- The expensive Opus call is never blocked on the cheap Haiku call succeeding.

Net effect: flag off, no corpus, unknown domain, or Haiku failure ⇒ the app's behavior is identical to current `main`.

---

## When retrieval fires

Only once a domain exists — a non-empty `metadata.title` **or** ≥1 topic in `sections`. This skips the opening "what's your topic?" turn (nothing to retrieve on) and avoids paying for a useless call. No per-turn rate cap beyond this guard; the cost is already negligible.

---

## Testing

`tests/test_retrieve.py` (stub `ANTHROPIC_API_KEY` before import, as the existing suites do):

- `load_corpus` parses fixtures; rejects/skips malformed entries
- `build_catalog`, `build_query`, `assemble_block` — golden-output tests (pure, no API)
- `select_entries` with a **mocked Haiku client** — parses ids; degrades on empty/garbage responses
- `retrieve_context` guards: returns `None` when no domain is set; returns `None` when the API raises

`tests/test_routes.py`:

- `/chat` accepts a `sections` body and injects the grounding block (both Haiku and Opus mocked); with `RAG_ENABLED` off, no Haiku call and no injection

Existing suites (`test_tools.py`, `test_gathering_prompt.py`, `duration.test.js`) are unaffected.

---

## Build phases

Each phase is independently shippable; phases 1–2 add zero behavior change until phase 3 connects them.

1. **Corpus** — JSON format, `load_corpus()`, seed entries (port the anti-pattern table + worked examples from `gathering.txt`; hand-write ~5 coverage maps). Pure + tested.
2. **Retriever** — `retrieve.py`: catalog/query/assemble helpers + the Haiku `select_entries` call with caching. Tested with mocks. Not yet wired in.
3. **Wire-in** — add `sections` to the `/chat` payload (frontend); call `retrieve_context()`; inject the mid-conversation system message (with the 400 fallback). End-to-end.
4. **(Optional) Reviewer reuse** — feed matched craft exemplars into `/review` and `/polish` fix suggestions, sharing the same corpus and retriever.

---

## What is added

- `retrieve.py` module
- `corpus/craft/*.json` and `corpus/coverage/*.json`
- `RAG_ENABLED` in `config.py`
- `retrieve_context()` call + optional `retrieved_block` in `app.py` / `stream_conversation()`
- `sections` in the `/chat` request body (`app.js`)
- `tests/test_retrieve.py`; one new case in `tests/test_routes.py`

## What is unchanged

- `prompts/gathering.txt`, `review.txt`, `fixer.txt` (gathering prompt may later be trimmed once craft exemplars cover the same ground, but not in this work)
- `format_template()`, the export path, the duration engine
- All existing behavior when RAG is disabled or unavailable

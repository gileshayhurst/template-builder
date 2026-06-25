# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env   # then add ANTHROPIC_API_KEY

# Run the app (auto-opens browser at localhost:5000)
python main.py

# Run Python tests (no API key needed — tests mock it)
pytest tests/

# Run a single Python test
pytest tests/test_tools.py::test_add_topic_with_probe

# Run JS tests for the pure duration module (needs Node 18+; no deps)
node --test tests/duration.test.js
```

**Two test suites:** `pytest tests/` covers Python (`process_tool_call`, the gathering prompt's structure). `node --test tests/duration.test.js` covers the DOM-free duration engine in `static/duration.js` (estimate math + the duration-coach suggestion engine). Run both when touching their respective areas.

**Windows note:** Start Flask via PowerShell (`python main.py`), not the Bash tool. Before restarting, kill any stale processes holding port 5000: `Stop-Process -Id <PID> -Force` (find PIDs with `netstat -ano | Select-String ':5000.*LISTENING'`).

## Architecture

Single-page research-template builder. The user chats with an AI assistant that fills a structured interview guide template in real time.

### Request flow

1. **Page load** → `startConversation()` in `app.js` calls `POST /reset` (clears server-side `conversation_history`), then `POST /chat` with an opening message.
2. **`/chat`** first calls `retrieve.retrieve_context(sections, message)` (RAG grounding — see below; best-effort, returns `None` on any failure), then streams SSE events from `stream_conversation()` in `app.py`, which calls the Anthropic API in a loop. The AI uses tool calls to update template sections; each tool call produces a `section_update` SSE event. Text tokens produce `chat_token` events. Exceptions are caught in `safe_stream()` and yielded as `error` events.
3. **`applyUpdate()`** in `app.js` receives `section_update` payloads and mutates `state.sections`, then re-renders.
4. **Export (two-phase):** `exportTemplate()` in `app.js` first calls `POST /review`, which runs a quality check via `prompts/review.txt` (tool-use, returns structured JSON). If issues are found the modal shows a report; if `overall == "pass"` it auto-proceeds. Phase 2 calls `POST /export`, which runs `format_template(sections)` — a deterministic Python function, no AI call — and returns the formatted template text.

### Key files

| File | Role |
|---|---|
| `app.py` | Flask server — `/chat`, `/review`, `/export`, `/reset` routes; `stream_conversation()` generator; `process_tool_call()` dispatcher; `format_template()` deterministic formatter |
| `main.py` | Entry point — starts Flask and opens browser after 1.2 s |
| `config.py` | Reads `ANTHROPIC_API_KEY` and `RAG_ENABLED` from env; sets `MODEL` and `PORT` |
| `retrieve.py` | RAG retrieval layer — loads the `corpus/` JSON at startup, selects relevant entries via a cheap Haiku call (`select_entries`, forced tool-use), and returns a grounding block. Pure helpers + `retrieve_context()` orchestrator; fail-open (returns `None` on any error) |
| `corpus/` | Curated RAG corpus — `craft/*.json` (good/bad objective exemplars) and `coverage/*.json` (per-domain dimension checklists), one entry per file |
| `static/app.js` | All frontend logic — `state`, rendering, SSE handling, depth/duration controls, duration-coach UI, two-phase export modal |
| `static/duration.js` | Pure, DOM-free duration engine — estimate math + coach suggestion engine (`window.DurationEngine`); loaded before `app.js`; unit-tested via `node --test` |
| `static/style.css` | All styles |
| `templates/index.html` | Single HTML shell |
| `prompts/gathering.txt` | System prompt for the AI builder conversation |
| `prompts/review.txt` | System prompt for the AI quality reviewer (`submit_review` tool-use, returns structured JSON) |

### Frontend state

`state` in `app.js` is the single source of truth:

```js
{
  streaming, exportFilename,
  depthSliderValue,     // 0/25/50/75/100 → breadth…deep
  durationTarget,       // minutes, set by user
  collapsedSections,    // Set of string keys
  sections: { metadata, pacing, focus, topics, expansion }
}
```

All rendering is pull-based: `renderTemplate()` rebuilds the entire template panel from `state`. `applyUpdate()` mutates state then calls `renderTemplate()` and `updateDurationDisplay()`.

### Depth presets

The depth slider maps to five named presets in `PACING_DEPTH_PRESETS` (breadth / slightly_broad / balanced / slightly_deep / deep). Each preset is a full set of 8 pacing rule texts. `applyDepthPreset()` overwrites `state.sections.pacing` with the chosen preset.

### AI tools (defined in `app.py`)

**Gathering tools** (`GATHERING_TOOLS`): `update_metadata`, `update_pacing`, `update_focus`, `add_topic`, `remove_topic`, `update_expansion`. Each is handled by `process_tool_call()`, which returns a `{section, payload}` dict serialised into a `section_update` SSE event.

**Review tool** (`REVIEW_TOOL`): `submit_review` — called by `POST /review` with `tool_choice: any`, forces a structured quality report (no free-text JSON parsing). The report has `overall` (`pass`/`warning`/`error`), `item_issues`, and `structural_issues`.

### RAG retrieval grounding (`retrieve.py`)

Before the gathering agent generates topics, `/chat` calls `retrieve_context(sections, message)`. Once a domain exists (a title or ≥1 topic), it builds a catalog of the `corpus/` entries, has Haiku (`claude-haiku-4-5`, forced `select_entries` tool-use) pick 3–5 relevant ones, and assembles a `<grounding>` block. That block is injected into the **current user turn only** for that one model call — never persisted to `conversation_history` (`stream_conversation`'s `retrieved_block` param). The corpus carries `cache_control` on the catalog for cheap repeat calls.

**Fail-open:** disabled via `RAG_ENABLED=0`, an empty corpus (`RAG_EFFECTIVE` auto-off), a domain-less turn, or any exception all make `retrieve_context` return `None`, and `/chat` behaves exactly as it did pre-feature. RAG is never on the critical path.

### Export — `format_template(sections)`

Pure Python function in `app.py`. Takes `state.sections` and returns the exact template string. No AI call. Pacing rules emit in groups: 1 / blank / 3 / blank / 3 / blank / 1, then three blank lines before `# Main Interview Guide`. Items use `_normalise_item()` to handle both dict and string forms.

### Tests

Four suites — all stub `ANTHROPIC_API_KEY` before importing `app`/`retrieve`:

| File | Covers |
|---|---|
| `tests/test_tools.py` | `process_tool_call()` dispatcher + `format_template()` (golden-output + edge cases) |
| `tests/test_routes.py` | Flask routes via test client — `/chat` SSE stream, tool call dispatch, `/export`, `/reset`, `build_settings_context()` |
| `tests/test_gathering_prompt.py` | `prompts/gathering.txt` content — verifies objective-writing rules, core/probe definitions, consumer framing |
| `tests/test_retrieve.py` | `retrieve.py` — corpus loader (parse/skip-malformed), pure helpers (catalog/query/block/domain guard), and the mocked Haiku selection + `retrieve_context` fail-open paths |

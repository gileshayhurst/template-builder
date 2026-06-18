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
2. **`/chat`** streams SSE events from `stream_conversation()` in `app.py`, which calls the Anthropic API in a loop. The AI uses tool calls to update template sections; each tool call produces a `section_update` SSE event. Text tokens produce `chat_token` events. Exceptions are caught in `safe_stream()` and yielded as `error` events.
3. **`applyUpdate()`** in `app.js` receives `section_update` payloads and mutates `state.sections`, then re-renders.
4. **`/export`** sends the current `state.sections` JSON to a second Anthropic call (non-streaming) using `prompts/generation.txt` as its system prompt, which formats it into the final template syntax.

### Key files

| File | Role |
|---|---|
| `app.py` | Flask server — `/chat`, `/export`, `/reset` routes; `stream_conversation()` generator; `process_tool_call()` dispatcher |
| `main.py` | Entry point — starts Flask and opens browser after 1.2 s |
| `config.py` | Reads `ANTHROPIC_API_KEY` from env; sets `MODEL` and `PORT` |
| `static/app.js` | All frontend logic — `state`, rendering, SSE handling, depth/duration controls, duration-coach UI |
| `static/duration.js` | Pure, DOM-free duration engine — estimate math + coach suggestion engine (`window.DurationEngine`); loaded before `app.js`; unit-tested via `node --test` |
| `static/style.css` | All styles |
| `templates/index.html` | Single HTML shell |
| `prompts/gathering.txt` | System prompt for the AI builder conversation |
| `prompts/generation.txt` | System prompt for the export formatter |

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

`update_metadata`, `update_pacing`, `update_focus`, `add_topic`, `remove_topic`, `update_expansion`. Each is handled by `process_tool_call()`, which returns a `{section, payload}` dict serialised into a `section_update` SSE event.

### Tests

`tests/test_tools.py` covers `process_tool_call()` only — no Flask routes, no Anthropic calls. The test file stubs `ANTHROPIC_API_KEY` before importing `app`.

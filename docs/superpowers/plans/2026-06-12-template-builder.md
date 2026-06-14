# Template Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local web app where clients describe their research goals in a chat interface and an AI assistant fills in a structured interview template live, which can then be exported as a correctly formatted template file.

**Architecture:** Python Flask backend holds a stateful `conversation_history` list (single-user local app). The `/chat` route accepts one new message at a time, appends to history, calls Claude with tool use, handles the tool-use loop internally, and streams SSE events — `chat_token` for text and `section_update` for template changes. The `/export` route runs a separate Claude call to format sections into template syntax. Vanilla JS frontend renders sections live from an in-memory state object.

**Tech Stack:** Python 3.10+, Flask, Anthropic Python SDK (claude-sonnet-4-6), vanilla HTML/CSS/JS, pytest, python-dotenv

---

## File Map

| File | Purpose |
|------|---------|
| `requirements.txt` | Python dependencies |
| `.env.example` | API key template |
| `config.py` | Loads env vars; defines MODEL and PORT |
| `app.py` | Flask app: conversation_history state, routes, tool definitions, SSE stream |
| `main.py` | Entry point — starts Flask, opens browser |
| `prompts/gathering.txt` | Phase 1 system prompt (conversational agent) |
| `prompts/generation.txt` | Phase 2 system prompt (template formatter) |
| `templates/index.html` | Two-panel HTML shell |
| `static/style.css` | Styling |
| `static/app.js` | All frontend logic |
| `output/` | Exported templates saved here |
| `tests/test_tools.py` | Unit tests for `process_tool_call` |
| `tests/test_routes.py` | Flask route tests (mocked Anthropic) |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `config.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
flask>=3.0.0
anthropic>=0.30.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-flask>=1.3.0
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=your_key_here
```

- [ ] **Step 3: Create config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = "claude-sonnet-4-6"
PORT = 5000
```

- [ ] **Step 4: Create directories and empty test init**

On Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force prompts, templates, static, output, tests
New-Item -ItemType File tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```
pip install -r requirements.txt
```

Expected: all packages install with no errors.

- [ ] **Step 6: Copy .env.example to .env and add real key**

```
copy .env.example .env
```

Edit `.env`, replace `your_key_here` with a real Anthropic API key.

- [ ] **Step 7: Commit**

```
git init
git add requirements.txt .env.example config.py tests/__init__.py
git commit -m "feat: project scaffolding"
```

---

## Task 2: System Prompts

**Files:**
- Create: `prompts/gathering.txt`
- Create: `prompts/generation.txt`

- [ ] **Step 1: Create prompts/gathering.txt**

```
You are a research design consultant helping a client build a qualitative interview guide template.

Your goal is to understand the client's research goals and build a complete interview template by asking questions and using your tools to fill in template sections as you learn enough to do so.

## Your Approach
- Open with: "Tell me about the research experience you want to explore. What's the topic, and who will you be interviewing?"
- Ask ONE question at a time. Never combine multiple questions in one message.
- After each answer, decide: do you have enough to fill a section? If yes, call the relevant tool immediately, then ask your next question.
- Fill sections incrementally — do not wait until the end to call tools.
- When all sections are reasonably complete, say: "I think we have a solid template. Take a look at the right panel and let me know if you'd like to adjust anything before exporting."

## Sections to Fill (in rough order)
1. update_metadata — as soon as you know the research topic title
2. update_focus — once you know what specific experience to anchor on
3. add_topic — one call per topic as you learn each theme (title + core + optional probes)
4. update_expansion — near the end, after main topics are established
5. update_pacing — ONLY if the client explicitly requests a change to pacing rules; otherwise leave defaults as-is

## Questions to Cover
- What experience or topic should the interview explore?
- Should the interview anchor on one specific recent occasion, or explore more broadly?
- What are the key themes to cover? (These become numbered topics — typical range: 6–10)
- For each theme: what must the interviewer find out? (Core) What would be good to explore if time allows? (Probe)
- What secondary areas could fill time if the interview finishes early? (Expansion topics)
- Any special pacing preferences? (Most clients use standard defaults — only ask if they raise it)

## Rules
- Never ask more than one question per message
- Call tools as soon as you have enough to fill a section — do not batch
- Pacing rules have standard defaults already loaded in the UI — only call update_pacing if the client explicitly requests a change
- Be warm and conversational — this is a collaborative design session, not a form
```

- [ ] **Step 2: Create prompts/generation.txt**

```
You are a template formatter. You receive structured template data as JSON and must output it in the exact syntax below. Output ONLY the formatted template — no explanation, no preamble, no markdown fences.

## Output Format

[Prompt metadata only: TITLE | vVERSION | DATE]

# Pacing Instructions
- **Do Not Rush** DO_NOT_RUSH_TEXT

- **Core vs. Probe:** CORE_VS_PROBE_TEXT
- **One main ask per turn:** ONE_ASK_TEXT
- **Keep questions light:** KEEP_LIGHT_TEXT

- **Follow strong signals:** FOLLOW_SIGNALS_TEXT
- **Original follow-ups allowed:** ORIGINAL_FOLLOWUPS_TEXT
- **Selective probing:** SELECTIVE_PROBING_TEXT

- **The Finish Line** FINISH_LINE_TEXT



# Main Interview Guide: TITLE

## Interview focus
- [Core] FOCUS_TEXT

## Topic 1: TOPIC_TITLE
- [Core] CORE_ITEM
- [Probe] PROBE_ITEM

## Topic 2: TOPIC_TITLE
...

# Expansion Topics
Use these for secondary discovery as instructed
- ITEM
- ITEM

## Rules
- Every core item: prefix with "- [Core] "
- Every probe item: prefix with "- [Probe] "
- Preserve the blank lines between pacing rule groups exactly as shown above
- Two blank lines between the last pacing rule and the "# Main Interview Guide" heading
- Output nothing except the formatted template
```

- [ ] **Step 3: Commit**

```
git add prompts/
git commit -m "feat: add gathering and generation system prompts"
```

---

## Task 3: Backend — Tool Definitions, process_tool_call, Unit Tests

**Files:**
- Create: `app.py` (tools + process_tool_call only — routes added in Task 4)
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_tools.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from app import process_tool_call


def test_update_metadata():
    result = process_tool_call("update_metadata", {"title": "Cooking First Dish"})
    assert result == {"section": "metadata", "payload": {"title": "Cooking First Dish"}}


def test_update_pacing():
    result = process_tool_call("update_pacing", {"rule": "do_not_rush", "text": "Take it slow."})
    assert result == {"section": "pacing", "payload": {"rule": "do_not_rush", "text": "Take it slow."}}


def test_update_focus():
    result = process_tool_call("update_focus", {"text": "Anchor on one recent occasion."})
    assert result == {"section": "focus", "payload": "Anchor on one recent occasion."}


def test_add_topic_with_probe():
    result = process_tool_call("add_topic", {
        "index": 1, "title": "Confirm the occasion",
        "core": ["Identify the dish"], "probe": ["Clarify if ambiguous"]
    })
    assert result == {
        "section": "topic",
        "payload": {"index": 1, "title": "Confirm the occasion",
                    "core": ["Identify the dish"], "probe": ["Clarify if ambiguous"]}
    }


def test_add_topic_probe_defaults_to_empty():
    result = process_tool_call("add_topic", {
        "index": 2, "title": "Basic facts", "core": ["Collect dish name"]
    })
    assert result["payload"]["probe"] == []


def test_remove_topic():
    result = process_tool_call("remove_topic", {"index": 3})
    assert result == {"section": "remove_topic", "payload": {"index": 3}}


def test_update_expansion():
    result = process_tool_call("update_expansion", {"items": ["role of family", "media inspiration"]})
    assert result == {"section": "expansion", "payload": ["role of family", "media inspiration"]}


def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        process_tool_call("nonexistent_tool", {})
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_tools.py -v
```

Expected: `ImportError` — `app.py` doesn't exist yet.

- [ ] **Step 3: Create app.py with tools and process_tool_call**

```python
import json
import os
from flask import Flask, request, Response, render_template, jsonify
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, PORT

app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

with open("prompts/gathering.txt") as f:
    GATHERING_PROMPT = f.read()

with open("prompts/generation.txt") as f:
    GENERATION_PROMPT = f.read()

conversation_history = []

GATHERING_TOOLS = [
    {
        "name": "update_metadata",
        "description": "Set the interview title in the template metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"]
        }
    },
    {
        "name": "update_pacing",
        "description": "Update one named pacing rule. Only call if the client explicitly requests a change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule": {
                    "type": "string",
                    "enum": ["do_not_rush", "core_vs_probe", "one_ask_per_turn", "keep_light",
                             "follow_signals", "original_followups", "selective_probing", "finish_line"]
                },
                "text": {"type": "string"}
            },
            "required": ["rule", "text"]
        }
    },
    {
        "name": "update_focus",
        "description": "Set the interview focus anchor statement.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    },
    {
        "name": "add_topic",
        "description": "Add or replace a numbered topic in the main interview guide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "1-based topic number"},
                "title": {"type": "string"},
                "core": {"type": "array", "items": {"type": "string"}},
                "probe": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["index", "title", "core"]
        }
    },
    {
        "name": "remove_topic",
        "description": "Remove a topic by its 1-based index.",
        "input_schema": {
            "type": "object",
            "properties": {"index": {"type": "integer"}},
            "required": ["index"]
        }
    },
    {
        "name": "update_expansion",
        "description": "Set the full list of expansion topics.",
        "input_schema": {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            "required": ["items"]
        }
    }
]


def process_tool_call(name, input_data):
    if name == "update_metadata":
        return {"section": "metadata", "payload": {"title": input_data["title"]}}
    elif name == "update_pacing":
        return {"section": "pacing", "payload": {"rule": input_data["rule"], "text": input_data["text"]}}
    elif name == "update_focus":
        return {"section": "focus", "payload": input_data["text"]}
    elif name == "add_topic":
        return {"section": "topic", "payload": {
            "index": input_data["index"],
            "title": input_data["title"],
            "core": input_data["core"],
            "probe": input_data.get("probe", [])
        }}
    elif name == "remove_topic":
        return {"section": "remove_topic", "payload": {"index": input_data["index"]}}
    elif name == "update_expansion":
        return {"section": "expansion", "payload": input_data["items"]}
    else:
        raise ValueError(f"Unknown tool: {name}")
```

- [ ] **Step 4: Run tests — verify they pass**

```
pytest tests/test_tools.py -v
```

Expected: all 8 PASS.

- [ ] **Step 5: Commit**

```
git add app.py tests/test_tools.py
git commit -m "feat: add tool definitions and process_tool_call with unit tests"
```

---

## Task 4: /chat, /reset Routes and SSE Stream

**Files:**
- Modify: `app.py` — add `stream_conversation`, `/`, `/chat`, `/reset`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_routes.py`:

```python
import json, sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import app as app_module
from app import app as flask_app


@pytest.fixture(autouse=True)
def clear_history():
    app_module.conversation_history.clear()
    yield
    app_module.conversation_history.clear()


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def make_mock_stream(text_chunks=None, tool_blocks=None):
    text_chunks = text_chunks or ["Hello ", "world"]
    tool_blocks = tool_blocks or []

    class FinalMsg:
        stop_reason = "tool_use" if tool_blocks else "end_turn"
        content = tool_blocks

    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter(text_chunks)
        def get_final_message(self): return FinalMsg()

    return Stream()


def make_end_stream():
    class FinalMsg:
        stop_reason = "end_turn"
        content = []
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter([])
        def get_final_message(self): return FinalMsg()
    return Stream()


def test_reset_clears_history(client):
    app_module.conversation_history.append({"role": "user", "content": "hi"})
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert app_module.conversation_history == []


def test_chat_returns_sse(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hi ", "there"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type
    body = resp.data.decode()
    assert "event: chat_token" in body
    assert "Hi " in body
    assert "event: done" in body


def test_chat_appends_to_history(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Reply"])
        client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
    assert len(app_module.conversation_history) == 2
    assert app_module.conversation_history[0] == {"role": "user", "content": "Hello"}
    assert app_module.conversation_history[1]["role"] == "assistant"


def test_chat_emits_section_update_on_tool_call(client):
    class ToolBlock:
        type = "tool_use"
        id = "tu_abc"
        name = "update_focus"
        input = {"text": "Anchor on cooking."}

    with patch("app.client") as mock_client:
        mock_client.messages.stream.side_effect = [
            make_mock_stream(text_chunks=[], tool_blocks=[ToolBlock()]),
            make_end_stream()
        ]
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
    body = resp.data.decode()
    assert "event: section_update" in body
    assert "focus" in body
    assert "Anchor on cooking." in body
```

- [ ] **Step 2: Run tests — verify they fail**

```
pytest tests/test_routes.py -v
```

Expected: FAIL — routes don't exist yet.

- [ ] **Step 3: Append routes and stream_conversation to app.py**

Add after `process_tool_call`:

```python
def stream_conversation(new_message):
    global conversation_history
    conversation_history.append({"role": "user", "content": new_message})

    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=GATHERING_PROMPT,
            tools=GATHERING_TOOLS,
            messages=conversation_history
        ) as stream:
            for text in stream.text_stream:
                yield f"event: chat_token\ndata: {json.dumps(text)}\n\n"
            final = stream.get_final_message()

        conversation_history.append({
            "role": "assistant",
            "content": [b.model_dump() for b in final.content]
        })

        if final.stop_reason == "tool_use":
            tool_results = []
            for block in final.content:
                if block.type == "tool_use":
                    update = process_tool_call(block.name, block.input)
                    yield f"event: section_update\ndata: {json.dumps(update)}\n\n"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Done"
                    })
            conversation_history.append({"role": "user", "content": tool_results})
        else:
            break

    yield f"event: done\ndata: {{}}\n\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    message = request.json["message"]
    return Response(stream_conversation(message), mimetype="text/event-stream")


@app.route("/export", methods=["POST"])
def export_route():
    pass  # implemented in Task 5


@app.route("/reset", methods=["POST"])
def reset():
    global conversation_history
    conversation_history.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=PORT, debug=True)
```

- [ ] **Step 4: Run all tests**

```
pytest tests/ -v
```

Expected: all tests in `test_tools.py` and `test_routes.py` PASS. (The export test doesn't exist yet — that's fine.)

- [ ] **Step 5: Commit**

```
git add app.py tests/test_routes.py
git commit -m "feat: add /chat SSE route with stateful conversation history and tool loop"
```

---

## Task 5: /export Route

**Files:**
- Modify: `app.py` — implement `export_route`
- Modify: `tests/test_routes.py` — add export test

- [ ] **Step 1: Add failing test — append to tests/test_routes.py**

```python
def test_export_returns_template(client):
    sections = {
        "metadata": {"title": "Cooking Test", "version": "1.0", "date": "2026-06-12"},
        "pacing": {"do_not_rush": "Take it slow."},
        "focus": "Anchor on one cooking occasion.",
        "topics": [{"index": 1, "title": "Confirm occasion", "core": ["Identify dish"], "probe": []}],
        "expansion": ["role of family"]
    }

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="[Prompt metadata only: Cooking Test | v1.0 | 2026-06-12]\n\n# Pacing...")]

    with patch("app.client") as mock_client:
        mock_client.messages.create.return_value = mock_resp
        resp = client.post("/export",
            data=json.dumps({"sections": sections}),
            content_type="application/json")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "template" in data
    assert "filename" in data
    assert "Cooking-Test" in data["filename"]
    assert data["filename"].endswith(".txt")
```

- [ ] **Step 2: Run to verify it fails**

```
pytest tests/test_routes.py::test_export_returns_template -v
```

Expected: FAIL — `export_route` returns `None`.

- [ ] **Step 3: Replace the export_route stub in app.py**

```python
@app.route("/export", methods=["POST"])
def export_route():
    sections = request.json["sections"]

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=GENERATION_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Format this template data into the exact template syntax:\n\n{json.dumps(sections, indent=2)}"
        }]
    )

    template_text = response.content[0].text

    title = sections.get("metadata", {}).get("title", "template")
    version = sections.get("metadata", {}).get("version", "1.0")
    date = sections.get("metadata", {}).get("date", "")
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip().replace(" ", "-")
    filename = f"{safe_title}-v{version}-{date}.txt"

    os.makedirs("output", exist_ok=True)
    with open(os.path.join("output", filename), "w", encoding="utf-8") as f:
        f.write(template_text)

    return jsonify({"template": template_text, "filename": filename})
```

- [ ] **Step 4: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```
git add app.py tests/test_routes.py
git commit -m "feat: add /export route with Claude generation and file save"
```

---

## Task 6: HTML Shell and CSS

**Files:**
- Create: `templates/index.html`
- Create: `static/style.css`

- [ ] **Step 1: Create templates/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Template Builder</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="app">

    <div class="panel chat-panel">
      <div class="panel-header">AI Assistant</div>
      <div class="messages" id="messages"></div>
      <div class="chat-input">
        <textarea id="input" placeholder="Type your response…" rows="2"></textarea>
        <button id="send-btn" onclick="sendMessage()">Send</button>
      </div>
    </div>

    <div class="panel template-panel">
      <div class="panel-header">
        <span>Live Template</span>
        <button class="export-btn" onclick="exportTemplate()">Export Template</button>
      </div>
      <div id="template-sections"></div>
    </div>

  </div>

  <div class="modal-overlay hidden" id="modal-overlay" onclick="closeModal()"></div>
  <div class="modal hidden" id="export-modal">
    <div class="modal-header">
      <h2>Exported Template</h2>
      <button class="modal-close" onclick="closeModal()">×</button>
    </div>
    <pre id="template-output"></pre>
    <button class="download-btn" onclick="downloadTemplate()">Download .txt</button>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create static/style.css**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: 14px;
  background: #f5f5f5;
  height: 100vh;
  overflow: hidden;
}

.app { display: flex; height: 100vh; }

.panel { display: flex; flex-direction: column; height: 100vh; background: #fff; }
.chat-panel { width: 38%; border-right: 1px solid #e0e0e0; }
.template-panel { flex: 1; }

.panel-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; border-bottom: 1px solid #e0e0e0;
  font-weight: 600; font-size: 12px; text-transform: uppercase;
  letter-spacing: 0.05em; color: #666; flex-shrink: 0;
}

/* Chat */
.messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
}

.message { max-width: 88%; border-radius: 10px; padding: 10px 13px; line-height: 1.5; }
.message.ai { background: #eef2ff; align-self: flex-start; }
.message.user { background: #f0f0f0; align-self: flex-end; }
.message .role { font-size: 10px; font-weight: 700; color: #888; margin-bottom: 3px; text-transform: uppercase; }
.message.ai .role { color: #4f46e5; }
.status-msg { font-size: 11px; color: #4f46e5; font-style: italic; align-self: flex-start; }

.chat-input {
  display: flex; gap: 8px; padding: 12px 14px;
  border-top: 1px solid #e0e0e0; flex-shrink: 0;
}
.chat-input textarea {
  flex: 1; border: 1px solid #ddd; border-radius: 6px;
  padding: 8px 10px; font-size: 13px; font-family: inherit; resize: none; outline: none;
}
.chat-input textarea:focus { border-color: #4f46e5; }

.chat-input button, .export-btn {
  background: #4f46e5; color: #fff; border: none;
  border-radius: 6px; padding: 8px 16px; font-size: 13px;
  cursor: pointer; font-family: inherit;
}
.chat-input button:disabled { background: #aaa; cursor: not-allowed; }
.export-btn { font-size: 11px; padding: 6px 12px; }

/* Template panel */
#template-sections {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 12px;
}

.section-block {
  border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.section-block.flash {
  border-color: #f59e0b;
  box-shadow: 0 0 0 3px rgba(245,158,11,0.2);
}
.section-title {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px; background: #fafafa;
  border-bottom: 1px solid #e0e0e0; font-weight: 600; font-size: 12px; color: #444;
}
.section-body { padding: 10px 12px; }

.pacing-rule { margin-bottom: 10px; }
.pacing-rule label { font-size: 11px; font-weight: 600; color: #555; display: block; margin-bottom: 3px; }
.pacing-rule textarea {
  width: 100%; border: 1px solid #ddd; border-radius: 4px;
  padding: 6px 8px; font-size: 12px; font-family: inherit; resize: vertical; min-height: 48px; outline: none;
}
.pacing-rule textarea:focus { border-color: #4f46e5; }
.reset-link {
  font-size: 10px; color: #999; cursor: pointer;
  background: none; border: none; text-decoration: underline; margin-top: 2px;
}
.reset-link:hover { color: #4f46e5; }

.metadata-fields { display: flex; flex-direction: column; gap: 6px; }
.metadata-fields label { font-size: 11px; color: #666; }
.metadata-fields input {
  border: 1px solid #ddd; border-radius: 4px; padding: 5px 8px;
  font-size: 13px; font-family: inherit; outline: none; width: 100%;
}
.metadata-fields input:focus { border-color: #4f46e5; }

.focus-textarea, .expansion-textarea {
  width: 100%; border: 1px solid #ddd; border-radius: 4px;
  padding: 8px; font-size: 13px; font-family: inherit; resize: vertical; outline: none; min-height: 48px;
}
.focus-textarea:focus, .expansion-textarea:focus { border-color: #4f46e5; }

.topic-block {
  border: 1px solid #e8e8e8; border-radius: 6px;
  padding: 10px; margin-bottom: 8px; position: relative;
}
.topic-title input {
  width: 100%; border: none; border-bottom: 1px solid #ddd;
  padding: 3px 0; font-weight: 600; font-size: 13px; outline: none; margin-bottom: 8px; font-family: inherit;
}
.items-list { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.item-row { display: flex; gap: 6px; align-items: flex-start; }
.item-badge {
  font-size: 10px; font-weight: 700; padding: 2px 5px;
  border-radius: 3px; flex-shrink: 0; margin-top: 5px;
}
.item-badge.core { background: #dcfce7; color: #15803d; }
.item-badge.probe { background: #ede9fe; color: #6d28d9; }
.item-row textarea {
  flex: 1; border: 1px solid #eee; border-radius: 4px;
  padding: 4px 6px; font-size: 12px; font-family: inherit; resize: vertical; min-height: 32px; outline: none;
}
.item-row textarea:focus { border-color: #4f46e5; }
.add-item-btn {
  font-size: 11px; background: none; border: 1px dashed #ccc;
  border-radius: 4px; padding: 3px 8px; cursor: pointer; color: #888;
}
.add-item-btn:hover { border-color: #4f46e5; color: #4f46e5; }
.remove-topic-btn {
  position: absolute; top: 8px; right: 8px;
  background: none; border: none; color: #ccc; cursor: pointer; font-size: 16px; line-height: 1;
}
.remove-topic-btn:hover { color: #ef4444; }

.add-topic-btn {
  background: none; border: 1px dashed #ccc; border-radius: 6px;
  padding: 8px; width: 100%; cursor: pointer; color: #888; font-size: 12px; font-family: inherit;
}
.add-topic-btn:hover { border-color: #4f46e5; color: #4f46e5; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 10; }
.modal {
  position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
  background: #fff; border-radius: 10px; padding: 24px; z-index: 11;
  width: 680px; max-width: 95vw; max-height: 80vh;
  display: flex; flex-direction: column; gap: 16px;
}
.hidden { display: none !important; }
.modal-header { display: flex; justify-content: space-between; align-items: center; }
.modal-header h2 { font-size: 16px; }
.modal-close { background: none; border: none; font-size: 22px; cursor: pointer; color: #888; }
#template-output {
  flex: 1; overflow-y: auto; background: #f8f8f8; border: 1px solid #e0e0e0;
  border-radius: 6px; padding: 16px; font-size: 12px; line-height: 1.7;
  white-space: pre-wrap; font-family: "Courier New", monospace;
}
.download-btn {
  background: #059669; color: #fff; border: none; border-radius: 6px;
  padding: 10px 20px; font-size: 13px; cursor: pointer; align-self: flex-start; font-family: inherit;
}
```

- [ ] **Step 3: Verify page loads**

```
python app.py
```

Open `http://localhost:5000` — two-panel layout should appear (empty sections). Stop server.

- [ ] **Step 4: Commit**

```
git add templates/ static/style.css
git commit -m "feat: add two-panel HTML shell and CSS"
```

---

## Task 7: app.js — State, Chat Panel, SSE Consumer

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Create static/app.js**

```javascript
// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const PACING_DEFAULTS = {
  do_not_rush: "If the participant provides brief answers, prioritize every [Probe] point in the Main Interview Guide to unlock more detail.",
  core_vs_probe: "Treat [Core] points as priorities and [Probe] points as optional. Some [Probe] points may go unasked.",
  one_ask_per_turn: "Each turn should usually contain one main question. You may combine a second ask only when it is tightly related, easy to answer in the same thought, and not from a different part of the story.",
  keep_light: "Avoid long or overloaded questions. Do not combine a broad main question with a list of sub-questions in the same turn.",
  follow_signals: "When something specific, emotional, surprising, or contradictory emerges, follow it briefly, then return to the interview guide.",
  original_followups: "You may ask original follow-up questions not explicitly listed in the interview guide when they help uncover better insight.",
  selective_probing: "Use follow-up probes selectively; they are optional tools, not required after every answer.",
  finish_line: "Reaching the end of the Main Interview Guide does not signal the end of the interview. If you finish those topics early, you must utilize the following two options to fill the time until remaining_minutes is 3 or less:\n  1. Circle Back: Revisit an earlier interesting moment to ask for \"thicker\" description (sensory details, specific emotions, or a deeper \"why\").\n  2. Expansion: Pivot to the Expansion Topics at the bottom of this plan."
};

const PACING_LABELS = {
  do_not_rush: "Do Not Rush",
  core_vs_probe: "Core vs. Probe",
  one_ask_per_turn: "One Main Ask Per Turn",
  keep_light: "Keep Questions Light",
  follow_signals: "Follow Strong Signals",
  original_followups: "Original Follow-ups Allowed",
  selective_probing: "Selective Probing",
  finish_line: "The Finish Line"
};

// ─── STATE ────────────────────────────────────────────────────────────────────

const state = {
  streaming: false,
  exportFilename: "",
  sections: {
    metadata: { title: "", version: "1.0", date: new Date().toISOString().split("T")[0] },
    pacing: { ...PACING_DEFAULTS },
    focus: "",
    topics: [],
    expansion: []
  }
};

// ─── INIT ─────────────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  renderTemplate();

  document.getElementById("input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  startConversation();
});

async function startConversation() {
  await streamFromServer("Hello, I am ready to create a template.");
}

// ─── CHAT ─────────────────────────────────────────────────────────────────────

function appendMessage(role, content) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = `message ${role}`;
  const roleLabel = role === "ai" ? "AI" : "You";
  div.innerHTML = `<div class="role">${roleLabel}</div><div class="body"></div>`;
  div.querySelector(".body").textContent = content;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div.querySelector(".body");
}

function appendStatusMsg(text) {
  const el = document.getElementById("messages");
  const div = document.createElement("div");
  div.className = "status-msg";
  div.textContent = text;
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
  return div;
}

async function sendMessage() {
  if (state.streaming) return;
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  appendMessage("user", text);
  await streamFromServer(text);
}

async function streamFromServer(message) {
  state.streaming = true;
  document.getElementById("send-btn").disabled = true;

  let aiBodyEl = null;
  let aiText = "";
  let statusEl = null;

  try {
    const resp = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      let currentEvent = null;
      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          const raw = line.slice(6).trim();
          if (currentEvent === "chat_token") {
            const token = JSON.parse(raw);
            if (!aiBodyEl) aiBodyEl = appendMessage("ai", "");
            aiText += token;
            aiBodyEl.textContent = aiText;
            document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
          } else if (currentEvent === "section_update") {
            if (!statusEl) statusEl = appendStatusMsg("✦ Updating template…");
            applyUpdate(JSON.parse(raw));
          } else if (currentEvent === "done") {
            if (statusEl) { statusEl.remove(); statusEl = null; }
          }
          currentEvent = null;
        }
      }
    }
  } finally {
    state.streaming = false;
    document.getElementById("send-btn").disabled = false;
  }
}

// ─── SECTION UPDATES ──────────────────────────────────────────────────────────

function applyUpdate(update) {
  const { section, payload } = update;

  if (section === "metadata") {
    Object.assign(state.sections.metadata, payload);
    flashSection("section-metadata");
  } else if (section === "pacing") {
    state.sections.pacing[payload.rule] = payload.text;
    flashSection("section-pacing");
  } else if (section === "focus") {
    state.sections.focus = payload;
    flashSection("section-focus");
  } else if (section === "topic") {
    const idx = state.sections.topics.findIndex(t => t.index === payload.index);
    if (idx >= 0) state.sections.topics[idx] = payload;
    else {
      state.sections.topics.push(payload);
      state.sections.topics.sort((a, b) => a.index - b.index);
    }
    flashSection("section-topics");
  } else if (section === "remove_topic") {
    state.sections.topics = state.sections.topics.filter(t => t.index !== payload.index);
    flashSection("section-topics");
  } else if (section === "expansion") {
    state.sections.expansion = payload;
    flashSection("section-expansion");
  }

  renderTemplate();
}

function flashSection(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add("flash");
  setTimeout(() => el.classList.remove("flash"), 1200);
}

// ─── TEMPLATE RENDERING ───────────────────────────────────────────────────────

function renderTemplate() {
  const container = document.getElementById("template-sections");
  container.innerHTML = "";
  container.appendChild(renderMetadata());
  container.appendChild(renderPacing());
  container.appendChild(renderFocus());
  container.appendChild(renderTopics());
  container.appendChild(renderExpansion());
}

function sectionBlock(id, title, bodyEl) {
  const block = document.createElement("div");
  block.className = "section-block";
  block.id = id;
  const header = document.createElement("div");
  header.className = "section-title";
  header.textContent = title;
  block.appendChild(header);
  const body = document.createElement("div");
  body.className = "section-body";
  body.appendChild(bodyEl);
  block.appendChild(body);
  return block;
}

function escHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function renderMetadata() {
  const s = state.sections.metadata;
  const body = document.createElement("div");
  body.className = "metadata-fields";
  body.innerHTML = `
    <label>Title
      <input value="${escHtml(s.title)}" placeholder="Research topic title"
        oninput="state.sections.metadata.title = this.value">
    </label>
    <label>Version
      <input value="${escHtml(s.version)}"
        oninput="state.sections.metadata.version = this.value">
    </label>
    <label>Date
      <input value="${escHtml(s.date)}"
        oninput="state.sections.metadata.date = this.value">
    </label>`;
  return sectionBlock("section-metadata", "Metadata", body);
}

function renderPacing() {
  const body = document.createElement("div");
  for (const [key, label] of Object.entries(PACING_LABELS)) {
    const rule = document.createElement("div");
    rule.className = "pacing-rule";
    rule.innerHTML = `
      <label>${escHtml(label)}</label>
      <textarea oninput="state.sections.pacing['${key}'] = this.value">${escHtml(state.sections.pacing[key])}</textarea>
      <button class="reset-link" onclick="resetPacing('${key}')">Reset to default</button>`;
    body.appendChild(rule);
  }
  return sectionBlock("section-pacing", "Pacing Instructions", body);
}

function renderFocus() {
  const body = document.createElement("div");
  body.innerHTML = `<textarea class="focus-textarea" placeholder="Interview focus anchor statement…"
    oninput="state.sections.focus = this.value">${escHtml(state.sections.focus)}</textarea>`;
  return sectionBlock("section-focus", "Interview Focus", body);
}

function renderTopics() {
  const body = document.createElement("div");
  for (const topic of state.sections.topics) body.appendChild(renderTopicBlock(topic));
  const addBtn = document.createElement("button");
  addBtn.className = "add-topic-btn";
  addBtn.textContent = "+ Add Topic";
  addBtn.onclick = addTopicManually;
  body.appendChild(addBtn);
  return sectionBlock("section-topics", `Topics (${state.sections.topics.length})`, body);
}

function renderTopicBlock(topic) {
  const block = document.createElement("div");
  block.className = "topic-block";

  const removeBtn = document.createElement("button");
  removeBtn.className = "remove-topic-btn";
  removeBtn.textContent = "×";
  removeBtn.onclick = () => removeTopicManually(topic.index);
  block.appendChild(removeBtn);

  const titleWrap = document.createElement("div");
  titleWrap.className = "topic-title";
  titleWrap.innerHTML = `<input value="${escHtml(topic.title)}" placeholder="Topic title…"
    oninput="updateTopicField(${topic.index}, 'title', this.value)">`;
  block.appendChild(titleWrap);

  const list = document.createElement("div");
  list.className = "items-list";
  topic.core.forEach((text, i) => list.appendChild(renderItemRow("core", topic.index, i, text)));
  topic.probe.forEach((text, i) => list.appendChild(renderItemRow("probe", topic.index, i, text)));
  block.appendChild(list);

  const btnRow = document.createElement("div");
  btnRow.style.cssText = "display:flex;gap:6px;margin-top:4px;";
  const ac = document.createElement("button");
  ac.className = "add-item-btn"; ac.textContent = "+ Core item";
  ac.onclick = () => addItem(topic.index, "core");
  const ap = document.createElement("button");
  ap.className = "add-item-btn"; ap.textContent = "+ Probe item";
  ap.onclick = () => addItem(topic.index, "probe");
  btnRow.appendChild(ac); btnRow.appendChild(ap);
  block.appendChild(btnRow);

  return block;
}

function renderItemRow(type, topicIndex, itemIndex, text) {
  const row = document.createElement("div");
  row.className = "item-row";
  row.innerHTML = `
    <span class="item-badge ${type}">${type === "core" ? "Core" : "Probe"}</span>
    <textarea oninput="updateItem(${topicIndex}, '${type}', ${itemIndex}, this.value)">${escHtml(text)}</textarea>`;
  return row;
}

function renderExpansion() {
  const joined = state.sections.expansion.join("\n");
  const body = document.createElement("div");
  body.innerHTML = `
    <div style="font-size:11px;color:#888;margin-bottom:6px;">One item per line</div>
    <textarea class="expansion-textarea" rows="5"
      placeholder="role of family and culture&#10;role of media or inspiration sources&#10;…"
      oninput="state.sections.expansion = this.value.split('\\n').map(s=>s.trim()).filter(Boolean)">${escHtml(joined)}</textarea>`;
  return sectionBlock("section-expansion", "Expansion Topics", body);
}

// ─── EDITING HELPERS ──────────────────────────────────────────────────────────

function resetPacing(rule) {
  state.sections.pacing[rule] = PACING_DEFAULTS[rule];
  renderTemplate();
}

function addTopicManually() {
  const nextIndex = state.sections.topics.length
    ? Math.max(...state.sections.topics.map(t => t.index)) + 1
    : 1;
  state.sections.topics.push({ index: nextIndex, title: "", core: [""], probe: [] });
  renderTemplate();
}

function removeTopicManually(index) {
  state.sections.topics = state.sections.topics.filter(t => t.index !== index);
  renderTemplate();
}

function updateTopicField(index, field, value) {
  const topic = state.sections.topics.find(t => t.index === index);
  if (topic) topic[field] = value;
}

function updateItem(topicIndex, type, itemIndex, value) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) topic[type][itemIndex] = value;
}

function addItem(topicIndex, type) {
  const topic = state.sections.topics.find(t => t.index === topicIndex);
  if (topic) { topic[type].push(""); renderTemplate(); }
}

// ─── EXPORT ───────────────────────────────────────────────────────────────────

async function exportTemplate() {
  const outputEl = document.getElementById("template-output");
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");

  outputEl.textContent = "Generating template…";
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");

  try {
    const resp = await fetch("/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sections: state.sections })
    });
    const data = await resp.json();
    outputEl.textContent = data.template;
    state.exportFilename = data.filename;
  } catch (err) {
    outputEl.textContent = "Error generating template. Check the console.";
    console.error(err);
  }
}

function downloadTemplate() {
  const text = document.getElementById("template-output").textContent;
  if (!text || text === "Generating template…") return;
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = state.exportFilename || "template.txt";
  a.click();
  URL.revokeObjectURL(url);
}

function closeModal() {
  document.getElementById("export-modal").classList.add("hidden");
  document.getElementById("modal-overlay").classList.add("hidden");
}
```

- [ ] **Step 2: Smoke test**

Run `python app.py`, open `http://localhost:5000`.
- AI's opening question should appear on load
- Template panel shows all sections with pacing defaults pre-filled
- Type a response, press Enter — AI replies; watch for yellow flashes on template sections
- Edit a pacing rule directly — text persists
- Click "Reset to default" — original text restores
- Click "+ Add Topic" — blank topic appears with + Core / + Probe buttons
- Click "Export Template" — modal opens, generates template, shows text, download works

Stop server.

- [ ] **Step 3: Commit**

```
git add static/app.js
git commit -m "feat: add full frontend — chat, SSE consumer, live template panel, export"
```

---

## Task 8: Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
import threading
import webbrowser
from app import app
from config import PORT


def open_browser():
    webbrowser.open(f"http://localhost:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.2, open_browser).start()
    app.run(port=PORT, debug=False)
```

- [ ] **Step 2: Test entry point**

```
python main.py
```

Expected: browser opens automatically at `http://localhost:5000`. Stop with Ctrl+C.

- [ ] **Step 3: Commit**

```
git add main.py
git commit -m "feat: add main.py entry point with auto browser launch"
```

---

## Task 9: End-to-End Smoke Test

**Files:** none — manual verification only

- [ ] **Step 1: Run the app**

```
python main.py
```

- [ ] **Step 2: Verify AI opens**

Chat panel shows: "Tell me about the research experience you want to explore. What's the topic, and who will you be interviewing?"

- [ ] **Step 3: Run a full template creation session**

Type responses to each AI question. After each reply verify:
- Metadata title fills in (yellow flash on Metadata section)
- Interview Focus fills in after you describe what to anchor on
- Topics appear one by one as the AI gathers theme information
- Each topic shows [Core] and [Probe] items correctly labeled
- Expansion topics fill in near the end

- [ ] **Step 4: Test manual editing**

- Edit a pacing rule text directly — persists through AI replies
- Click "Reset to default" — restores original wording
- Click "+ Add Topic" — blank topic appears
- Add a Core item — appears labeled "Core" in green
- Click × on a topic — topic removed

- [ ] **Step 5: Export and verify template syntax**

Click "Export Template". Verify the modal shows text with this exact structure:

```
[Prompt metadata only: Your Title | v1.0 | 2026-06-12]

# Pacing Instructions
- **Do Not Rush** ...
...

# Main Interview Guide: Your Title

## Interview focus
- [Core] ...

## Topic 1: ...
- [Core] ...
- [Probe] ...

# Expansion Topics
Use these for secondary discovery as instructed
- ...
```

- [ ] **Step 6: Verify file saved**

Check that `output/` directory contains a `.txt` file with the template.

- [ ] **Step 7: Run full test suite**

```
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 8: Final commit**

```
git add .
git commit -m "feat: complete template builder — verified end-to-end"
```

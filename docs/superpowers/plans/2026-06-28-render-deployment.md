# Render Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy the Flask template-builder to Render with per-session conversation isolation so multiple concurrent users don't share state.

**Architecture:** Replace the global `conversation_history` list with a `conversations` dict keyed by UUID session IDs stored in signed Flask cookies. `stream_conversation()` takes the session's list as a parameter. Two routes need updating (`/reset`, `/chat`); `/export` and `/polish` are unchanged. Gunicorn with 1 worker + 4 threads handles concurrent SSE streams while keeping the dict in a single process.

**Tech Stack:** Flask, Gunicorn, Render (render.yaml), pytest

**Spec:** `docs/superpowers/specs/2026-06-28-render-deployment-design.md`

---

## File Map

| File | Change |
|---|---|
| `requirements.txt` | Add `gunicorn` |
| `Procfile` | New — `web: gunicorn --workers 1 --threads 4 app:app` |
| `config.py` | `PORT` reads from env var |
| `app.py` | Session isolation: `conversations` dict, helpers, updated routes and `stream_conversation` |
| `render.yaml` | New — service definition with env var declarations |
| `tests/test_routes.py` | Update fixtures and tests that reference the old global list |
| `tests/test_session_isolation.py` | New — tests for per-session isolation |

---

## Task 1: Infrastructure — gunicorn and Procfile

**Files:**
- Modify: `requirements.txt`
- Create: `Procfile`

- [ ] **Step 1: Add gunicorn to requirements.txt**

Open `requirements.txt`. It currently ends with `pytest-flask>=1.3.0`. Add one line:

```
flask>=3.0.0
anthropic>=0.30.0
python-dotenv>=1.0.0
pytest>=8.0.0
pytest-flask>=1.3.0
gunicorn>=21.0.0
```

- [ ] **Step 2: Create Procfile**

Create `Procfile` at the repo root (no extension) with exactly this content:

```
web: gunicorn --workers 1 --threads 4 app:app
```

`--workers 1` keeps all sessions in one process (the in-memory `conversations` dict is shared). `--threads 4` allows 4 concurrent SSE streams without blocking.

- [ ] **Step 3: Verify gunicorn installs**

```bash
pip install -r requirements.txt
gunicorn --version
```

Expected: prints a version like `gunicorn (version 21.x.x)` with no errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt Procfile
git commit -m "feat: add gunicorn and Procfile for Render deployment"
```

---

## Task 2: Fix PORT to read from environment

**Files:**
- Modify: `config.py`

Render assigns a dynamic port via the `PORT` environment variable. The app currently hardcodes 5000. This task makes the app bind to whatever port Render assigns.

- [ ] **Step 1: Update config.py**

Replace the current `PORT = 5000` line:

```python
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key.")
MODEL = "claude-sonnet-4-6"
PORT = int(os.environ.get("PORT", 5000))
RAG_ENABLED = os.environ.get("RAG_ENABLED", "1") != "0"
```

- [ ] **Step 2: Verify locally still works**

```bash
python main.py
```

Expected: app starts on port 5000 (since `PORT` is not set in your local env), browser opens at `localhost:5000`. Ctrl-C to stop.

- [ ] **Step 3: Commit**

```bash
git add config.py
git commit -m "feat: read PORT from environment variable for Render"
```

---

## Task 3: Write failing tests for session isolation

**Files:**
- Create: `tests/test_session_isolation.py`

These tests verify that two browser sessions can't interfere with each other. They will fail until Task 4 implements the feature.

- [ ] **Step 1: Create the test file**

Create `tests/test_session_isolation.py`:

```python
import json, sys, os, pytest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
import app as app_module
from app import app as flask_app


@pytest.fixture(autouse=True)
def clear_conversations():
    app_module.conversations.clear()
    yield
    app_module.conversations.clear()


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    return flask_app


def test_reset_creates_unique_session_id(app):
    """Each test client gets a distinct session UUID on /reset."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    client1.post("/reset")
    client2.post("/reset")

    with client1.session_transaction() as sess1:
        sid1 = sess1.get("id")
    with client2.session_transaction() as sess2:
        sid2 = sess2.get("id")

    assert sid1 is not None
    assert sid2 is not None
    assert sid1 != sid2


def test_reset_only_clears_own_session(app):
    """Resetting one session leaves another session's history untouched."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    client1.post("/reset")
    client2.post("/reset")

    # Inject history into client2's session
    with client2.session_transaction() as sess:
        sid2 = sess["id"]
    app_module.conversations[sid2] = [{"role": "user", "content": "hello"}]

    # Reset client1 — must not touch client2
    client1.post("/reset")

    assert app_module.conversations[sid2] == [{"role": "user", "content": "hello"}]


def make_mock_stream(text_chunks):
    class FinalMsg:
        stop_reason = "end_turn"
        content = []
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter(text_chunks)
        def get_final_message(self): return FinalMsg()
    return Stream()


def test_two_clients_have_independent_histories(app):
    """Messages sent by one client don't appear in the other client's history."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hi"])
        client1.post("/chat",
            data=json.dumps({"message": "from client1"}),
            content_type="application/json").data

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hello"])
        client2.post("/chat",
            data=json.dumps({"message": "from client2"}),
            content_type="application/json").data

    with client1.session_transaction() as sess:
        sid1 = sess["id"]
    with client2.session_transaction() as sess:
        sid2 = sess["id"]

    history1 = app_module.conversations[sid1]
    history2 = app_module.conversations[sid2]

    assert any(m["content"] == "from client1" for m in history1 if m["role"] == "user")
    assert not any(m.get("content") == "from client2" for m in history1)
    assert any(m["content"] == "from client2" for m in history2 if m["role"] == "user")
    assert not any(m.get("content") == "from client1" for m in history2)
```

- [ ] **Step 2: Run tests and confirm they fail**

```bash
pytest tests/test_session_isolation.py -v
```

Expected: all three tests FAIL with `AttributeError: module 'app' has no attribute 'conversations'`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_session_isolation.py
git commit -m "test: add failing session isolation tests (TDD)"
```

---

## Task 4: Implement session isolation in app.py

**Files:**
- Modify: `app.py`

This is the core change. Replace the global list with a per-session dict, add two helpers, update `stream_conversation` to accept a `history` parameter, and update the two routes that use it (`/reset` and `/chat`).

- [ ] **Step 1: Update the imports at the top of app.py**

The current imports block (lines 1–8):

```python
import json
import logging
import os
import traceback
from flask import Flask, request, Response, render_template, jsonify
import anthropic
import retrieve
from config import ANTHROPIC_API_KEY, MODEL, PORT
```

Replace with:

```python
import json
import logging
import os
import traceback
import uuid
from flask import Flask, request, Response, render_template, jsonify, session
import anthropic
import retrieve
from config import ANTHROPIC_API_KEY, MODEL, PORT
```

- [ ] **Step 2: Replace the global list and add the secret key + helpers**

Find this line (currently right after `app = Flask(__name__)`):

```python
app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
```

Replace with:

```python
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
```

Then find the line:

```python
conversation_history = []
```

Replace it with:

```python
conversations: dict = {}  # session_id → list[message dict]


def get_history() -> list:
    sid = session.get("id")
    if not sid:
        sid = str(uuid.uuid4())
        session["id"] = sid
    return conversations.setdefault(sid, [])


def clear_history() -> None:
    sid = session.get("id")
    if sid:
        conversations[sid] = []
```

- [ ] **Step 3: Update stream_conversation to accept history as a parameter**

Find the current signature:

```python
def stream_conversation(new_message, system=None, retrieved_block=None):
```

Replace the entire function with this version (same logic, `history` param instead of global):

```python
def stream_conversation(history, new_message, system=None, retrieved_block=None):
    if system is None:
        system = GATHERING_PROMPT
    history.append({"role": "user", "content": new_message})

    while True:
        if retrieved_block:
            messages = history[:-1] + [{
                "role": "user",
                "content": history[-1]["content"] + "\n\n" + retrieved_block,
            }]
            retrieved_block = None
        else:
            messages = list(history)

        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=GATHERING_TOOLS,
            messages=messages
        ) as stream:
            for text in stream.text_stream:
                yield f"event: chat_token\ndata: {json.dumps(text)}\n\n"
            final = stream.get_final_message()

        history.append({
            "role": "assistant",
            "content": [b.model_dump(exclude_none=True) for b in final.content]
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
            history.append({"role": "user", "content": tool_results})
        else:
            break

    yield f"event: done\ndata: {{}}\n\n"
```

- [ ] **Step 4: Update the /chat route to pass session history**

Find the `/chat` route body. Replace the `safe_stream` inner function call:

```python
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data["message"]
    settings = data.get("settings", {})
    sections = data.get("sections", {})
    settings_context = build_settings_context(settings)
    system = GATHERING_PROMPT + settings_context
    retrieved_block = retrieve.retrieve_context(sections, message)
    history = get_history()
    def safe_stream():
        try:
            yield from stream_conversation(history, message, system, retrieved_block)
        except Exception as e:
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps(type(e).__name__ + ': ' + str(e))}\n\n"
    return Response(safe_stream(), mimetype="text/event-stream")
```

- [ ] **Step 5: Update the /reset route**

Find:

```python
@app.route("/reset", methods=["POST"])
def reset():
    conversation_history.clear()
    return jsonify({"ok": True})
```

Replace with:

```python
@app.route("/reset", methods=["POST"])
def reset():
    clear_history()
    return jsonify({"ok": True})
```

- [ ] **Step 6: Run the new session isolation tests — they should now pass**

```bash
pytest tests/test_session_isolation.py -v
```

Expected: all three tests PASS.

---

## Task 5: Update existing route tests

**Files:**
- Modify: `tests/test_routes.py`

The existing tests reference `app_module.conversation_history` (the old global list). Now that the list is keyed by session, these tests need to use session-aware lookups. The `clear_history` autouse fixture and three tests need updating.

- [ ] **Step 1: Update the autouse fixture and client fixture**

Find the two fixtures at the top of `tests/test_routes.py`:

```python
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
```

Replace with:

```python
@pytest.fixture(autouse=True)
def clear_history():
    app_module.conversations.clear()
    yield
    app_module.conversations.clear()


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    with flask_app.test_client(use_cookies=True) as c:
        yield c
```

- [ ] **Step 2: Update test_reset_clears_history**

Find:

```python
def test_reset_clears_history(client):
    app_module.conversation_history.append({"role": "user", "content": "hi"})
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert app_module.conversation_history == []
```

Replace with:

```python
def test_reset_clears_history(client):
    # Establish a session, then inject history, then verify /reset clears it
    client.post("/reset")
    with client.session_transaction() as sess:
        sid = sess["id"]
    app_module.conversations[sid] = [{"role": "user", "content": "hi"}]
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert app_module.conversations.get(sid) == []
```

- [ ] **Step 3: Update test_chat_appends_to_history**

Find:

```python
def test_chat_appends_to_history(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Reply"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        _ = resp.data  # consume stream so generator runs to completion
    assert len(app_module.conversation_history) == 2
    assert app_module.conversation_history[0] == {"role": "user", "content": "Hello"}
    assert app_module.conversation_history[1]["role"] == "assistant"
```

Replace with:

```python
def test_chat_appends_to_history(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Reply"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        _ = resp.data
    with client.session_transaction() as sess:
        sid = sess["id"]
    history = app_module.conversations[sid]
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1]["role"] == "assistant"
```

- [ ] **Step 4: Update test_chat_injects_grounding_block**

Find the assertion at the end of `test_chat_injects_grounding_block`:

```python
    # Grounding is transient -- not persisted to history
    assert app_module.conversation_history[0]["content"] == "Hello"
```

Replace with:

```python
    # Grounding is transient -- not persisted to history
    with client.session_transaction() as sess:
        sid = sess["id"]
    assert app_module.conversations[sid][0]["content"] == "Hello"
```

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests in `test_routes.py`, `test_session_isolation.py`, `test_tools.py`, `test_gathering_prompt.py`, and `test_retrieve.py` PASS. Zero failures.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: per-session conversation history for concurrent users"
```

---

## Task 6: Create render.yaml

**Files:**
- Create: `render.yaml`

This is the infrastructure-as-code definition Render reads when you connect the repo. It defines the web service, the build command, the start command, and how env vars are managed.

- [ ] **Step 1: Create render.yaml at the repo root**

```yaml
services:
  - type: web
    name: template-builder
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn --workers 1 --threads 4 app:app
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: SECRET_KEY
        generateValue: true
```

`ANTHROPIC_API_KEY` with `sync: false` means Render will prompt you to enter the value in the dashboard — it is never committed to the repo. `SECRET_KEY` with `generateValue: true` means Render auto-generates a cryptographically secure stable value.

- [ ] **Step 2: Run tests one final time to confirm nothing is broken**

```bash
pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add render.yaml
git commit -m "feat: add render.yaml for Render deployment"
```

---

## Task 7: Deploy on Render

This task is manual — no code changes.

- [ ] **Step 1: Push the branch to GitHub**

```bash
git push origin master
```

- [ ] **Step 2: Create a new Blueprint on Render**

1. Go to [render.com](https://render.com) and log in (create account if needed)
2. Click **New +** → **Blueprint**
3. Connect your GitHub account and select this repository
4. Render detects `render.yaml` automatically and shows a preview of the `template-builder` service
5. Click **Apply**

- [ ] **Step 3: Set ANTHROPIC_API_KEY**

Render pauses and prompts for the value of `ANTHROPIC_API_KEY` (because it has `sync: false`). Enter your Anthropic API key. Click **Apply** to start the deploy.

- [ ] **Step 4: Verify the deploy**

Wait for the deploy to complete (2–3 minutes). Render will show a green "Live" badge and a URL like `https://template-builder-xxxx.onrender.com`.

Open the URL in two browser tabs simultaneously. In each tab, start a conversation. Verify that the conversations are independent — messages in tab 1 don't appear in tab 2.

- [ ] **Step 5: Note the free tier behaviour**

On the free tier, the service sleeps after 15 minutes of inactivity. The first request after sleep takes ~30 seconds. If this is disruptive, upgrade to the Starter plan ($7/month) in the Render dashboard under the service settings.

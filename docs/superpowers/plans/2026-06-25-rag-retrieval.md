# RAG Retrieval Grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ground the gathering agent in a curated corpus (craft exemplars + coverage maps) by retrieving 3–5 relevant entries per turn via a cheap Haiku call and injecting them into the model's context, additively and fail-open.

**Architecture:** A new `retrieve.py` module loads a JSON corpus at startup and exposes `retrieve_context(sections, latest_msg)`. `/chat` calls it before the Sonnet gathering call; the returned guidance is appended to the current user turn's content **for that API call only** (not persisted), which is cache-safe and needs no beta header. Any failure, missing corpus, or domain-less turn returns `None` and the app behaves exactly as today.

**Tech Stack:** Python 3 / Flask, the `anthropic` SDK (already a dependency), `pytest`. No new dependencies.

> **Note on injection mechanism:** The spec named a mid-conversation `role:"system"` message as the primary injection and user-turn content as the fallback. Because `config.MODEL` is `claude-sonnet-4-6` (not Opus 4.8), this plan uses the spec's documented fallback — user-turn content injection — as the primary mechanism. It is cache-safe (appended after the cached prefix), works on every model, and needs no beta header.

---

### Task 1: Config flag + corpus loader

**Files:**
- Modify: `config.py:9-10`
- Create: `retrieve.py`
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Add the config flag**

In `config.py`, after the `MODEL` / `PORT` lines, add:

```python
RAG_ENABLED = os.environ.get("RAG_ENABLED", "1") != "0"
```

- [ ] **Step 2: Write the failing loader tests**

Create `tests/test_retrieve.py`:

```python
import os, json
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
import retrieve


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_load_corpus_parses_valid(tmp_path):
    _write(tmp_path / "craft" / "a.json",
           {"id": "craft-a", "type": "craft", "bad": "x", "good": "y", "note": "n"})
    _write(tmp_path / "coverage" / "b.json",
           {"id": "cov-b", "type": "coverage", "dimensions": ["d1"], "note": "n"})
    corpus = retrieve.load_corpus(str(tmp_path))
    assert {e["id"] for e in corpus} == {"craft-a", "cov-b"}


def test_load_corpus_skips_malformed(tmp_path):
    _write(tmp_path / "craft" / "good.json",
           {"id": "craft-a", "type": "craft", "bad": "x", "good": "y"})
    _write(tmp_path / "craft" / "nobad.json",
           {"id": "craft-bad", "type": "craft", "good": "y"})   # missing bad
    _write(tmp_path / "craft" / "noid.json",
           {"type": "craft", "bad": "x", "good": "y"})           # missing id
    corpus = retrieve.load_corpus(str(tmp_path))
    assert [e["id"] for e in corpus] == ["craft-a"]
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_retrieve.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'retrieve'`

- [ ] **Step 4: Create `retrieve.py` with the loader**

```python
import os
import glob
import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY, RAG_ENABLED

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_DIR = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(BASE_DIR, "corpus")

HAIKU_MODEL = "claude-haiku-4-5"


def _valid_entry(e):
    if not isinstance(e, dict) or not e.get("id") or e.get("type") not in ("craft", "coverage"):
        return False
    if e["type"] == "craft":
        return bool(e.get("bad")) and bool(e.get("good"))
    return bool(e.get("dimensions"))


def load_corpus(corpus_dir=CORPUS_DIR):
    entries = []
    for sub in ("craft", "coverage"):
        for path in sorted(glob.glob(os.path.join(corpus_dir, sub, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    e = json.load(f)
            except (OSError, json.JSONDecodeError):
                logging.warning("corpus: could not read %s", path)
                continue
            if _valid_entry(e):
                entries.append(e)
            else:
                logging.warning("corpus: skipping malformed entry %s", path)
    return entries


CORPUS = load_corpus()
RAG_EFFECTIVE = RAG_ENABLED and bool(CORPUS)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_retrieve.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add config.py retrieve.py tests/test_retrieve.py
git commit -m "feat: add RAG config flag and corpus loader

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Seed corpus entries

**Files:**
- Create: `corpus/craft/*.json` (7 files)
- Create: `corpus/coverage/*.json` (5 files)
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_retrieve.py`:

```python
def test_real_corpus_loads_nonempty():
    corpus = retrieve.load_corpus()
    assert len(corpus) >= 8
    assert all(e["type"] in ("craft", "coverage") for e in corpus)
    assert len({e["id"] for e in corpus}) == len(corpus)  # ids unique
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_retrieve.py::test_real_corpus_loads_nonempty -v`
Expected: FAIL — `assert 0 >= 8` (no corpus files yet)

- [ ] **Step 3: Create the craft entries**

`corpus/craft/double-barreled.json`:
```json
{
  "id": "craft-double-barreled-01",
  "type": "craft",
  "rule": "one_ask_per_turn",
  "tags": ["compound-question", "any-domain"],
  "bad": "Understand why checkout was frustrating and slow.",
  "good": "Explore how checkout unfolded and how the participant felt about it.",
  "note": "Splits two asks into one and drops the assumption of frustration."
}
```

`corpus/craft/diagnostic-verb.json`:
```json
{
  "id": "craft-diagnostic-verb-01",
  "type": "craft",
  "rule": "exploratory_verbs",
  "tags": ["yes-no", "any-domain"],
  "bad": "Determine whether the participant was satisfied with the service.",
  "good": "Explore how the participant felt about the service during the visit.",
  "note": "Diagnostic verbs collapse to yes/no; exploratory verbs open narrative."
}
```

`corpus/craft/typical-trap.json`:
```json
{
  "id": "craft-typical-trap-01",
  "type": "craft",
  "rule": "episodic",
  "tags": ["typical", "any-domain"],
  "bad": "Walk through what a typical grocery visit looks like for the participant.",
  "good": "Walk through how the participant arrived and entered the store on their most recent visit.",
  "note": "Typical framing invites generic description; anchor on a specific episode."
}
```

`corpus/craft/high-altitude.json`:
```json
{
  "id": "craft-high-altitude-01",
  "type": "craft",
  "rule": "scope_to_slice",
  "tags": ["overall-impression", "any-domain"],
  "bad": "Explore the participant's overall impression of the store.",
  "good": "Trace the moment during the visit when the participant made an unplanned decision.",
  "note": "Whole-experience scope yields summary; target a bounded slice."
}
```

`corpus/craft/comparison-core.json`:
```json
{
  "id": "craft-comparison-core-01",
  "type": "craft",
  "rule": "no_comparison_core",
  "tags": ["comparison", "any-domain"],
  "bad": "Explore how this store compares to others the participant uses.",
  "good": "Surface a specific moment during the visit when something stood out compared to what they expected.",
  "note": "Comparison-as-core makes the participant the analyst; anchor on one occasion."
}
```

`corpus/craft/visual-stimulus.json`:
```json
{
  "id": "craft-visual-stimulus-01",
  "type": "craft",
  "rule": "voiceable",
  "tags": ["visual-stimulus", "any-domain"],
  "bad": "Ask the participant to react to the store's new logo.",
  "good": "Draw out a moment the participant noticed something about how the store looked or felt.",
  "note": "No screen in a voice interview; anchor on a remembered moment, not a shown stimulus."
}
```

`corpus/craft/probe-restates-core.json`:
```json
{
  "id": "craft-probe-restates-core-01",
  "type": "craft",
  "rule": "probe_adds_direction",
  "tags": ["redundant-probe", "any-domain"],
  "bad": "Probe: ask again how checkout went.",
  "good": "Probe: surface one specific thing that felt smooth or awkward at checkout, if anything stood out.",
  "note": "A probe must add a new direction, not restate its core."
}
```

- [ ] **Step 4: Create the coverage entries**

`corpus/coverage/grocery.json`:
```json
{
  "id": "coverage-grocery-01",
  "type": "coverage",
  "domain_tags": ["grocery", "retail", "in-store shopping"],
  "dimensions": ["arrival & entry", "finding items", "unplanned decisions", "checkout friction", "leaving"],
  "note": "Anchor each on the most recent specific visit, not a typical one."
}
```

`corpus/coverage/commute.json`:
```json
{
  "id": "coverage-commute-01",
  "type": "coverage",
  "domain_tags": ["commuting", "travel", "transit"],
  "dimensions": ["leaving home", "the journey itself", "disruptions or delays", "other people", "arrival & transition"],
  "note": "Anchor on the most recent commute, not a typical one."
}
```

`corpus/coverage/banking-app.json`:
```json
{
  "id": "coverage-banking-app-01",
  "type": "coverage",
  "domain_tags": ["banking app", "mobile banking", "fintech"],
  "dimensions": ["opening the app", "the task they came to do", "moments of hesitation or doubt", "security & trust feelings", "completing or abandoning"],
  "note": "Anchor on the most recent session and a specific task."
}
```

`corpus/coverage/healthcare-visit.json`:
```json
{
  "id": "coverage-healthcare-visit-01",
  "type": "coverage",
  "domain_tags": ["healthcare visit", "doctor", "clinic"],
  "dimensions": ["booking & arrival", "waiting", "the consultation itself", "being heard or not", "leaving & next steps"],
  "note": "Sensitive topic — place emotionally loaded dimensions later in the funnel."
}
```

`corpus/coverage/streaming.json`:
```json
{
  "id": "coverage-streaming-01",
  "type": "coverage",
  "domain_tags": ["streaming", "video", "entertainment app"],
  "dimensions": ["deciding to watch", "browsing & choosing", "the moment of starting something", "interruptions", "stopping or finishing"],
  "note": "Anchor on the most recent specific viewing session."
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_retrieve.py::test_real_corpus_loads_nonempty -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add corpus tests/test_retrieve.py
git commit -m "feat: add seed RAG corpus (craft exemplars + coverage maps)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Pure helpers (catalog, query, block, domain guard)

**Files:**
- Modify: `retrieve.py`
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_retrieve.py`:

```python
def test_build_catalog_format():
    corpus = [
        {"id": "craft-a", "type": "craft", "tags": ["t1", "t2"], "note": "split asks"},
        {"id": "cov-b", "type": "coverage", "domain_tags": ["grocery"], "note": "dims"},
    ]
    cat = retrieve.build_catalog(corpus)
    assert "[craft-a] (craft) t1,t2 :: split asks" in cat
    assert "[cov-b] (coverage) grocery :: dims" in cat


def test_build_query_assembles_context():
    sections = {
        "metadata": {"title": "Grocery Study"},
        "focus": "most recent visit",
        "topics": [{"title": "Arrival"}, {"title": "Checkout"}],
    }
    q = retrieve.build_query(sections, "I want to explore checkout")
    assert "Grocery Study" in q
    assert "most recent visit" in q
    assert "Arrival" in q and "Checkout" in q
    assert "I want to explore checkout" in q


def test_assemble_block_renders_chosen_entries():
    corpus = [
        {"id": "craft-a", "type": "craft", "rule": "one_ask", "bad": "B", "good": "G", "note": "N"},
        {"id": "cov-b", "type": "coverage", "domain_tags": ["grocery"],
         "dimensions": ["arrival", "checkout"], "note": "anchor"},
        {"id": "unused", "type": "craft", "bad": "x", "good": "y"},
    ]
    block = retrieve.assemble_block(corpus, ["craft-a", "cov-b"])
    assert block.startswith("<grounding>")
    assert block.rstrip().endswith("</grounding>")
    assert "B" in block and "G" in block          # craft bad/good
    assert "arrival; checkout" in block            # coverage dimensions
    assert "y" not in block                         # unused entry not rendered


def test_assemble_block_empty_returns_empty_string():
    assert retrieve.assemble_block([{"id": "a", "type": "craft"}], []) == ""
    assert retrieve.assemble_block([{"id": "a", "type": "craft"}], ["missing"]) == ""


def test_has_domain():
    assert retrieve._has_domain({"metadata": {"title": "X"}, "topics": []}) is True
    assert retrieve._has_domain({"metadata": {"title": ""}, "topics": [{"title": "T"}]}) is True
    assert retrieve._has_domain({"metadata": {"title": ""}, "topics": []}) is False
    assert retrieve._has_domain({}) is False
    assert retrieve._has_domain(None) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retrieve.py -k "catalog or query or assemble or has_domain" -v`
Expected: FAIL — `AttributeError: module 'retrieve' has no attribute 'build_catalog'`

- [ ] **Step 3: Add the helpers to `retrieve.py`**

Insert these functions after `load_corpus` (before the `CORPUS = ...` line):

```python
def build_catalog(corpus):
    lines = []
    for e in corpus:
        tags = ",".join(e.get("tags") or e.get("domain_tags") or [])
        lines.append(f"[{e['id']}] ({e['type']}) {tags} :: {e.get('note', '')}")
    return "\n".join(lines)


def build_query(sections, latest_msg):
    sections = sections or {}
    meta = sections.get("metadata") or {}
    title = meta.get("title", "")
    focus = sections.get("focus", "")
    topics = sections.get("topics") or []
    topic_titles = ", ".join(t.get("title", "") for t in topics)
    return (f"Title: {title}\nFocus: {focus}\nTopics: {topic_titles}\n"
            f"Latest message: {latest_msg}")


def assemble_block(corpus, ids):
    by_id = {e["id"]: e for e in corpus}
    chosen = [by_id[i] for i in ids if i in by_id]
    if not chosen:
        return ""
    parts = [
        "<grounding>",
        "Relevant interview-design guidance for this draft. Apply it; do not quote it to the client.",
    ]
    for e in chosen:
        if e["type"] == "craft":
            parts.append(
                f"- Craft ({e.get('rule', '')}): avoid \"{e['bad']}\" -> prefer \"{e['good']}\". {e.get('note', '')}"
            )
        else:
            dims = "; ".join(e.get("dimensions", []))
            tags = ",".join(e.get("domain_tags", []))
            parts.append(f"- Coverage ({tags}): ensure dimensions -- {dims}. {e.get('note', '')}")
    parts.append("</grounding>")
    return "\n".join(parts)


def _has_domain(sections):
    sections = sections or {}
    title = (sections.get("metadata") or {}).get("title", "")
    topics = sections.get("topics") or []
    return bool(title) or len(topics) > 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_retrieve.py -k "catalog or query or assemble or has_domain" -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add retrieve.py tests/test_retrieve.py
git commit -m "feat: add pure RAG helpers (catalog, query, block, domain guard)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Haiku selection call + orchestrator

**Files:**
- Modify: `retrieve.py`
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_retrieve.py`:

```python
def _tool_resp(entry_ids):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "select_entries"
    block.input = {"entry_ids": entry_ids}
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_select_entries_parses_ids():
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp(["craft-a", "cov-b"])
        ids = retrieve.select_entries("query", "catalog")
    assert ids == ["craft-a", "cov-b"]


def test_select_entries_caps_at_5():
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp([f"id{i}" for i in range(10)])
        ids = retrieve.select_entries("q", "c")
    assert len(ids) == 5


def test_select_entries_no_tool_use_returns_empty():
    text_block = MagicMock()
    text_block.type = "text"
    resp = MagicMock()
    resp.content = [text_block]
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = resp
        assert retrieve.select_entries("q", "c") == []


def test_retrieve_context_none_when_disabled(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", False)
    assert retrieve.retrieve_context({"metadata": {"title": "Grocery"}}, "hi") is None


def test_retrieve_context_none_without_domain(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS",
                        [{"id": "craft-a", "type": "craft", "bad": "x", "good": "y"}])
    assert retrieve.retrieve_context({"metadata": {"title": ""}, "topics": []}, "hi") is None


def test_retrieve_context_returns_block_with_domain(monkeypatch):
    corpus = [{"id": "craft-a", "type": "craft", "rule": "r", "bad": "BAD", "good": "GOOD", "note": "n"}]
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS", corpus)
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp(["craft-a"])
        block = retrieve.retrieve_context({"metadata": {"title": "Grocery"}, "topics": []}, "hi")
    assert block is not None
    assert "<grounding>" in block
    assert "BAD" in block and "GOOD" in block


def test_retrieve_context_none_on_exception(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS",
                        [{"id": "craft-a", "type": "craft", "bad": "x", "good": "y"}])
    with patch("retrieve.client") as mc:
        mc.messages.create.side_effect = RuntimeError("boom")
        assert retrieve.retrieve_context({"metadata": {"title": "Grocery"}}, "hi") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retrieve.py -k "select_entries or retrieve_context" -v`
Expected: FAIL — `AttributeError: module 'retrieve' has no attribute 'select_entries'`

- [ ] **Step 3: Add the selection call + orchestrator to `retrieve.py`**

Add near the top of `retrieve.py`, after the `HAIKU_MODEL` line:

```python
SELECT_SYSTEM = (
    "You help a research-interview-design assistant. Given the current draft and a "
    "catalog of guidance entries, choose the 3-5 entries most relevant to improving "
    "the draft right now -- a mix of craft (phrasing) and coverage (missing dimensions) "
    "when both apply. Call select_entries with their ids. Choose only ids that appear "
    "in the catalog; if nothing is relevant, return an empty list."
)

SELECT_TOOL = {
    "name": "select_entries",
    "description": "Return the ids of the corpus entries most relevant to the current interview draft.",
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_ids": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["entry_ids"]
    }
}
```

Add these functions at the end of `retrieve.py` (after `_has_domain`):

```python
def select_entries(query, catalog):
    resp = client.messages.create(
        model=HAIKU_MODEL,
        max_tokens=512,
        system=[{
            "type": "text",
            "text": SELECT_SYSTEM + "\n\nCATALOG:\n" + catalog,
            "cache_control": {"type": "ephemeral"},
        }],
        tools=[SELECT_TOOL],
        tool_choice={"type": "tool", "name": "select_entries"},
        messages=[{"role": "user", "content": query}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "select_entries":
            ids = block.input.get("entry_ids", []) or []
            return [i for i in ids if isinstance(i, str)][:5]
    return []


def retrieve_context(sections, latest_msg):
    if not RAG_EFFECTIVE:
        return None
    if not _has_domain(sections):
        return None
    try:
        catalog = build_catalog(CORPUS)
        query = build_query(sections, latest_msg)
        ids = select_entries(query, catalog)
        block = assemble_block(CORPUS, ids)
        return block or None
    except Exception:
        logging.exception("retrieve_context failed; proceeding without grounding")
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_retrieve.py -v`
Expected: PASS (all retrieve tests green)

- [ ] **Step 5: Commit**

```bash
git add retrieve.py tests/test_retrieve.py
git commit -m "feat: add Haiku selection call and retrieve_context orchestrator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wire retrieval into `/chat`

**Files:**
- Modify: `app.py:1-23` (import), `app.py:338-375` (`stream_conversation`), `app.py:383-396` (`/chat`)
- Test: `tests/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_routes.py`:

```python
def test_chat_injects_grounding_block(client):
    with patch("app.retrieve.retrieve_context", return_value="<grounding>GUIDE</grounding>"), \
         patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Ok"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello",
                             "sections": {"metadata": {"title": "Grocery"}}}),
            content_type="application/json")
        _ = resp.data
    sent = mock_client.messages.stream.call_args.kwargs["messages"]
    assert sent[-1]["role"] == "user"
    assert "<grounding>GUIDE</grounding>" in sent[-1]["content"]
    assert "Hello" in sent[-1]["content"]
    # Grounding is transient — not persisted to history
    assert app_module.conversation_history[0]["content"] == "Hello"


def test_chat_no_grounding_when_retrieval_returns_none(client):
    with patch("app.retrieve.retrieve_context", return_value=None), \
         patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Ok"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        _ = resp.data
    sent = mock_client.messages.stream.call_args.kwargs["messages"]
    assert sent[-1]["content"] == "Hello"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_routes.py -k "grounding" -v`
Expected: FAIL — `AttributeError: <module 'app'> does not have the attribute 'retrieve'`

- [ ] **Step 3: Add the import**

In `app.py`, after `import anthropic` (line 6), add:

```python
import retrieve
```

- [ ] **Step 4: Update `stream_conversation` to accept and inject the block**

Replace the `stream_conversation` function (currently starting at `app.py:338`). Change the signature and add the transient-injection block; everything else is unchanged:

```python
def stream_conversation(new_message, system=None, retrieved_block=None):
    if system is None:
        system = GATHERING_PROMPT
    conversation_history.append({"role": "user", "content": new_message})

    while True:
        if retrieved_block:
            # Inject grounding into the current user turn for THIS call only.
            # Not persisted to conversation_history (would bloat history and go
            # stale next turn). Appended after the cached prefix -> cache-safe.
            messages = conversation_history[:-1] + [{
                "role": "user",
                "content": conversation_history[-1]["content"] + "\n\n" + retrieved_block,
            }]
            retrieved_block = None  # inject once, on the first model call of the turn
        else:
            messages = conversation_history

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

        conversation_history.append({
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
            conversation_history.append({"role": "user", "content": tool_results})
        else:
            break

    yield f"event: done\ndata: {{}}\n\n"
```

- [ ] **Step 5: Update the `/chat` route to retrieve and pass the block**

Replace the `chat()` function body (currently at `app.py:383`):

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
    def safe_stream():
        try:
            yield from stream_conversation(message, system, retrieved_block)
        except Exception as e:
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps(type(e).__name__ + ': ' + str(e))}\n\n"
    return Response(safe_stream(), mimetype="text/event-stream")
```

- [ ] **Step 6: Run the new tests and the full route suite**

Run: `pytest tests/test_routes.py -v`
Expected: PASS — new grounding tests pass and all pre-existing route tests still pass.

- [ ] **Step 7: Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: wire RAG retrieval into /chat with transient grounding injection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: Send `sections` from the frontend

**Files:**
- Modify: `static/app.js:245-253`

- [ ] **Step 1: Add `sections` to the `/chat` request body**

In `static/app.js`, in the `/chat` fetch body (currently lines 245–253), add `sections: state.sections,` alongside `message` and `settings`:

```javascript
      body: JSON.stringify({
        message,
        sections: state.sections,
        settings: {
          depthValue: state.depthSliderValue,
          depthLabel: { 0: "Breadth", 25: "Slightly Broad", 50: "Balanced", 75: "Slightly Deep", 100: "Deep" }[state.depthSliderValue] || "Balanced",
          durationTarget: state.durationTarget,
          estimate: estimateDuration()
        }
      })
```

- [ ] **Step 2: Run the full Python suite to confirm nothing regressed**

Run: `pytest tests/`
Expected: PASS (all suites green)

- [ ] **Step 3: Manual smoke check (requires a real API key)**

1. `python main.py`
2. In the browser, say: "I want a comprehensive interview about grocery shopping."
3. Confirm topics still populate and the conversation behaves normally (grounding is invisible to the user — it only shapes the model's output).
4. Stop the server.

> If no API key is available, skip step 3 — the pytest suite already covers the wiring with mocks.

- [ ] **Step 4: Commit**

```bash
git add static/app.js
git commit -m "feat: send sections state on /chat for RAG retrieval

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Out of scope (future work)

- **Phase 4 — reviewer reuse:** feeding matched craft exemplars into `/review` and `/polish` fix suggestions (spec §"Build phases" item 4). Deferred; the corpus and `retrieve.py` are reusable for it later.
- **Trimming `prompts/gathering.txt`** once craft exemplars cover the same ground.
- **Expanding the corpus** beyond the seed set.

---

## Self-review

**Spec coverage:**
- Corpus (two types, JSON, loaded at startup) → Tasks 1–2 ✓
- Retriever helpers + Haiku selection + caching → Tasks 3–4 ✓
- `RAG_ENABLED` flag + auto-off when corpus empty → Task 1 (`RAG_EFFECTIVE`) ✓
- Fail-open / degradation → Task 4 (`retrieve_context` try/except, guards) + Task 5 (`retrieved_block=None` path) ✓
- Cache-safe injection → Task 5 (transient user-turn append; mechanism deviation from spec documented in header) ✓
- `sections` on `/chat` payload → Task 6 ✓
- Tests (`test_retrieve.py` + one route test) → Tasks 1–5 ✓

**Placeholder scan:** none — every code step shows complete content.

**Type consistency:** `load_corpus`, `build_catalog`, `build_query`, `assemble_block`, `_has_domain`, `select_entries`, `retrieve_context`, `CORPUS`, `RAG_EFFECTIVE`, `SELECT_TOOL`, `HAIKU_MODEL` are named identically across tasks and tests. `stream_conversation(new_message, system, retrieved_block)` signature matches its `/chat` call site.

# Render Deployment Design

**Date:** 2026-06-28
**Scope:** Deploy the Flask template-builder app to Render with multi-user session isolation.

---

## Goals

1. Deploy the app as a live web service on Render.
2. Fix concurrent-user session isolation so multiple users don't share or clobber each other's `conversation_history`.
3. Keep the change minimal — no new external services, no schema changes, no behavioural changes for the user.

---

## Session Isolation

### Problem

`conversation_history` in `app.py` is a single module-level list. Multiple concurrent users interleave their messages, and any `/reset` call wipes history for everyone.

### Solution — in-memory dict keyed by session ID (Option A)

Replace the global list with a dict:

```python
conversations: dict = {}  # session_id (str) → list[message dict]
```

Each browser receives a UUID stored in a signed Flask cookie (`session["id"]`). Two helpers manage access:

```python
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

Two routes read or mutate `conversation_history` and need updating:
- `/reset` — calls `conversation_history.clear()` → replace with `clear_history()`
- `/chat` → `stream_conversation()` reads and appends to `conversation_history` → pass `get_history()` as a parameter

`/export` and `/polish` do not use `conversation_history` and need no changes.

### Secret key

Flask requires `app.secret_key` to sign cookies. Read from env:

```python
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))
```

The `os.urandom(24)` fallback means cookies are invalidated on restart (acceptable for a chat tool). On Render, `SECRET_KEY` is auto-generated and stable across deploys (see `render.yaml` below).

### Trade-offs accepted

- Sessions are **not persistent** — a redeploy clears all in-flight conversations. Acceptable for this tool; users simply start a new session.
- The `conversations` dict grows unboundedly. For the expected traffic (small number of concurrent users), this is not a concern. No GC needed.
- With `--workers 1`, all sessions share one process and one dict. Thread safety for simple dict and list operations is guaranteed by Python's GIL.

---

## Deployment Infrastructure

### `requirements.txt`

Add `gunicorn` (no version pin needed — latest stable is fine).

### `config.py`

Change the hardcoded port to read from the environment:

```python
PORT = int(os.environ.get("PORT", 5000))
```

Render assigns the port dynamically via the `PORT` env var. Local dev continues to default to 5000.

### `Procfile` (new)

```
web: gunicorn --workers 1 --threads 4 app:app
```

- `--workers 1` — single process so the in-memory `conversations` dict is shared across all requests.
- `--threads 4` — up to 4 concurrent SSE streaming connections without blocking.
- `app:app` — points Gunicorn at the `app` Flask object in `app.py`. `main.py` is not used on Render (it's only for local dev with browser auto-open).

### `render.yaml` (new)

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

- `ANTHROPIC_API_KEY` with `sync: false` — Render prompts for the value in the dashboard; never committed to the repo.
- `SECRET_KEY` with `generateValue: true` — Render auto-generates a cryptographically secure value that persists across deploys.

---

## Manual Render Setup (one-time)

After pushing the code changes to GitHub:

1. Go to Render → **New → Blueprint**
2. Connect the GitHub repo
3. Render reads `render.yaml` and creates the web service; it pauses to ask for `ANTHROPIC_API_KEY`
4. Enter the API key → deploy

The app will be live at a `.onrender.com` URL.

### Free tier note

Render's free tier spins down after 15 minutes of inactivity; the first request after a cold start takes ~30 seconds. The Starter plan ($7/month) keeps the service always-on. An external uptime monitor pinging the service every 10 minutes is a free workaround.

---

## Files Changed

| File | Change |
|---|---|
| `app.py` | Replace `conversation_history` global list with `conversations` dict; add `get_history()` / `clear_history()` helpers; update all four routes; add `app.secret_key` |
| `config.py` | `PORT = int(os.environ.get("PORT", 5000))` |
| `requirements.txt` | Add `gunicorn` |
| `Procfile` | New — `web: gunicorn --workers 1 --threads 4 app:app` |
| `render.yaml` | New — service definition with env var declarations |

---

## Notes on `/export` and the `output/` directory

`/export` writes the formatted template to `output/<filename>.txt` on disk before returning it in the JSON response. On Render's ephemeral filesystem, the write succeeds and the browser download works correctly — but the file is not persisted between deploys. This is fine: the browser receives the content directly from the JSON response, so the disk write is effectively a no-op from the user's perspective. No change needed.

---

## Out of Scope

- Persistent session storage (Redis, database) — not needed at this scale
- Multiple Render instances / horizontal scaling — single worker is sufficient
- Custom domain — can be added later via Render dashboard
- RAG corpus updates — corpus JSON files are committed to git and deploy automatically

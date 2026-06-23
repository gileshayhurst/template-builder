# Inline Auto-Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After every AI chat turn, silently run a two-step review + item-level fix pass that rewrites flagged interview questions without user interaction; simplify export to skip the review gate entirely.

**Architecture:** New `POST /polish` endpoint calls the existing review agent then a new fixer agent (restricted to `add_topic` only), returns section_update payloads. Frontend fires `polishTemplate()` after every SSE `done` event (fire-and-forget). Export modal drops straight into `generateTemplate()`.

**Tech Stack:** Flask, Anthropic Python SDK (`client.messages.create`), vanilla JS (fetch + SSE reader), pytest

---

## File map

| Action | File | Purpose |
|---|---|---|
| Create | `prompts/fixer.txt` | System prompt for fixer agent |
| Modify | `app.py` | Add `_run_review()`, `_run_fixer()`, `FIXER_PROMPT`, `FIXER_TOOLS`, `POST /polish`; remove `POST /review` |
| Modify | `tests/test_tools.py` | Add `/polish` fast-path test |
| Modify | `static/app.js` | Add `polishTemplate()`, wire SSE handler, simplify `exportTemplate()` / `generateTemplate()`, remove 4 review functions |
| Modify | `templates/index.html` | Remove `#modal-review` div; remove `class="hidden"` from `#modal-template` |
| Modify | `static/style.css` | Remove entire `/* Export review panel */` block (lines 340–398) |

---

### Task 1: Write failing test for `/polish` fast path

**Files:**
- Modify: `tests/test_tools.py`

- [ ] **Step 1: Add imports and the test at the bottom of `tests/test_tools.py`**

The existing file already has `os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")` at the top and imports `from app import process_tool_call, format_template`. Add the new import line and the test at the very end of the file:

```python
from unittest.mock import patch, MagicMock
from app import app as flask_app


def _make_review_response(overall="pass", item_issues=None, structural_issues=None):
    """Build a fake Anthropic response that looks like a submit_review tool call."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_review"
    tool_block.input = {
        "overall": overall,
        "item_issues": item_issues or [],
        "structural_issues": structural_issues or [],
    }
    resp = MagicMock()
    resp.content = [tool_block]
    return resp


def test_polish_no_fixable_issues_returns_empty():
    """When review finds no item issues with suggestions, /polish returns {updates: []}."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        with patch("app.client.messages.create",
                   return_value=_make_review_response(overall="pass")):
            resp = c.post("/polish", json={"sections": {}})
    assert resp.status_code == 200
    assert resp.get_json() == {"updates": []}
```

- [ ] **Step 2: Run the test — confirm it fails with 404**

```bash
pytest tests/test_tools.py::test_polish_no_fixable_issues_returns_empty -v
```

Expected output contains:
```
FAILED tests/test_tools.py::test_polish_no_fixable_issues_returns_empty
AssertionError: assert 404 == 200
```

---

### Task 2: Create `prompts/fixer.txt`

**Files:**
- Create: `prompts/fixer.txt`

- [ ] **Step 1: Create the file with this exact content**

```
You are a template quality fixer. You receive a partially-built interview template and a list of specific item issues — individual core or probe questions that violate interview design rules.

Your job is to apply targeted rewrites to exactly the flagged items and nothing else.

## Rules

1. For each topic that contains at least one flagged item, call `add_topic` with the COMPLETE, UPDATED topic.
2. Copy ALL unflagged items exactly — same text, same priority, same order.
3. For each flagged item, apply the provided suggestion. If no suggestion is given or it cannot be applied sensibly, copy the item unchanged.
4. Do NOT add new items, remove items, reorder items, or change item priorities.
5. Do NOT call `add_topic` for topics that contain no flagged items.
6. Do NOT change the topic index, title, or topic-level priority.

## Item index convention

`item_index` in the issues list is 0-based within its type (core or probe).
So `item_type: "core", item_index: 2` refers to `topics[topic_index - 1].core[2]`.
`topic_index` is 1-based.
```

---

### Task 3: Add helpers, `FIXER_TOOLS`, `/polish` route to `app.py`; remove `/review`

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Load `fixer.txt` alongside the other prompts (after line 18)**

Find this block in `app.py` (around lines 14–18):
```python
with open(os.path.join(BASE_DIR, "prompts", "gathering.txt")) as f:
    GATHERING_PROMPT = f.read()

with open(os.path.join(BASE_DIR, "prompts", "review.txt")) as f:
    REVIEW_PROMPT = f.read()
```

Add one line immediately after:
```python
with open(os.path.join(BASE_DIR, "prompts", "fixer.txt")) as f:
    FIXER_PROMPT = f.read()
```

- [ ] **Step 2: Add `FIXER_TOOLS` constant after `REVIEW_TOOL` (after line 171)**

Find the closing `}` of `REVIEW_TOOL` (around line 171). After it, add:
```python
FIXER_TOOLS = [t for t in GATHERING_TOOLS if t["name"] == "add_topic"]
```

- [ ] **Step 3: Add `_run_review()` and `_run_fixer()` helpers before `build_settings_context()` (around line 174)**

Insert both functions between `FIXER_TOOLS` and `def build_settings_context`:

```python
def _run_review(sections: dict) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=REVIEW_PROMPT,
        tools=[REVIEW_TOOL],
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": f"Review this interview template:\n\n{json.dumps(sections, indent=2)}"
        }]
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_review":
            return block.input
    raise ValueError("reviewer returned no tool call")


def _run_fixer(sections: dict, item_issues: list) -> list:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=FIXER_PROMPT,
        tools=FIXER_TOOLS,
        tool_choice={"type": "auto"},
        messages=[{
            "role": "user",
            "content": (
                f"Here is the current template:\n\n{json.dumps(sections, indent=2)}\n\n"
                f"Here are the specific items that need fixing:\n\n"
                f"{json.dumps(item_issues, indent=2)}\n\n"
                "Fix only the flagged items. Preserve all other items exactly as they are."
            )
        }]
    )
    updates = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "add_topic":
            updates.append(process_tool_call("add_topic", block.input))
    return updates
```

- [ ] **Step 4: Add `POST /polish` route after the `reset` route (around line 385)**

Find `@app.route("/review", methods=["POST"])`. Insert the new route **before** it:

```python
@app.route("/polish", methods=["POST"])
def polish_route():
    body = request.get_json(silent=True) or {}
    sections = body.get("sections", {})
    try:
        review = _run_review(sections)
        fixable = [i for i in review.get("item_issues", []) if i.get("suggestion")]
        if not fixable:
            return jsonify({"updates": []})
        updates = _run_fixer(sections, fixable)
        return jsonify({"updates": updates})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"updates": []})
```

- [ ] **Step 5: Delete the entire `review_route()` function**

Remove this entire block (the decorator plus the function body, ~lines 388–411):
```python
@app.route("/review", methods=["POST"])
def review_route():
    body = request.get_json(silent=True) or {}
    sections = body.get("sections", {})
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=REVIEW_PROMPT,
            tools=[REVIEW_TOOL],
            tool_choice={"type": "any"},
            messages=[{
                "role": "user",
                "content": f"Review this interview template:\n\n{json.dumps(sections, indent=2)}"
            }]
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == "submit_review":
                return jsonify(block.input)
        logging.warning("review_route: API returned no submit_review tool call")
        return jsonify({"error": "reviewer returned no tool call"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
```

---

### Task 4: Run tests and commit backend

**Files:** none (verification only)

- [ ] **Step 1: Run all Python tests**

```bash
pytest tests/ -v
```

Expected: all existing tests pass AND the new test `test_polish_no_fixable_issues_returns_empty` PASSES.

- [ ] **Step 2: Commit backend changes**

```bash
git add app.py prompts/fixer.txt tests/test_tools.py
git commit -m "feat: add /polish endpoint with inline review+fix; remove /review route"
```

---

### Task 5: Add `polishTemplate()` to `app.js` and wire it into the SSE handler

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Add `polishTemplate()` before the `// ─── EXPORT ───` section (around line 845)**

Find the comment `// ─── EXPORT ───────────────────────────────────────────────────────────────────`. Insert the new function immediately before it:

```js
async function polishTemplate() {
  try {
    const resp = await fetch("/polish", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sections: state.sections })
    });
    const data = await resp.json();
    for (const update of (data.updates || [])) {
      applyUpdate(update);
    }
  } catch (err) {
    console.warn("Polish failed:", err);
  }
}
```

- [ ] **Step 2: Wire `polishTemplate()` into `streamFromServer()` after the SSE read loop**

Find the `while (true)` loop in `streamFromServer()` (around lines 261–292). It ends with a closing `}` before the `} catch (err) {`. The exact code to find:

```js
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
          } else if (currentEvent === "error") {
            throw new Error(JSON.parse(raw));
          }
          currentEvent = null;
        }
      }
    }
  } catch (err) {
```

Replace the last two lines of the while loop block (the `}` that closes `while` and then `} catch`) with:

```js
    }
    polishTemplate();
  } catch (err) {
```

The full block after the change should end like this:
```js
          } else if (currentEvent === "done") {
            if (statusEl) { statusEl.remove(); statusEl = null; }
          } else if (currentEvent === "error") {
            throw new Error(JSON.parse(raw));
          }
          currentEvent = null;
        }
      }
    }
    polishTemplate();
  } catch (err) {
    appendMessage("ai", `⚠ Could not reach AI: ${err.message}`);
  } finally {
```

---

### Task 6: Simplify `exportTemplate()` and fix `generateTemplate()` in `app.js`

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Replace `exportTemplate()` with the simplified version**

Find the entire current `exportTemplate()` function (lines ~847–882):
```js
async function exportTemplate() {
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");
  const reviewEl = document.getElementById("modal-review");
  const templateEl = document.getElementById("modal-template");
  const titleEl = document.getElementById("modal-title");

  titleEl.textContent = "Export Template — Reviewing…";
  reviewEl.innerHTML = reviewSpinnerHtml();
  reviewEl.classList.remove("hidden");
  templateEl.classList.add("hidden");
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");

  let reviewData;
  try {
    const resp = await fetch("/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sections: state.sections })
    });
    if (!resp.ok) throw new Error(`Review failed: ${resp.status}`);
    reviewData = await resp.json();
    if (reviewData.error) throw new Error(reviewData.error);
  } catch (err) {
    reviewEl.innerHTML = reviewErrorHtml(err.message);
    return;
  }

  if (reviewData.overall === "pass") {
    await generateTemplate();
  } else {
    titleEl.textContent = "Export Template — Quality Review";
    reviewEl.innerHTML = reviewReportHtml(reviewData);
  }
}
```

Replace the entire function with:
```js
async function exportTemplate() {
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");
  await generateTemplate();
}
```

- [ ] **Step 2: Remove `reviewEl` and `templateEl` references from `generateTemplate()`**

Find the opening of `generateTemplate()` (lines ~943–952):
```js
async function generateTemplate() {
  const reviewEl = document.getElementById("modal-review");
  const templateEl = document.getElementById("modal-template");
  const outputEl = document.getElementById("template-output");
  const titleEl = document.getElementById("modal-title");

  titleEl.textContent = "Exported Template";
  reviewEl.classList.add("hidden");
  templateEl.classList.remove("hidden");
  outputEl.textContent = "Generating template…";
```

Replace with:
```js
async function generateTemplate() {
  const outputEl = document.getElementById("template-output");
  const titleEl = document.getElementById("modal-title");

  titleEl.textContent = "Exported Template";
  outputEl.textContent = "Generating template…";
```

The rest of `generateTemplate()` (the fetch, catch block) is unchanged.

---

### Task 7: Remove the four review display functions from `app.js`

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Delete `reviewSpinnerHtml()`**

Find and delete this entire function:
```js
function reviewSpinnerHtml() {
  return `<div class="review-spinner">
    <div class="spinner"></div>
    <p>Reviewing template quality&hellip;</p>
    <p class="review-hint">Checking objectives against interview guide rules</p>
  </div>`;
}
```

- [ ] **Step 2: Delete `reviewErrorHtml()`**

Find and delete this entire function:
```js
function reviewErrorHtml(msg) {
  return `<div class="review-error">
    <p>Quality review unavailable: ${escHtml(msg)}</p>
    <button class="btn-generate" onclick="generateTemplate()">Generate Anyway &rarr;</button>
  </div>`;
}
```

- [ ] **Step 3: Delete `reviewReportHtml()`**

Find and delete this entire function (lines ~899–921):
```js
function reviewReportHtml(data) {
  const itemIssues = data.item_issues || [];
  const structIssues = data.structural_issues || [];
  const count = itemIssues.length + structIssues.length;
  const sev = ["warning", "error"].includes(data.overall) ? data.overall : "warning";

  let html = `<div class="review-badge ${sev}">&#9888; ${count} issue${count !== 1 ? "s" : ""} found</div>`;

  if (itemIssues.length > 0) {
    html += `<div class="review-section-label">Item issues</div>`;
    itemIssues.forEach(issue => { html += issueCardHtml(issue, true); });
  }
  if (structIssues.length > 0) {
    html += `<div class="review-section-label">Structural</div>`;
    structIssues.forEach(issue => { html += issueCardHtml(issue, false); });
  }

  html += `<div class="review-actions">
    <button class="btn-fix" onclick="closeModal()">&larr; Fix Issues</button>
    <button class="btn-generate" onclick="generateTemplate()">Generate Anyway &rarr;</button>
  </div>`;
  return html;
}
```

- [ ] **Step 4: Delete `issueCardHtml()`**

Find and delete this entire function (lines ~923–941):
```js
function issueCardHtml(issue, isItemIssue) {
  const sev = issue.severity === "error" ? "error" : "warning";
  const loc = isItemIssue
    ? `Topic ${issue.topic_index} &middot; ${escHtml(issue.topic_title)} &middot; ${issue.item_type === "core" ? "Core" : "Probe"} ${issue.item_index + 1}`
    : "";
  const textLine = isItemIssue
    ? `<div class="issue-text">&ldquo;${escHtml(issue.text)}&rdquo;</div>` : "";
  const suggestion = issue.suggestion
    ? `<div class="issue-suggestion"><strong>Suggestion:</strong> ${escHtml(issue.suggestion)}</div>` : "";
  return `<div class="issue-card ${sev}">
    <div class="issue-header">
      <span class="issue-badge ${sev}">${sev === "error" ? "Error" : "Warning"}</span>
      ${loc ? `<span class="issue-loc">${loc}</span>` : ""}
    </div>
    ${textLine}
    <div class="issue-explanation">${escHtml(issue.explanation)}</div>
    ${suggestion}
  </div>`;
}
```

- [ ] **Step 5: Commit all JS changes**

```bash
git add static/app.js
git commit -m "feat: add polishTemplate(), simplify export, remove review display functions"
```

---

### Task 8: Update `index.html`

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1: Replace the export modal HTML**

Find the current modal block (lines ~39–49):
```html
  <div class="modal-overlay hidden" id="modal-overlay" onclick="closeModal()"></div>
  <div class="modal hidden" id="export-modal">
    <div class="modal-header">
      <h2 id="modal-title">Export Template</h2>
      <button class="modal-close" onclick="closeModal()" aria-label="Close">×</button>
    </div>
    <div id="modal-review"></div>
    <div id="modal-template" class="hidden">
      <pre id="template-output"></pre>
      <button class="download-btn" onclick="downloadTemplate()">Download .txt</button>
    </div>
  </div>
```

Replace with (removed `#modal-review` div; removed `class="hidden"` from `#modal-template`):
```html
  <div class="modal-overlay hidden" id="modal-overlay" onclick="closeModal()"></div>
  <div class="modal hidden" id="export-modal">
    <div class="modal-header">
      <h2 id="modal-title">Export Template</h2>
      <button class="modal-close" onclick="closeModal()" aria-label="Close">×</button>
    </div>
    <div id="modal-template">
      <pre id="template-output"></pre>
      <button class="download-btn" onclick="downloadTemplate()">Download .txt</button>
    </div>
  </div>
```

- [ ] **Step 2: Commit**

```bash
git add templates/index.html
git commit -m "feat: remove review panel from export modal HTML"
```

---

### Task 9: Remove review-panel CSS from `style.css`

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Delete the entire `/* Export review panel */` block**

Find the comment `/* Export review panel */` (line 340). Delete from that comment through the last line of the block (`#modal-review { overflow-y: auto; max-height: 55vh; }`, line 398). This removes all of the following rules:

- `/* Export review panel */` (comment)
- `.review-spinner { ... }`
- `.spinner { ... }`
- `@keyframes spin { ... }`
- `.review-hint { ... }`
- `.review-error { ... }`
- `.review-badge { ... }`, `.review-badge.error`, `.review-badge.warning`
- `.review-section-label { ... }`
- `.issue-card { ... }`, `.issue-card.error`, `.issue-card.warning`
- `.issue-header { ... }`
- `.issue-badge { ... }`, `.issue-badge.error`, `.issue-badge.warning`
- `.issue-loc { ... }`
- `.issue-text { ... }`
- `.issue-explanation { ... }`
- `.issue-suggestion { ... }`
- `.review-actions { ... }`
- `.btn-fix { ... }`, `.btn-fix:hover`
- `.btn-generate { ... }`, `.btn-generate:hover`
- `#modal-review { ... }`

The exact block to remove is lines 340–398:
```css
/* Export review panel */
.review-spinner {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 40px 20px; gap: 10px; color: #666;
}
.spinner {
  width: 28px; height: 28px;
  border: 3px solid #e0e0e0; border-top-color: #4f46e5;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.review-hint { font-size: 12px; color: #aaa; }
.review-error { padding: 16px; display: flex; flex-direction: column; gap: 12px; align-items: flex-start; }
.review-badge {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-radius: 6px; margin-bottom: 12px;
  font-weight: 600; font-size: 13px;
}
.review-badge.error { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.review-badge.warning { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.review-section-label {
  font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em;
  color: #aaa; font-weight: 700; margin: 8px 0 5px;
}
.issue-card {
  border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; font-size: 12px;
}
.issue-card.error { background: #fef2f2; border: 1px solid #fecaca; }
.issue-card.warning { background: #fffbeb; border: 1px solid #fde68a; }
.issue-header { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; }
.issue-badge {
  font-size: 10px; padding: 2px 7px; border-radius: 4px;
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; flex-shrink: 0;
}
.issue-badge.error { background: #fecaca; color: #dc2626; }
.issue-badge.warning { background: #fde68a; color: #b45309; }
.issue-loc { font-size: 11px; color: #888; }
.issue-text { color: #444; font-style: italic; margin-bottom: 4px; }
.issue-explanation { color: #555; margin-bottom: 4px; }
.issue-suggestion { color: #15803d; }
.review-actions {
  display: flex; gap: 8px; margin-top: 16px;
  padding-top: 12px; border-top: 1px solid #e0e0e0;
  position: sticky; bottom: 0; background: #fff;
}
.btn-fix {
  flex: 1; padding: 9px; border-radius: 6px;
  border: 1px solid #ddd; background: #fff; color: #555;
  cursor: pointer; font-size: 13px; font-family: inherit;
}
.btn-fix:hover { border-color: #4f46e5; color: #4f46e5; }
.btn-generate {
  flex: 1; padding: 9px; border-radius: 6px; border: none;
  background: #4f46e5; color: #fff;
  cursor: pointer; font-size: 13px; font-weight: 600; font-family: inherit;
}
.btn-generate:hover { background: #3f35c5; }
#modal-review { overflow-y: auto; max-height: 55vh; }
```

After deletion, the file should end with the `.coach-undo:hover` rule group (line ~302) and the drag-reorder styles.

- [ ] **Step 2: Run JS tests to confirm nothing broke**

```bash
node --test tests/duration.test.js
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "chore: remove review-panel CSS (review modal removed)"
```

---

### Task 10: End-to-end smoke test

- [ ] **Step 1: Run all Python tests**

```bash
pytest tests/ -v
```

Expected: all pass, no failures.

- [ ] **Step 2: Start the app**

```bash
python main.py
```

Expected: Flask starts, browser opens at `http://localhost:5000`.

- [ ] **Step 3: Verify export flow**

Click "Export Template" in the browser. Expected:
- Modal opens immediately showing "Generating template…" (no review spinner, no review report)
- After a moment, the formatted template text appears
- "Download .txt" button is visible and works

- [ ] **Step 4: Verify polish runs silently**

Chat with the AI to build a template (or use the existing conversation if fields are already populated). After each AI response completes, watch the template panel — if the AI wrote any compound or yes/no questions, the fields may quietly update a second time as polish applies fixes. No spinner, no toast, no error shown to the user.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: inline auto-polish — silent review+fix after every chat turn"
```

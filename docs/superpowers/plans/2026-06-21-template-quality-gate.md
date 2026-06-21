# Template Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the AI-based export formatter with a deterministic Python function, and add an AI quality reviewer that checks every objective against the interview guide rules before generating the template.

**Architecture:** Two-phase export: Phase 1 calls `POST /review` (AI reviewer using a `submit_review` tool call, returns structured JSON), Phase 2 calls `POST /export` (deterministic `format_template()` function, no Claude). The export modal shows a spinner, then either a quality report or auto-proceeds on pass. The existing file-saving logic in `/export` is unchanged.

**Tech Stack:** Python/Flask (server), Anthropic Python SDK (tool-use for structured review output), vanilla JS (frontend modal states), pytest (formatter unit tests)

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| Delete | `prompts/generation.txt` | Replaced by deterministic formatter |
| Add | `prompts/review.txt` | System prompt for the AI Reviewer |
| Modify | `app.py` | Add `format_template()`, add `REVIEW_TOOL` + `REVIEW_PROMPT`, add `/review` route, update `/export` |
| Modify | `tests/test_tools.py` | Add `format_template` unit tests |
| Modify | `templates/index.html` | Restructure export modal for two-phase flow |
| Modify | `static/app.js` | Two-phase `exportTemplate()`, helper render functions |
| Modify | `static/style.css` | Review panel styles |

---

## Task 1: Deterministic Formatter

**Files:**
- Modify: `app.py` — add `format_template(sections)` and update `/export`
- Modify: `tests/test_tools.py` — add formatter tests
- Delete: `prompts/generation.txt`

- [ ] **Step 1.1: Write the failing formatter tests**

Add these tests to the bottom of `tests/test_tools.py`:

```python
from app import format_template


FULL_SECTIONS = {
    "metadata": {"title": "T", "version": "2.0", "date": "2026-01-01"},
    "pacing": {
        "do_not_rush": "A", "core_vs_probe": "B", "one_ask_per_turn": "C",
        "keep_light": "D", "follow_signals": "E", "original_followups": "F",
        "selective_probing": "G", "finish_line": "H"
    },
    "focus": "Focus text.",
    "topics": [
        {
            "index": 1, "title": "Topic one", "priority": 5,
            "core": [{"text": "Core item.", "priority": 5}],
            "probe": [{"text": "Probe item.", "priority": 2}]
        },
        {
            "index": 2, "title": "Topic two", "priority": 3,
            "core": [{"text": "Core two.", "priority": 3}],
            "probe": []
        }
    ],
    "expansion": ["Exp A", "Exp B"]
}

EXPECTED_FULL = (
    "[Prompt metadata only: T | v2.0 | 2026-01-01]\n"
    "\n"
    "# Pacing Instructions\n"
    "- **Do Not Rush** A\n"
    "\n"
    "- **Core vs. Probe:** B\n"
    "- **One main ask per turn:** C\n"
    "- **Keep questions light:** D\n"
    "\n"
    "- **Follow strong signals:** E\n"
    "- **Original follow-ups allowed:** F\n"
    "- **Selective probing:** G\n"
    "\n"
    "- **The Finish Line** H\n"
    "\n"
    "\n"
    "\n"
    "# Main Interview Guide: T\n"
    "\n"
    "## Interview focus\n"
    "- [Core] Focus text.\n"
    "\n"
    "## Topic 1 [P:5]: Topic one\n"
    "- [Core][P:5] Core item.\n"
    "- [Probe][P:2] Probe item.\n"
    "\n"
    "## Topic 2 [P:3]: Topic two\n"
    "- [Core][P:3] Core two.\n"
    "\n"
    "# Expansion Topics\n"
    "Use these for secondary discovery as instructed\n"
    "- Exp A\n"
    "- Exp B"
)


def test_format_template_full():
    assert format_template(FULL_SECTIONS) == EXPECTED_FULL


def test_format_template_no_focus():
    s = {**FULL_SECTIONS, "focus": ""}
    result = format_template(s)
    assert "## Interview focus" not in result
    assert "- [Core] " not in result
    assert "# Main Interview Guide: T" in result


def test_format_template_no_expansion():
    s = {**FULL_SECTIONS, "expansion": []}
    result = format_template(s)
    assert "# Expansion Topics" not in result


def test_format_template_no_probe_lines():
    """A topic with no probe items must emit no [Probe] lines."""
    result = format_template(FULL_SECTIONS)
    lines = result.splitlines()
    topic2_idx = next(i for i, l in enumerate(lines) if "Topic two" in l)
    # Collect lines belonging to topic 2 (up to next ## or end)
    topic2_lines = []
    for line in lines[topic2_idx + 1:]:
        if line.startswith("## ") or line.startswith("# "):
            break
        topic2_lines.append(line)
    assert not any("[Probe]" in l for l in topic2_lines)


def test_format_template_default_priority():
    """Items missing priority should default to 3."""
    s = {
        **FULL_SECTIONS,
        "topics": [
            {"index": 1, "title": "T", "priority": 3,
             "core": [{"text": "No prio"}], "probe": []}
        ]
    }
    result = format_template(s)
    assert "- [Core][P:3] No prio" in result


def test_format_template_pacing_groups():
    """Verify blank-line grouping: 1 / blank / 3 / blank / 3 / blank / 1 / 3-blanks / heading."""
    result = format_template(FULL_SECTIONS)
    # Three blank lines between The Finish Line and # Main Interview Guide
    assert "- **The Finish Line** H\n\n\n\n# Main Interview Guide" in result
    # One blank line between do_not_rush and core_vs_probe group
    assert "- **Do Not Rush** A\n\n- **Core vs. Probe:**" in result
```

- [ ] **Step 1.2: Run the tests to verify they fail**

```
pytest tests/test_tools.py::test_format_template_full tests/test_tools.py::test_format_template_no_focus tests/test_tools.py::test_format_template_no_expansion tests/test_tools.py::test_format_template_no_probe_lines tests/test_tools.py::test_format_template_default_priority tests/test_tools.py::test_format_template_pacing_groups -v
```

Expected: all 6 FAIL with `ImportError: cannot import name 'format_template'`

- [ ] **Step 1.3: Implement `format_template` in `app.py`**

Add this function to `app.py` after the `_normalise_item` function (around line 162):

```python
def format_template(sections: dict) -> str:
    meta = sections.get("metadata", {})
    title = meta.get("title", "")
    version = meta.get("version", "1.0")
    date = meta.get("date", "")
    pacing = sections.get("pacing", {})
    focus = sections.get("focus", "")
    topics = sections.get("topics", [])
    expansion = sections.get("expansion", [])

    parts = []
    parts.append(f"[Prompt metadata only: {title} | v{version} | {date}]")
    parts.append("")
    parts.append("# Pacing Instructions")
    parts.append(f"- **Do Not Rush** {pacing.get('do_not_rush', '')}")
    parts.append("")
    parts.append(f"- **Core vs. Probe:** {pacing.get('core_vs_probe', '')}")
    parts.append(f"- **One main ask per turn:** {pacing.get('one_ask_per_turn', '')}")
    parts.append(f"- **Keep questions light:** {pacing.get('keep_light', '')}")
    parts.append("")
    parts.append(f"- **Follow strong signals:** {pacing.get('follow_signals', '')}")
    parts.append(f"- **Original follow-ups allowed:** {pacing.get('original_followups', '')}")
    parts.append(f"- **Selective probing:** {pacing.get('selective_probing', '')}")
    parts.append("")
    parts.append(f"- **The Finish Line** {pacing.get('finish_line', '')}")
    parts.append("")
    parts.append("")
    parts.append("")
    parts.append(f"# Main Interview Guide: {title}")
    parts.append("")

    if focus:
        parts.append("## Interview focus")
        parts.append(f"- [Core] {focus}")
        parts.append("")

    for i, topic in enumerate(topics, 1):
        p = topic.get("priority", 3)
        parts.append(f"## Topic {i} [P:{p}]: {topic.get('title', '')}")
        for item in topic.get("core", []):
            ip = item.get("priority", 3) if isinstance(item, dict) else 3
            text = item.get("text", "") if isinstance(item, dict) else item
            parts.append(f"- [Core][P:{ip}] {text}")
        for item in topic.get("probe", []):
            ip = item.get("priority", 3) if isinstance(item, dict) else 3
            text = item.get("text", "") if isinstance(item, dict) else item
            parts.append(f"- [Probe][P:{ip}] {text}")
        parts.append("")

    if expansion:
        parts.append("# Expansion Topics")
        parts.append("Use these for secondary discovery as instructed")
        for item in expansion:
            parts.append(f"- {item}")

    return "\n".join(parts)
```

- [ ] **Step 1.4: Remove the `GENERATION_PROMPT` load from `app.py`**

Delete these three lines near the top of `app.py` (they load the file we just stopped using):

```python
with open(os.path.join(BASE_DIR, "prompts", "generation.txt")) as f:
    GENERATION_PROMPT = f.read()
```

- [ ] **Step 1.5: Update the `/export` route to use `format_template`**

Replace the current `/export` function body in `app.py`. Keep the file-saving logic identical; only remove the Claude call:

```python
@app.route("/export", methods=["POST"])
def export_route():
    sections = request.json["sections"]

    template_text = format_template(sections)

    def safe_str(s, default=""):
        return "".join(c if c.isalnum() or c in " -_" else "" for c in str(s or default)).strip()

    title = sections.get("metadata", {}).get("title", "template")
    version = sections.get("metadata", {}).get("version", "1.0")
    date = sections.get("metadata", {}).get("date", "")
    safe_title = safe_str(title, "template").replace(" ", "-")
    safe_version = safe_str(version, "1.0")
    safe_date = safe_str(date)
    filename = f"{safe_title}-v{safe_version}-{safe_date}.txt"

    output_dir = os.path.join(BASE_DIR, "output")
    os.makedirs(output_dir, exist_ok=True)
    with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
        f.write(template_text)

    return jsonify({"template": template_text, "filename": filename})
```

- [ ] **Step 1.6: Run all formatter tests to verify they pass**

```
pytest tests/test_tools.py::test_format_template_full tests/test_tools.py::test_format_template_no_focus tests/test_tools.py::test_format_template_no_expansion tests/test_tools.py::test_format_template_no_probe_lines tests/test_tools.py::test_format_template_default_priority tests/test_tools.py::test_format_template_pacing_groups -v
```

Expected: all 6 PASS

- [ ] **Step 1.7: Run the full test suite to check for regressions**

```
pytest tests/ -v
```

Expected: all existing tests plus the 6 new ones PASS

- [ ] **Step 1.8: Delete `prompts/generation.txt`**

```
git rm prompts/generation.txt
```

- [ ] **Step 1.9: Commit**

```
git add app.py tests/test_tools.py
git commit -m "feat: replace AI formatter with deterministic format_template(); remove generation.txt"
```

---

## Task 2: AI Reviewer Prompt and Route

**Files:**
- Create: `prompts/review.txt`
- Modify: `app.py` — add `REVIEW_PROMPT`, `REVIEW_TOOL`, and `POST /review` route

- [ ] **Step 2.1: Create `prompts/review.txt`**

Create `prompts/review.txt` with this exact content:

```
You are a quality reviewer for qualitative interview guide templates.

Your only output is to call the submit_review tool with your complete findings. Do not write any text — only call the tool.

## Objective-writing rules (checked per core/probe item)

Check every core and probe item in every topic. For each violation, add an entry to item_issues.

### compound_ask (severity: error)
The item joins two distinct objectives with "and". Each item must contain exactly one ask.
Bad: "Explore what the participant bought and determine if they'll return"
Good: "Explore what the participant bought on this visit"

### diagnostic_verb (severity: error)
The item uses one of: determine / assess / evaluate / confirm / verify / identify whether.
These verbs collapse open questions into yes/no dead-ends.
Use instead: explore / capture / walk through / surface / trace / draw out / understand how / understand why.
Bad: "Determine whether the participant was satisfied with checkout"
Good: "Explore how the checkout experience unfolded from start to finish"

### assumed_experience (severity: error)
The item assumes an emotion, event, or outcome occurred. Frame conditionally.
Bad: "Understand why checkout was frustrating" (assumes frustration happened)
Good: "Explore how checkout unfolded and how the participant felt about it"

### vague_specificity (severity: warning)
The item names no concrete thing. "Their experience" or "their thoughts" alone is contentless.
Bad: "Understand their overall experience in the store"
Good: "Walk through how the participant navigated to find the items they came for"

### probe_restates_core (severity: warning)
A probe that adds no new direction. A probe must add something new: a sensory detail, a specific example, the "why", a contrast, or a deeper dimension not present in the core.
Bad core: "Walk through how checkout unfolded" / Bad probe: "Ask about the checkout process"
Good probe: "Capture any specific moment in the queue that stood out — and what made it stand out"

## Structural checks (add to structural_issues)

### missing_probe (severity: error)
A topic has zero probe items. The interviewer has no depth tool if the participant gives a thin answer. Name the specific topic in the explanation.

### topic_overlap (severity: warning)
Two topics target the same underlying thing. Name both topics in the explanation.

### wrong_topic_order (severity: warning)
A sensitive or emotionally loaded topic appears before concrete, easy warm-up topics. Interview guides should funnel from easy/concrete to sensitive/evaluative to reflective.

### focus_is_goal (severity: error)
The focus statement is written as a research goal ("understand what drives X") rather than an experience anchor ("the participant's most recent [event], anchored on [specific occasion]"). A focus anchor names a real occasion; a research goal names what the researcher wants to discover.
Bad: "Understand what drives loyalty to the store"
Good: "The participant's most recent visit to the store, anchored on that specific occasion"

### priority_spread (severity: warning)
All topics or all items share the same priority value. Mention the specific value observed. Priorities should discriminate: 5 = must cover in every interview, 1 = rarely needed.

### topic_count (severity: warning)
Fewer than 4 or more than 9 topics in the main guide.

### expansion_missing (severity: warning)
Fewer than 2 expansion topics. The interviewer needs options to fill time if the main guide finishes early.

## Severity rules

- overall = "error": one or more issues have severity "error"
- overall = "warning": issues exist but none have severity "error"
- overall = "pass": item_issues and structural_issues are both empty

Call submit_review now with your complete findings.
```

- [ ] **Step 2.2: Load `review.txt` and add `REVIEW_TOOL` + `REVIEW_PROMPT` to `app.py`**

Add the following after the `GATHERING_PROMPT` load block at the top of `app.py` (after the `with open(... gathering.txt)` block). This is where `GENERATION_PROMPT` used to be loaded:

```python
with open(os.path.join(BASE_DIR, "prompts", "review.txt")) as f:
    REVIEW_PROMPT = f.read()
```

Then add the tool definition after `GATHERING_TOOLS` (around line 123):

```python
REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit the quality review findings for the interview template.",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall": {
                "type": "string",
                "enum": ["pass", "warning", "error"]
            },
            "item_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_index": {"type": "integer"},
                        "topic_title": {"type": "string"},
                        "item_type": {"type": "string", "enum": ["core", "probe"]},
                        "item_index": {"type": "integer"},
                        "text": {"type": "string"},
                        "rule": {"type": "string"},
                        "severity": {"type": "string", "enum": ["error", "warning"]},
                        "explanation": {"type": "string"},
                        "suggestion": {"type": "string"}
                    },
                    "required": ["topic_index", "topic_title", "item_type",
                                 "item_index", "text", "rule", "severity", "explanation"]
                }
            },
            "structural_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule": {"type": "string"},
                        "severity": {"type": "string", "enum": ["error", "warning"]},
                        "explanation": {"type": "string"}
                    },
                    "required": ["rule", "severity", "explanation"]
                }
            }
        },
        "required": ["overall", "item_issues", "structural_issues"]
    }
}
```

- [ ] **Step 2.3: Add the `/review` route to `app.py`**

Add this route after the `/reset` route (around line 287):

```python
@app.route("/review", methods=["POST"])
def review_route():
    sections = request.json["sections"]
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
        return jsonify({"overall": "pass", "item_issues": [], "structural_issues": []})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
```

- [ ] **Step 2.4: Run the existing test suite to verify nothing is broken**

```
pytest tests/ -v
```

Expected: all tests PASS (the new route is not covered by unit tests — it wraps the API and is verified by running the app)

- [ ] **Step 2.5: Commit**

```
git add prompts/review.txt app.py
git commit -m "feat: add AI reviewer prompt and POST /review route with submit_review tool"
```

---

## Task 3: Frontend Two-Phase Export Modal

**Files:**
- Modify: `templates/index.html` — restructure export modal
- Modify: `static/app.js` — two-phase `exportTemplate()`, helper render functions
- Modify: `static/style.css` — review panel styles

- [ ] **Step 3.1: Update the export modal in `templates/index.html`**

Replace the current modal block (lines 38–46) with:

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

- [ ] **Step 3.2: Replace `exportTemplate()` in `static/app.js` and add helper functions**

Find `exportTemplate()` in `static/app.js` (around line 847) and replace the entire function with the following block. Also add the four helper functions immediately after it:

```javascript
async function exportTemplate() {
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");
  const reviewEl = document.getElementById("modal-review");
  const templateEl = document.getElementById("modal-template");

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
    reviewEl.innerHTML = reviewErrorHtml(escHtml(err.message));
    return;
  }

  if (reviewData.overall === "pass") {
    await generateTemplate();
  } else {
    reviewEl.innerHTML = reviewReportHtml(reviewData);
  }
}

function reviewSpinnerHtml() {
  return `<div class="review-spinner">
    <div class="spinner"></div>
    <p>Reviewing template quality&hellip;</p>
    <p class="review-hint">Checking objectives against interview guide rules</p>
  </div>`;
}

function reviewErrorHtml(msg) {
  return `<div class="review-error">
    <p>Quality review unavailable: ${msg}</p>
    <button class="btn-generate" onclick="generateTemplate()">Generate Anyway &rarr;</button>
  </div>`;
}

function reviewReportHtml(data) {
  const itemIssues = data.item_issues || [];
  const structIssues = data.structural_issues || [];
  const count = itemIssues.length + structIssues.length;
  const sev = data.overall;

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

function issueCardHtml(issue, isItemIssue) {
  const sev = issue.severity;
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

async function generateTemplate() {
  const reviewEl = document.getElementById("modal-review");
  const templateEl = document.getElementById("modal-template");
  const outputEl = document.getElementById("template-output");

  reviewEl.classList.add("hidden");
  templateEl.classList.remove("hidden");
  outputEl.textContent = "Generating template…";

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
```

- [ ] **Step 3.3: Add review panel styles to `static/style.css`**

Append to the end of `static/style.css`:

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

- [ ] **Step 3.4: Run the app and verify the full export flow manually**

```
python main.py
```

1. Type a research topic in the chat and let the AI populate the template.
2. Click **Export Template**.
3. Verify State 1: spinner shows with "Reviewing template quality…"
4. If the template has issues: verify State 2a — issue cards appear with Fix Issues / Generate Anyway buttons.
5. Click **Generate Anyway** → verify the template text appears correctly.
6. Close the modal and fix one issue in the template panel, then export again.
7. If the template is clean: verify State 2b — "All checks passed" auto-proceeds to template text.
8. Verify the downloaded `.txt` file content is identical to what's shown in the modal.

- [ ] **Step 3.5: Run the full test suite one final time**

```
pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 3.6: Commit**

```
git add templates/index.html static/app.js static/style.css
git commit -m "feat: two-phase export modal — AI quality review then deterministic generation"
```

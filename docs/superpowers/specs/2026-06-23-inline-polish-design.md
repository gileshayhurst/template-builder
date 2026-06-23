# Inline Auto-Polish — Design Spec
**Date:** 2026-06-23

## Problem

The quality review gate lives at export time. Users must explicitly trigger it, and the resulting issues modal blocks them from getting the template. The review finding suggestions are displayed but never automatically applied — the user has to fix issues manually or click "Generate Anyway."

## Goal

Move quality improvement into the conversation loop so the template is silently kept clean after every AI response. Export becomes a direct, no-friction action.

---

## Architecture

### New flow (per turn)

```
User message → POST /chat (SSE)
  → gathering agent fills fields
  → done event
      → frontend calls POST /polish (fire-and-forget, fully silent)
          → server: run review internally
          → if item_issues with suggestions exist: run fixer agent
          → return {updates: [...section_update payloads]}
      → frontend calls applyUpdate() for each update silently

User clicks Export Template
  → modal opens → POST /export → show template → download
  (no review gate)
```

### What changes

| Area | Change |
|---|---|
| `app.py` | Add `POST /polish` route; extract `_run_review()` helper; add `_run_fixer()` helper; add `FIXER_PROMPT` constant; keep `REVIEW_TOOL` as internal constant; remove `POST /review` route |
| `prompts/fixer.txt` | New system prompt for the fixer agent |
| `static/app.js` | After `done` SSE event, call `polishTemplate()` silently; simplify `exportTemplate()` to open modal and call `generateTemplate()` directly; remove `reviewSpinnerHtml`, `reviewReportHtml`, `reviewErrorHtml`, `issueCardHtml` functions |
| `templates/index.html` | Remove `<div id="modal-review">` |
| `static/style.css` | Remove all review-panel styles (review-spinner, review-badge, review-section-label, issue-card, issue-header, issue-badge, issue-loc, issue-text, issue-explanation, issue-suggestion, btn-fix, review-actions, review-error, review-hint, #modal-review rule) |

---

## Server: `/polish` endpoint

```python
POST /polish
Body: { "sections": { ...state.sections... } }
Response: { "updates": [ {section, payload}, ... ] }
```

Steps:
1. Call `_run_review(sections)` — reuses existing review logic, returns structured findings.
2. Filter to `item_issues` that have a non-empty `suggestion` field.
3. If no fixable issues, return `{"updates": []}` immediately.
4. Call `_run_fixer(sections, fixable_issues)` — returns a list of `{section, payload}` dicts.
5. Return `{"updates": updates}`.

Both helpers wrap their Anthropic calls in try/except and raise on failure; the route catches and returns `{"updates": []}` (fail-open — a polish failure never blocks the user).

---

## Fixer agent

**Scope:** item-level rewording only. The fixer agent may only call `add_topic` (a subset of the gathering tools). It must not add or remove topics, change metadata, pacing, focus, or expansion.

**Input to the agent:**
- System prompt from `prompts/fixer.txt`
- Single user message containing the full sections JSON and the list of flagged item issues with their suggestions

**Behavior:**
- For each affected topic, call `add_topic` with the full topic — all items preserved exactly — except the flagged items are rewritten per their suggestions.
- Only topics containing flagged items are touched.
- If a suggestion cannot be applied sensibly, the item is left unchanged.

**Tool:** `add_topic` only (no other gathering tools supplied).

**Call style:** non-streaming, `tool_choice={"type": "auto"}`, single-turn (no conversation history). Max tokens: 2048.

---

## Frontend: `polishTemplate()`

Called automatically after the SSE `done` event. Silent — no spinner, no toast.

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

`applyUpdate()` already handles all section types; no changes needed there.

`generateTemplate()` currently references `reviewEl` (to hide it) and `templateEl` (to un-hide it). With `#modal-review` removed and `#modal-template` no longer starting hidden, both of those lines must be removed from `generateTemplate()`.

---

## Frontend: Export simplification

`exportTemplate()` loses the review phase entirely. The button opens the modal and generates the template directly:

```js
async function exportTemplate() {
  const modal = document.getElementById("export-modal");
  const overlay = document.getElementById("modal-overlay");
  modal.classList.remove("hidden");
  overlay.classList.remove("hidden");
  await generateTemplate();
}
```

`generateTemplate()` is unchanged — it shows the spinner, calls `/export`, and renders the result.

The four review-display functions (`reviewSpinnerHtml`, `reviewReportHtml`, `reviewErrorHtml`, `issueCardHtml`) are removed.

---

## HTML simplification

`#modal-review` div is removed from `index.html`. The modal structure becomes:

```html
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

Note: `#modal-template` no longer starts hidden (no review panel to hide it behind), so its `class="hidden"` is removed and `generateTemplate()` no longer needs to toggle it.

---

## Error handling

- `/polish` fails (network, API, timeout): silently swallowed in frontend catch block. Template is unchanged. No user-visible effect.
- Review finds no fixable item issues: returns `{updates: []}` immediately, no fixer call.
- Fixer agent returns no tool calls: `_run_fixer` returns `[]`. `/polish` returns `{updates: []}`.
- `/export` is unaffected by polish — they are independent paths.

---

## What is removed

- `POST /review` HTTP route in `app.py`
- `reviewSpinnerHtml()`, `reviewReportHtml()`, `reviewErrorHtml()`, `issueCardHtml()` in `app.js`
- Review-phase logic in `exportTemplate()` (first ~30 lines)
- `#modal-review` div in `index.html`
- All review-panel CSS rules in `style.css`

`REVIEW_PROMPT` constant and `prompts/review.txt` are **kept** — still loaded by `app.py` for the internal `_run_review()` helper inside `/polish`.

---

## Testing

Existing `pytest tests/test_tools.py` covers `process_tool_call()` — unaffected.

Manual verification:
1. Build a template with the AI, check that fields silently improve after each turn
2. Export goes straight to template with no review gate
3. Close and reopen export modal works
4. Polish failure (e.g., bad API key) does not surface an error to the user

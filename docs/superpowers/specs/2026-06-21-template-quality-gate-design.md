# Template Quality Gate — Design Spec
**Date:** 2026-06-21

## Problem

The export step currently uses an AI call (`prompts/generation.txt`) to format the sections JSON into the final template text. This is an unnecessary risk: the format is fully specified and mechanical, yet an AI could silently alter wording, drop a topic, or restate an objective differently. There is also no quality gate — a template with compound asks, diagnostic verbs, or flat priorities can be exported to the interview agent without any check.

## Goal

Make the exported template reliable by:
1. Replacing the AI-based formatter with a deterministic Python function.
2. Adding an AI Quality Reviewer that checks every objective against the objective-writing rules before the template is generated.

## Scope

This spec covers only the export pipeline. It does not add live in-conversation hints or change the gathering prompt.

---

## Architecture

### Current pipeline

```
User clicks Export
  → POST /export
  → Claude call (generation.txt): formats JSON → template text
  → modal shows template text
```

### New pipeline

```
User clicks Export
  → POST /review
  → Phase 1: AI Reviewer (review.txt) → structured quality report (JSON)
  → modal shows quality report; user fixes or proceeds
  → Phase 2: POST /export → format_template(sections) → template text
  → modal shows template text + download button
```

If `overall == "pass"`, Phase 2 begins automatically with no extra user action.

---

## Codebase Changes

| Action | File |
|---|---|
| Remove | `prompts/generation.txt` |
| Remove | Claude call inside `POST /export` in `app.py` |
| Add | `prompts/review.txt` — AI Reviewer system prompt |
| Add | `format_template(sections)` function in `app.py` |
| Add | `POST /review` route in `app.py` |
| Update | `POST /export` — calls `format_template()` only, no Claude |
| Add | formatter tests in `tests/test_tools.py` |
| Update | `static/app.js` — two-phase export modal flow |

---

## The Deterministic Formatter

### Function signature

```python
def format_template(sections: dict) -> str:
```

Takes `state.sections` as received by the `/export` route. Returns the complete template string.

### Output format

Follows the exact syntax previously defined in `generation.txt`:

```
[Prompt metadata only: TITLE | vVERSION | DATE]

# Pacing Instructions
- **Do Not Rush** {do_not_rush}

- **Core vs. Probe:** {core_vs_probe}
- **One main ask per turn:** {one_ask_per_turn}
- **Keep questions light:** {keep_light}

- **Follow strong signals:** {follow_signals}
- **Original follow-ups allowed:** {original_followups}
- **Selective probing:** {selective_probing}

- **The Finish Line** {finish_line}



# Main Interview Guide: TITLE

## Interview focus
- [Core] FOCUS_TEXT

## Topic N [P:N]: TOPIC_TITLE
- [Core][P:N] CORE_ITEM
- [Probe][P:N] PROBE_ITEM

# Expansion Topics
Use these for secondary discovery as instructed
- ITEM
```

Rules hardcoded in the formatter (not inferred):
- Pacing rules appear in groups: 1 / 3 / 3 / 1, with blank lines between groups.
- Two blank lines between the last pacing rule and `# Main Interview Guide`.
- `[Core][P:N]` prefix on every core item; `[Probe][P:N]` on every probe item.
- `[Core]` with no priority tag on the focus line.
- Topic heading: `## Topic N [P:N]: TITLE` (1-based index, topic's priority value).

### Edge cases

| Condition | Behaviour |
|---|---|
| Topic has no probe items | Omit all `[Probe]` lines for that topic |
| Focus is empty string | Omit the "Interview focus" block entirely |
| No expansion topics | Omit the "# Expansion Topics" block entirely |
| Item priority missing | Default to 3 (matches existing `_normalise_item` logic) |

### Testing

New pytest cases in `tests/test_tools.py`. Given a `sections` dict, assert the exact string output character-by-character. No API key required; `format_template` is a pure function.

---

## The AI Reviewer

### System prompt (`prompts/review.txt`)

Instructs Claude to call a single tool — `submit_review` — with a structured payload. Using a tool call (rather than asking for JSON in free text) guarantees valid, schema-conforming output with no parsing risk.

The prompt includes:
- The complete list of checks (see below).
- A worked example of a flagged item with a good vs. bad objective.
- An instruction to set `overall` to `"pass"` only when there are zero issues.

### What the reviewer checks

**Per-item checks** (applied to every core and probe objective):

| Rule code | What it catches |
|---|---|
| `compound_ask` | "and" joining two distinct objectives in one item |
| `diagnostic_verb` | determine / assess / evaluate / confirm / verify / identify whether |
| `assumed_experience` | emotion or event assumed to have occurred (e.g. "why checkout was frustrating") |
| `vague_specificity` | contentless phrasing — "their experience" or "their thoughts" with nothing specific named |

**Per-topic checks:**

| Rule code | What it catches |
|---|---|
| `probe_restates_core` | A probe that adds no new direction — is effectively a reworded core |
| `missing_probe` | A topic with no probe at all |

**Structural checks** (holistic, across the whole template):

| Rule code | What it catches |
|---|---|
| `topic_overlap` | Two topics targeting the same underlying thing |
| `wrong_topic_order` | Sensitive or evaluative topic placed before concrete warm-up topics |
| `focus_is_goal` | Focus written as a research goal ("understand loyalty drivers") not an experience anchor |
| `priority_spread` | All topics or all items at the same priority (flat distribution gives no triage signal) |
| `topic_count` | Fewer than 4 or more than 9 topics |
| `expansion_missing` | Expansion topic list empty or has fewer than 2 items |

### Structured response

The `submit_review` tool schema:

```json
{
  "overall": "pass" | "warning" | "error",
  "item_issues": [
    {
      "topic_index": <int>,
      "topic_title": <string>,
      "item_type": "core" | "probe",
      "item_index": <int>,
      "text": <the objective text>,
      "rule": <rule code>,
      "severity": "error" | "warning",
      "explanation": <one sentence>,
      "suggestion": <rewritten objective>
    }
  ],
  "structural_issues": [
    {
      "rule": <rule code>,
      "severity": "error" | "warning",
      "explanation": <one sentence>
    }
  ]
}
```

`overall` is `"error"` if any issue has `severity == "error"`, `"warning"` if only warnings, `"pass"` if the lists are both empty.

### `/review` route

```python
@app.route("/review", methods=["POST"])
def review_route():
    sections = request.json["sections"]
    # Claude call with review.txt + submit_review tool
    # Extract tool_use.input directly — no JSON parsing from free text
    return jsonify(review_data)
```

---

## UX — Export Modal

### State 1: Review running

Modal opens immediately. Shows a spinner and the text "Reviewing template quality…".

### State 2a: Issues found (`overall == "warning"` or `"error"`)

Shows a summary badge ("N issues found"), then two lists:

- **Item issues** — each card shows: severity badge (Error / Warning in red / amber), topic + item location, the verbatim objective text in italics, the rule explanation, and a suggested rewrite.
- **Structural issues** — each card shows: severity badge, rule explanation.

Two buttons:
- **"← Fix Issues"** — closes the modal, returns user to the template panel to edit.
- **"Generate Anyway →"** — proceeds to Phase 2 (the formatter) without fixing. Available even for errors, since the user may disagree with a flag.

### State 2b: All clear (`overall == "pass"`)

Shows "✓ All checks passed" and auto-proceeds to Phase 2 with no extra click.

### State 3: Template text

Same as today — template text rendered in the modal, download button available.

### Error handling

If the `/review` API call fails (network error, API error), show a warning banner in the modal ("Quality review unavailable") with a "Generate Anyway" button. Do not block export on reviewer failure.

---

## Out of Scope

- Live objective quality hints during the gathering conversation.
- Changes to `prompts/gathering.txt`.
- Auto-fixing issues on the user's behalf.
- Blocking export on error-level issues (user can always override).

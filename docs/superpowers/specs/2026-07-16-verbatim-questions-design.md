# Verbatim Questions — Design Spec
**Date:** 2026-07-16

## Problem

The Golden Child templates pinned certain questions **verbatim** — the "busy
day" projective prompt, the "sauces or drizzles" concept choice — and those
appeared near-word-for-word in every transcript, while described objectives got
paraphrased. Those are **stimulus questions where the wording *is* the
instrument**: in concept / message / claim testing, if the interviewer rewords
the stimulus differently each interview, that variance is measurement noise and
comparability is lost.

Our builder forbids literal question wording entirely (`gathering.txt` rule 6,
"Instructions, not scripts"). That rule is correct *for AI-generated
objectives* — it forces good objective-writing and prevents robotic
interviewing. But it leaves no way to pin the handful of questions where exact
wording matters.

## Goal

A dedicated, **user-authored** section where the user types exact questions/lines
to be asked word-for-word. The AI never writes or proposes them; the reviewer
never checks them. The "no scripts" discipline stays fully intact for
AI-generated objectives — this is a separate, deliberate human override.

## Decisions (from brainstorming)

- **User-authored only.** The AI does not propose, write, or edit verbatim
  questions. No tool, no SSE writes. (This replaced an earlier "AI proposes,
  user confirms" direction.)
- **Its own section, not a per-item flag.** Because it's a separate list, no
  item-schema change and no reviewer/objective-rule exemption logic is
  needed — the "no scripts" rule is untouched.
- **Woven in naturally.** The export instructs the interviewer to ask each one
  word-for-word at a natural point during the interview (not anchored to a
  topic, not clustered at the close). Matches how the golden-set interviewer
  folded quoted questions into the flow.

## Non-goals

- AI awareness of the list (no de-duplication against objectives). The user owns
  the field; a verbatim line that overlaps an objective is the user's choice.
- Anchoring lines to specific topics, or wiring them into the time-pressure
  backstop. Possible later; not needed for v1.
- The last deferred thread (short-interview ordering).

---

## Architecture

Mirrors the existing `expansion` section (a user-editable line list) — minus the
AI tool that writes `expansion`.

| Area | Change |
|---|---|
| `static/app.js` — initial state | Add `verbatim: []` to `state.sections`. |
| `static/app.js` — rendering | New `renderVerbatimSection()` (textarea, one line per question, `oninput` → `state.sections.verbatim`), mirroring the Expansion Topics panel. Call it from `renderTemplate()`, placed after Topics and before Expansion. |
| `app.py` — `format_template` | If `verbatim` non-empty, emit a "Verbatim Questions" block after the Interview focus, before the topics. |
| `tests/test_tools.py` | `format_template` emits the block (quoted lines + instruction) when present; omits it when absent/empty. |

**Untouched:** item schema, `add_topic`/`_normalise_item`, `GATHERING_TOOLS`
(no new tool), `gathering.txt`, `review.txt` and the review route,
`build_settings_context` (the AI is fed UI settings, not sections, so it never
sees this field). No new pacing rule.

---

## The section

### State

`state.sections.verbatim` — an array of strings, initialized `[]`. Populated
only by the user via the panel textarea. Flows to `/export` in the
client-posted `sections` body (export already reads `body.get("sections")`), and
into `format_template`.

### Panel (`static/app.js`)

Direct copy of the Expansion Topics pattern (`app.js:887–894`) — a textarea whose
`oninput` splits on newlines, trims, and drops blank lines:

```js
function renderVerbatimSection() {
  const joined = state.sections.verbatim.join("\n");
  const body = document.createElement("div");
  body.innerHTML =
    `<p class="section-hint">Exact lines to ask word-for-word, woven in naturally. You author these — the assistant never edits them.</p>
     <textarea class="expansion-textarea" rows="4" aria-label="Verbatim questions, one per line"
       oninput="state.sections.verbatim = this.value.split('\\n').map(s=>s.trim()).filter(Boolean)">${escHtml(joined)}</textarea>`;
  return sectionBlock("section-verbatim", "Verbatim Questions", body, "verbatim");
}
```

Called from `renderTemplate()` between the Topics and Expansion blocks. Reuses
the existing `.expansion-textarea` style and `sectionBlock` collapse framework
(collapse key `section-verbatim`), so no new CSS is required. The `section-hint`
class already exists in the stylesheet; if not, it falls back to unstyled text
(acceptable — a follow-up can style it).

### Export block (`app.py`, `format_template`)

Inserted immediately after the `focus` block (so the interviewer reads it before
the topics), guarded like `expansion`:

```python
    verbatim = sections.get("verbatim", [])
    # ... after the focus block, before the topics loop:
    if verbatim:
        parts.append("## Verbatim Questions")
        parts.append("Ask each of the following word-for-word, at a natural point in the interview. Do not paraphrase or reword them.")
        for line in verbatim:
            parts.append(f'- "{line}"')
        parts.append("")
```

Each line is wrapped in quotes to signal "say this literally" (the same cue the
golden templates used). Empty/whitespace lines never reach here — the panel
filters them — but the `if verbatim` guard also means an empty list emits
nothing, leaving existing exports byte-identical.

Add `verbatim = sections.get("verbatim", [])` alongside the other
`sections.get(...)` reads near the top of `format_template`.

---

## Data flow

1. User types lines into the Verbatim Questions textarea → `oninput` updates
   `state.sections.verbatim`.
2. Export → the client POSTs `state.sections` (now including `verbatim`) to
   `/export` → `format_template` emits the block.
3. The exported guide hands the block to the downstream interviewer agent, which
   asks each line verbatim.

No AI round-trip, no SSE, no server-side state — consistent with `/export` being
a pure, deterministic formatter.

## Edge cases

- **Blank lines** — filtered at input (`.filter(Boolean)`) and guarded at export
  (`if verbatim`).
- **Empty list** — no block emitted; existing exports unchanged (protects the
  `format_template` golden tests).
- **Lines containing a double-quote** — not escaped; rendered as-is inside the
  wrapping quotes. Acceptable for a human-read research guide; note only.
- **Reset / page load** — `verbatim` initializes to `[]` in frontend state like
  the other sections; nothing server-side to clear.

## Testing (`tests/test_tools.py`)

```python
def test_format_template_emits_verbatim_block():
    sections = {
        "metadata": {"title": "T", "version": "1.0", "date": "2026-01-01"},
        "focus": "the participant's most recent visit",
        "topics": [],
        "verbatim": ["Think of a busy day. How did you cope?", "Which would you try first, and why?"],
    }
    out = format_template(sections)
    assert "## Verbatim Questions" in out
    assert "word-for-word" in out
    assert '- "Think of a busy day. How did you cope?"' in out
    # Sits after the Interview focus (and thus before the topics loop)
    assert out.index("## Interview focus") < out.index("## Verbatim Questions")

def test_format_template_omits_empty_verbatim():
    sections = {"metadata": {"title": "T"}, "topics": [], "verbatim": []}
    assert "Verbatim Questions" not in format_template(sections)

def test_format_template_no_verbatim_key_unchanged():
    # A sections dict without the key behaves exactly as before.
    sections = {"metadata": {"title": "T"}, "topics": []}
    assert "Verbatim Questions" not in format_template(sections)
```

The existing `format_template` golden tests (`tests/test_tools.py`) have no
`verbatim` key, so they stay green unchanged.

## Build phases

1. **Export** — add the `verbatim` read + block to `format_template`; add the
   three `test_tools.py` tests. Pure Python + tests, green suite.
2. **Panel** — add `verbatim: []` to initial state; add
   `renderVerbatimSection()` and wire it into `renderTemplate()`. Verify in the
   browser: type lines, export, confirm the block appears and reorder/other
   sections are unaffected.

## What is unchanged

- The "no scripts" rule for AI objectives, `review.txt`, the review route.
- `GATHERING_TOOLS`, `process_tool_call`, item schema, `gathering.txt`.
- `build_settings_context` (AI stays unaware of the field).
- The ordering and coverage-guarantee features.

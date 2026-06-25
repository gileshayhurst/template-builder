# Voice-First Objective Checks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two voice-safety checks — `requires_visual_stimulus` (error) and `enumeration_or_ranking` (warning) — to the template-quality system, since the downstream interview agent is voice-only.

**Architecture:** Prompt + test change only. Prevention rules go in `prompts/gathering.txt` (followed by the builder AI live); detection checks go in `prompts/review.txt` (the independent export gate). Both prompts are plain text consumed by the Anthropic API at runtime; they are verified by substring-assertion tests, matching the existing `tests/test_gathering_prompt.py` pattern. No `app.py`, `app.js`, tool-schema, or UI changes — the review tool's `rule` field is already a free-form string and the frontend renders issues generically.

**Tech Stack:** Python prompt text files, `pytest` for content assertions.

---

## Context for the implementer (read first)

- The two prompts live at `prompts/gathering.txt` and `prompts/review.txt` (relative to repo root `C:\Users\giles\Downloads\Template`).
- Run Python tests with `python -m pytest tests/ -q`. No API key needed — these are pure text-content tests.
- Baseline is green: `46 passed` before you start. Every commit must keep all tests passing.
- The design spec is `docs/superpowers/specs/2026-06-24-voice-first-objective-checks-design.md`.
- **Do not** touch the duration JS, `app.py`, `app.js`, or expansion-topic logic — all out of scope.
- Edits are additive. Use exact string matching; the anchor strings below already exist in the files.

---

## Task 1: Voice-safety prevention rules in `gathering.txt`

**Files:**
- Modify: `prompts/gathering.txt`
- Test: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Write the failing tests**

Append these three tests to the end of `tests/test_gathering_prompt.py`:

```python
def test_prompt_has_voiceability_rule():
    text = _prompt_text()
    assert "voiceable by ear" in text
    assert "there is no screen" in text


def test_prompt_anti_patterns_include_visual_and_enumeration():
    text = _prompt_text()
    assert "no screen in a voice call" in text
    assert "draw items out one at a time through narrative" in text


def test_prompt_consolidation_gate_has_voice_check():
    assert "answerable by voice alone" in _prompt_text()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_gathering_prompt.py -q`
Expected: 3 failures (`AssertionError`) — the new substrings are not in the prompt yet. All pre-existing tests still pass.

- [ ] **Step 3: Add rule 7 to the "Writing objectives" list**

In `prompts/gathering.txt`, find the heading line:

```
## Writing objectives (the core craft)
Each core/probe item is an OBJECTIVE: an instruction telling the interviewer what to accomplish — never a literal question to read aloud. Nine rules:
```

Change `Nine rules:` to `Ten rules:` on that line.

Then find rule 6, which reads:

```
6. Instructions, not scripts. Never write the literal question wording; the interviewer phrases the actual question.
```

Add a new line immediately after it:

```
7. Voiceable by ear. Every objective must be answerable in spoken conversation with no screen. Never require the participant to look at, react to, or choose among visual stimuli (images, layouts, designs, colours, logos, on-screen options) — there is no screen. Never require them to list or rank items from memory aloud; ask for one thing at a time and let narrative surface the rest.
```

- [ ] **Step 4: Add two rows to the anti-pattern table**

Find the "Anti-patterns (never ship these)" table. Its last row is:

```
| "how does X compare to Y" | participant does analysis, not recall | anchor on a specific occasion when the contrast was felt |
```

Add these two rows immediately after it:

```
| "react to / look at" a visual | no screen in a voice call | anchor on a remembered moment, not a shown stimulus |
| "rank / list all the X" | hard to do by ear, forces thin data | draw items out one at a time through narrative |
```

- [ ] **Step 5: Add a checkbox to the Consolidation Gate**

Find the Consolidation Gate checklist. Its last checkbox item is:

```
- [ ] Expansion topics populated (4–6 items); each is distinct from main topics and plausible as a secondary direction
```

Add this checkbox immediately after it:

```
- [ ] Every objective is answerable by voice alone — no visual stimulus, no list/ranking from memory
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `python -m pytest tests/test_gathering_prompt.py -q`
Expected: PASS (all tests in the file, including the 3 new ones).

- [ ] **Step 7: Run the full suite to confirm no regression**

Run: `python -m pytest tests/ -q`
Expected: all pass (49 total).

- [ ] **Step 8: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "feat: add voice-safety prevention rules to gathering prompt"
```

---

## Task 2: Voice-safety detection checks in `review.txt`

**Files:**
- Modify: `prompts/review.txt`
- Test (create): `tests/test_review_prompt.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_review_prompt.py` with this exact content:

```python
import os

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "review.txt"
)


def _prompt_text():
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().lower()


def test_review_has_visual_stimulus_check():
    text = _prompt_text()
    assert "requires_visual_stimulus (severity: error)" in text


def test_review_has_enumeration_check():
    text = _prompt_text()
    assert "enumeration_or_ranking (severity: warning)" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_review_prompt.py -q`
Expected: 2 failures (`AssertionError`) — the check headers are not in the prompt yet.

- [ ] **Step 3: Add the two check blocks to `review.txt`**

In `prompts/review.txt`, find the existing `### probe_restates_core (severity: warning)` block. It ends just before the line:

```
## Structural checks (add to structural_issues)
```

Insert the following two blocks immediately before that `## Structural checks` line (keep a blank line above and below):

```
### requires_visual_stimulus (severity: error)
The item requires the participant to see, look at, react to, or choose among something visual (an image, screen, layout, design, colour, logo, or on-screen option). The interview is voice-only — there is no screen, so the agent cannot execute this.
Bad: "Explore the participant's reaction to the homepage layout"
Good: "Trace a recent moment the participant tried to find something on the site and what happened"

### enumeration_or_ranking (severity: warning)
The item asks the participant to list many items, or rank/order items, from memory and aloud. By ear this overloads recall and forces thin, artificial answers. Draw items out one at a time through narrative instead.
Bad: "Have the participant rank the five factors that matter most when choosing a brand"
Good: "Surface what mattered most the last time the participant chose a brand, and why"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_review_prompt.py -q`
Expected: PASS (2 tests).

- [ ] **Step 5: Run the full suite to confirm no regression**

Run: `python -m pytest tests/ -q`
Expected: all pass (51 total).

- [ ] **Step 6: Commit**

```bash
git add prompts/review.txt tests/test_review_prompt.py
git commit -m "feat: add voice-safety detection checks to review prompt"
```

---

## Done criteria

- `python -m pytest tests/ -q` passes with 51 tests (46 baseline + 3 gathering + 2 review).
- `prompts/gathering.txt` contains rule 7 (voiceability), two new anti-pattern rows, and the new Consolidation Gate checkbox; the rules header reads "Ten rules".
- `prompts/review.txt` contains the `requires_visual_stimulus` (error) and `enumeration_or_ranking` (warning) check blocks.
- No changes to `app.py`, `static/app.js`, the review tool schema, or any duration logic.

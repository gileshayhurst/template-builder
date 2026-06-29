# Priority-Assignment Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the gathering AI a concrete decision procedure for assigning 1–5 priorities, plus a reasoned annotation on the worked example, via a prompt-only edit.

**Architecture:** Two text additions to `prompts/gathering.txt` — a "How to choose" triage test in the Priority ratings block, and a priority-reasoning annotation on the grocery worked example — each guarded by a new assertion in `tests/test_gathering_prompt.py`. No code, corpus, or schema changes.

**Tech Stack:** Plain-text prompt file; pytest (the test harness reads `prompts/gathering.txt` and lowercases it before substring matching).

---

## File Structure

- `prompts/gathering.txt` — the gathering system prompt. Two regions change:
  - Priority ratings block (currently ends ~line 125): gains the "How to choose" test.
  - Worked example (currently ends ~line 100): gains a priority-reasoning sentence.
- `tests/test_gathering_prompt.py` — content assertions over the prompt. Gains two test functions. The module-level `_prompt_text()` helper **lowercases** the file, so all assertion anchors must be lowercase.

Both changes are independent of each other and of all code. There is no runtime behavior to mock or run beyond the existing prompt-content tests.

---

## Task 1: Add the "How to choose" decision procedure

**Files:**
- Modify: `prompts/gathering.txt` (Priority ratings block, after the "1 Minimal" rubric line, before the "Set topic priority by…" sentence)
- Test: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Write the failing test**

Add this function to `tests/test_gathering_prompt.py` (append at end of file):

```python
def test_prompt_has_priority_decision_procedure():
    text = _prompt_text()
    assert "how to choose" in text
    assert "protect at all costs" in text
    assert "force the spread" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gathering_prompt.py::test_prompt_has_priority_decision_procedure -v`
Expected: FAIL — assertion error on `"how to choose"` (text not yet in prompt).

- [ ] **Step 3: Add the decision procedure to the prompt**

In `prompts/gathering.txt`, locate the Priority ratings block. It currently reads (the rubric, then a guidance sentence):

```
- 1 Minimal: rarely needed; for completeness
Set topic priority by how central the theme is to the research goal; set item priority by how important that objective is within its topic. Never omit priority.
```

Insert a new paragraph **between** the "1 Minimal" line and the "Set topic priority by…" line, so it reads:

```
- 1 Minimal: rarely needed; for completeness

**How to choose:** Imagine the interview must end at the 70% mark. What would you protect at all costs? Those are your 5s. What would you skip without a second thought? Those are your 1–2s. Most items fall in between — force the spread, don't cluster at 3.

Set topic priority by how central the theme is to the research goal; set item priority by how important that objective is within its topic. Never omit priority.
```

Do not change any other line in the block. Leave the downstream-use sentence ("These ratings are not cosmetic…") exactly as-is.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gathering_prompt.py::test_prompt_has_priority_decision_procedure -v`
Expected: PASS.

- [ ] **Step 5: Run the full prompt-test suite to confirm no regression**

Run: `pytest tests/test_gathering_prompt.py -v`
Expected: all tests PASS (the 18 pre-existing tests plus the new one).

- [ ] **Step 6: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "feat: add priority decision procedure to gathering prompt"
```

---

## Task 2: Annotate the worked example with priority reasoning

**Files:**
- Modify: `prompts/gathering.txt` (worked example, the "Then ask your clarifying question. Note the objectives…" line, ~line 100)
- Test: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Write the failing test**

Add this function to `tests/test_gathering_prompt.py` (append at end of file):

```python
def test_prompt_worked_example_explains_priority_choices():
    text = _prompt_text()
    assert "core purpose of the visit" in text
    assert "thin-answer path" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_gathering_prompt.py::test_prompt_worked_example_explains_priority_choices -v`
Expected: FAIL — assertion error on `"core purpose of the visit"`.

- [ ] **Step 3: Add the reasoning annotation to the prompt**

In `prompts/gathering.txt`, find the line that closes the grocery worked example. It currently reads:

```
Then ask your clarifying question. Note the objectives: single ask, exploratory verbs, conditional framing, and every topic has a directional probe.
```

Add a new line **immediately after** it:

```
Note the priorities too: "Finding what they came for" rates a 5 — it is the core purpose of the visit and the heart of the research; arrival rates a 4 — it sets context but isn't the point; the probes sit at 3 in this guide because they only pay off if the core surfaces friction. Elsewhere a probe can rate higher when it maps to a critical thin-answer path — judge each item on its role, not on whether it is core or probe.
```

This phrases the probe values as role-specific to this example and explicitly notes probes can rate higher elsewhere — consistent with the no-probe-cap decision in the spec.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_gathering_prompt.py::test_prompt_worked_example_explains_priority_choices -v`
Expected: PASS.

- [ ] **Step 5: Run the full prompt-test suite to confirm no regression**

Run: `pytest tests/test_gathering_prompt.py -v`
Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "feat: annotate worked example with priority reasoning"
```

---

## Task 3: Final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the entire Python test suite**

Run: `pytest tests/`
Expected: all tests PASS — confirms the prompt edits didn't break `test_tools.py`, `test_routes.py`, or `test_retrieve.py` (none import the prompt, but this is the project's "run both suites when touching their areas" guard).

- [ ] **Step 2: Confirm no unintended prompt changes**

Run: `git diff --stat HEAD~2 -- prompts/gathering.txt`
Expected: `prompts/gathering.txt` shows only insertions (the two new paragraphs), zero deletions. If any line was deleted or reworded, revert and re-apply as pure insertions.

---

## Self-Review

**Spec coverage:**
- "How to choose" decision procedure → Task 1. ✓
- No probe cap → enforced by Task 2's annotation wording ("judge each item on its role, not on whether it is core or probe") and the absence of any cap rule; nothing in the plan adds a cap. ✓
- Annotate worked example → Task 2. ✓
- "What stays unchanged" (rubric, gate, downstream sentence, all code) → Tasks 1–2 are pure insertions; Task 3 Step 2 verifies zero deletions. ✓
- Tests assert presence via stable anchor phrases, not whole sentences → Task 1 uses `"how to choose"` / `"protect at all costs"` / `"force the spread"`; Task 2 uses `"core purpose of the visit"` / `"thin-answer path"`. All lowercase to match `_prompt_text()`. ✓
- Out of scope (RAG, corpus, duration weighting, schemas) → no task touches them. ✓

**Placeholder scan:** No TBD/TODO/"handle edge cases"; every step shows exact text and commands. ✓

**Type/anchor consistency:** Test anchor strings in each task's Step 1 exactly match the inserted prompt text in that task's Step 3 (case-folded). `"protect at all costs"`, `"force the spread"`, `"how to choose"`, `"core purpose of the visit"`, `"thin-answer path"` all appear verbatim in the inserted paragraphs. ✓

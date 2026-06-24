# Core Objective Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three new core-writing rules, three anti-pattern table rows, and a before/after worked example block to `prompts/gathering.txt` so the gathering AI writes core objectives that invite specific narrative answers instead of thin, one-sentence responses.

**Architecture:** All changes are to a single prompt file (`prompts/gathering.txt`). No code changes. Tests are added to the existing `tests/test_gathering_prompt.py` (which reads the prompt and asserts on lowercased string presence). TDD order: write failing tests first, then edit the prompt, then verify.

**Tech Stack:** Python / pytest for tests; plain text for the prompt file.

---

### Task 1: Write failing tests for all three prompt changes

**Files:**
- Modify: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Add the three new test functions**

Open `tests/test_gathering_prompt.py` and append the following three functions at the end of the file (after the existing `test_prompt_has_settings_awareness` function):

```python
def test_prompt_has_no_typical_framing_rule():
    text = _prompt_text()
    assert "no \"typical\" framing" in text


def test_prompt_has_scope_to_slice_rule():
    assert "scope to a slice" in _prompt_text()


def test_prompt_has_no_comparison_as_core_rule():
    assert "no comparison-as-core" in _prompt_text()


def test_prompt_anti_patterns_include_typical_framing():
    assert "typical commute / typical day" in _prompt_text()


def test_prompt_anti_patterns_include_high_altitude_scope():
    assert "overall impression / from start to finish" in _prompt_text()


def test_prompt_anti_patterns_include_comparison_trap():
    assert "how does x compare to y" in _prompt_text()


def test_prompt_worked_example_has_before_after_pairs():
    text = _prompt_text()
    assert "\"typical\" trap" in text
    assert "high-altitude scope" in text
    assert "comparison trap" in text
```

- [ ] **Step 2: Run the new tests to confirm they all fail**

```
pytest tests/test_gathering_prompt.py -v -k "typical or slice or comparison_as_core or anti_patterns_include or before_after"
```

Expected: all 7 new tests FAIL (strings not yet in the prompt).

---

### Task 2: Add three new core-writing rules to gathering.txt

**Files:**
- Modify: `prompts/gathering.txt`

The current line reads:
```
Each core/probe item is an OBJECTIVE: an instruction telling the interviewer what to accomplish — never a literal question to read aloud. Six rules:
```

Rule 4 currently reads:
```
4. Prefer episodic over attitudinal. Where the interview anchors on a specific occasion, phrase objectives to draw out what actually happened, not general opinions. Episodic memory yields richer, less rationalized data.
```

Rule 5 currently reads:
```
5. Specificity floor. Every objective must name the concrete thing sought — a moment, decision, friction, or feeling. "Understand their experience" is contentless and banned.
```

- [ ] **Step 1: Change "Six rules" to "Nine rules"**

Find and replace exactly:
- Old: `Each core/probe item is an OBJECTIVE: an instruction telling the interviewer what to accomplish — never a literal question to read aloud. Six rules:`
- New: `Each core/probe item is an OBJECTIVE: an instruction telling the interviewer what to accomplish — never a literal question to read aloud. Nine rules:`

- [ ] **Step 2: Insert the three new sub-rules after rule 4**

Find exactly:
```
4. Prefer episodic over attitudinal. Where the interview anchors on a specific occasion, phrase objectives to draw out what actually happened, not general opinions. Episodic memory yields richer, less rationalized data.
5. Specificity floor.
```

Replace with:
```
4. Prefer episodic over attitudinal. Where the interview anchors on a specific occasion, phrase objectives to draw out what actually happened, not general opinions. Episodic memory yields richer, less rationalized data.
4a. No "typical" framing. Every core must anchor on a specific episode: the most recent visit, the last time they commuted, a day that came to mind. Never ask about a generalised pattern — "typical" invites description from memory of a category, not recall of an event.
4b. Scope to a slice, not the whole experience. Cores that target the whole experience ("from start to finish," "overall impression") ask for summary and get summary. Target a bounded slice: a specific moment, decision point, the first few minutes, the moment they left. The smaller the scope, the more concrete the answer.
4c. No comparison-as-core. Asking a participant to compare two settings or experiences ("how does X compare to Y") makes them the analyst. Comparisons belong in probes, after a specific episode has been established. A core anchors on one occasion; a probe can then draw out the contrast.
5. Specificity floor.
```

- [ ] **Step 3: Run the three rule tests to confirm they now pass**

```
pytest tests/test_gathering_prompt.py -v -k "typical_framing_rule or scope_to_slice or comparison_as_core"
```

Expected: 3 PASS.

---

### Task 3: Add three new rows to the anti-patterns table

**Files:**
- Modify: `prompts/gathering.txt`

The current anti-patterns table ends with:
```
| sensitive topic placed first | guarded answers | move it later in the funnel |
```

- [ ] **Step 1: Append three new rows after the last existing row**

Find exactly:
```
| sensitive topic placed first | guarded answers | move it later in the funnel |
```

Replace with:
```
| sensitive topic placed first | guarded answers | move it later in the funnel |
| "typical commute / typical day" | invites generic description | anchor on the most recent or a specific remembered episode |
| "overall impression / from start to finish" | yields summary, not narrative | scope to a slice: a specific moment, decision, or feeling |
| "how does X compare to Y" | participant does analysis, not recall | anchor on a specific occasion when the contrast was felt |
```

- [ ] **Step 2: Run the three anti-pattern table tests**

```
pytest tests/test_gathering_prompt.py -v -k "anti_patterns_include"
```

Expected: 3 PASS.

---

### Task 4: Add before/after block to the worked example

**Files:**
- Modify: `prompts/gathering.txt`

The worked example currently opens with:
```
## Worked example
If the client says "I want a comprehensive interview about my grocery store," immediately call:
- update_metadata: title = "Grocery Store Experience"
```

- [ ] **Step 1: Insert the before/after block between the opening line and the first tool call**

Find exactly:
```
## Worked example
If the client says "I want a comprehensive interview about my grocery store," immediately call:
- update_metadata: title = "Grocery Store Experience"
```

Replace with:
```
## Worked example
The three most common core failure modes — and how to fix them:

**"Typical" trap:** "Walk through what a typical grocery visit looks like for the participant" → invites generic description. Fix: "Walk through how the participant arrived and entered the store on their most recent visit."

**High-altitude scope:** "Explore the participant's overall impression of the store" → yields one-sentence summary. Fix: "Trace the moment during the visit when the participant made an unplanned decision — to pick up something they hadn't planned to buy, or to skip something they'd intended to get."

**Comparison trap:** "Explore how this store compares to others the participant uses" → participant does analysis, not recall. Fix: "Surface a specific moment during the visit when something about the store stood out — positively or negatively — compared to what they expected."

If the client says "I want a comprehensive interview about my grocery store," immediately call:
- update_metadata: title = "Grocery Store Experience"
```

- [ ] **Step 2: Run the worked example test**

```
pytest tests/test_gathering_prompt.py -v -k "before_after"
```

Expected: 1 PASS.

---

### Task 5: Run full test suite and commit

**Files:**
- No changes — verification only.

- [ ] **Step 1: Run the full Python test suite**

```
pytest tests/ -v
```

Expected: all tests PASS. Note: this suite stubs `ANTHROPIC_API_KEY` automatically — no key needed.

- [ ] **Step 2: Run the JS tests to confirm nothing was disturbed**

```
node --test tests/duration.test.js
```

Expected: all tests PASS.

- [ ] **Step 3: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "$(cat <<'EOF'
feat: add core-objective quality rules to gathering prompt

Three new rules (no typical framing, scope to a slice, no comparison-as-core),
three anti-pattern table rows, and a before/after worked example block teach the
gathering AI to write cores that invite narrative answers rather than thin
one-sentence responses.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

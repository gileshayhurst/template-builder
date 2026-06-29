# Priority & Focus Pacing Rule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 9th preset-driven pacing rule, "Priority & Focus," that teaches the interview agent how to act on the `[P:N]` priority tags it already receives.

**Architecture:** The rule is a new key (`priority_focus`) added to the pacing system. It carries a distinct text per Depth-vs-Breadth preset, renders first in the Pacing Instructions panel, and exports as the headline line of the `# Pacing Instructions` block. No new mechanism — it rides the existing key-agnostic pacing plumbing. The priority→duration weighting is unchanged.

**Tech Stack:** Python/Flask (`app.py`), vanilla JS (`static/app.js`), pytest, `node --test`.

**Spec:** `docs/superpowers/specs/2026-06-29-priority-focus-pacing-rule-design.md`

---

## File Structure

| File | Change |
|---|---|
| `app.py` | Add `priority_focus` to `update_pacing` enum; add headline line to `format_template`. |
| `static/app.js` | Add `priority_focus` to `PACING_DEFAULTS`, `PACING_LABELS`, and the 4 non-balanced presets in `PACING_DEPTH_PRESETS`. |
| `prompts/gathering.txt` | Add one sentence to the "Priority ratings" block. |
| `tests/test_tools.py` | Update golden output + grouping test; add render check + enum check. |
| `tests/test_gathering_prompt.py` | Add assertion for the new sentence. |

`static/duration.js` and `tests/duration.test.js` are intentionally untouched.

---

## Task 1: Backend — export the rule and accept the new key (`app.py`)

**Files:**
- Modify: `app.py` (the `update_pacing` tool's `rule` enum, ~line 62; `format_template`, ~line 291)
- Test: `tests/test_tools.py`

- [ ] **Step 1: Update the golden-output fixtures and add new tests**

In `tests/test_tools.py`, add `priority_focus` to the `FULL_SECTIONS` pacing dict. Change the `pacing` block (lines 101–105) to:

```python
    "pacing": {
        "priority_focus": "Z", "do_not_rush": "A", "core_vs_probe": "B",
        "one_ask_per_turn": "C", "keep_light": "D", "follow_signals": "E",
        "original_followups": "F", "selective_probing": "G", "finish_line": "H"
    },
```

In `EXPECTED_FULL`, insert the headline line right after the `# Pacing Instructions` line. Change:

```python
    "# Pacing Instructions\n"
    "- **Do Not Rush** A\n"
```

to:

```python
    "# Pacing Instructions\n"
    "- **Priority & Focus:** Z\n"
    "\n"
    "- **Do Not Rush** A\n"
```

In `test_format_template_pacing_groups`, add a third assertion at the end of the function:

```python
    # Priority & Focus is the headline rule, followed by a blank line then Do Not Rush
    assert "# Pacing Instructions\n- **Priority & Focus:** Z\n\n- **Do Not Rush** A" in result
```

Add two new tests at the end of the file:

```python
def test_format_template_renders_priority_focus():
    """The priority_focus text appears in the Pacing Instructions block."""
    s = {**FULL_SECTIONS, "pacing": {**FULL_SECTIONS["pacing"], "priority_focus": "Use [P:N] to allocate attention."}}
    result = format_template(s)
    assert "- **Priority & Focus:** Use [P:N] to allocate attention." in result


def test_update_pacing_enum_includes_priority_focus():
    """The AI's update_pacing tool can target the new rule."""
    from app import GATHERING_TOOLS
    tool = next(t for t in GATHERING_TOOLS if t["name"] == "update_pacing")
    assert "priority_focus" in tool["input_schema"]["properties"]["rule"]["enum"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL — `test_format_template_full`, `test_format_template_pacing_groups`, `test_format_template_renders_priority_focus` fail (missing headline line); `test_update_pacing_enum_includes_priority_focus` fails (key not in enum).

- [ ] **Step 3: Add `priority_focus` to the `update_pacing` enum**

In `app.py`, change the enum (lines 62–63) to put `priority_focus` first:

```python
                "rule": {
                    "type": "string",
                    "enum": ["priority_focus", "do_not_rush", "core_vs_probe", "one_ask_per_turn",
                             "keep_light", "follow_signals", "original_followups",
                             "selective_probing", "finish_line"]
                },
```

- [ ] **Step 4: Add the headline line to `format_template`**

In `app.py`, change the start of the pacing block (lines 291–292) from:

```python
    parts.append("# Pacing Instructions")
    parts.append(f"- **Do Not Rush** {pacing.get('do_not_rush', '')}")
```

to:

```python
    parts.append("# Pacing Instructions")
    parts.append(f"- **Priority & Focus:** {pacing.get('priority_focus', '')}")
    parts.append("")
    parts.append(f"- **Do Not Rush** {pacing.get('do_not_rush', '')}")
```

- [ ] **Step 5: Run the full Python suite to verify it passes**

Run: `pytest tests/`
Expected: PASS — all tests green.

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_tools.py
git commit -m "feat: export Priority & Focus as headline pacing rule"
```

---

## Task 2: Frontend — add the rule and its five preset texts (`static/app.js`)

**Files:**
- Modify: `static/app.js` (`PACING_DEFAULTS` ~lines 3–12; `PACING_LABELS` ~lines 14–23; `PACING_DEPTH_PRESETS` ~lines 25–67)

> **Note:** `static/app.js` has no automated unit harness (only `static/duration.js` is unit-tested). Verification for this task is the unchanged JS suite (regression safety) plus a visual check in the running app.

- [ ] **Step 1: Add the Balanced text to `PACING_DEFAULTS`**

In `static/app.js`, add `priority_focus` as the **first** property of `PACING_DEFAULTS` (before `do_not_rush`):

```javascript
  priority_focus: "Each topic and item is marked [P:1]–[P:5]. Use this to allocate attention: spend more time and probe harder on [P:4]–[P:5] material, keep [P:1]–[P:2] efficient, and treat [P:3] as the normal baseline. Aim to cover every topic — a higher priority earns more depth, not the exclusion of lower-priority topics. Priority orders attention within the Core/Probe split, it does not override it. If time runs short, trim the lowest-[P:N] material first, and only drop a whole item or topic as a last resort, lowest priority first.",
```

- [ ] **Step 2: Add the label to `PACING_LABELS`**

Add `priority_focus` as the **first** property of `PACING_LABELS`:

```javascript
  priority_focus: "Priority & Focus",
```

- [ ] **Step 3: Add the four non-balanced preset texts to `PACING_DEPTH_PRESETS`**

Add `priority_focus` as the **first** property of each of the four presets. (`balanced` is `{ ...PACING_DEFAULTS }` and already has it — leave it alone.)

In `breadth`:

```javascript
    priority_focus: "Every topic carries a priority from [P:1] to [P:5]; treat these as a light dial on attention, not an on/off switch. Reaching every topic is the goal. Give [P:4]–[P:5] topics and items modestly more room and perhaps one extra probe, and keep [P:1]–[P:3] brisk — but never let a high-priority topic run so long that later topics go unasked. Priority orders attention within the Core/Probe split, it does not override it. If you fall behind, shorten the lowest-priority material first; drop an item only when time is nearly gone, lowest [P:N] first.",
```

In `slightly_broad`:

```javascript
    priority_focus: "Topics and items are marked [P:1]–[P:5]. Use these to share out attention while still covering everything: spend a little more time and the occasional extra probe on [P:4]–[P:5] material, keep [P:1]–[P:2] efficient, and treat [P:3] as the baseline. Cover every topic before depth on any one — a higher priority earns a little more depth, not the exclusion of lower-priority topics. Priority orders attention within the Core/Probe split, not against it. Under time pressure, trim the lowest-[P:N] material first.",
```

In `slightly_deep`:

```javascript
    priority_focus: "Topics and items are marked [P:1]–[P:5]. Invest your richer probing where the number is higher — follow [P:4]–[P:5] material a couple of layers deeper — while keeping [P:1]–[P:2] efficient. Still reach every topic at least briefly; do not let one or two high-priority topics dominate the whole interview. Priority orders attention within the Core/Probe split, not against it. Under time pressure, sacrifice depth on the lowest-[P:N] material first, then drop the lowest-priority items only if you must.",
```

In `deep`:

```javascript
    priority_focus: "Each topic and item carries a priority from [P:1] to [P:5]. Concentrate your richest probing where it is highest — go several layers deep on [P:5] and [P:4] material, and accept brief answers on [P:1]–[P:2]. Even so, every topic should be reached at least briefly before time runs out; never let one or two high-priority topics swallow the interview. Priority orders attention within the Core/Probe split, it does not override it. Under time pressure, sacrifice depth on the lowest-[P:N] material first, then drop the lowest-priority items entirely before higher-priority ones.",
```

- [ ] **Step 4: Run the JS suite to confirm no regression**

Run: `node --test tests/duration.test.js`
Expected: PASS (unaffected — sanity check that nothing in the shared static layer broke).

- [ ] **Step 5: Visual smoke check in the running app**

Start the app (PowerShell, per CLAUDE.md): `python main.py`. In the browser:
1. Expand **Pacing Instructions** → confirm **"Priority & Focus"** is the **first** rule and its textarea shows the Balanced text.
2. Move the **Depth vs. Breadth** slider across positions → confirm the Priority & Focus text changes at each notch (Breadth/Slightly Broad/Balanced/Slightly Deep/Deep).
3. Click **Export** → confirm the exported `# Pacing Instructions` block starts with `- **Priority & Focus:** …` followed by a blank line then `- **Do Not Rush** …`.

Stop the server when done (find PID with `netstat -ano | Select-String ':5000.*LISTENING'`, then `Stop-Process -Id <PID> -Force`).

- [ ] **Step 6: Commit**

```bash
git add static/app.js
git commit -m "feat: add Priority & Focus pacing rule with per-preset texts"
```

---

## Task 3: Reinforce priority in the gathering prompt (`prompts/gathering.txt`)

**Files:**
- Modify: `prompts/gathering.txt` (the "Priority ratings" block, ~lines 117–124)
- Test: `tests/test_gathering_prompt.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_gathering_prompt.py`, add at the end of the file:

```python
def test_prompt_explains_priority_drives_agent_attention():
    text = _prompt_text()
    assert "priority & focus" in text
    assert "attention" in text
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_gathering_prompt.py::test_prompt_explains_priority_drives_agent_attention -v`
Expected: FAIL — `"priority & focus"` not found in the prompt.

- [ ] **Step 3: Add the reinforcing sentence**

In `prompts/gathering.txt`, append this sentence to the end of the "Priority ratings" block, right after the line ending `Never omit priority.` (line 124):

```
These ratings are not cosmetic: the interview agent reads them through the "Priority & Focus" pacing rule to decide where to invest time and depth and what to sacrifice first under time pressure, so a discriminating spread directly shapes how the interview runs.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_gathering_prompt.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add prompts/gathering.txt tests/test_gathering_prompt.py
git commit -m "docs: note priority drives agent attention in gathering prompt"
```

---

## Final verification

- [ ] Run the full Python suite: `pytest tests/` → all PASS.
- [ ] Run the JS suite: `node --test tests/duration.test.js` → all PASS.
- [ ] Confirm `git log --oneline` shows the three feature commits on the `priority-focus-pacing-rule` branch.

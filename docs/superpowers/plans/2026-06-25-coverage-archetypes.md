# RAG Coverage Archetypes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make RAG coverage grounding generalize to unseen domains by adding 8 broad experience-archetype coverage entries alongside the 5 concrete maps, surfaced through the existing retriever.

**Architecture:** Archetype maps are ordinary `coverage` entries with an optional `archetype` field, broad `domain_tags`, and generalized `dimensions`. The existing `select_entries` Haiku call ranks them, so a concrete map wins for its own domain and an archetype wins for an unseen one. Code changes are limited to surfacing `archetype` in `build_catalog`/`assemble_block` and one `SELECT_SYSTEM` sentence. Backward compatible: entries without `archetype` render byte-identically to today.

**Tech Stack:** Python 3, the `anthropic` SDK, `pytest`. No new dependencies.

**Reference:** Spec at `docs/superpowers/specs/2026-06-25-coverage-archetypes-design.md`. The existing module is `retrieve.py`; existing tests are in `tests/test_retrieve.py`. Run all commands from the repo root `C:\Users\giles\Downloads\Template`. This is Windows; use the Bash tool for git/pytest.

---

### Task 1: Archetype corpus entries + the `archetype` field on concrete maps

**Files:**
- Modify (overwrite): `corpus/coverage/grocery.json`, `commute.json`, `banking-app.json`, `healthcare-visit.json`, `streaming.json`
- Create: `corpus/coverage/archetype-physical-place.json`, `archetype-service-encounter.json`, `archetype-app-session.json`, `archetype-media-session.json`, `archetype-routine-transition.json`, `archetype-decision-journey.json`, `archetype-onboarding.json`, `archetype-support-resolution.json`
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Write the failing lint tests**

Append to `tests/test_retrieve.py`:

```python
ARCHETYPE_IDS = {
    "coverage-archetype-physical-place-01",
    "coverage-archetype-service-encounter-01",
    "coverage-archetype-app-session-01",
    "coverage-archetype-media-session-01",
    "coverage-archetype-routine-transition-01",
    "coverage-archetype-decision-journey-01",
    "coverage-archetype-onboarding-01",
    "coverage-archetype-support-resolution-01",
}


def test_archetype_entries_present():
    ids = {e["id"] for e in retrieve.load_corpus()}
    assert ARCHETYPE_IDS <= ids


def test_all_coverage_entries_have_archetype_and_dimensions():
    cov = [e for e in retrieve.load_corpus() if e["type"] == "coverage"]
    assert len(cov) >= 13
    for e in cov:
        assert e.get("archetype"), f"{e['id']} missing archetype"
        assert e.get("dimensions"), f"{e['id']} missing dimensions"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retrieve.py -k "archetype or have_archetype" -v`
Expected: FAIL — `test_archetype_entries_present` (archetype ids absent) and `test_all_coverage_entries_have_archetype_and_dimensions` (concrete maps lack `archetype`, and count < 13).

- [ ] **Step 3: Overwrite the 5 concrete coverage files, adding the `archetype` field**

`corpus/coverage/grocery.json`:
```json
{"id": "coverage-grocery-01", "type": "coverage", "archetype": "physical place visit", "domain_tags": ["grocery", "retail", "in-store shopping"], "dimensions": ["arrival & entry", "finding items", "unplanned decisions", "checkout friction", "leaving"], "note": "Anchor each on the most recent specific visit, not a typical one."}
```

`corpus/coverage/commute.json`:
```json
{"id": "coverage-commute-01", "type": "coverage", "archetype": "routine/transition", "domain_tags": ["commuting", "travel", "transit"], "dimensions": ["leaving home", "the journey itself", "disruptions or delays", "other people", "arrival & transition"], "note": "Anchor on the most recent commute, not a typical one."}
```

`corpus/coverage/banking-app.json`:
```json
{"id": "coverage-banking-app-01", "type": "coverage", "archetype": "transactional app/site session", "domain_tags": ["banking app", "mobile banking", "fintech"], "dimensions": ["opening the app", "the task they came to do", "moments of hesitation or doubt", "security & trust feelings", "completing or abandoning"], "note": "Anchor on the most recent session and a specific task."}
```

`corpus/coverage/healthcare-visit.json`:
```json
{"id": "coverage-healthcare-visit-01", "type": "coverage", "archetype": "in-person service encounter", "domain_tags": ["healthcare visit", "doctor", "clinic"], "dimensions": ["booking & arrival", "waiting", "the consultation itself", "being heard or not", "leaving & next steps"], "note": "Sensitive topic -- place emotionally loaded dimensions later in the funnel."}
```

`corpus/coverage/streaming.json`:
```json
{"id": "coverage-streaming-01", "type": "coverage", "archetype": "media/content session", "domain_tags": ["streaming", "video", "entertainment app"], "dimensions": ["deciding to watch", "browsing & choosing", "the moment of starting something", "interruptions", "stopping or finishing"], "note": "Anchor on the most recent specific viewing session."}
```

- [ ] **Step 4: Create the 8 archetype coverage files**

`corpus/coverage/archetype-physical-place.json`:
```json
{"id": "coverage-archetype-physical-place-01", "type": "coverage", "archetype": "physical place visit", "domain_tags": ["physical place visit", "venue", "store", "in-person location", "bricks-and-mortar"], "dimensions": ["arrival & first impression", "orienting / finding your way", "the core activity in that space", "a friction or surprise moment", "leaving & what stuck"], "note": "Generalized archetype -- specialize each dimension to the actual place; anchor on a specific recent visit, not a typical one, and keep every objective voiceable."}
```

`corpus/coverage/archetype-service-encounter.json`:
```json
{"id": "coverage-archetype-service-encounter-01", "type": "coverage", "archetype": "in-person service encounter", "domain_tags": ["in-person service", "service encounter", "face-to-face", "appointment", "staffed interaction"], "dimensions": ["the lead-up / what they came for", "first contact with the person", "the exchange itself", "feeling heard or handled, or not", "resolution & departure"], "note": "Generalized archetype -- specialize to the actual service and anchor on a specific recent encounter. Emotionally loaded dimensions (feeling heard) belong later in the funnel."}
```

`corpus/coverage/archetype-app-session.json`:
```json
{"id": "coverage-archetype-app-session-01", "type": "coverage", "archetype": "transactional app/site session", "domain_tags": ["app session", "website session", "digital task", "online account", "self-service"], "dimensions": ["opening / why they came", "the task they set out to do", "a moment of hesitation or doubt", "trust / security / confidence", "completing or abandoning"], "note": "Generalized archetype -- specialize to the actual app or site and a specific task from the most recent session; keep every objective voiceable."}
```

`corpus/coverage/archetype-media-session.json`:
```json
{"id": "coverage-archetype-media-session-01", "type": "coverage", "archetype": "media/content session", "domain_tags": ["media", "content", "viewing", "listening", "reading", "entertainment"], "dimensions": ["deciding to engage", "choosing what", "the moment of starting something", "an interruption or drop-off", "stopping & what stuck"], "note": "Generalized archetype -- specialize to the actual content type; anchor on a specific recent session, not a typical one."}
```

`corpus/coverage/archetype-routine-transition.json`:
```json
{"id": "coverage-archetype-routine-transition-01", "type": "coverage", "archetype": "routine/transition", "domain_tags": ["routine", "daily transition", "habitual passage", "getting from a to b", "everyday journey"], "dimensions": ["the trigger to set off", "the passage itself", "a disruption or variation", "other people in it", "arrival & shift of mode"], "note": "Generalized archetype -- specialize to the actual routine; anchor on the most recent occurrence, not a typical one."}
```

`corpus/coverage/archetype-decision-journey.json`:
```json
{"id": "coverage-archetype-decision-journey-01", "type": "coverage", "archetype": "decision/purchase journey", "domain_tags": ["decision", "purchase journey", "buying", "choosing", "evaluation", "consideration"], "dimensions": ["what prompted the search", "gathering options", "the moment of comparison or narrowing", "the point of commitment or stall", "second-guessing afterward"], "note": "Generalized archetype -- specialize to the actual decision; anchor on a specific recent purchase or choice and trace it as it unfolded."}
```

`corpus/coverage/archetype-onboarding.json`:
```json
{"id": "coverage-archetype-onboarding-01", "type": "coverage", "archetype": "onboarding/first use", "domain_tags": ["onboarding", "first use", "first time", "getting started", "trial", "signup"], "dimensions": ["expectations going in", "the very first step", "the first thing that worked or confused", "the aha or the wall", "deciding whether to continue"], "note": "Generalized archetype -- specialize to the actual product or service; anchor on the participant's actual first use, not a general impression."}
```

`corpus/coverage/archetype-support-resolution.json`:
```json
{"id": "coverage-archetype-support-resolution-01", "type": "coverage", "archetype": "support/problem resolution", "domain_tags": ["support", "problem resolution", "help", "complaint", "troubleshooting", "customer service"], "dimensions": ["noticing the problem", "deciding how to seek help", "the help interaction itself", "whether it actually resolved", "how it left them feeling about the provider"], "note": "Generalized archetype -- specialize to the actual problem; anchor on a specific recent incident. Place frustration or blame dimensions later in the funnel."}
```

- [ ] **Step 5: Run the lint tests and the full suite**

Run: `pytest tests/test_retrieve.py -k "archetype or have_archetype" -v`
Expected: PASS (both).

Run: `pytest tests/ -q`
Expected: all pass (the existing `test_real_corpus_loads_nonempty` still holds — corpus is now larger; all 20 entries valid).

- [ ] **Step 6: Commit**

```bash
git add corpus tests/test_retrieve.py
git commit -m "feat: add experience-archetype coverage maps + archetype tags

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Surface `archetype` in retrieval (catalog, block, prompt)

**Files:**
- Modify: `retrieve.py` (`SELECT_SYSTEM` constant, `build_catalog`, `assemble_block`)
- Test: `tests/test_retrieve.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_retrieve.py`:

```python
def test_build_catalog_includes_archetype():
    corpus = [{"id": "cov-x", "type": "coverage", "archetype": "physical place visit",
               "domain_tags": ["store"], "note": "n"}]
    cat = retrieve.build_catalog(corpus)
    assert "<physical place visit>" in cat
    assert "[cov-x] (coverage)" in cat


def test_build_catalog_no_archetype_unchanged():
    corpus = [{"id": "craft-a", "type": "craft", "tags": ["t1"], "note": "x"}]
    assert retrieve.build_catalog(corpus) == "[craft-a] (craft) t1 :: x"


def test_assemble_block_labels_archetype():
    corpus = [{"id": "cov-x", "type": "coverage", "archetype": "physical place visit",
               "domain_tags": ["store"], "dimensions": ["arrival", "leaving"], "note": "specialize"}]
    block = retrieve.assemble_block(corpus, ["cov-x"])
    assert "physical place visit" in block
    assert "arrival; leaving" in block


def test_select_system_mentions_archetype():
    assert "archetype" in retrieve.SELECT_SYSTEM
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_retrieve.py -k "includes_archetype or labels_archetype or select_system_mentions" -v`
Expected: FAIL — `test_build_catalog_includes_archetype` (catalog has no `<...>`), `test_assemble_block_labels_archetype` (block shows domain_tags "store", not the archetype), `test_select_system_mentions_archetype` (no "archetype" in the constant). (`test_build_catalog_no_archetype_unchanged` already passes — it is a backward-compat guard.)

- [ ] **Step 3: Update `build_catalog` in `retrieve.py`**

Replace the existing `build_catalog` function with:

```python
def build_catalog(corpus):
    lines = []
    for e in corpus:
        tags = ",".join(e.get("tags") or e.get("domain_tags") or [])
        arch = e.get("archetype")
        arch_str = f" <{arch}>" if arch else ""
        lines.append(f"[{e['id']}] ({e['type']}){arch_str} {tags} :: {e.get('note', '')}")
    return "\n".join(lines)
```

- [ ] **Step 4: Update the coverage branch of `assemble_block` in `retrieve.py`**

In `assemble_block`, replace the `else:` (coverage) branch:

```python
        else:
            dims = "; ".join(e.get("dimensions", []))
            tags = ",".join(e.get("domain_tags", []))
            parts.append(f"- Coverage ({tags}): ensure dimensions -- {dims}. {e.get('note', '')}")
```

with:

```python
        else:
            dims = "; ".join(e.get("dimensions", []))
            tags = ",".join(e.get("domain_tags", []))
            label = e.get("archetype") or tags
            parts.append(f"- Coverage ({label}): ensure dimensions -- {dims}. {e.get('note', '')}")
```

- [ ] **Step 5: Update the `SELECT_SYSTEM` constant in `retrieve.py`**

Replace the existing `SELECT_SYSTEM` assignment with:

```python
SELECT_SYSTEM = (
    "You help a research-interview-design assistant. Given the current draft and a "
    "catalog of guidance entries, choose the 3-5 entries most relevant to improving "
    "the draft right now -- a mix of craft (phrasing) and coverage (missing dimensions) "
    "when both apply. For coverage, prefer a specific-domain map when one closely fits "
    "the domain; otherwise pick the closest experience archetype (shown in angle brackets). "
    "Call select_entries with their ids. Choose only ids that appear "
    "in the catalog; if nothing is relevant, return an empty list."
)
```

- [ ] **Step 6: Run the new tests and the full suite**

Run: `pytest tests/test_retrieve.py -v`
Expected: all pass — the new archetype tests AND the pre-existing backward-compat tests (`test_build_catalog_format`, `test_assemble_block_renders_chosen_entries`) still green.

Run: `pytest tests/ -q`
Expected: all pass (no regression in `test_routes.py` / `test_tools.py` / `test_gathering_prompt.py`).

- [ ] **Step 7: Commit**

```bash
git add retrieve.py tests/test_retrieve.py
git commit -m "feat: surface archetype in catalog, grounding block, and selection prompt

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-review

**Spec coverage:**
- 8 archetype entries → Task 1 Step 4 ✓
- `archetype` field added to 5 concrete maps → Task 1 Step 3 ✓
- `archetype` optional in loader (`_valid_entry` unchanged) → not modified by either task ✓ (no task touches `_valid_entry`)
- `build_catalog` surfaces archetype → Task 2 Step 3 ✓
- `assemble_block` labels archetype → Task 2 Step 4 ✓
- `SELECT_SYSTEM` nudge → Task 2 Step 5 ✓
- Lint tests (archetypes present; every coverage entry has archetype + dimensions) → Task 1 Step 1 ✓
- Catalog/render tests + backward-compat guards → Task 2 Step 1 ✓
- Backward compatibility (existing tests stay green) → verified in Task 1 Step 5 and Task 2 Step 6 ✓

**Placeholder scan:** none — every JSON file and every code block is given in full.

**Type/name consistency:** the 8 ids in `ARCHETYPE_IDS` (Task 1) exactly match the `id` fields of the 8 created files (Task 1 Step 4). `build_catalog`/`assemble_block`/`SELECT_SYSTEM` names match the existing `retrieve.py` symbols. The `archetype` field name is used identically across corpus files, tests, and code.

**Backward-compat arithmetic check:** `build_catalog` with no `archetype` → `arch_str=""` → `[id] (type) tags :: note` (matches `test_build_catalog_format` and `test_build_catalog_no_archetype_unchanged`). `assemble_block` with no `archetype` → `label = tags` → coverage line identical to today (matches `test_assemble_block_renders_chosen_entries`, which asserts `"grocery" in block`).

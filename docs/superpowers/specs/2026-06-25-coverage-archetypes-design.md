# RAG Coverage Archetypes — Design Spec
**Date:** 2026-06-25

## Problem

The RAG coverage corpus (`corpus/coverage/`) holds 5 concrete, domain-specific dimension checklists (grocery, commute, banking app, healthcare visit, streaming). Coverage grounding therefore only fires for those 5 domains; for any unseen domain ("gym visit", "car buying") the retriever finds no coverage match and the agent falls back to ungrounded behavior. Coverage is the part of RAG that is *not* yet universally applicable.

## Goal

Make coverage grounding generalize to (almost) any domain by adding ~8 broad **experience-archetype** coverage entries alongside the concrete maps. A never-seen domain has no concrete match, so the retriever picks the closest archetype — universality falls out of the existing ranking, with no new branching logic. The concrete maps stay as the sharper match for their own domains.

This is primarily a **corpus-content change** plus a one-sentence prompt nudge and a small rendering tweak. The retrieval mechanism, the `<grounding>` injection, and the fail-open contract are unchanged.

---

## Architecture

| Area | Change |
|---|---|
| `corpus/coverage/` | Add 8 archetype coverage entries. Keep all 5 concrete maps. |
| Coverage schema | Add one **optional** field `archetype` (string). Each concrete map gains the archetype tag it belongs to; each archetype map names itself. Optional in the loader → existing entries stay valid, no migration. |
| `retrieve.py` — `build_catalog` | Surface `archetype` (in angle brackets) on the catalog line so Haiku can see and prefer it. |
| `retrieve.py` — `assemble_block` | Label a chosen coverage entry with its `archetype` (when present) so the agent knows to specialize a generalized map. |
| `retrieve.py` — `SELECT_SYSTEM` | One sentence: prefer a specific-domain map when one closely fits; otherwise pick the closest archetype. |
| `retrieve.py` — `_valid_entry` | **Unchanged** — `archetype` is NOT required (loader stays lenient; fail-open). |
| `tests/test_retrieve.py` | Corpus-lint (every coverage entry has `archetype` + `dimensions`; 8 archetypes present), catalog/render tests, backward-compat checks. |

### Why no new entry type or preference code

Archetype maps are ordinary `coverage` entries with broad `domain_tags` and generalized `dimensions`. `select_entries` (the existing Haiku call) already ranks the catalog, so a concrete map naturally wins for its own domain and an archetype wins for an unseen one. The `SELECT_SYSTEM` sentence makes that preference explicit; no code branches on it.

---

## The archetype set

8 archetype entries, one JSON file each under `corpus/coverage/`. Each is a `coverage` entry with `archetype`, broad `domain_tags`, generalized `dimensions`, and a `note` reminding the agent to specialize and obey the craft rules.

| id | `archetype` | dimensions | concrete that folds in |
|---|---|---|---|
| `coverage-archetype-physical-place-01` | physical place visit | arrival & first impression; orienting / finding your way; the core activity there; a friction or surprise moment; leaving & what stuck | grocery |
| `coverage-archetype-service-encounter-01` | in-person service encounter | the lead-up / what they came for; first contact with the person; the exchange itself; feeling heard or handled, or not; resolution & departure | healthcare-visit |
| `coverage-archetype-app-session-01` | transactional app/site session | opening / why they came; the task they set out to do; a moment of hesitation or doubt; trust / security / confidence; completing or abandoning | banking-app |
| `coverage-archetype-media-session-01` | media/content session | deciding to engage; choosing what; the moment of starting something; an interruption or drop-off; stopping & what stuck | streaming |
| `coverage-archetype-routine-transition-01` | routine/transition | the trigger to set off; the passage itself; a disruption or variation; other people in it; arrival & shift of mode | commute |
| `coverage-archetype-decision-journey-01` | decision/purchase journey | what prompted the search; gathering options; the moment of comparison or narrowing; the point of commitment or stall; second-guessing afterward | *(net-new)* |
| `coverage-archetype-onboarding-01` | onboarding/first use | expectations going in; the very first step; the first thing that worked or confused; the aha or the wall; deciding whether to continue | *(net-new)* |
| `coverage-archetype-support-resolution-01` | support/problem resolution | noticing the problem; deciding how to seek help; the help interaction itself; whether it actually resolved; how it left them feeling about the provider | *(net-new)* |

The 5 concrete maps stay and each gains its `archetype` tag (grocery → physical place visit; healthcare-visit → in-person service encounter; banking-app → transactional app/site session; streaming → media/content session; commute → routine/transition).

Net corpus: 5 concrete + 8 archetype = **13 coverage entries**, plus the unchanged 7 craft = **20 total**. Still trivially small for the Haiku catalog.

### Example archetype entry (`corpus/coverage/archetype-physical-place.json`)

```json
{
  "id": "coverage-archetype-physical-place-01",
  "type": "coverage",
  "archetype": "physical place visit",
  "domain_tags": ["physical place visit", "venue", "store", "in-person location", "bricks-and-mortar"],
  "dimensions": ["arrival & first impression", "orienting / finding your way", "the core activity in that space", "a friction or surprise moment", "leaving & what stuck"],
  "note": "Generalized archetype -- specialize each dimension to the actual place; anchor on a specific recent visit, not a typical one, and keep every objective voiceable."
}
```

### Example concrete entry gaining the tag (`corpus/coverage/grocery.json`)

Unchanged except for the added line `"archetype": "physical place visit",`.

---

## Retrieval changes (`retrieve.py`)

### `build_catalog`

Surface the archetype (in angle brackets) when present, so Haiku sees it. Backward compatible — entries without `archetype` render exactly as today.

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

For an entry with no `archetype`, `arch_str` is `""`, producing `[id] (type) tags :: note` — identical to current output (the existing `test_build_catalog_format` still passes).

### `assemble_block`

Label a chosen coverage entry with its archetype when present (falls back to `domain_tags` otherwise, preserving current behavior):

```python
        else:
            dims = "; ".join(e.get("dimensions", []))
            tags = ",".join(e.get("domain_tags", []))
            label = e.get("archetype") or tags
            parts.append(f"- Coverage ({label}): ensure dimensions -- {dims}. {e.get('note', '')}")
```

A coverage entry without `archetype` falls back to `tags` (the existing `test_assemble_block_renders_chosen_entries`, whose fixture has no archetype and asserts `"grocery" in block`, still passes).

### `SELECT_SYSTEM`

Add one sentence after the "a mix of craft … coverage … when both apply." sentence:

> "For coverage, prefer a specific-domain map when one closely fits the domain; otherwise pick the closest experience archetype (shown in angle brackets)."

### `_valid_entry`

Unchanged. `archetype` is optional; a coverage entry is valid as long as it has truthy `dimensions`. The loader stays lenient (fail-open); the corpus-lint test (below) enforces the field on *our* entries.

---

## Testing (`tests/test_retrieve.py`)

All without an API key (mocks where the model is involved), consistent with the existing suite.

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
```

The existing tests (`test_build_catalog_format`, `test_assemble_block_renders_chosen_entries`, `test_real_corpus_loads_nonempty`) must continue to pass unchanged — the changes are backward compatible for entries without `archetype`.

---

## Build phases

1. **Corpus** — add the 8 archetype JSON files; add the `archetype` field to the 5 concrete maps. Add the lint tests (`test_archetype_entries_present`, `test_all_coverage_entries_have_archetype_and_dimensions`). Pure data + tests.
2. **Retrieval surfacing** — update `build_catalog` and `assemble_block` to surface/label `archetype`; add the `SELECT_SYSTEM` sentence. Add `test_build_catalog_includes_archetype`, `test_build_catalog_no_archetype_unchanged`, `test_assemble_block_labels_archetype`. Confirm the full suite (incl. the unchanged backward-compat tests) is green.

---

## Out of scope (clean follow-ons)

- **Generative coverage fallback** — synthesizing a dimension checklist on the fly for domains that don't match any archetype. The next spec, informed by where archetypes still miss.
- **LLM-judge eval harness** — measuring grounded-vs-ungrounded topic quality across a domain basket. Separate effort; needs a live API key, which breaks the "tests mock it" convention.
- **Deepening the craft set.**

## What is unchanged

- The retrieval mechanism (`select_entries`, `retrieve_context`), the `<grounding>` injection in `app.py`, the fail-open contract, `RAG_ENABLED`.
- The 7 craft entries.
- `_valid_entry` / `load_corpus` leniency.

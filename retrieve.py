import os
import glob
import json
import logging

import anthropic

from config import ANTHROPIC_API_KEY, RAG_ENABLED

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_DIR = os.path.dirname(__file__)
CORPUS_DIR = os.path.join(BASE_DIR, "corpus")

HAIKU_MODEL = "claude-haiku-4-5"


def _valid_entry(e):
    if not isinstance(e, dict) or not e.get("id") or e.get("type") not in ("craft", "coverage"):
        return False
    if e["type"] == "craft":
        return bool(e.get("bad")) and bool(e.get("good"))
    return bool(e.get("dimensions"))


def load_corpus(corpus_dir=CORPUS_DIR):
    entries = []
    for sub in ("craft", "coverage"):
        for path in sorted(glob.glob(os.path.join(corpus_dir, sub, "*.json"))):
            try:
                with open(path, encoding="utf-8") as f:
                    e = json.load(f)
            except (OSError, json.JSONDecodeError):
                logging.warning("corpus: could not read %s", path)
                continue
            if _valid_entry(e):
                entries.append(e)
            else:
                logging.warning("corpus: skipping malformed entry %s", path)
    return entries


def build_catalog(corpus):
    lines = []
    for e in corpus:
        tags = ",".join(e.get("tags") or e.get("domain_tags") or [])
        lines.append(f"[{e['id']}] ({e['type']}) {tags} :: {e.get('note', '')}")
    return "\n".join(lines)


def build_query(sections, latest_msg):
    sections = sections or {}
    meta = sections.get("metadata") or {}
    title = meta.get("title", "")
    focus = sections.get("focus", "")
    topics = sections.get("topics") or []
    topic_titles = ", ".join(t.get("title", "") for t in topics)
    return (f"Title: {title}\nFocus: {focus}\nTopics: {topic_titles}\n"
            f"Latest message: {latest_msg}")


def assemble_block(corpus, ids):
    by_id = {e["id"]: e for e in corpus}
    chosen = [by_id[i] for i in ids if i in by_id]
    if not chosen:
        return ""
    parts = [
        "<grounding>",
        "Relevant interview-design guidance for this draft. Use it; do not quote it to the client.",
    ]
    for e in chosen:
        if e["type"] == "craft":
            parts.append(
                f"- Craft ({e.get('rule', '')}): avoid \"{e['bad']}\" -> prefer \"{e['good']}\". {e.get('note', '')}"
            )
        else:
            dims = "; ".join(e.get("dimensions", []))
            parts.append(f"- Coverage: ensure dimensions -- {dims}. {e.get('note', '')}")
    parts.append("</grounding>")
    return "\n".join(parts)


def _has_domain(sections):
    sections = sections or {}
    title = (sections.get("metadata") or {}).get("title", "")
    topics = sections.get("topics") or []
    return bool(title) or len(topics) > 0


CORPUS = load_corpus()
RAG_EFFECTIVE = RAG_ENABLED and bool(CORPUS)

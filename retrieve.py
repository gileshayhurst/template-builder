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


CORPUS = load_corpus()
RAG_EFFECTIVE = RAG_ENABLED and bool(CORPUS)

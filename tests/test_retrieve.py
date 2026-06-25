import os
import json
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
import retrieve


def _write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def test_load_corpus_parses_valid(tmp_path):
    _write(tmp_path / "craft" / "a.json",
           {"id": "craft-a", "type": "craft", "bad": "x", "good": "y", "note": "n"})
    _write(tmp_path / "coverage" / "b.json",
           {"id": "cov-b", "type": "coverage", "dimensions": ["d1"], "note": "n"})
    corpus = retrieve.load_corpus(str(tmp_path))
    assert {e["id"] for e in corpus} == {"craft-a", "cov-b"}


def test_load_corpus_skips_malformed(tmp_path):
    _write(tmp_path / "craft" / "good.json",
           {"id": "craft-a", "type": "craft", "bad": "x", "good": "y"})
    _write(tmp_path / "craft" / "nobad.json",
           {"id": "craft-bad", "type": "craft", "good": "y"})   # missing bad
    _write(tmp_path / "craft" / "noid.json",
           {"type": "craft", "bad": "x", "good": "y"})           # missing id
    corpus = retrieve.load_corpus(str(tmp_path))
    assert [e["id"] for e in corpus] == ["craft-a"]


def test_load_corpus_skips_invalid_json(tmp_path):
    (tmp_path / "craft").mkdir(parents=True)
    (tmp_path / "craft" / "bad.json").write_text("not json", encoding="utf-8")
    corpus = retrieve.load_corpus(str(tmp_path))
    assert corpus == []


def test_real_corpus_loads_nonempty():
    corpus = retrieve.load_corpus()
    assert len(corpus) >= 8
    assert all(e["type"] in ("craft", "coverage") for e in corpus)
    assert len({e["id"] for e in corpus}) == len(corpus)  # ids unique

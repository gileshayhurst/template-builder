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


def test_build_catalog_format():
    corpus = [
        {"id": "craft-a", "type": "craft", "tags": ["t1", "t2"], "note": "split asks"},
        {"id": "cov-b", "type": "coverage", "domain_tags": ["grocery"], "note": "dims"},
    ]
    cat = retrieve.build_catalog(corpus)
    assert "[craft-a] (craft) t1,t2 :: split asks" in cat
    assert "[cov-b] (coverage) grocery :: dims" in cat


def test_build_query_assembles_context():
    sections = {
        "metadata": {"title": "Grocery Study"},
        "focus": "most recent visit",
        "topics": [{"title": "Arrival"}, {"title": "Checkout"}],
    }
    q = retrieve.build_query(sections, "I want to explore checkout")
    assert "Grocery Study" in q
    assert "most recent visit" in q
    assert "Arrival" in q and "Checkout" in q
    assert "I want to explore checkout" in q


def test_assemble_block_renders_chosen_entries():
    corpus = [
        {"id": "craft-a", "type": "craft", "rule": "one_ask", "bad": "BADTEXT", "good": "GOODTEXT", "note": "N"},
        {"id": "cov-b", "type": "coverage", "domain_tags": ["grocery"],
         "dimensions": ["arrival", "checkout"], "note": "anchor"},
        {"id": "unused", "type": "craft", "bad": "UNUSEDBAD", "good": "UNUSEDGOOD"},
    ]
    block = retrieve.assemble_block(corpus, ["craft-a", "cov-b"])
    assert block.startswith("<grounding>")
    assert block.rstrip().endswith("</grounding>")
    assert "BADTEXT" in block and "GOODTEXT" in block   # craft bad/good
    assert "arrival; checkout" in block                  # coverage dimensions
    assert "grocery" in block                            # coverage domain tags rendered
    assert "UNUSEDGOOD" not in block                     # unused entry not rendered


def test_assemble_block_empty_returns_empty_string():
    assert retrieve.assemble_block([{"id": "a", "type": "craft"}], []) == ""
    assert retrieve.assemble_block([{"id": "a", "type": "craft"}], ["missing"]) == ""


def test_has_domain():
    assert retrieve._has_domain({"metadata": {"title": "X"}, "topics": []}) is True
    assert retrieve._has_domain({"metadata": {"title": ""}, "topics": [{"title": "T"}]}) is True
    assert retrieve._has_domain({"metadata": {"title": ""}, "topics": []}) is False
    assert retrieve._has_domain({}) is False
    assert retrieve._has_domain(None) is False


def _tool_resp(entry_ids):
    block = MagicMock()
    block.type = "tool_use"
    block.name = "select_entries"
    block.input = {"entry_ids": entry_ids}
    resp = MagicMock()
    resp.content = [block]
    return resp


def test_select_entries_parses_ids():
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp(["craft-a", "cov-b"])
        ids = retrieve.select_entries("query", "catalog")
    assert ids == ["craft-a", "cov-b"]


def test_select_entries_caps_at_5():
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp([f"id{i}" for i in range(10)])
        ids = retrieve.select_entries("q", "c")
    assert len(ids) == 5


def test_select_entries_no_tool_use_returns_empty():
    text_block = MagicMock()
    text_block.type = "text"
    resp = MagicMock()
    resp.content = [text_block]
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = resp
        assert retrieve.select_entries("q", "c") == []


def test_retrieve_context_none_when_disabled(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", False)
    assert retrieve.retrieve_context({"metadata": {"title": "Grocery"}}, "hi") is None


def test_retrieve_context_none_without_domain(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS",
                        [{"id": "craft-a", "type": "craft", "bad": "x", "good": "y"}])
    assert retrieve.retrieve_context({"metadata": {"title": ""}, "topics": []}, "hi") is None


def test_retrieve_context_returns_block_with_domain(monkeypatch):
    corpus = [{"id": "craft-a", "type": "craft", "rule": "r", "bad": "BAD", "good": "GOOD", "note": "n"}]
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS", corpus)
    with patch("retrieve.client") as mc:
        mc.messages.create.return_value = _tool_resp(["craft-a"])
        block = retrieve.retrieve_context({"metadata": {"title": "Grocery"}, "topics": []}, "hi")
    assert block is not None
    assert "<grounding>" in block
    assert "BAD" in block and "GOOD" in block


def test_retrieve_context_none_on_exception(monkeypatch):
    monkeypatch.setattr(retrieve, "RAG_EFFECTIVE", True)
    monkeypatch.setattr(retrieve, "CORPUS",
                        [{"id": "craft-a", "type": "craft", "bad": "x", "good": "y"}])
    with patch("retrieve.client") as mc:
        mc.messages.create.side_effect = RuntimeError("boom")
        assert retrieve.retrieve_context({"metadata": {"title": "Grocery"}}, "hi") is None

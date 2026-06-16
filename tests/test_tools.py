import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from app import process_tool_call


def test_update_metadata():
    result = process_tool_call("update_metadata", {"title": "Cooking First Dish"})
    assert result == {"section": "metadata", "payload": {"title": "Cooking First Dish"}}


def test_update_pacing():
    result = process_tool_call("update_pacing", {"rule": "do_not_rush", "text": "Take it slow."})
    assert result == {"section": "pacing", "payload": {"rule": "do_not_rush", "text": "Take it slow."}}


def test_update_focus():
    result = process_tool_call("update_focus", {"text": "Anchor on one recent occasion."})
    assert result == {"section": "focus", "payload": "Anchor on one recent occasion."}


def test_add_topic_with_probe():
    result = process_tool_call("add_topic", {
        "index": 1,
        "title": "Confirm the occasion",
        "priority": 5,
        "core": [{"text": "Identify the dish", "priority": 5}],
        "probe": [{"text": "Clarify if ambiguous", "priority": 2}]
    })
    assert result == {
        "section": "topic",
        "payload": {
            "index": 1,
            "title": "Confirm the occasion",
            "priority": 5,
            "core": [{"text": "Identify the dish", "priority": 5}],
            "probe": [{"text": "Clarify if ambiguous", "priority": 2}]
        }
    }


def test_add_topic_probe_defaults_to_empty():
    result = process_tool_call("add_topic", {
        "index": 2, "title": "Basic facts",
        "core": [{"text": "Collect dish name", "priority": 3}]
    })
    assert result["payload"]["probe"] == []


def test_add_topic_priority_defaults_to_3():
    result = process_tool_call("add_topic", {
        "index": 3, "title": "No priority given",
        "core": [{"text": "Some item", "priority": 3}]
    })
    assert result["payload"]["priority"] == 3


def test_add_topic_string_items_normalised():
    result = process_tool_call("add_topic", {
        "index": 4, "title": "Legacy call",
        "priority": 4,
        "core": ["Plain string item"],
        "probe": ["Another plain string"]
    })
    assert result["payload"]["core"] == [{"text": "Plain string item", "priority": 3}]
    assert result["payload"]["probe"] == [{"text": "Another plain string", "priority": 3}]


def test_add_topic_item_priority_defaults_to_3():
    result = process_tool_call("add_topic", {
        "index": 5, "title": "Item missing priority",
        "priority": 3,
        "core": [{"text": "No priority on this item"}]
    })
    assert result["payload"]["core"] == [{"text": "No priority on this item", "priority": 3}]


def test_remove_topic():
    result = process_tool_call("remove_topic", {"index": 3})
    assert result == {"section": "remove_topic", "payload": {"index": 3}}


def test_update_expansion():
    result = process_tool_call("update_expansion", {"items": ["role of family", "media inspiration"]})
    assert result == {"section": "expansion", "payload": ["role of family", "media inspiration"]}


def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        process_tool_call("nonexistent_tool", {})

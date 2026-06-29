import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from app import process_tool_call, format_template
from app import app as flask_app


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


FULL_SECTIONS = {
    "metadata": {"title": "T", "version": "2.0", "date": "2026-01-01"},
    "pacing": {
        "priority_focus": "Z", "do_not_rush": "A", "core_vs_probe": "B",
        "one_ask_per_turn": "C", "keep_light": "D", "follow_signals": "E",
        "original_followups": "F", "selective_probing": "G", "finish_line": "H"
    },
    "focus": "Focus text.",
    "topics": [
        {
            "index": 1, "title": "Topic one", "priority": 5,
            "core": [{"text": "Core item.", "priority": 5}],
            "probe": [{"text": "Probe item.", "priority": 2}]
        },
        {
            "index": 2, "title": "Topic two", "priority": 3,
            "core": [{"text": "Core two.", "priority": 3}],
            "probe": []
        }
    ],
    "expansion": ["Exp A", "Exp B"]
}

EXPECTED_FULL = (
    "[Prompt metadata only: T | v2.0 | 2026-01-01]\n"
    "\n"
    "# Pacing Instructions\n"
    "- **Priority & Focus:** Z\n"
    "\n"
    "- **Do Not Rush** A\n"
    "\n"
    "- **Core vs. Probe:** B\n"
    "- **One main ask per turn:** C\n"
    "- **Keep questions light:** D\n"
    "\n"
    "- **Follow strong signals:** E\n"
    "- **Original follow-ups allowed:** F\n"
    "- **Selective probing:** G\n"
    "\n"
    "- **The Finish Line** H\n"
    "\n"
    "\n"
    "\n"
    "# Main Interview Guide: T\n"
    "\n"
    "## Interview focus\n"
    "- [Core] Focus text.\n"
    "\n"
    "## Topic 1 [P:5]: Topic one\n"
    "- [Core][P:5] Core item.\n"
    "- [Probe][P:2] Probe item.\n"
    "\n"
    "## Topic 2 [P:3]: Topic two\n"
    "- [Core][P:3] Core two.\n"
    "\n"
    "# Expansion Topics\n"
    "Use these for secondary discovery as instructed\n"
    "- Exp A\n"
    "- Exp B"
)


def test_format_template_full():
    assert format_template(FULL_SECTIONS) == EXPECTED_FULL


def test_format_template_no_focus():
    s = {**FULL_SECTIONS, "focus": ""}
    result = format_template(s)
    assert "## Interview focus" not in result
    assert "- [Core] " not in result
    assert "# Main Interview Guide: T" in result


def test_format_template_no_expansion():
    s = {**FULL_SECTIONS, "expansion": []}
    result = format_template(s)
    assert "# Expansion Topics" not in result


def test_format_template_no_probe_lines():
    """A topic with no probe items must emit no [Probe] lines."""
    result = format_template(FULL_SECTIONS)
    lines = result.splitlines()
    topic2_idx = next(i for i, l in enumerate(lines) if "Topic two" in l)
    # Collect lines belonging to topic 2 (up to next ## or end)
    topic2_lines = []
    for line in lines[topic2_idx + 1:]:
        if line.startswith("## ") or line.startswith("# "):
            break
        topic2_lines.append(line)
    assert not any("[Probe]" in l for l in topic2_lines)


def test_format_template_default_priority():
    """Items missing priority should default to 3."""
    s = {
        **FULL_SECTIONS,
        "topics": [
            {"index": 1, "title": "T", "priority": 3,
             "core": [{"text": "No prio"}], "probe": []}
        ]
    }
    result = format_template(s)
    assert "- [Core][P:3] No prio" in result


def test_format_template_pacing_groups():
    """Verify blank-line grouping between pacing rules and 3 blank lines before the guide heading."""
    result = format_template(FULL_SECTIONS)
    # Three blank lines between The Finish Line and # Main Interview Guide
    assert "- **The Finish Line** H\n\n\n\n# Main Interview Guide" in result
    # One blank line between do_not_rush and core_vs_probe group
    assert "- **Do Not Rush** A\n\n- **Core vs. Probe:**" in result
    # Priority & Focus is the headline rule, followed by a blank line then Do Not Rush
    assert "# Pacing Instructions\n- **Priority & Focus:** Z\n\n- **Do Not Rush** A" in result


def _make_review_response(overall="pass", item_issues=None, structural_issues=None):
    """Build a fake Anthropic response that looks like a submit_review tool call."""
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "submit_review"
    tool_block.input = {
        "overall": overall,
        "item_issues": item_issues or [],
        "structural_issues": structural_issues or [],
    }
    resp = MagicMock()
    resp.content = [tool_block]
    return resp


def test_polish_no_fixable_issues_returns_empty():
    """When review finds no item issues with suggestions, /polish returns {updates: []}."""
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        with patch("app.client.messages.create",
                   return_value=_make_review_response(overall="pass")):
            resp = c.post("/polish", json={"sections": {}})
    assert resp.status_code == 200
    assert resp.get_json() == {"updates": []}


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

import json
import logging
import os
import traceback
from flask import Flask, request, Response, render_template, jsonify
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, PORT

app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, "prompts", "gathering.txt")) as f:
    GATHERING_PROMPT = f.read()

with open(os.path.join(BASE_DIR, "prompts", "review.txt")) as f:
    REVIEW_PROMPT = f.read()

with open(os.path.join(BASE_DIR, "prompts", "fixer.txt")) as f:
    FIXER_PROMPT = f.read()

conversation_history = []

GATHERING_TOOLS = [
    {
        "name": "update_metadata",
        "description": "Set the interview title in the template metadata.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"]
        }
    },
    {
        "name": "update_pacing",
        "description": "Update one named pacing rule. Only call if the client explicitly requests a change.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule": {
                    "type": "string",
                    "enum": ["do_not_rush", "core_vs_probe", "one_ask_per_turn", "keep_light",
                             "follow_signals", "original_followups", "selective_probing", "finish_line"]
                },
                "text": {"type": "string"}
            },
            "required": ["rule", "text"]
        }
    },
    {
        "name": "update_focus",
        "description": "Set the interview focus anchor statement.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    },
    {
        "name": "add_topic",
        "description": "Add or replace a numbered topic in the main interview guide.",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "integer", "description": "1-based topic number"},
                "title": {"type": "string"},
                "priority": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5,
                    "description": "Overall topic importance 1–5. Default 3 if unsure."
                },
                "core": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Item importance 1–5. Default 3 if unsure."
                            }
                        },
                        "required": ["text"]
                    }
                },
                "probe": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5,
                                "description": "Item importance 1–5. Default 3 if unsure."
                            }
                        },
                        "required": ["text"]
                    }
                }
            },
            "required": ["index", "title", "core"]
        }
    },
    {
        "name": "remove_topic",
        "description": "Remove a topic by its 1-based index.",
        "input_schema": {
            "type": "object",
            "properties": {"index": {"type": "integer"}},
            "required": ["index"]
        }
    },
    {
        "name": "update_expansion",
        "description": "Set the full list of expansion topics — secondary themes to explore if the main guide runs short. Call in the initial burst with domain-inferred drafts, and re-call whenever the research focus or main topic set changes significantly. Items should be concise topic labels, distinct from the main topics.",
        "input_schema": {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            "required": ["items"]
        }
    }
]

REVIEW_TOOL = {
    "name": "submit_review",
    "description": "Submit the quality review findings for the interview template.",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall": {
                "type": "string",
                "enum": ["pass", "warning", "error"]
            },
            "item_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic_index": {"type": "integer"},
                        "topic_title": {"type": "string"},
                        "item_type": {"type": "string", "enum": ["core", "probe"]},
                        "item_index": {"type": "integer"},
                        "text": {"type": "string"},
                        "rule": {"type": "string"},
                        "severity": {"type": "string", "enum": ["error", "warning"]},
                        "explanation": {"type": "string"},
                        "suggestion": {"type": "string"}
                    },
                    "required": ["topic_index", "topic_title", "item_type",
                                 "item_index", "text", "rule", "severity", "explanation"]
                }
            },
            "structural_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "rule": {"type": "string"},
                        "severity": {"type": "string", "enum": ["error", "warning"]},
                        "explanation": {"type": "string"}
                    },
                    "required": ["rule", "severity", "explanation"]
                }
            }
        },
        "required": ["overall", "item_issues", "structural_issues"]
    }
}

FIXER_TOOLS = [t for t in GATHERING_TOOLS if t["name"] == "add_topic"]


def _run_review(sections: dict) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=REVIEW_PROMPT,
        tools=[REVIEW_TOOL],
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": f"Review this interview template:\n\n{json.dumps(sections, indent=2)}"
        }]
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_review":
            return block.input
    raise ValueError("reviewer returned no tool call")


def _run_fixer(sections: dict, item_issues: list) -> list:
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=FIXER_PROMPT,
        tools=FIXER_TOOLS,
        tool_choice={"type": "any"},
        messages=[{
            "role": "user",
            "content": (
                f"Here is the current template:\n\n{json.dumps(sections, indent=2)}\n\n"
                f"Here are the specific items that need fixing:\n\n"
                f"{json.dumps(item_issues, indent=2)}\n\n"
                "Fix only the flagged items. Preserve all other items exactly as they are."
            )
        }]
    )
    updates = []
    for block in response.content:
        if block.type == "tool_use" and block.name == "add_topic":
            updates.append(process_tool_call("add_topic", block.input))
    return updates


def build_settings_context(settings):
    """Return a system-prompt snippet from UI settings, or '' if nothing meaningful."""
    if not settings or not isinstance(settings, dict):
        return ''
    _VALID_DEPTH_LABELS = {"Breadth", "Slightly Broad", "Balanced", "Slightly Deep", "Deep"}
    depth_value = settings.get('depthValue')
    depth_label = settings.get('depthLabel', '')
    if depth_label not in _VALID_DEPTH_LABELS:
        depth_label = 'Balanced'
    target = settings.get('durationTarget', 0)
    estimate = settings.get('estimate', 0)

    if not isinstance(depth_value, (int, float)) or not (0 <= depth_value <= 100):
        depth_value = None
    if not isinstance(target, (int, float)):
        target = 0
    target = max(0, min(90, int(target)))
    if not isinstance(estimate, (int, float)):
        estimate = 0
    estimate = max(0, min(90, int(estimate)))

    lines = []
    if depth_value is not None:
        lines.append(f'Depth/breadth slider: {int(depth_value)}/100 ({depth_label})')
    if target > 0:
        lines.append(f'Duration target: {target} min')
        lines.append(f'Current estimate: {estimate} min')
    if not lines:
        return ''
    return '\n\n## Current UI settings\n' + '\n'.join(f'- {l}' for l in lines)


def _normalise_item(item):
    if isinstance(item, str):
        return {"text": item, "priority": 3}
    return {"text": item["text"], "priority": item.get("priority", 3)}


def format_template(sections: dict) -> str:
    meta = sections.get("metadata", {})
    title = meta.get("title") or ""
    version = meta.get("version") or "1.0"
    date = meta.get("date") or ""
    pacing = sections.get("pacing", {})
    focus = sections.get("focus", "")
    topics = sections.get("topics", [])
    expansion = sections.get("expansion", [])

    parts = []
    parts.append(f"[Prompt metadata only: {title} | v{version} | {date}]")
    parts.append("")
    parts.append("# Pacing Instructions")
    parts.append(f"- **Do Not Rush** {pacing.get('do_not_rush', '')}")
    parts.append("")
    parts.append(f"- **Core vs. Probe:** {pacing.get('core_vs_probe', '')}")
    parts.append(f"- **One main ask per turn:** {pacing.get('one_ask_per_turn', '')}")
    parts.append(f"- **Keep questions light:** {pacing.get('keep_light', '')}")
    parts.append("")
    parts.append(f"- **Follow strong signals:** {pacing.get('follow_signals', '')}")
    parts.append(f"- **Original follow-ups allowed:** {pacing.get('original_followups', '')}")
    parts.append(f"- **Selective probing:** {pacing.get('selective_probing', '')}")
    parts.append("")
    parts.append(f"- **The Finish Line** {pacing.get('finish_line', '')}")
    parts.append("")
    parts.append("")
    parts.append("")
    parts.append(f"# Main Interview Guide: {title}")
    parts.append("")

    if focus:
        parts.append("## Interview focus")
        parts.append(f"- [Core] {focus}")
        parts.append("")

    for i, topic in enumerate(topics, 1):
        p = topic.get("priority", 3)
        parts.append(f"## Topic {i} [P:{p}]: {topic.get('title', '')}")
        for item in topic.get("core", []):
            item = _normalise_item(item)
            parts.append(f"- [Core][P:{item['priority']}] {item['text']}")
        for item in topic.get("probe", []):
            item = _normalise_item(item)
            parts.append(f"- [Probe][P:{item['priority']}] {item['text']}")
        parts.append("")

    if expansion:
        parts.append("# Expansion Topics")
        parts.append("Use these for secondary discovery as instructed")
        for item in expansion:
            parts.append(f"- {item}")

    return "\n".join(parts)


def process_tool_call(name, input_data):
    if name == "update_metadata":
        return {"section": "metadata", "payload": {"title": input_data["title"]}}
    elif name == "update_pacing":
        return {"section": "pacing", "payload": {"rule": input_data["rule"], "text": input_data["text"]}}
    elif name == "update_focus":
        return {"section": "focus", "payload": input_data["text"]}
    elif name == "add_topic":
        return {"section": "topic", "payload": {
            "index": input_data["index"],
            "title": input_data["title"],
            "priority": input_data.get("priority", 3),
            "core": [_normalise_item(i) for i in input_data["core"]],
            "probe": [_normalise_item(i) for i in input_data.get("probe", [])]
        }}
    elif name == "remove_topic":
        return {"section": "remove_topic", "payload": {"index": input_data["index"]}}
    elif name == "update_expansion":
        return {"section": "expansion", "payload": input_data["items"]}
    else:
        raise ValueError(f"Unknown tool: {name}")


def stream_conversation(new_message, system=None):
    if system is None:
        system = GATHERING_PROMPT
    conversation_history.append({"role": "user", "content": new_message})

    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=GATHERING_TOOLS,
            messages=conversation_history
        ) as stream:
            for text in stream.text_stream:
                yield f"event: chat_token\ndata: {json.dumps(text)}\n\n"
            final = stream.get_final_message()

        conversation_history.append({
            "role": "assistant",
            "content": [b.model_dump(exclude_none=True) for b in final.content]
        })

        if final.stop_reason == "tool_use":
            tool_results = []
            for block in final.content:
                if block.type == "tool_use":
                    update = process_tool_call(block.name, block.input)
                    yield f"event: section_update\ndata: {json.dumps(update)}\n\n"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "Done"
                    })
            conversation_history.append({"role": "user", "content": tool_results})
        else:
            break

    yield f"event: done\ndata: {{}}\n\n"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data["message"]
    settings = data.get("settings", {})
    settings_context = build_settings_context(settings)
    system = GATHERING_PROMPT + settings_context
    def safe_stream():
        try:
            yield from stream_conversation(message, system)
        except Exception as e:
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps(type(e).__name__ + ': ' + str(e))}\n\n"
    return Response(safe_stream(), mimetype="text/event-stream")


@app.route("/export", methods=["POST"])
def export_route():
    body = request.get_json(silent=True) or {}
    sections = body.get("sections", {})

    try:
        template_text = format_template(sections)

        def safe_str(s, default=""):
            return "".join(c if c.isalnum() or c in " -_" else "" for c in str(s or default)).strip()

        title = sections.get("metadata", {}).get("title", "template")
        version = sections.get("metadata", {}).get("version", "1.0")
        date = sections.get("metadata", {}).get("date", "")
        safe_title = safe_str(title, "template").replace(" ", "-")
        safe_version = safe_str(version, "1.0")
        safe_date = safe_str(date)
        filename = f"{safe_title}-v{safe_version}-{safe_date}.txt"

        output_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(template_text)

        return jsonify({"template": template_text, "filename": filename})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/reset", methods=["POST"])
def reset():
    conversation_history.clear()
    return jsonify({"ok": True})


@app.route("/polish", methods=["POST"])
def polish_route():
    body = request.get_json(silent=True) or {}
    sections = body.get("sections", {})
    try:
        review = _run_review(sections)
        fixable = [i for i in review.get("item_issues", []) if i.get("suggestion")]
        if not fixable:
            return jsonify({"updates": []})
        updates = _run_fixer(sections, fixable)
        return jsonify({"updates": updates})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"updates": []})


if __name__ == "__main__":
    app.run(port=PORT, debug=True)

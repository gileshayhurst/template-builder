import json
import os
from flask import Flask, request, Response, render_template, jsonify
import anthropic
from config import ANTHROPIC_API_KEY, MODEL, PORT

app = Flask(__name__)
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BASE_DIR = os.path.dirname(__file__)

with open(os.path.join(BASE_DIR, "prompts", "gathering.txt")) as f:
    GATHERING_PROMPT = f.read()

with open(os.path.join(BASE_DIR, "prompts", "generation.txt")) as f:
    GENERATION_PROMPT = f.read()

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
                "core": {"type": "array", "items": {"type": "string"}},
                "probe": {"type": "array", "items": {"type": "string"}}
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
        "description": "Set the full list of expansion topics.",
        "input_schema": {
            "type": "object",
            "properties": {"items": {"type": "array", "items": {"type": "string"}}},
            "required": ["items"]
        }
    }
]


def _normalise_item(item):
    if isinstance(item, str):
        return {"text": item, "priority": 3}
    return {"text": item["text"], "priority": item.get("priority", 3)}


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


def stream_conversation(new_message):
    conversation_history.append({"role": "user", "content": new_message})

    while True:
        with client.messages.stream(
            model=MODEL,
            max_tokens=4096,
            system=GATHERING_PROMPT,
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
    message = request.json["message"]
    def safe_stream():
        try:
            yield from stream_conversation(message)
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps(type(e).__name__ + ': ' + str(e))}\n\n"
    return Response(safe_stream(), mimetype="text/event-stream")


@app.route("/export", methods=["POST"])
def export_route():
    sections = request.json["sections"]

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=GENERATION_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Format this template data into the exact template syntax:\n\n{json.dumps(sections, indent=2)}"
        }]
    )

    template_text = response.content[0].text

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


@app.route("/reset", methods=["POST"])
def reset():
    conversation_history.clear()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(port=PORT, debug=True)

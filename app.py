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
            "core": input_data["core"],
            "probe": input_data.get("probe", [])
        }}
    elif name == "remove_topic":
        return {"section": "remove_topic", "payload": {"index": input_data["index"]}}
    elif name == "update_expansion":
        return {"section": "expansion", "payload": input_data["items"]}
    else:
        raise ValueError(f"Unknown tool: {name}")

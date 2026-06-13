import json, sys, os, pytest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
import app as app_module
from app import app as flask_app


@pytest.fixture(autouse=True)
def clear_history():
    app_module.conversation_history.clear()
    yield
    app_module.conversation_history.clear()


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def make_mock_stream(text_chunks=None, tool_blocks=None):
    text_chunks = text_chunks or ["Hello ", "world"]
    tool_blocks = tool_blocks or []

    class FinalMsg:
        stop_reason = "tool_use" if tool_blocks else "end_turn"
        content = tool_blocks

    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter(text_chunks)
        def get_final_message(self): return FinalMsg()

    return Stream()


def make_end_stream():
    class FinalMsg:
        stop_reason = "end_turn"
        content = []
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter([])
        def get_final_message(self): return FinalMsg()
    return Stream()


def test_reset_clears_history(client):
    app_module.conversation_history.append({"role": "user", "content": "hi"})
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    assert app_module.conversation_history == []


def test_chat_returns_sse(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hi ", "there"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        body = resp.data.decode()  # consume inside patch so generator runs with mock
    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type
    assert "event: chat_token" in body
    assert "Hi " in body
    assert "event: done" in body


def test_chat_appends_to_history(client):
    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Reply"])
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        _ = resp.data  # consume stream so generator runs to completion
    assert len(app_module.conversation_history) == 2
    assert app_module.conversation_history[0] == {"role": "user", "content": "Hello"}
    assert app_module.conversation_history[1]["role"] == "assistant"


def test_chat_emits_section_update_on_tool_call(client):
    class ToolBlock:
        type = "tool_use"
        id = "tu_abc"
        name = "update_focus"
        input = {"text": "Anchor on cooking."}
        def model_dump(self, **kwargs):
            return {"type": "tool_use", "id": self.id, "name": self.name, "input": self.input}

    with patch("app.client") as mock_client:
        mock_client.messages.stream.side_effect = [
            make_mock_stream(text_chunks=[], tool_blocks=[ToolBlock()]),
            make_end_stream()
        ]
        resp = client.post("/chat",
            data=json.dumps({"message": "Hello"}),
            content_type="application/json")
        body = resp.data.decode()  # consume inside patch so both stream calls use mocks
    assert "event: section_update" in body
    assert "focus" in body
    assert "Anchor on cooking." in body


def test_export_returns_template(client):
    sections = {
        "metadata": {"title": "Cooking Test", "version": "1.0", "date": "2026-06-12"},
        "pacing": {"do_not_rush": "Take it slow."},
        "focus": "Anchor on one cooking occasion.",
        "topics": [{"index": 1, "title": "Confirm occasion", "core": ["Identify dish"], "probe": []}],
        "expansion": ["role of family"]
    }

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="[Prompt metadata only: Cooking Test | v1.0 | 2026-06-12]\n\n# Pacing...")]

    with patch("app.client") as mock_client:
        mock_client.messages.create.return_value = mock_resp
        resp = client.post("/export",
            data=json.dumps({"sections": sections}),
            content_type="application/json")

    assert resp.status_code == 200
    data = resp.get_json()
    assert "template" in data
    assert "filename" in data
    assert "Cooking-Test" in data["filename"]
    assert data["filename"].endswith(".txt")

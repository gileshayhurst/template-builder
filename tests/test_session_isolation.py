import json, sys, os, pytest
from unittest.mock import patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-placeholder")
import app as app_module
from app import app as flask_app


@pytest.fixture(autouse=True)
def clear_conversations():
    app_module.conversations.clear()
    yield
    app_module.conversations.clear()


@pytest.fixture
def app():
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    return flask_app


def test_reset_creates_unique_session_id(app):
    """Each test client gets a distinct session UUID on /reset."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    client1.post("/reset")
    client2.post("/reset")

    with client1.session_transaction() as sess1:
        sid1 = sess1.get("id")
    with client2.session_transaction() as sess2:
        sid2 = sess2.get("id")

    assert sid1 is not None
    assert sid2 is not None
    assert sid1 != sid2


def test_reset_only_clears_own_session(app):
    """Resetting one session leaves another session's history untouched."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    client1.post("/reset")
    client2.post("/reset")

    # Inject history into client2's session
    with client2.session_transaction() as sess:
        sid2 = sess["id"]
    app_module.conversations[sid2] = [{"role": "user", "content": "hello"}]

    # Reset client1 — must not touch client2
    client1.post("/reset")

    assert app_module.conversations[sid2] == [{"role": "user", "content": "hello"}]


def make_mock_stream(text_chunks):
    class FinalMsg:
        stop_reason = "end_turn"
        content = []
    class Stream:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        @property
        def text_stream(self): return iter(text_chunks)
        def get_final_message(self): return FinalMsg()
    return Stream()


def test_two_clients_have_independent_histories(app):
    """Messages sent by one client don't appear in the other client's history."""
    client1 = app.test_client(use_cookies=True)
    client2 = app.test_client(use_cookies=True)

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hi"])
        client1.post("/chat",
            data=json.dumps({"message": "from client1"}),
            content_type="application/json").data

    with patch("app.client") as mock_client:
        mock_client.messages.stream.return_value = make_mock_stream(["Hello"])
        client2.post("/chat",
            data=json.dumps({"message": "from client2"}),
            content_type="application/json").data

    with client1.session_transaction() as sess:
        sid1 = sess["id"]
    with client2.session_transaction() as sess:
        sid2 = sess["id"]

    history1 = app_module.conversations[sid1]
    history2 = app_module.conversations[sid2]

    assert any(m["content"] == "from client1" for m in history1 if m["role"] == "user")
    assert not any(m.get("content") == "from client2" for m in history1)
    assert any(m["content"] == "from client2" for m in history2 if m["role"] == "user")
    assert not any(m.get("content") == "from client1" for m in history2)

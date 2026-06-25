import os

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "review.txt"
)


def _prompt_text():
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().lower()


def test_review_has_visual_stimulus_check():
    text = _prompt_text()
    assert "requires_visual_stimulus (severity: error)" in text
    assert "there is no screen" in text  # substantive description, not just the header


def test_review_has_enumeration_check():
    text = _prompt_text()
    assert "enumeration_or_ranking (severity: warning)" in text
    assert "draw items out one at a time through narrative" in text  # substantive description

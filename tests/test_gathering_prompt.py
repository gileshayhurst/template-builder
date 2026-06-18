import os

PROMPT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "prompts", "gathering.txt"
)


def _prompt_text():
    with open(PROMPT_PATH, encoding="utf-8") as f:
        return f.read().lower()


def test_prompt_has_consumer_framing():
    assert "live interview with a real person" in _prompt_text()


def test_prompt_has_objective_rules():
    text = _prompt_text()
    assert "one objective = one ask" in text
    assert "exploratory verbs" in text
    assert "determine" in text          # banned-verb list present
    assert "specificity floor" in text


def test_prompt_has_core_probe_definitions():
    text = _prompt_text()
    assert "askable cold" in text
    assert "new direction" in text


def test_prompt_has_focus_anchor_rule():
    assert "experience anchor" in _prompt_text()


def test_prompt_has_consolidation_gate():
    text = _prompt_text()
    assert "consolidation gate" in text
    assert "no two topics overlap" in text


def test_prompt_has_anti_pattern_table():
    text = _prompt_text()
    assert "red flag" in text
    assert "double-barreled" in text

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


def test_prompt_has_settings_awareness():
    text = _prompt_text()
    assert "ui settings awareness" in text
    assert "flag" in text
    assert "25%" in text


def test_prompt_has_no_typical_framing_rule():
    text = _prompt_text()
    assert "no \"typical\" framing" in text


def test_prompt_has_scope_to_slice_rule():
    assert "scope to a slice" in _prompt_text()


def test_prompt_has_no_comparison_as_core_rule():
    assert "no comparison-as-core" in _prompt_text()


def test_prompt_anti_patterns_include_typical_framing():
    assert "typical commute / typical day" in _prompt_text()


def test_prompt_anti_patterns_include_high_altitude_scope():
    assert "overall impression / from start to finish" in _prompt_text()


def test_prompt_anti_patterns_include_comparison_trap():
    assert "how does x compare to y" in _prompt_text()


def test_prompt_worked_example_has_before_after_pairs():
    text = _prompt_text()
    assert "\"typical\" trap" in text
    assert "high-altitude scope" in text
    assert "comparison trap" in text


def test_prompt_has_voiceability_rule():
    text = _prompt_text()
    assert "voiceable by ear" in text
    assert "there is no screen" in text


def test_prompt_anti_patterns_include_visual_and_enumeration():
    text = _prompt_text()
    assert "no screen in a voice call" in text
    assert "draw items out one at a time through narrative" in text


def test_prompt_consolidation_gate_has_voice_check():
    assert "answerable by voice alone" in _prompt_text()

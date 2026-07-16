import os

APP_JS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "app.js")


def _app_js():
    with open(APP_JS, encoding="utf-8") as f:
        return f.read()


def test_every_finish_line_has_coverage_backstop():
    # One occurrence per source finish_line: PACING_DEFAULTS + 4 explicit presets
    # (balanced spreads from defaults, so no 6th).
    assert _app_js().count("the latest uncovered [P:5] topic") == 5


def test_backstop_names_the_p5_jump():
    assert "[P:5] topic has not yet been reached" in _app_js()

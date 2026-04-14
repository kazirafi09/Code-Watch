from __future__ import annotations


def test_full_prompt_includes_code():
    from backend.services.prompt_builder import build_prompt

    prompt = build_prompt("main.py", "python", "full", "x = 1\ny = 2\n")
    assert "main.py" in prompt
    assert "python" in prompt
    assert "x = 1" in prompt


def test_diff_prompt_includes_diff():
    from backend.services.prompt_builder import build_prompt

    diff = "@@ -1,2 +1,3 @@\n x = 1\n+y = 2\n z = 3\n"
    prompt = build_prompt("main.py", "python", "diff", diff)
    assert "main.py" in prompt
    assert "@@" in prompt


def test_prompt_truncation():
    from backend.services.prompt_builder import build_prompt, TRUNCATION_MARKER

    long_code = "x = 1\n" * 10000
    prompt = build_prompt("main.py", "python", "full", long_code, max_chars=500)
    assert TRUNCATION_MARKER in prompt
    assert len(prompt) < 600


def test_severity_detection():
    from backend.services.reviewer import _detect_severity

    assert _detect_severity("This is a critical security vulnerability") == "critical"
    assert _detect_severity("There is a warning about this bug") == "warning"
    assert _detect_severity("This is a minor suggestion") == "suggestion"

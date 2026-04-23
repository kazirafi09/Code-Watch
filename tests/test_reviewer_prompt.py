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
    from backend.services.prompt_builder import TRUNCATION_MARKER, build_prompt

    long_code = "x = 1\n" * 10000
    prompt = build_prompt("main.py", "python", "full", long_code, max_chars=6000)
    assert TRUNCATION_MARKER in prompt
    assert len(prompt) < 6200  # small slack for template boilerplate


def test_severity_detection():
    from backend.services.reviewer import _detect_severity

    # Free-form output (no JSON, no headers) → falls back to phrase match.
    assert _detect_severity("This is a critical security vulnerability") == "critical"
    assert _detect_severity("There is a warning about this bug") == "warning"
    assert _detect_severity("This is a minor suggestion") == "suggestion"


def test_severity_from_structured_json():
    from backend.services.reviewer import _detect_severity

    output = """## Summary
One issue.

## Issues
### [critical] L5 — foo (confidence: 0.9)

## Machine-readable
```json
{"issues": [{"severity": "critical", "confidence": 0.9, "line": 5, "title": "foo"}]}
```
"""
    assert _detect_severity(output, 0.5) == "critical"


def test_low_confidence_filtered():
    from backend.services.reviewer import _detect_severity

    output = """## Machine-readable
```json
{"issues": [{"severity": "critical", "confidence": 0.2, "line": 5, "title": "hunch"}]}
```
"""
    # Below threshold → no critical surfaces, falls back to suggestion.
    assert _detect_severity(output, 0.5) == "suggestion"


def test_full_diff_prompt_includes_both():
    from backend.services.prompt_builder import build_prompt

    code = "def foo():\n    return 1\n"
    diff = "@@ -1,2 +1,2 @@\n-    return 0\n+    return 1\n"
    prompt = build_prompt("main.py", "python", "full+diff", {"code": code, "diff": diff})
    assert "Full file:" in prompt
    assert "Recent diff:" in prompt
    assert "def foo" in prompt
    assert "@@" in prompt

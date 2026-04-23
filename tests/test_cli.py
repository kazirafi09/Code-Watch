from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch, tmp_path):
    """Pin the CLI to a loopback Ollama and a known model for each test."""
    import backend.core.config as cfg_mod

    cfg_mod._config = None
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "model: 'test-model'\nollama_url: 'http://localhost:11434'\n"
    )
    yield
    cfg_mod._config = None


def _install_fake_client(monkeypatch, tokens: list[str]):
    """Replace get_ollama_client with a stub that yields preset tokens."""

    class _Stub:
        async def generate_stream(self, model, prompt):
            for t in tokens:
                yield t

        async def close(self):
            return None

    monkeypatch.setattr(
        "backend.services.ollama_client.get_ollama_client",
        lambda: _Stub(),
    )


def test_cli_missing_file_returns_2(tmp_path):
    from backend.cli.main import main

    rc = main(["review", str(tmp_path / "nope.py"), "--quiet"])
    assert rc == 2


def test_cli_clean_review_exits_zero(tmp_path, monkeypatch, capsys):
    target = tmp_path / "clean.py"
    target.write_text("def add(a, b):\n    return a + b\n")

    # Model returns a checklist that marks everything absent → severity falls
    # back to "suggestion" because no header blocks are present.
    clean_output = "## Summary\nNothing flagged.\n## Issues\nNone.\n"
    _install_fake_client(monkeypatch, [clean_output])

    from backend.cli.main import main

    rc = main(["review", str(target), "--quiet", "--fail-on", "critical"])
    assert rc == 0


def test_cli_critical_review_exits_one(tmp_path, monkeypatch):
    target = tmp_path / "bad.py"
    target.write_text("import os\nos.system(user_input)\n")

    # Emit a header block that _detect_severity classifies as critical.
    critical_output = (
        "## Summary\nUnsafe shell call.\n"
        "## Issues\n### [critical] L2 — command injection (confidence: 0.95)\n"
        "os.system is unsafe with untrusted input.\n"
        '```json\n{"issues": [{"severity": "critical", "confidence": 0.95, '
        '"line": 2, "category": "command_injection", "title": "os.system", '
        '"rationale": "user_input flows to shell"}]}\n```\n'
    )
    _install_fake_client(monkeypatch, [critical_output])

    from backend.cli.main import main

    rc = main(["review", str(target), "--quiet", "--fail-on", "critical"])
    assert rc == 1


def test_cli_fail_on_warning_escalates(tmp_path, monkeypatch):
    target = tmp_path / "warn.py"
    target.write_text("x = 1\n")

    warning_output = (
        "## Issues\n### [warning] L1 — something suspicious (confidence: 0.7)\n"
        '```json\n{"issues": [{"severity": "warning", "confidence": 0.7, '
        '"line": 1, "category": "other", "title": "x", "rationale": "y"}]}\n```\n'
    )
    _install_fake_client(monkeypatch, [warning_output])

    from backend.cli.main import main

    # fail-on=critical → 0, fail-on=warning → 1
    assert main(["review", str(target), "--quiet", "--fail-on", "critical"]) == 0
    assert main(["review", str(target), "--quiet", "--fail-on", "warning"]) == 1


def test_cli_no_model_configured_returns_2(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text("model: ''\n")
    import backend.core.config as cfg_mod

    cfg_mod._config = None

    target = tmp_path / "f.py"
    target.write_text("pass\n")

    from backend.cli.main import main

    assert main(["review", str(target), "--quiet"]) == 2

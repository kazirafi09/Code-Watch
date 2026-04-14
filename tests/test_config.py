from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml


def test_default_config_loads():
    import backend.core.config as cfg_mod
    cfg_mod._config = None
    # Without config.yaml, defaults should apply
    cfg = cfg_mod._build_config()
    assert cfg.ollama_url == "http://localhost:11434"
    assert cfg.debounce_seconds == 1.5
    assert ".py" in cfg.watch_extensions


def test_config_update_persists(tmp_path, monkeypatch):
    import backend.core.config as cfg_mod

    config_file = tmp_path / "config.yaml"
    config_file.write_text("model: ''\nollama_url: 'http://localhost:11434'\n")
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", config_file)
    cfg_mod._config = None

    cfg_mod.update({"model": "codellama:latest"})

    with config_file.open() as f:
        data = yaml.safe_load(f)
    assert data["model"] == "codellama:latest"


def test_secrets_not_written_to_yaml(tmp_path, monkeypatch):
    import backend.core.config as cfg_mod

    config_file = tmp_path / "config.yaml"
    config_file.write_text("model: ''\n")
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", config_file)
    cfg_mod._config = None

    cfg_mod.update({"notifications": {"telegram_token": "secret123"}})

    with config_file.open() as f:
        data = yaml.safe_load(f)
    notifications = data.get("notifications", {})
    assert "telegram_token" not in notifications


def test_invalid_review_mode_raises():
    import backend.core.config as cfg_mod
    with pytest.raises(Exception):
        cfg_mod.AppConfig(review_mode="invalid_mode")

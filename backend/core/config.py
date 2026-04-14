from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("config.yaml")
ENV_PATH = Path(".env")

_change_callbacks: list = []


class NotificationSettings(BaseSettings):
    desktop: bool = True
    desktop_severities: list[str] = ["critical", "warning"]
    telegram: bool = False
    telegram_severities: list[str] = ["critical"]
    telegram_token: str = ""
    telegram_chat_id: str = ""

    model_config = {"extra": "ignore"}


class AppConfig(BaseSettings):
    # Ollama
    model: str = ""
    ollama_url: str = "http://localhost:11434"
    ollama_timeout_seconds: int = 120

    # Watching
    watch_extensions: list[str] = [
        ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
        ".java", ".cpp", ".c", ".h", ".rb", ".php", ".cs", ".kt", ".swift",
    ]
    ignore_patterns: list[str] = [
        "node_modules", "__pycache__", ".git", "dist", "build", ".venv", ".env",
    ]
    respect_gitignore: bool = True
    debounce_seconds: float = 1.5
    max_file_lines: int = 400
    skip_unchanged: bool = True

    # Review behavior
    review_mode: str = "auto"
    max_concurrency: int = 1
    prompt_max_chars: int = 16000

    # Notifications
    notifications: NotificationSettings = NotificationSettings()

    # Misc
    log_level: str = "INFO"

    model_config = {"extra": "ignore", "env_prefix": "CODEWATCH_"}

    @field_validator("review_mode")
    @classmethod
    def validate_review_mode(cls, v: str) -> str:
        allowed = {"auto", "always_full", "always_diff"}
        if v not in allowed:
            raise ValueError(f"review_mode must be one of {allowed}")
        return v


def _load_yaml() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_env_secrets() -> dict[str, Any]:
    secrets: dict[str, Any] = {}
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if telegram_token:
        secrets["telegram_token"] = telegram_token
    if telegram_chat_id:
        secrets["telegram_chat_id"] = telegram_chat_id
    return secrets


_config: AppConfig | None = None


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = _build_config()
    return _config


def _build_config() -> AppConfig:
    data = _load_yaml()
    env_secrets = _load_env_secrets()

    # Merge env secrets into notifications
    if env_secrets:
        notifications = data.get("notifications", {})
        notifications.update(env_secrets)
        data["notifications"] = notifications

    return AppConfig(**data)


def reload_from_disk() -> AppConfig:
    global _config
    _config = _build_config()
    logger.info("Config reloaded from disk")
    _notify_callbacks()
    return _config


def update(patch: dict[str, Any]) -> AppConfig:
    global _config
    current = _load_yaml()

    # Never persist secrets to yaml
    secret_keys = {"telegram_token", "telegram_chat_id"}
    notifications_patch = patch.get("notifications", {})
    for key in secret_keys:
        notifications_patch.pop(key, None)

    # Deep merge
    for k, v in patch.items():
        if k == "notifications" and isinstance(v, dict):
            current_notif = current.get("notifications", {})
            current_notif.update({kk: vv for kk, vv in v.items() if kk not in secret_keys})
            current["notifications"] = current_notif
        else:
            current[k] = v

    with CONFIG_PATH.open("w", encoding="utf-8") as f:
        yaml.dump(current, f, default_flow_style=False, allow_unicode=True)

    return reload_from_disk()


def register_change_callback(cb) -> None:
    _change_callbacks.append(cb)


def _notify_callbacks() -> None:
    for cb in _change_callbacks:
        try:
            cb()
        except Exception:
            logger.exception("Error in config change callback")

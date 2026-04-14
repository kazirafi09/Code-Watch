from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from backend.core import config as cfg_module

router = APIRouter(prefix="/api/config", tags=["config"])
logger = logging.getLogger(__name__)


class ConfigResponse(BaseModel):
    model: str
    ollama_url: str
    ollama_timeout_seconds: int
    watch_extensions: list[str]
    ignore_patterns: list[str]
    respect_gitignore: bool
    debounce_seconds: float
    max_file_lines: int
    skip_unchanged: bool
    review_mode: str
    max_concurrency: int
    prompt_max_chars: int
    notifications: dict[str, Any]
    log_level: str


def _safe_config() -> dict[str, Any]:
    cfg = cfg_module.get_config()
    notif = cfg.notifications
    return {
        "model": cfg.model,
        "ollama_url": cfg.ollama_url,
        "ollama_timeout_seconds": cfg.ollama_timeout_seconds,
        "watch_extensions": cfg.watch_extensions,
        "ignore_patterns": cfg.ignore_patterns,
        "respect_gitignore": cfg.respect_gitignore,
        "debounce_seconds": cfg.debounce_seconds,
        "max_file_lines": cfg.max_file_lines,
        "skip_unchanged": cfg.skip_unchanged,
        "review_mode": cfg.review_mode,
        "max_concurrency": cfg.max_concurrency,
        "prompt_max_chars": cfg.prompt_max_chars,
        "notifications": {
            "desktop": notif.desktop,
            "desktop_severities": notif.desktop_severities,
            "telegram": notif.telegram,
            "telegram_severities": notif.telegram_severities,
            # Redact secrets
            "telegram_token": "***" if notif.telegram_token else "",
            "telegram_chat_id": "***" if notif.telegram_chat_id else "",
        },
        "log_level": cfg.log_level,
    }


@router.get("")
async def get_config() -> dict[str, Any]:
    return _safe_config()


@router.post("")
async def update_config(patch: dict[str, Any]) -> dict[str, Any]:
    # Strip redacted values before persisting
    notif_patch = patch.get("notifications", {})
    for secret_key in ("telegram_token", "telegram_chat_id"):
        if notif_patch.get(secret_key) == "***":
            notif_patch.pop(secret_key)

    cfg_module.update(patch)

    # Trigger watcher reload
    from backend.services.watcher import watcher_supervisor
    watcher_supervisor.reload_config()

    # Restart queue workers if concurrency changed
    from backend.services.queue import review_queue
    new_cfg = cfg_module.get_config()
    await review_queue.restart_workers(new_cfg.max_concurrency)

    return _safe_config()

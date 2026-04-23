from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["status"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_status() -> dict[str, Any]:
    from backend.core.config import get_config
    from backend.services.ollama_client import get_ollama_client
    from backend.services.queue import review_queue
    from backend.services.reviewer import get_last_stats

    cfg = get_config()
    client = get_ollama_client()
    ollama_ok = await client.health()
    last_duration_ms, tokens_per_sec = get_last_stats()

    from backend.core.database import get_pending_review_count

    pending_reviews = get_pending_review_count()

    return {
        "ollama_ok": ollama_ok,
        "model": cfg.model,
        "queue_depth": review_queue.depth,
        "pending_reviews": pending_reviews,
        "last_duration_ms": last_duration_ms or None,
        "tokens_per_sec": round(tokens_per_sec, 2) if tokens_per_sec else None,
    }


@router.delete("/queue", status_code=200)
async def clear_queue() -> dict[str, int]:
    from backend.core.database import cleanup_pending_reviews
    from backend.services.queue import review_queue

    removed = await review_queue.clear()
    removed += cleanup_pending_reviews()
    return {"removed": removed}


@router.get("/models")
async def list_models() -> dict[str, Any]:
    from backend.services.ollama_client import OllamaUnavailableError, get_ollama_client

    client = get_ollama_client()
    try:
        models = await client.list_models()
        return {"models": models, "available": True}
    except OllamaUnavailableError:
        return {"models": [], "available": False}

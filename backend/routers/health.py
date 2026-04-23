from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/livez", include_in_schema=False)
async def livez() -> dict[str, str]:
    """Liveness: is the process up? Always 200 unless the process is dying."""
    return {"status": "ok"}


@router.get("/healthz", include_in_schema=False)
async def healthz() -> JSONResponse:
    """Readiness: are our dependencies (DB, Ollama) usable?

    Returns 200 when everything is healthy, 503 when any dependency is down —
    so Docker / k8s / uptime pings get a truthful signal and don't route
    traffic to a broken backend.
    """
    from sqlmodel import Session, text

    from backend.core.database import engine
    from backend.services.ollama_client import get_ollama_client

    checks: dict[str, bool] = {}

    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        checks["db"] = True
    except Exception as exc:
        logger.warning("healthz: db check failed: %s", exc)
        checks["db"] = False

    try:
        client = get_ollama_client()
        checks["ollama"] = await client.health()
    except Exception as exc:
        logger.warning("healthz: ollama check failed: %s", exc)
        checks["ollama"] = False

    ok = all(checks.values())
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "checks": checks},
    )

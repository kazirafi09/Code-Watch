from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core import config as cfg_module
from backend.core.auth import get_or_create_token, is_auth_enabled, require_token
from backend.core.database import init_db
from backend.core.logging import setup_logging
from backend.core.ws_manager import manager
from backend.models.events import Toast
from backend.routers import config, health, projects, reviews, status, ws
from backend.services.queue import review_queue
from backend.services.reviewer import reviewer
from backend.services.watcher import watcher_supervisor

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Keep strong refs to fire-and-forget tasks so the event loop doesn't GC them
# mid-flight (the asyncio docs are explicit about this; ruff flags it as RUF006).
_BACKGROUND_TASKS: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cfg = cfg_module.get_config()
    setup_logging(cfg.log_level)
    logger.info("Starting CodeWatch...")

    init_db()

    if is_auth_enabled():
        token = get_or_create_token()
        logger.info("Bearer auth enabled. Access URL: http://localhost:8000/?token=%s", token)

    # Remove reviews that were left in "pending" by a previous interrupted run
    from backend.core.database import cleanup_pending_reviews

    removed = cleanup_pending_reviews()
    if removed:
        logger.info("Cleaned up %d orphaned pending review(s) from previous run", removed)

    # Wire up reviewer into queue
    review_queue.set_reviewer(reviewer)

    # Start queue workers
    await review_queue.start(cfg.max_concurrency)

    # Start file watcher
    loop = asyncio.get_event_loop()
    watcher_supervisor.start(loop)

    # Watch all active projects
    from backend.core.database import get_projects

    for project in get_projects():
        if project.is_active:
            watcher_supervisor.add_project(project)

    logger.info("CodeWatch is ready. Open http://localhost:8000")

    yield

    # Shutdown
    logger.info("Shutting down CodeWatch...")
    watcher_supervisor.stop()
    await review_queue.stop()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    app = FastAPI(
        title="CodeWatch",
        description="Local AI code review tool",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:8000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers. Health is public (liveness/readiness probes must be reachable
    # without credentials). Everything else is gated by require_token when
    # CODEWATCH_REQUIRE_TOKEN=1; otherwise the dep is a no-op.
    app.include_router(health.router)
    protected = [Depends(require_token)]
    app.include_router(projects.router, dependencies=protected)
    app.include_router(reviews.router, dependencies=protected)
    app.include_router(config.router, dependencies=protected)
    app.include_router(status.router, dependencies=protected)
    app.include_router(ws.router)

    # Serve built frontend
    if FRONTEND_DIST.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

        @app.get("/", include_in_schema=False)
        async def serve_index() -> FileResponse:
            return FileResponse(str(FRONTEND_DIST / "index.html"))

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            file = FRONTEND_DIST / full_path
            if file.exists() and file.is_file():
                return FileResponse(str(file))
            return FileResponse(str(FRONTEND_DIST / "index.html"))

    # Global error handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        task = asyncio.create_task(
            manager.broadcast(Toast(level="error", message=str(exc)).model_dump())
        )
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "message": str(exc)},
        )

    return app


app = create_app()

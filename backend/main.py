from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.core import config as cfg_module
from backend.core.database import init_db
from backend.core.logging import setup_logging
from backend.core.ws_manager import manager
from backend.models.events import Toast
from backend.routers import config, projects, reviews, status, ws
from backend.services.queue import review_queue
from backend.services.reviewer import reviewer
from backend.services.watcher import watcher_supervisor

logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cfg = cfg_module.get_config()
    setup_logging(cfg.log_level)
    logger.info("Starting CodeWatch...")

    init_db()

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

    # Routers
    app.include_router(projects.router)
    app.include_router(reviews.router)
    app.include_router(config.router)
    app.include_router(status.router)
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
        asyncio.create_task(
            manager.broadcast(Toast(level="error", message=str(exc)).model_dump())
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "message": str(exc)},
        )

    return app


app = create_app()

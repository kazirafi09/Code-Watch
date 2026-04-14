# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend

```bash
# Install dependencies (first time)
python -m venv .venv
.venv/Scripts/activate       # Windows
source .venv/bin/activate    # Unix/macOS
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run the server (dev mode)
uvicorn backend.main:app --reload --port 8000

# Run all tests
pytest

# Run a single test file
pytest tests/test_config.py

# Run a single test
pytest tests/test_reviewer_prompt.py::test_severity_detection

# Lint
ruff check backend/ tests/
ruff format backend/ tests/
```

### Frontend

```bash
cd frontend
npm install
npm run dev      # Vite dev server at http://localhost:5173 (proxies to backend)
npm run build    # Outputs to frontend/dist/ (served by FastAPI in production)
```

### Install & start scripts

```bash
# Unix/macOS one-command setup
./install.sh && ./start.sh

# Windows one-command setup
install.bat
start.bat
```

## Architecture

CodeWatch is a **local AI code review tool**: a FastAPI backend watches project folders, feeds changed files to Ollama, streams the review tokens via WebSocket, and persists reviews to SQLite. A React/Tailwind frontend subscribes to the WebSocket and renders the live feed.

### Request / data flow

```
File save → watchdog (thread) → asyncio.run_coroutine_threadsafe → ReviewQueue
    → Reviewer.run() → OllamaClient.generate_stream() → WS broadcast (token by token)
    → save Review to SQLite → notify() desktop/Telegram
```

### Backend layers

- **`backend/core/`** — cross-cutting concerns: `config.py` (Pydantic Settings + YAML hot-reload), `database.py` (SQLModel + helper functions), `ws_manager.py` (WebSocket `ConnectionManager`), `logging.py`
- **`backend/models/`** — SQLModel DB models (`Project`, `Review`) and Pydantic WS event schemas (`events.py`)
- **`backend/routers/`** — FastAPI routers mounted in `main.py`: `projects`, `reviews`, `config`, `status`, `ws`
- **`backend/services/`** — business logic: `watcher.py` (watchdog supervisor + per-project handlers with debounce/gitignore), `queue.py` (asyncio queue with de-duplication), `reviewer.py` (review pipeline orchestrator), `ollama_client.py` (httpx async Ollama client), `diff.py` (content hash + unified diff cache), `prompt_builder.py` (full-file and diff-aware templates), `notifier.py`
- **`backend/utils/`** — `language.py` (extension→language map), `gitignore.py` (pathspec matcher)

### Frontend layers

- **`src/api/`** — `client.ts` (typed fetch wrapper for all endpoints), `types.ts` (TS types mirroring backend Pydantic models + WS event union)
- **`src/hooks/`** — `useWebSocket` (auto-reconnect with exponential backoff), `useProjects`, `useReviews` (streaming state tracked in a ref), `useStatus` (10s polling)
- **`src/components/`** — `App.tsx` wires everything; `Sidebar` / `ReviewFeed` / `ReviewCard` / `ReviewDetail` / `StatusBar` / `Settings` / `Toast`
- **`src/lib/`** — `severity.ts` (color/badge helpers), `format.ts` (timestamp/duration/basename)

### Key design notes

- **Thread boundary**: watchdog runs in a background thread; jobs are posted to asyncio via `asyncio.run_coroutine_threadsafe`. Never call async code directly from watchdog handlers.
- **Queue de-duplication**: rapid saves to the same `(project_id, path)` replace the pending job rather than stacking — see `ReviewQueue.enqueue()`.
- **Config hot-reload**: `POST /api/config` → `cfg_module.update()` → `reload_from_disk()` → notifies registered callbacks (watcher reload, queue restart). No server restart needed.
- **Secrets**: `telegram_token` / `telegram_chat_id` load only from `.env` (env vars `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`). They are never written to `config.yaml` — see `update()` in `core/config.py`.
- **Path handling**: use `pathlib.Path` everywhere and normalize to POSIX slashes before sending to the frontend.
- **DB helpers**: `backend/core/database.py` exposes free functions (`get_projects`, `save_review`, etc.) that open their own sessions — safe to call from services without dependency injection.

# CodeWatch — Build Prompt for Claude CLI

You are an expert software engineer. Build a complete, production-ready local application called **CodeWatch** — a local AI code review tool that watches a project folder, sends changed files to a local LLM via Ollama, and streams the review results to a web UI in real time. Everything runs locally. No cloud. No internet required after setup.

---

## Project Overview

- **Name:** CodeWatch
- **Purpose:** Watch a local project folder for file changes, automatically send changed files to a local LLM for code review, stream results to a web dashboard in real time
- **LLM runtime:** Ollama (installed separately by the user — CodeWatch only talks to it via REST API at http://localhost:11434)
- **Model:** user-selected — the user installs Ollama themselves and pulls whichever model they want. CodeWatch reads the model name from `config.yaml` and must work with any Ollama-compatible model. Do not hardcode or auto-pull a model.
- **No n8n, no cloud services, no external APIs**

---

## Full Project Structure

Build ALL of the following files with complete, working code. The backend is organized by concern (routers, services, core) rather than as a flat module pile — this keeps it approachable as the project grows.

```
codewatch/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app factory, lifespan, mounts routers + static frontend
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings: loads config.yaml + .env, hot-reload
│   │   ├── database.py          # SQLModel engine + init_db(), session dep
│   │   ├── logging.py           # Structured logging setup (stdlib logging + JSON option)
│   │   └── ws_manager.py        # WebSocket ConnectionManager (broadcast, per-client send)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py           # Project SQLModel
│   │   ├── review.py            # Review SQLModel + ReviewStatus enum
│   │   └── events.py            # Pydantic schemas for WS event payloads
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── projects.py          # /api/projects CRUD
│   │   ├── reviews.py           # /api/reviews list/get/delete/export + manual trigger
│   │   ├── config.py            # /api/config get/update
│   │   ├── status.py            # /api/status (Ollama health, model, metrics)
│   │   └── ws.py                # /ws WebSocket endpoint
│   ├── services/
│   │   ├── __init__.py
│   │   ├── watcher.py           # watchdog Observer, per-project handlers, debounce, gitignore-aware filter
│   │   ├── reviewer.py          # Orchestrates: queue → prompt → Ollama stream → persist → notify
│   │   ├── ollama_client.py     # Thin async client for Ollama REST API (generate stream, list models, health)
│   │   ├── queue.py             # asyncio.Queue-backed review queue with max concurrency
│   │   ├── diff.py              # Compute per-file diff vs last-reviewed snapshot (and git diff when available)
│   │   ├── prompt_builder.py    # Build review prompts (full-file or diff-aware)
│   │   └── notifier.py          # Desktop (plyer) + optional Telegram, non-blocking, safe failures
│   └── utils/
│       ├── __init__.py
│       ├── language.py          # Extension → language name mapping
│       └── gitignore.py         # pathspec-based .gitignore matcher
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css                 # Tailwind entry
│       ├── components/
│       │   ├── Sidebar.tsx           # Project list, add/remove, watcher status per project
│       │   ├── ReviewFeed.tsx        # Virtualized live feed of reviews, filter + search
│       │   ├── ReviewCard.tsx        # Single review: badges, streaming text, actions
│       │   ├── ReviewDetail.tsx      # Right-pane full review with copy/export/delete
│       │   ├── FileTree.tsx          # Tree view of watched folder with "Review now" action
│       │   ├── Settings.tsx          # Model picker (populated from /api/models), patterns, notifications
│       │   ├── StatusBar.tsx         # Ollama status, current model, queue depth, tokens/sec
│       │   └── Toast.tsx             # Transient error/success toasts surfaced from API layer
│       ├── hooks/
│       │   ├── useWebSocket.ts       # WS with auto-reconnect (exponential backoff)
│       │   ├── useProjects.ts        # Project CRUD via REST
│       │   ├── useReviews.ts         # Paginated reviews + live updates from WS
│       │   └── useStatus.ts          # Polls /api/status every 10s
│       ├── api/
│       │   ├── client.ts             # Typed fetch wrapper for all endpoints
│       │   └── types.ts              # Shared TS types mirroring backend Pydantic models
│       └── lib/
│           ├── severity.ts           # Severity color + icon helpers
│           └── format.ts             # Timestamp, filesize, duration helpers
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                   # pytest fixtures: temp DB, temp project dir, mocked Ollama
│   ├── test_config.py
│   ├── test_watcher_debounce.py
│   ├── test_gitignore.py
│   ├── test_queue.py
│   └── test_reviewer_prompt.py
│
├── docs/
│   ├── screenshot.png                # Placeholder — README references this
│   └── architecture.md               # Short diagram + data-flow explainer
│
├── config.example.yaml               # Template config copied to config.yaml on first run
├── .env.example                      # Template for secrets (Telegram token etc.)
├── .gitignore                        # Ignore venv, node_modules, config.yaml, .env, *.db, dist/
├── .editorconfig                     # Consistent whitespace across editors
├── pyproject.toml                    # Ruff + pytest config
├── requirements.txt                  # Runtime Python deps
├── requirements-dev.txt              # Dev deps: pytest, pytest-asyncio, ruff, httpx
├── Dockerfile                        # Multi-stage: build frontend → Python runtime
├── docker-compose.yml                # Service for CodeWatch; expects host-running Ollama
├── install.sh                        # Unix/macOS one-command setup
├── install.bat                       # Windows one-command setup
├── start.sh                          # Unix/macOS start script
├── start.bat                         # Windows start script
├── LICENSE                           # MIT license
└── README.md                         # Setup guide, config reference, troubleshooting
```

---

## Backend Specification

### `backend/main.py`
- FastAPI app factory
- Use `lifespan` context (not deprecated `@app.on_event`) to: load config, init DB, start watcher supervisor, start review queue worker, shut everything down cleanly
- Include routers from `backend/routers/`
- CORS enabled for `http://localhost:5173` (Vite dev) in addition to same-origin
- Mount built frontend at `/` (serve `frontend/dist`); fall through to SPA index for unknown routes
- REST endpoints (implemented across routers):
  - `GET /api/projects` — list all watched projects (each with `is_watching` flag)
  - `POST /api/projects` — add a new project (body: `{name, path}`); validates path exists and is a directory
  - `DELETE /api/projects/{id}` — remove project and stop watching
  - `GET /api/reviews` — paginated review history (query: `project_id`, `severity`, `search`, `limit`, `offset`)
  - `GET /api/reviews/{id}` — single review
  - `DELETE /api/reviews/{id}` — delete a review
  - `GET /api/reviews/{id}/export` — return review as downloadable Markdown
  - `POST /api/reviews/trigger` — manually queue a review (body: `{project_id, relative_path}`)
  - `GET /api/status` — Ollama health, current model, queue depth, last-review duration, tokens/sec
  - `GET /api/models` — list of models currently available in Ollama (proxied from `/api/tags`)
  - `GET /api/config` — return current config as JSON (redact secrets)
  - `POST /api/config` — update config; triggers hot-reload of watcher + reviewer
- WebSocket: `WS /ws` — streams review events, queue updates, and status changes
- Global exception handler surfaces errors as structured JSON and broadcasts a `toast` WS event

### `backend/services/watcher.py`
- `WatcherSupervisor` holds one `watchdog` `Observer` per active project
- Each project handler:
  - watches file extensions from config (default: `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.cpp`, `.c`, `.h`, `.rb`, `.php`, `.cs`, `.kt`, `.swift`)
  - ignores patterns from config AND automatically respects `.gitignore` in the project root (use `pathspec`)
  - debounces: only trigger review if file hasn't changed again within `debounce_seconds` (default 1.5s)
  - skips: files larger than `max_file_lines` lines, binary files (null-byte sniff), files unchanged since last review (content hash)
  - on trigger: enqueue a `ReviewJob(project_id, path)` onto the review queue — never call the reviewer directly
- `add_project(project)` / `remove_project(project_id)` let routers manipulate the supervisor at runtime
- Catches permission and decode errors and logs+skips instead of crashing

### `backend/services/queue.py`
- `ReviewQueue` wraps an `asyncio.Queue[ReviewJob]` with:
  - `max_concurrency` (default 1 — local LLM, one at a time) from config
  - de-duplication: if a job for the same (project_id, path) is already pending, replace it rather than stacking
  - worker task(s) pull jobs and call `reviewer.run(job)`
  - broadcast `queue_update` WS events whenever depth changes

### `backend/services/ollama_client.py`
- Async client using `httpx.AsyncClient`
- Methods: `health() -> bool`, `list_models() -> list[str]`, `generate_stream(model, prompt) -> AsyncIterator[str]`
- Timeouts configurable; streams token-by-token from `/api/generate` with `stream: true`
- Raises typed errors (`OllamaUnavailable`, `OllamaModelNotFound`) that routers translate to 503/404

### `backend/services/diff.py`
- Keeps an in-memory + on-disk cache of last-reviewed content per (project_id, path)
- Computes unified diff vs last snapshot; if the project is a git repo and the file is tracked, prefer `git diff HEAD -- <path>` for richer context
- Returns `(mode, payload)` where mode is `"full"` (first review) or `"diff"` (subsequent), which `prompt_builder` uses to pick a template

### `backend/services/prompt_builder.py`
- Two templates: full-file review and diff-aware review
- Diff template includes the diff plus surrounding context lines and asks the model to focus only on changed regions while flagging anything risky nearby
- Enforces max prompt length by truncating with a clear marker

### `backend/services/reviewer.py`
- Build a structured code review prompt via `prompt_builder`:
  ```
  You are an expert code reviewer. Review the following code for:
  1. Bugs and logic errors
  2. Security vulnerabilities
  3. Performance issues
  4. Code quality and maintainability
  5. Specific improvements with examples

  File: {filename}
  Language: {language}

  ```{language}
  {code}
  ```

  Respond with a structured review. For each issue found, state: severity (critical/warning/suggestion), location (line number if possible), and a concrete fix.
  ```
- Call Ollama REST API: `POST http://localhost:11434/api/generate` with `stream: true`
- Stream tokens via WebSocket to all connected clients using `ws_manager.broadcast()`
- WebSocket message format:
  ```json
  {
    "type": "review_start",
    "review_id": "uuid",
    "project_id": 1,
    "filename": "src/auth.py",
    "timestamp": "ISO8601"
  }
  ```
  ```json
  {
    "type": "review_token",
    "review_id": "uuid",
    "token": "partial text..."
  }
  ```
  ```json
  {
    "type": "review_done",
    "review_id": "uuid",
    "full_text": "complete review...",
    "severity": "warning"
  }
  ```
- After streaming, save complete review to SQLite and call `notifier.notify()`
- Auto-detect severity from content: if review contains "critical" or "security" → `critical`, contains "warning" or "bug" → `warning`, else → `suggestion`

### `backend/core/ws_manager.py`
- `ConnectionManager` class
- Methods: `connect(websocket)`, `disconnect(websocket)`, `broadcast(message: dict)`
- Keep a `List[WebSocket]` of active connections
- Handle disconnect gracefully (remove from list on error)

### `backend/models/*.py`
SQLModel models:
- `Project`: id, name, path, created_at, is_active
- `Review`: id, project_id, filename, language, full_text, severity, mode (`full`|`diff`), prompt_tokens, completion_tokens, duration_ms, created_at
- `ReviewStatus`: enum `critical | warning | suggestion | pending`
- Pydantic `events.py` defines WS payload schemas: `ReviewStart`, `ReviewToken`, `ReviewDone`, `QueueUpdate`, `StatusUpdate`, `Toast`

### `backend/core/database.py`
- SQLite engine at `./codewatch.db` with `check_same_thread=False`
- `init_db()` creates tables on startup (via lifespan)
- `get_session()` FastAPI dependency for request-scoped sessions
- Helper functions used by routers/services: `save_review()`, `get_reviews()`, `get_projects()`, `add_project()`, `delete_project()`

### `backend/core/config.py`
- Pydantic `BaseSettings` (pydantic-settings) merges `config.yaml` + `.env`
- Secrets (`telegram_token`) loaded only from `.env`, never written back to `config.yaml`
- `reload_from_disk()` re-parses files; `update(patch)` merges and persists non-secret fields to `config.yaml`
- Emits `config_changed` events so watcher/reviewer/queue can reconfigure without restart

### `backend/core/logging.py`
- Stdlib logging configured with level from config (`log_level`)
- Optional JSON formatter when running under Docker (`LOG_JSON=1`)
- Route all service modules through named loggers so users can grep by subsystem

### `backend/services/notifier.py`
- Desktop notification via `plyer.notification.notify()` — title: "CodeWatch — {severity}", message: filename + first 100 chars of review
- Optional Telegram: if `telegram_token` and `telegram_chat_id` are set, POST to `https://api.telegram.org/bot{token}/sendMessage`
- Per-severity toggles (e.g. suggestions-silent) from config
- Never crash the main flow if notification fails — wrap in try/except and log

---

## Frontend Specification

### Design
- Dark theme by default (can toggle)
- Three-column layout: narrow sidebar (projects) | main feed (reviews) | detail panel (selected review)
- Monospace font for code content in reviews
- Color-coded severity badges: red for critical, amber for warning, blue for suggestion
- Smooth token streaming — append tokens to the active review card in real time
- Responsive: collapse to single column on narrow screens

### `src/hooks/useWebSocket.ts`
- Connect to `ws://localhost:8000/ws`
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s... max 30s)
- Parse incoming JSON messages and dispatch to state
- Expose: `isConnected`, `lastMessage`, `connectionAttempts`

### `src/hooks/useProjects.ts`
- Fetch projects on mount
- Methods: `addProject(name, path)`, `removeProject(id)`
- Keep local state in sync after mutations

### `src/api/client.ts`
- Base URL: `http://localhost:8000`
- Typed functions for all endpoints: `getProjects()`, `addProject()`, `deleteProject()`, `getReviews()`, `deleteReview()`, `getStatus()`, `getConfig()`, `updateConfig()`
- Handle errors gracefully, return typed results

### `src/components/ReviewCard.tsx`
- Show: filename (with language icon), severity badge, timestamp, streaming text or full review
- While streaming: show a blinking cursor at the end of the text
- When done: show "Copy" button, "Delete" button
- Parse review text to highlight severity words: wrap "critical", "security", "bug" in red spans; "warning" in amber; "suggestion" in blue

### `src/components/Settings.tsx`
- Form to update: **model dropdown populated from `GET /api/models`** (falls back to free-text input if Ollama unreachable) with "Test connection" button, debounce seconds, max file lines, max concurrency, watch extensions, ignored patterns (tag input), per-severity notification toggles (desktop, Telegram), Telegram token + chat ID fields (masked)
- On save: `POST /api/config` — no restart required
- Inline validation with clear error messages

### `src/components/StatusBar.tsx`
- Shows: green/red dot for Ollama connection, current model name, queue depth, last review duration, tokens/sec
- Polls `/api/status` every 10 seconds AND subscribes to `status_update` WS events for faster feedback

### `src/components/ReviewFeed.tsx`
- Virtualized list (react-window not required — manual windowing is fine) so history doesn't bog down
- Top bar: severity filter chips (critical/warning/suggestion), project filter, search input (filters by filename + content)
- Empty state with friendly onboarding hints when no projects or no reviews yet

### `src/components/FileTree.tsx`
- Shows the selected project's tree (fetched via a backend helper that respects the same ignore rules as the watcher)
- Each file row has a "Review now" button that POSTs to `/api/reviews/trigger`

---

## Config File

### `config.yaml`
```yaml
# Ollama
model: ""  # Set to a model you've pulled (e.g. qwen2.5-coder:3b, llama3.2, codellama)
ollama_url: http://localhost:11434
ollama_timeout_seconds: 120

# Watching
watch_extensions:
  - .py
  - .js
  - .ts
  - .tsx
  - .jsx
  - .go
  - .rs
  - .java
  - .cpp
  - .c
  - .h
  - .rb
  - .php
  - .cs
  - .kt
  - .swift
ignore_patterns:
  - node_modules
  - __pycache__
  - .git
  - dist
  - build
  - .venv
  - .env
respect_gitignore: true
debounce_seconds: 1.5
max_file_lines: 400
skip_unchanged: true

# Review behavior
review_mode: auto    # auto (diff when possible, full otherwise) | always_full | always_diff
max_concurrency: 1   # Local LLM — 1 is usually best
prompt_max_chars: 16000

# Notifications
notifications:
  desktop: true
  desktop_severities: [critical, warning]
  telegram: false
  telegram_severities: [critical]
  telegram_token: ""      # Prefer .env
  telegram_chat_id: ""    # Prefer .env

# Misc
log_level: INFO
```

---

## Dependencies

### `requirements.txt`
```
fastapi
uvicorn[standard]
watchdog
sqlmodel
pydantic-settings
plyer
python-dotenv
pyyaml
httpx
pathspec
```

### `requirements-dev.txt`
```
pytest
pytest-asyncio
pytest-mock
ruff
```

### `package.json` (frontend)
```json
{
  "name": "codewatch-ui",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

---

## Scripts

CodeWatch must be runnable on Linux, macOS, and Windows. Ship both shell and batch versions of the install/start scripts. Scripts must:
- create a Python virtual environment (`.venv`) if one doesn't exist, and install deps into it
- copy `config.example.yaml` → `config.yaml` and `.env.example` → `.env` only if they don't already exist (never overwrite user config)
- fail with a clear message if Python 3.10+, Node 18+, or npm aren't found

### `install.sh` (Unix/macOS)
```bash
#!/usr/bin/env bash
set -e
echo "Installing CodeWatch..."
echo "Reminder: install Ollama separately from https://ollama.com and pull any model you like."
echo "  Example: ollama pull qwen2.5-coder:3b"
echo "Then set the model name in config.yaml."

# Python venv + deps
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Frontend
cd frontend
npm install
npm run build
cd ..

# First-run config
[ -f config.yaml ] || cp config.example.yaml config.yaml
[ -f .env ] || cp .env.example .env

echo "Done! Run ./start.sh to launch CodeWatch."
```

### `install.bat` (Windows)
```bat
@echo off
setlocal
echo Installing CodeWatch...
echo Reminder: install Ollama separately from https://ollama.com and pull any model you like.
echo   Example: ollama pull qwen2.5-coder:3b
echo Then set the model name in config.yaml.

python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

cd frontend
call npm install
call npm run build
cd ..

if not exist config.yaml copy config.example.yaml config.yaml
if not exist .env copy .env.example .env

echo Done! Run start.bat to launch CodeWatch.
endlocal
```

### `start.sh` (Unix/macOS)
```bash
#!/usr/bin/env bash
echo "Starting CodeWatch..."
source .venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
PID=$!
sleep 2
xdg-open http://localhost:8000 2>/dev/null || open http://localhost:8000 2>/dev/null || echo "Open http://localhost:8000 in your browser"
wait $PID
```

### `start.bat` (Windows)
```bat
@echo off
echo Starting CodeWatch...
call .venv\Scripts\activate.bat
start "" http://localhost:8000
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### `.gitignore`
```
.venv/
__pycache__/
*.pyc
node_modules/
frontend/dist/
config.yaml
.env
*.db
.DS_Store
```

### `LICENSE`
- Ship an MIT license file so the project is safely reusable by anyone cloning from GitHub.

---

The README must be written so that **anyone who clones this repo from GitHub can get it running on their own machine without prior knowledge of the project**. Write it in a friendly, approachable tone. Include:

1. **Header** — project name, one-line tagline, badges (license, Python, Node), and a short screenshot/GIF placeholder section (`![screenshot](docs/screenshot.png)`)
2. **What it does** — 2–3 sentences explaining the value: "watches your code, gives you AI reviews locally, your code never leaves your machine"
3. **Features** — bullet list (live file watching, streaming reviews, works with any Ollama model, desktop + optional Telegram notifications, local-only, dark UI)
4. **Requirements**
   - Python 3.10+
   - Node.js 18+ and npm
   - [Ollama](https://ollama.com) installed separately, running locally, with at least one model pulled (examples: `ollama pull qwen2.5-coder:3b`, `ollama pull llama3.2`, `ollama pull codellama`). The user chooses the model; CodeWatch works with any Ollama-compatible model.
5. **Quick start** — copy-pasteable commands for both Unix/macOS and Windows:
   ```bash
   git clone https://github.com/<your-username>/codewatch.git
   cd codewatch
   ./install.sh        # or install.bat on Windows
   # edit config.yaml and set `model:` to a model you've pulled in Ollama
   ./start.sh          # or start.bat on Windows
   ```
   Then open http://localhost:8000 in a browser.
6. **Using CodeWatch** — how to add a project folder via the UI, how reviews appear in the feed, how to delete/copy reviews
7. **Configuration reference** — every key in `config.yaml` explained in a table (name, type, default, description). Emphasize that `model` must match a model the user has already pulled in Ollama.
8. **Changing the model** — edit `config.yaml` or use the Settings page in the UI; no restart required (hot-reload)
9. **Notifications** — how to enable desktop notifications; how to set up optional Telegram (create bot via @BotFather, add token + chat ID to `.env`)
10. **Troubleshooting**
    - Ollama not running → start `ollama serve` or the Ollama desktop app
    - Model name mismatch → run `ollama list` and copy the exact tag into `config.yaml`
    - Connection refused on port 11434 → check firewall, confirm Ollama is listening
    - Port 8000 already in use → pass `--port` to uvicorn in the start script
    - Slow reviews → try a smaller model (e.g. a 3B Q4 quant) or increase `debounce_seconds`
11. **Contributing** — short section inviting PRs, link to issues
12. **License** — MIT, link to `LICENSE` file
13. **Acknowledgements** — Ollama, FastAPI, React, Vite, Tailwind, watchdog

---

## Docker (optional but included)

### `Dockerfile`
- Multi-stage: stage 1 builds the frontend with Node; stage 2 uses `python:3.12-slim`, copies the built `frontend/dist` and backend sources, installs `requirements.txt`, runs uvicorn
- Exposes port 8000
- Does NOT bundle Ollama — the container talks to Ollama on the host

### `docker-compose.yml`
- Single service `codewatch` with:
  - volume mounts for `./config.yaml`, `./.env`, `./codewatch.db`, and any project folders the user wants to watch
  - `extra_hosts: ["host.docker.internal:host-gateway"]` so the container can reach `http://host.docker.internal:11434`
  - env var `OLLAMA_URL=http://host.docker.internal:11434`

---

## Testing

- `pytest` + `pytest-asyncio`
- Tests must not require a running Ollama — mock `ollama_client` via `pytest-mock`
- Cover the non-obvious logic: debounce, gitignore matching, queue de-duplication, prompt truncation, config hot-reload
- `pyproject.toml` configures pytest and Ruff (line length 100, sensible rule set)

---

## Implementation Notes
- Write complete, runnable code for every file — no placeholders, no `# TODO` comments
- Use Python type hints throughout; `from __future__ import annotations` where helpful
- All I/O paths in the backend are async; never block the event loop with sync `requests` or sync file reads of large files
- Use `pathlib.Path`, not `os.path`, for path handling — critical for cross-platform correctness on Windows
- Normalize paths to POSIX style when sending to the frontend so the UI doesn't have to care about OS
- The frontend must work correctly when `npm run build` output is served by FastAPI (relative asset paths)
- WebSocket must handle multiple simultaneous browser clients and recover cleanly from individual client disconnects
- File watcher must survive file permission errors, binary files, and encoding errors gracefully (catch and skip; log at debug)
- All user-facing errors should surface in the UI via `toast` WS events AND the StatusBar, not just the terminal
- Secrets (`telegram_token`, etc.) live only in `.env` — never echo them back in `GET /api/config`
- No hardcoded absolute paths; no machine-specific assumptions

Start by creating the full directory structure, then implement each file completely before moving to the next. When finished, verify: `./install.sh && ./start.sh` (or `.bat` equivalents) produces a working app on a freshly cloned repo.

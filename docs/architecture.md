# CodeWatch Architecture

## Data flow

```
File change on disk
      │
      ▼
watchdog Observer (per project)
      │  debounce + filter (extension, gitignore, binary, line count)
      ▼
ReviewQueue (asyncio.Queue, de-duplicated)
      │  worker pulls job
      ▼
Reviewer.run(job)
  ├─ reads file
  ├─ compute_diff() → mode + payload
  ├─ build_prompt() → truncated prompt string
  ├─ OllamaClient.generate_stream() → token iterator
  │     │
  │     └── WS broadcast review_token per token
  ├─ save Review to SQLite
  └─ notify() → desktop / Telegram
        │
        └── WS broadcast review_done
```

## Component map

```
backend/
  main.py          — FastAPI app, lifespan (starts watcher + queue)
  core/
    config.py      — Pydantic settings, hot-reload, YAML persistence
    database.py    — SQLModel engine, helper functions
    ws_manager.py  — ConnectionManager (broadcast to all WS clients)
  models/
    project.py     — Project DB model
    review.py      — Review DB model + ReviewStatus enum
    events.py      — Pydantic WS payload schemas
  routers/
    projects.py    — /api/projects CRUD
    reviews.py     — /api/reviews CRUD + export + manual trigger
    config.py      — /api/config get/update
    status.py      — /api/status + /api/models
    ws.py          — /ws WebSocket endpoint
  services/
    watcher.py     — WatcherSupervisor + per-project watchdog handlers
    queue.py       — ReviewQueue (asyncio, de-duplication, broadcast)
    reviewer.py    — Orchestrates review pipeline
    ollama_client  — httpx async client for Ollama REST API
    diff.py        — Unified diff + git diff, content hash cache
    prompt_builder — Full-file and diff-aware prompt templates
    notifier.py    — Desktop (plyer) + Telegram notifications
  utils/
    language.py    — Extension → language name
    gitignore.py   — pathspec .gitignore matcher

frontend/src/
  App.tsx          — Root: layout, WS dispatch, state wiring
  hooks/
    useWebSocket   — Auto-reconnect WS with exponential backoff
    useProjects    — Project CRUD state
    useReviews     — Review list + streaming state
    useStatus      — Polls /api/status every 10s
  components/
    Sidebar        — Project list + add/remove form
    ReviewFeed     — Filtered, paginated review list
    ReviewCard     — Single review preview with streaming cursor
    ReviewDetail   — Full review detail panel
    StatusBar      — Ollama status, model, queue, throughput
    Settings       — Config form (model picker, notifications, etc.)
    Toast          — Transient error/success notifications
```

## Key design decisions

- **Single asyncio event loop** — watchdog runs in a background thread and posts jobs via `asyncio.run_coroutine_threadsafe`
- **Queue de-duplication** — rapid saves to the same file replace the pending job rather than stacking
- **Config hot-reload** — `POST /api/config` updates config.yaml and re-configures watcher/queue without restart
- **No secrets in YAML** — Telegram token/chat ID are loaded only from `.env`
- **pathlib.Path everywhere** — ensures cross-platform path handling

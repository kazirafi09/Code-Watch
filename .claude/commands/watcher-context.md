# /watcher-context — Architecture context for watcher/queue edits

Load this before editing `backend/services/watcher.py` or `backend/services/queue.py`.

## Critical invariants

**Thread boundary** — watchdog runs in a background thread. Never `await` or call async functions directly from watchdog handlers. Cross the thread boundary with:
```python
asyncio.run_coroutine_threadsafe(coro, loop)
```

**Queue de-duplication** — `ReviewQueue.enqueue()` replaces any pending job for the same `(project_id, path)` pair. Rapid saves must NOT stack — only the latest job should survive. Preserve this guarantee when modifying enqueue logic.

**Debounce** — per-project file handlers debounce events before posting to the queue. Changes to debounce timing affect review latency; don't raise it without reason.

**gitignore filtering** — `backend/utils/gitignore.py` (pathspec matcher) is applied inside the watcher handler. Always filter before enqueuing.

## Data flow
```
File save → watchdog handler (thread)
  → asyncio.run_coroutine_threadsafe → ReviewQueue.enqueue()
  → Reviewer.run() → OllamaClient.generate_stream()
  → WS broadcast → save Review to SQLite → notifier
```

## Key files
- `backend/services/watcher.py` — watchdog supervisor + per-project handlers
- `backend/services/queue.py` — asyncio queue with de-duplication
- `backend/services/reviewer.py` — review pipeline orchestrator

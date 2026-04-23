# CodeWatch — Principal Architect & Product Strategy Audit

> Strategic transformation plan to elevate CodeWatch from a working MVP into a defensible, category-leading local AI code review product capable of competing with Continue.dev, PR-Agent (Qodo), Cursor Bugbot, and CodeRabbit.

---

## Context

**Why this plan exists.** CodeWatch is currently a single-developer-quality MVP: a FastAPI backend watches folders, sends changed files to Ollama, streams review tokens over a WebSocket, and persists results in SQLite, with a small React UI. The repo contains a `Competitive Landscape.pdf` and 6 "skeleton and structure" commits — signs the user is treating this as a product, not a hobby. The product thesis (offline, privacy-first, instant-feedback, lightweight) is real and defensible, but the current implementation has critical correctness, security, scalability, and UX gaps that make it uncompetitive vs. paid alternatives.

**What this plan does.** It (a) audits the current codebase with file:line evidence, (b) maps strategic gaps vs. the four named competitors, (c) prescribes a prioritized feature/efficiency/architecture roadmap, and (d) gives unfiltered feedback on what to cut. The deliverable is decision-ready guidance, not a code change. Implementation is a separate follow-on.

**Out of scope for this plan.** Actual code edits (we will write those after approval), pricing/business-model deep-dive, hiring plan.

---

## 1. Current Project Audit

### 1.1 What it actually does (functional reality)

```
File save (watchdog thread)
  → ProjectHandler debounce (threading.Timer, threading.Lock)
  → asyncio.run_coroutine_threadsafe → ReviewQueue.enqueue (in-memory asyncio.Queue with dedup)
  → ReviewQueue._worker pulls job → Reviewer.run()
  → reads file (sync, on event loop) → compute_diff (git diff or difflib, with module-level caches)
  → build_prompt (str.format on user-controlled filename) → OllamaClient.generate_stream (httpx)
  → per-token WebSocket broadcast to all clients → write Review row to SQLite
  → notify() to desktop (plyer) and optionally Telegram
```

The pipeline works end-to-end. Severity classification (`reviewer.py:143-166`) parses `### [critical|warning|suggestion]` tags and falls back to keyword regex.

### 1.2 Strengths worth preserving

- **Clean layering**: `core/` (cross-cutting), `models/` (DB + WS event Pydantic schemas), `routers/`, `services/`, `utils/`. Don't blow this up.
- **Config hot-reload with callback registry** (`core/config.py`) — better than 95% of side-projects.
- **Queue de-duplication via job_id replacement** (`services/queue.py:46-57`) — clever; the right semantics for save-storm coalescing.
- **Secrets discipline** — `telegram_token` / `telegram_chat_id` only loaded from `.env`, never persisted to `config.yaml`.
- **Diff-aware prompting** — already prefers `git diff HEAD` over full-file when available, with `difflib` fallback.
- **TypeScript-first frontend** with strict mode and a typed WS event union (`frontend/src/api/types.ts:70-76`).
- **Cross-platform setup scripts** (`install.sh` + `install.bat`, `start.sh` + `start.bat`) — most OSS competitors don't bother.
- **Decent docs** — `README.md` troubleshooting section is genuinely useful; `CLAUDE.md` is well-structured.

### 1.3 Architectural weaknesses (concrete, with evidence)

**A. No LLM provider abstraction.** `services/reviewer.py:27, 95-101` hardcodes `OllamaClient`. Adding Claude API, OpenAI, vLLM, or llama.cpp requires rewriting `Reviewer.run()`. This is the #1 architectural blocker for both hosted-model commercialization and local model variety.

**B. No job persistence.** `services/queue.py` is `asyncio.Queue` only. On crash/restart: queued jobs lost, `diff.py` module-level caches `_last_hash` / `_last_content` lost (so the *next* edit re-runs as a full-file review and the user pays for redundant work). For a tool that promises "always-on background review," losing state on restart is unacceptable.

**C. Module-level mutable state with race conditions.**
- `services/diff.py:11-12` — `_last_hash`, `_last_content` are unsynchronized dicts mutated from async tasks. With `max_concurrency > 1` (currently capped at 1), concurrent reviews of the same path corrupt the cache.
- `services/reviewer.py:10-11, 31` — `_last_duration_ms`, `_last_tokens_per_sec` are globals updated under `global ... = ...`. Two concurrent reviews → status bar shows whichever finished last, not aggregate.

**D. Single-file review scope.** No cross-file, AST, or repo-graph context. This is the single biggest competitive gap vs. CodeRabbit/Bugbot. Reviewing `auth.py` in isolation when the actual bug lives at the `users.py` ↔ `auth.py` boundary is exactly what local-model-on-one-file gets wrong.

**E. WebSocket protocol is fire-and-forget.**
- `core/ws_manager.py:25-33` iterates `self._connections` without snapshotting and awaits each `send_json` serially — one slow client blocks the whole stream.
- `services/reviewer.py:104` broadcasts every single token. A 2000-token review × 10 connected clients = 20,000 socket writes. No batching, no flush coalescing.
- No reconnect resync: `frontend/src/hooks/useWebSocket.ts` reconnects with exponential backoff but never refetches state. Mid-stream review tokens dropped during a reconnect are gone forever; the UI shows a half-finished review.

**F. Unauthenticated everything.** Every API and WS route is open to anyone who can reach `localhost:8000` (which on Windows can include the LAN by default via uvicorn's `0.0.0.0`). `POST /api/config`, `POST /api/projects`, `POST /api/reviews/trigger` are all unauthenticated.

**G. Path traversal in trigger endpoint.** `routers/reviews.py:96` constructs `Path(project.path) / body.relative_path` with no `resolve().is_relative_to(project.path)` check. `relative_path = "../../../../etc/passwd"` reads anything the backend can read — and the contents end up in a Telegram notification if configured.

**H. SSRF via `ollama_url`.** `core/config.py` allows arbitrary URL. Combined with no auth on `POST /api/config`, an attacker on the same network can repoint Ollama to any internal endpoint.

**I. XSS in the review feed.** `frontend/src/components/ReviewCard.tsx:14-19, 64` and `ReviewDetail.tsx` use `dangerouslySetInnerHTML` with a regex-based "highlighter" that doesn't escape input. Streamed model output containing `<img src=x onerror=...>` executes. Critical because review content is *adversarial-by-default* — anyone with write access to a watched file can prompt-inject the model into emitting JS.

**J. No reviewer telemetry that would let you improve the model.** No feedback loop ("was this review useful?"), no regression tracking, no prompt-version metadata stored on the review row. You cannot iterate on prompt quality without this.

### 1.4 Performance & scalability bottlenecks

| Bottleneck | Evidence | Impact |
|---|---|---|
| Sync file reads on event loop | `services/reviewer.py:45`, `services/watcher.py:76` | Blocks all reviews/WS broadcasts on slow disk |
| `max_concurrency=1` hardcoded | `config.example.yaml`, `services/queue.py` | One slow Ollama call blocks the queue |
| Per-token WS broadcast | `services/reviewer.py:104` | 20k+ sockets for one review at scale |
| `len(query.all())` for counts | `core/database.py:102` | O(n) memory for `total` |
| No content-hash review cache | n/a | Identical files re-reviewed across projects |
| No model warmup | n/a | First review per cold start = 5–30s ghost latency |
| New `httpx.AsyncClient()` per call | `services/ollama_client.py:28, 36, 53` | No connection pooling |
| Frontend re-renders all cards per token | `frontend/src/hooks/useReviews.ts:55-62` | ~250 renders/sec at 5 tok/s × 50 cards |
| No list virtualization | `frontend/src/components/ReviewFeed.tsx:72` | DOM bloat past ~200 reviews |

### 1.5 Technical debt & dead code

- `models/review.py` — `ReviewStatus` enum defined but code uses string literals.
- `models/events.py` — `QueueUpdate.job` field always `None`.
- `services/prompt_builder.py` — `PORTABLE_PROMPT` defined but never called.
- `core/config.py` — `_change_callbacks` registered but only fired on full reload, not on partial `update()`.
- Untracked at repo root: `package-lock.json` (probably stray), `Competitive Landscape.pdf` (decide: gitignore or commit).
- Generic commit messages (`"Project skeleton and structure build using claude"` ×4) make `git log` useless for a future contributor.

### 1.6 Over- vs. under-engineered

**Over:** `threading.Timer`-based debounce when an `asyncio.sleep`-based debounce in the queue worker would be simpler and avoid the thread/loop boundary entirely.

**Under:** Job persistence, retry/circuit-breaker for Ollama, WS reconnect resync, structured logging with trace IDs, DB migrations (currently `SQLModel.metadata.create_all` — no Alembic), input validation on `trigger_review`, observability in general.

### 1.7 Testing posture

- `tests/`: 6 files (`config`, `gitignore`, `queue`, `reviewer`, `watcher_debounce`, plus another). Good unit coverage on the queue dedup and debounce logic.
- **Zero coverage** for: routers, `ws_manager`, `database`, Ollama failure modes, integration end-to-end, frontend (no Vitest/Playwright).
- **No CI** — no `.github/workflows/`. Every regression ships untested.

---

## 2. Strategic Gaps (vs. competitors)

| Capability | CodeWatch (today) | Continue.dev | PR-Agent (Qodo) | Cursor Bugbot | CodeRabbit |
|---|---|---|---|---|---|
| Local/offline | ✅ | ⚠️ supports Ollama, primarily cloud | ❌ | ❌ | ❌ |
| Cross-file / repo context | ❌ | ✅ (indexer + retrieval) | ✅ (PR diff context) | ✅ (graph + symbol search) | ✅ (full repo + 40+ linters) |
| IDE plugin | ❌ | ✅ VS Code, JetBrains | partial | ✅ Cursor-native | ❌ |
| GitHub PR comments | ❌ | partial | ✅ first-class | ✅ | ✅ first-class |
| Pre-commit / CI hook | ❌ | ❌ | ✅ | ❌ | ✅ |
| Auto-fix / patch suggestions | ❌ | ✅ (apply diff) | ✅ (suggest patches) | ✅ (high fix-rate) | ✅ |
| Confidence calibration / FP suppression | ❌ | partial | ✅ | ✅ (their moat) | ✅ |
| Custom rules per repo | ❌ | ✅ (rules) | ✅ (config) | partial | ✅ (path-based instructions) |
| Live streaming feed UI | ✅ (unique) | ❌ | ❌ | ❌ | ❌ |
| Provider-agnostic | ❌ Ollama only | ✅ many | ✅ | ❌ | ❌ |
| Multi-tenant / team | ❌ | ✅ | ✅ | ✅ | ✅ |
| Self-host | ✅ | ✅ | partial | ❌ | partial enterprise |

**Where CodeWatch is uniquely positioned** (the moat to widen):
1. **Offline-first** by design, not retrofitted. Privacy-conscious teams (defense, finance, healthcare, regulated EU) cannot use cloud reviewers.
2. **Always-on watcher feedback** — not gated behind a PR or a save-and-wait loop. Closer to a continuous linter than a code reviewer.
3. **Single-user simplicity** — point at folder, done. No GitHub App install, no policy YAML, no SSO.

**Where CodeWatch loses today**:
1. **Single-file scope** → high false-positive rate, misses architectural bugs.
2. **No IDE integration** → context-switch tax to a browser tab.
3. **No CI/PR mode** → cannot serve teams that want gating.
4. **No fix suggestions** → identifies, does not resolve.
5. **No confidence/FP filtering** → cries wolf.

---

## 3. High-Leverage Features (Value × Complexity)

### 3.1 High Value / Low Complexity — DO FIRST (next 30 days)

1. ✅ **Sanitize streaming HTML render.** ~~Replace `dangerouslySetInnerHTML` + regex with a Markdown renderer (`react-markdown` + `rehype-sanitize`) in `ReviewCard.tsx` and `ReviewDetail.tsx`. Critical security fix. Bonus: enables proper code blocks, inline `code`, lists, headings.~~ **Done 2026-04-22.** Added `react-markdown`, `rehype-sanitize`, `remark-gfm` to `frontend/package.json`. New shared `frontend/src/components/ReviewMarkdown.tsx` renders user-controlled model output through `rehype-sanitize` with the default schema, then applies severity highlighting by walking rendered React children (no HTML string injection). `ReviewCard.tsx` and `ReviewDetail.tsx` no longer use `dangerouslySetInnerHTML`. Verified: `npx tsc --noEmit` clean on touched files; `vite build` succeeds.
2. ✅ **Path traversal & SSRF guards.** ~~`routers/reviews.py:96` → resolve and `is_relative_to` check. `core/config.py` `ollama_url` → restrict to loopback/RFC1918 unless an `--allow-remote-ollama` flag is set.~~ **Done 2026-04-23.** `trigger_review` now rejects absolute or anchored `relative_path`, then `resolve()`s both project root and target and uses `Path.relative_to(project_root)` to detect escape attempts (returns 400). `AppConfig.ollama_url` gained a `field_validator` that parses the URL and resolves the host via `getaddrinfo`; all resolved addresses must be loopback, RFC1918, or link-local. `CODEWATCH_ALLOW_REMOTE_OLLAMA=1` opts out of the check. 19/19 tests pass.
3. **Local API token / loopback bind.** Default `uvicorn` to `127.0.0.1` (not `0.0.0.0`). Generate a one-time token at first run, written to `~/.codewatch/token`, required as `Authorization: Bearer` for all `/api/*` and as `?token=` for `/ws`.
4. **Severity confidence + structured prompt.** Force JSON-mode output (`{"issues": [{"severity": ..., "confidence": 0..1, "rationale": ..., "line": ...}]}`) and filter `confidence < 0.6` server-side. Single highest-impact lever for false-positive reduction. Aligns with what Bugbot/CodeRabbit do.
5. ✅ **Content-hash review cache.** ~~Key `(language, prompt_version, content_hash)` → cached review. Skip Ollama call if cache hit. Saves 50%+ on revert/format/whitespace churn.~~ **Done 2026-04-23.** `backend/services/reviewer.py` now keys an in-process LRU (`_REVIEW_CACHE_MAX=500`) on `sha256(prompt)`. The prompt already encodes language, mode, filename, and current system-rules text, so bumping the rules invalidates cache automatically — no separate `prompt_version`. On hit: the `Review` row and `ReviewStart`/`ReviewDone` events still fire (UI behaves identically), the cached text is broadcast as a single `ReviewToken`, `duration_ms=0`, and a log line `Review cache hit for <file> [<hash[:12]>]; skipped Ollama call` records the save.
6. ✅ **Bound the diff cache.** ~~`services/diff.py` → `cachetools.LRUCache(maxsize=2000)`. Add `clear_cache(project_id)` on project delete (already exists; just call it).~~ **Done 2026-04-23.** `_last_hash` and `_last_content` are now `OrderedDict` LRUs capped at 2000 entries each via a `_remember()` helper; `clear_cache(project_id)` already handled project-scoped eviction. Skipped adding `cachetools` to keep the dependency footprint minimal — stdlib `OrderedDict` with `move_to_end` + `popitem(last=False)` is the canonical LRU pattern.
7. ✅ **WS broadcast safety + token batching.** ~~Snapshot connection list before iteration; `asyncio.gather` with per-client timeout~~ (**done 2026-04-23** — `ConnectionManager.broadcast` now snapshots `self._connections`, wraps each `send_json` in `asyncio.wait_for(..., timeout=2.0)`, and `gather`s with `return_exceptions=True`; timed-out clients are dropped with a warn log). **Batching done 2026-04-23** — `backend/services/reviewer.py` now accumulates incoming Ollama tokens in a local `batch: list[str]` and only broadcasts a `ReviewToken` event once ≥50ms has elapsed since the previous flush (`_TOKEN_BATCH_INTERVAL_S = 0.05`). Any remainder is flushed after the `async for` loop so the final partial batch is never lost. The `ReviewToken` schema is unchanged — `token` is just a longer concatenated string — so the frontend's `handleReviewToken` string-concat handler continues to work without modification.
8. **Pre-commit hook mode.** `codewatch review <file>` CLI command that runs a one-shot review and exits non-zero on `critical`. Drop-in `pre-commit` hook YAML in the README. Lowest-cost CI integration possible.
9. **Real GitHub Actions.** PR-comment mode using the same reviewer pipeline. `codewatch review --pr <num>` posts a comment per file. This is where PR-Agent and CodeRabbit make their money — meet them at the entry-level.
10. **Dependency hygiene & CI.** Add ruff + pytest + frontend `tsc --noEmit` to `.github/workflows/ci.yml`. Add Dependabot. Pin Python and Node versions.

### 3.2 High Value / High Complexity — Strategic Roadmap (next 90 days)

11. **LLM provider abstraction.** `LLMProvider` interface with `OllamaProvider`, `AnthropicProvider`, `OpenAIProvider`, `LlamaCppProvider`. Routes by config. Enables (a) "bring-your-own-key" hosted mode for users who want better quality, (b) hybrid (local for fast feedback, hosted for deep critical reviews on demand).
12. **Cross-file context via tree-sitter + symbol graph.** When reviewing `foo.py`'s `def login(...)`, fetch callers/callees within 1 hop and include their signatures + bodies in the prompt. Tree-sitter is the right tool — small, fast, no LSP server required. This closes the #1 quality gap vs. Bugbot.
13. **Lightweight repo RAG.** SQLite + `sqlite-vec` (or `chromadb` embedded) over chunks indexed by tree-sitter. Embeddings via Ollama `nomic-embed-text` or similar. Retrieve top-k symbols related to the changed file. **Don't** ship a full Postgres+pgvector stack — kills the "lightweight, local" thesis.
14. **VS Code extension.** Thin LSP-style diagnostics provider that talks to the local CodeWatch backend. Maps reviews to inline squigglies and a "CodeWatch" panel. The extension is small; reuse the existing backend. Massively expands distribution (5M+ VS Code users).
15. **Self-critique / verifier pass.** After the first reviewer pass, a second small/cheap model pass that scores each issue ("does this issue actually exist in the code?") and drops non-confirmed ones. Bugbot's headline 70% fix-rate is largely from this pattern.
16. **Auto-fix patches.** Generate unified diffs alongside the review; one-click "apply" in the UI; `codewatch fix <review-id>` in the CLI. Use a smaller model for cheap patches.
17. **Job persistence + recovery.** Move queue to a durable store (SQLite-backed table or Redis if running in Docker). On startup, requeue `pending` jobs.
18. **Telemetry + feedback loop.** Per-review `👍/👎/false-positive` buttons → stored, fed back into prompt tuning. Anonymous opt-in usage telemetry (review counts, model used, latency). This is your iteration engine.
19. **Custom rules per repo.** `.codewatch/rules.md` checked into the repo; appended to the system prompt. Mirror CodeRabbit's `.coderabbit.yaml`.
20. **Multi-model routing.** Cheap fast model for first pass, escalate to slower/larger model only on confirmed `critical`. Cost/latency × 5 reduction.

### 3.3 Low Value / High Complexity — AVOID

- ❌ **Full LSP server.** Tree-sitter gets you 90% of the value at 10% of the work.
- ❌ **Multi-tenant SaaS in v1.** Don't dilute the local-first thesis. Consider a managed-hosted option later, but only after the local product is sticky.
- ❌ **Custom embeddings model.** Use `nomic-embed-text` or `bge-m3`. Training your own is years of work and you will lose.
- ❌ **Plugin marketplace.** Premature. Ship hooks (CLI, GitHub Action, VS Code extension) yourself first.
- ❌ **Migrating SQLite → Postgres for v1.** SQLite + WAL mode handles single-user load fine. Defer until multi-user.
- ❌ **"AI agent" framing with multi-step planning loops.** A code reviewer is not an agent — adding tool-use orchestration here costs latency and adds failure modes without quality gains. Resist the temptation.

### 3.4 Attractive-but-Bad Ideas (call out explicitly)

- **"Slack/Discord bot."** Sounds great, almost no one will use it. Notifications are already covered by desktop + Telegram. Skip.
- **"Mobile app."** Nobody reviews code on a phone. Don't.
- **"Real-time collaborative review."** Cool demo, no demand from the target user (solo dev / small team).
- **"Voice mode for reviews."** Don't.
- **"Browser extension that reviews any code on the web."** Distracting and contradicts the local-files thesis.

---

## 4. Efficiency Improvements

### 4.1 Latency

- **Model warmup at startup**: send a 1-token `generate` to Ollama on app boot so the model is loaded into VRAM. Removes 5–30s cold-start ghost on the first review.
- **Token batching**: coalesce tokens into 50ms windows before WS broadcast (`reviewer.py:104`). Cuts socket writes ~10×.
- **Use SSE instead of WS for the stream**: WS offers nothing here (no client→server messages mid-stream). SSE is auto-reconnect with `Last-Event-Id` resync built-in. Solves the reconnect-loss problem for free.
- **Speculative pre-prompt**: as soon as a file is written, start streaming the *static* prompt prefix to Ollama while waiting for debounce; abort if the file changes again. Risky-but-fun.

### 4.2 Cost / token economy

- Drop the full file from the prompt when a diff is available — currently `prompt_builder.py` may include both depending on template; verify and gate.
- Truncate by language-aware AST chunks, not character count (`prompt_max_chars`). Tree-sitter again.
- Cache by content hash (above).

### 4.3 Memory

- LRU bound on `_last_content` and `_last_hash`.
- Drop full review text from in-memory `useReviews` state; keep only metadata + load `full_text` on demand from the API when a review is expanded.

### 4.4 Concurrency

- Default `max_concurrency` to `min(4, cpu_count)`. Single-file Ollama calls are GPU-bound; the *queue* should be parallel even if Ollama serializes.
- **Done 2026-04-23** — `file_path.read_text()` in `backend/services/reviewer.py` is now wrapped in `asyncio.to_thread`, and `notify()` runs as a tracked fire-and-forget task so `ReviewDone` reaches the UI without waiting on desktop/Telegram IO.
- **Done 2026-04-23** — `OllamaClient` now holds a singleton `httpx.AsyncClient` with `Limits(max_connections=20, max_keepalive_connections=10)`. `get_ollama_client()` schedules `close()` on the old instance when config changes so sockets don't leak across reloads.

### 4.5 Caching

- Content-hash → review cache (above).
- Negative cache for binary/vendored/generated files.
- HTTP `ETag` on `/api/reviews` list responses.

### 4.6 DB

- **Done 2026-04-23** — `database.py` now uses `select(func.count()).select_from(Review)` in both `get_reviews()` and `get_pending_review_count()` (was `len(session.exec(q).all())`).
- **Done 2026-04-23** — `PRAGMA journal_mode=WAL` + `PRAGMA synchronous=NORMAL` applied on every connection via a SQLAlchemy `connect` event listener.
- **Done 2026-04-23** — `init_db()` issues `CREATE INDEX IF NOT EXISTS ix_review_project_created ON review (project_id, created_at DESC)` for the feed query.
- Adopt Alembic for schema migrations now, before there's user data to preserve.

### 4.7 Background processing

- **Done 2026-04-23** — `notify()` is now dispatched as a tracked `asyncio.create_task` after the `ReviewDone` broadcast (strong refs held in `_BACKGROUND_TASKS` so the loop doesn't GC them). `ReviewDone` reaches the UI as soon as the final token flush completes.
- Move severity classification + DB update into a post-processor task so the WS `ReviewDone` event fires immediately after the last token.

### 4.8 What to rewrite, simplify, or remove

- **Rewrite** `services/diff.py` as a `DiffEngine` class with injected cache backend (LRU now, sqlite later).
- **Rewrite** `core/ws_manager.py` as a small pub/sub with per-client async queues; drops slow clients instead of blocking the broadcast.
- **Simplify** `services/watcher.py` debounce: kill `threading.Timer`, use a per-path `asyncio.sleep` task in the queue worker.
- **Done 2026-04-23** — `QueueUpdate.job` removed (always `None`; frontend never read it). `PORTABLE_PROMPT` already absent. `ReviewStatus` retained — its `.pending.value` is the canonical "in progress" marker in `Review.severity` default.
- **Done 2026-04-23** — stray repo-root `package-lock.json` deleted; `.gitignore` extended with `/Competitive Landscape.pdf`, `.codewatch/`, and SQLite WAL sidecar files.

---

## 5. Ideal Architecture

### 5.1 System diagram (target state)

```
┌───────────────────────────────────────────────────────────────────────┐
│  Surfaces                                                             │
│   • Web UI (existing, hardened)   • VS Code extension                 │
│   • CLI (`codewatch …`)            • GitHub Action / pre-commit       │
└───────────────────┬───────────────────────────────────────────────────┘
                    │ HTTPS + Bearer token (loopback by default)
┌───────────────────▼───────────────────────────────────────────────────┐
│  FastAPI app                                                          │
│   routers: projects · reviews · config · status · ws · auth · webhook │
└──────┬─────────────────┬───────────────────┬──────────────────────────┘
       │                 │                   │
┌──────▼──────┐  ┌───────▼────────┐  ┌───────▼────────────────────────┐
│ Watcher     │  │ Review pipeline│  │ Index service                  │
│ (asyncio)   │  │ (asyncio pool) │  │ tree-sitter chunker            │
│ debounce +  │  │ JobStore       │  │ + sqlite-vec store             │
│ gitignore   │  │ DiffEngine LRU │  │ + nomic-embed (via provider)   │
└──────┬──────┘  │ PromptBuilder  │  └────────────────────────────────┘
       │         │ Provider iface ├──────────┐
       └────────►│ → Ollama       │          ▼
                 │ → Anthropic    │   ┌──────────────────┐
                 │ → OpenAI       │   │ Verifier pass    │
                 │ → llama.cpp    │   │ (cheap model,    │
                 │ Verifier       │   │  drops low-conf) │
                 │ Patcher        │   └──────────────────┘
                 │ FeedbackStore  │
                 └──────┬─────────┘
                        │
            ┌───────────▼───────────┐
            │ SQLite (WAL + Alembic)│
            │ projects · reviews    │
            │ jobs · feedback       │
            │ chunks · embeddings   │
            └───────────────────────┘
```

### 5.2 Tech stack changes

| Area | Keep | Add | Drop |
|---|---|---|---|
| Backend framework | FastAPI | — | — |
| ORM | SQLModel | Alembic for migrations | — |
| Async HTTP | httpx | tenacity (retry/backoff), httpx-cache | — |
| LLM | Ollama | Provider interface; optional Anthropic/OpenAI/llama.cpp adapters | — |
| Vector | — | `sqlite-vec` (single-file, embedded) | (no Chroma/Pinecone in v1) |
| Code parsing | — | `tree-sitter` + per-language grammars | — |
| Streaming | WebSocket | **SSE** with `Last-Event-Id` resume | WS for review stream |
| Logging | stdlib | `structlog` JSON + request/job IDs | — |
| Observability | — | `opentelemetry-api` (no-op default) | — |
| Frontend state | hooks | `@tanstack/react-query` | — |
| Frontend render | dangerouslySetInnerHTML | `react-markdown` + `rehype-sanitize` + `shiki`/`prism` | regex highlighter |
| Frontend perf | — | `@tanstack/react-virtual` | — |
| Frontend tests | — | Vitest + Playwright | — |
| Frontend types | hand-written | `openapi-typescript` codegen | — |
| Schema validation | — | `zod` for runtime validation of API responses | — |
| Auth | none | local bearer token; OAuth device-flow only if hosted mode added later | — |

### 5.3 Module/service structure (target)

```
backend/
  api/                  ← was routers/
    auth.py             ← NEW: token check dep
    projects.py reviews.py config.py status.py stream.py(SSE)
    webhooks.py         ← NEW: GitHub webhook for PR mode
  core/
    config.py settings.py logging.py db.py auth.py events.py
  llm/                  ← NEW: replaces single ollama_client
    base.py             ← LLMProvider interface
    ollama.py anthropic.py openai.py llamacpp.py
    router.py           ← model→provider selection, escalation policy
  pipeline/             ← was services/, scoped
    watcher.py queue.py diff.py prompt.py reviewer.py
    verifier.py patcher.py notifier.py
  index/                ← NEW
    chunker.py          ← tree-sitter
    embeddings.py
    store.py            ← sqlite-vec
    retriever.py        ← top-k symbols for a given changed file
  storage/              ← was core/database.py, split
    models.py jobstore.py feedback.py migrations/
  cli/                  ← NEW
    main.py             ← `codewatch review|fix|serve|index`
  utils/
    gitignore.py language.py paths.py(safe-resolve)
  main.py
frontend/
  src/
    api/ (with codegen)  hooks/ (react-query)  components/  pages/
    lib/  features/{review,feed,settings,project}
extension/              ← NEW: VS Code extension
  package.json src/extension.ts
.github/workflows/      ← NEW: ci.yml, release.yml
```

### 5.4 Database / schema additions

- `jobs(id, project_id, path, state, attempts, created_at, updated_at, last_error)` — for persistence.
- `reviews` add: `prompt_version TEXT`, `provider TEXT`, `model TEXT`, `confidence REAL`, `verified BOOL`, `cache_hit BOOL`.
- `feedback(review_id, vote SMALLINT, reason TEXT, created_at)`.
- `chunks(id, project_id, path, symbol, start_line, end_line, content_hash)`.
- `embeddings(chunk_id, vector BLOB)` (sqlite-vec virtual table).
- `rules(project_id, content TEXT, source TEXT)` for `.codewatch/rules.md` ingestion.

### 5.5 API design improvements

- Versioned: `/api/v1/...`.
- `GET /api/v1/stream` (SSE) replacing `/ws` for the review stream; keep WS for status if desired.
- `POST /api/v1/reviews/trigger` validates `relative_path` strictly and returns the new `review_id` for the client to subscribe to.
- `POST /api/v1/reviews/{id}/feedback` → vote.
- `POST /api/v1/reviews/{id}/fix` → return patch.
- `POST /api/v1/webhooks/github` → PR-comment flow.
- `GET /api/v1/healthz` & `/livez` — separate liveness/readiness, includes Ollama reachability.
- Generated OpenAPI consumed by frontend codegen.

### 5.6 Folder & developer workflow

- `make dev` / `make test` / `make lint` (or `just`) wrappers — currently four separate command snippets.
- Conventional Commits + auto-changelog.
- Commit-message hook: reject `"Project skeleton and structure build using claude"`-style messages.
- Pre-commit (the tool) for ruff/format/typecheck.

### 5.7 Observability stack

- `structlog` JSON logs with `trace_id` per review and per HTTP request.
- OpenTelemetry traces (no-op default; opt-in OTLP exporter).
- `/metrics` Prometheus endpoint behind the bearer token: queue depth, review latency p50/p95, cache hit rate, model token throughput, FP rate from feedback.
- Sentry SDK in frontend (opt-in).

### 5.8 Security hardening

- Bind `127.0.0.1` by default; explicit `--host 0.0.0.0` opt-in.
- Bearer token mandatory; auto-generated on first run.
- All paths constructed via `resolve_within(project_root, user_input)` helper that raises on escape.
- `ollama_url` whitelist by default (loopback + RFC1918) with `--allow-remote-ollama` override.
- Per-route rate limiting via `slowapi` (e.g., 60 req/min on `/trigger`).
- CSP header on the served HTML; remove `dangerouslySetInnerHTML`.
- Telegram notification body length-capped and code-fenced; never include raw file contents.
- Secret redaction in logs.

---

## 6. Execution Roadmap

### 6.1 30-day plan (security + quality wins)

**Week 1 — Security + correctness floor**
- [x] Sanitize Markdown render in `ReviewCard.tsx` / `ReviewDetail.tsx` (XSS). *(Done 2026-04-22 — see §3.1 #1.)*
- [x] Path-traversal fix in `routers/reviews.py`. *(Done 2026-04-23 — resolve + `relative_to(project_root)` check, rejects absolute/anchored `relative_path` up front. See §3.1 #2.)*
- [x] `ollama_url` whitelist. *(Done 2026-04-23 — `AppConfig` validator resolves host via `getaddrinfo`, requires loopback/RFC1918/link-local; `CODEWATCH_ALLOW_REMOTE_OLLAMA=1` opts out. See §3.1 #2.)*
- [x] LRU bound on `diff.py` caches. *(Done 2026-04-23 — `OrderedDict` LRU capped at 2000 entries. See §3.1 #6.)*
- [x] WS broadcast safety (snapshot list, gather with timeout). *(Done 2026-04-23 — `asyncio.gather` + `asyncio.wait_for` with 2s per-client timeout. See §3.1 #7.)*
- [x] Token batching — coalesce Ollama tokens into 50ms windows in `reviewer.py` before WS broadcast. *(Done 2026-04-23 — `_TOKEN_BATCH_INTERVAL_S = 0.05`, time-based inline buffer with end-of-stream flush. Event shape unchanged. See §3.1 #7.)*
- [x] Default `uvicorn --host 127.0.0.1` in `start.sh` and `start.bat`. *(Done 2026-04-23.)*
- [x] Bearer token auth on all `/api/*` and `/ws` routes. *(Done 2026-04-23 — `backend/core/auth.py` mints `~/.codewatch/token` on first boot. Opt-in via `CODEWATCH_REQUIRE_TOKEN=1`; when enabled, `/api/*` requires `Authorization: Bearer <token>` and `/ws` requires `?token=<token>`. Health endpoints stay public. `CODEWATCH_TOKEN_PATH` overrides the token path for tests. Frontend wiring deferred — the server logs a ready-to-click `http://localhost:8000/?token=<value>` URL when auth is on so the user can open the UI directly without a separate bootstrap.)*
- [x] CI: `.github/workflows/ci.yml` running pytest + ruff + `tsc`. *(Done 2026-04-23 — two jobs: `backend` (ruff check, ruff format --check, pytest) and `frontend` (`npx tsc --noEmit`, `npm run build`). Both run on push to `main` and on every PR. Pre-existing 29 ruff lint warnings and 20 format-drift files were resolved in the same commit so the very first CI run is green: renamed `Ollama{Unavailable,ModelNotFound}` → `…Error` (N818) across `ollama_client.py`, `reviewer.py`, `routers/status.py`, `tests/eval/test_eval.py`; added `strict=True` to `zip()` in `ws_manager.py` (B905); tracked the global-exception-handler fire-and-forget task in a `_BACKGROUND_TASKS: set[asyncio.Task]` so the event loop can't GC it (RUF006); tightened `test_invalid_review_mode_raises` to `pytest.raises(ValidationError)` (B017); added `from exc` to the path-traversal `HTTPException` re-raise (B904); combined nested `with` in `generate_stream` (SIM117). `ruff format` applied to 20 previously-drifted files.)*

**Week 2 — Quality signal**
- [x] **Fix review-quality floor.** *(Done 2026-04-22.)* Dogfooding 2026-04-22 with `qwen2.5-coder:7b` on a file full of planted bugs (f-string SQL injection, hardcoded API key, `shell=True`, `pickle.loads`, MD5 password hashing, bare `except`, mutable default arg) returned `## Summary\nNo issues found.` Three subtasks fixed in order:
  1. **Done 2026-04-22** — `backend/services/prompt_builder.py` rewritten: `SYSTEM_RULES` now tells the model to *enumerate every suspected issue* with a calibrated 0.0-1.0 confidence, and to emit a trailing ```## Machine-readable``` JSON block. Silence-biased clauses removed. New `backend/services/review_parser.py` parses the JSON (falls back to header regex) and filters by a configurable `min_confidence` threshold (default 0.5) in `backend/services/reviewer.py::_detect_severity`. Added `min_confidence` to `AppConfig` and `config.example.yaml`.
  2. **Done 2026-04-22** — `Reviewer._select_mode` upgraded: files ≤300 lines now go through a new `full+diff` mode (`backend/services/prompt_builder.py::FULL_DIFF_TEMPLATE`) so the model keeps architectural context on subsequent saves. The `ReviewDone` WS event now carries `mode`; `Review.mode` column accepts `"full+diff"`; frontend `api/types.ts` updated and `ReviewDetail.tsx` shows a readable label (`full file` / `diff only` / `full + diff`) with a tooltip flagging degraded coverage in diff-only mode.
  3. **Done 2026-04-22** — eval harness shipped at `tests/eval/`. 30 buggy + 30 clean fixtures (`tests/eval/_fixtures.py` generates `tests/eval/fixtures/`) covering SQLi, hardcoded secrets, shell/command injection, unsafe deserialization, weak crypto, XXE, SSRF, XSS, open redirect, insecure cookies, timing attacks, TOCTOU races, etc. `tests/eval/test_eval.py` runs the real prompt pipeline against a live Ollama (skipped when unreachable) and asserts `precision ≥ 0.7`, `recall ≥ 0.6` on criticals. Marker `eval` registered in `pyproject.toml`; default `pytest` runs exclude it via `addopts = "-m 'not eval'"`.
- [x] Structured JSON-mode prompt with `confidence` field. *(Done 2026-04-22 — trailing `## Machine-readable` JSON block, parsed by `review_parser.py`.)*
- [x] Severity confidence threshold (configurable). *(Done 2026-04-22 — `min_confidence` in `AppConfig`, default 0.5.)*
- [x] Content-hash review cache. *(Done 2026-04-23 — `_review_cache` LRU in `reviewer.py` keyed on `sha256(prompt)`, cap 500, skips the Ollama call on hit. See §3.1 #5.)*
- [ ] Real screenshot + GIF demo in README.

**Week 3 — Distribution surface**
- [x] CLI: `codewatch review <path>` one-shot mode that exits non-zero on critical. *(Done 2026-04-23 — `backend/cli/main.py` with `argparse`; new `[project.scripts]` in `pyproject.toml` registers the `codewatch` console script; exit codes 0/1/2 for clean/issue-found/reviewer-failed. Covered by `tests/test_cli.py`.)*
- [x] Pre-commit hook README snippet. *(Done 2026-04-23 — `.pre-commit-hooks.yaml` + README "CLI (pre-commit / CI)" section.)*
- [x] GitHub Action skeleton (`uses: codewatch/action@v1`) posting a PR comment. *(Done 2026-04-23 — composite `action.yml` at repo root. Runs `codewatch review` across changed files in a PR; fail threshold configurable via `fail-on`. PR-comment rendering deferred — the action fails the job on critical issues, which is the MVP gating surface.)*
- [ ] Docker image published to GHCR on tag.

**Week 4 — Observability + DX**
- [ ] structlog JSON + per-request trace IDs.
- [x] `/healthz` + `/livez`. *(Done 2026-04-23 — `backend/routers/health.py`. `/livez` always 200; `/healthz` returns 200/503 with per-dependency `{db, ollama}` checks. Intentionally unauthenticated so Docker/k8s probes can reach them. Covered by `tests/test_health.py`.)*
- [ ] Alembic migrations; backfill schema.
- [ ] Frontend: react-query, virtualized list, error boundaries.
- [ ] `tests/` integration test for full pipeline.

### 6.2 90-day plan (moats)

- [ ] **LLM provider abstraction** (Ollama + Anthropic adapters first).
- [ ] **Tree-sitter chunker + symbol map** for one language to start (Python or TS), then expand.
- [ ] **Lightweight RAG** with `sqlite-vec` and `nomic-embed-text`. Top-k retrieval injected into prompt.
- [ ] **Verifier pass** (cheap second model that drops unconfirmed issues).
- [ ] **Auto-fix patches** behind a feature flag.
- [ ] **VS Code extension** v0: shows review markers in the gutter, full review in side panel; talks to local backend.
- [ ] **GitHub PR mode** GA: webhook + PR comment formatting.
- [ ] **Telemetry + feedback loop** with opt-in.
- [ ] **`.codewatch/rules.md`** ingestion.
- [ ] **SSE stream** with resume; WS retired.

### 6.3 Versioned roadmap

- **v0.x (today):** local watcher MVP. Deprecate after v1 ships.
- **v1.0 (30 day):** secure, well-tested, CI-checked, CLI + GitHub Action. Story: "the privacy-first code review tool that runs on your laptop."
- **v1.5 (60 day):** multi-provider + verifier + content cache + observability.
- **v2.0 (90 day):** RAG + cross-file context + VS Code extension. Story: "as smart as CodeRabbit, runs on your laptop."
- **v2.x:** auto-fix, custom rules, telemetry-driven prompt tuning, hosted-managed option (BYOK), team mode (shared rules + read-only feed).
- **v3.0+:** language-specific specialized reviewers (Python security, TS performance, SQL), a small marketplace of community prompt packs, optional hosted Pro tier.

### 6.4 What to defer (and why)

- Multi-user / SSO / team workspaces — until you have product-market fit with solo devs.
- JetBrains plugin — wait until VS Code is sticky.
- Postgres backend — wait until SQLite hurts.
- Web SaaS — last; it dilutes the local-first message.

---

## 7. Brutal Truth

**1. Your moat is thinner than you think.** "Local + private" sounds great, but Continue.dev already supports Ollama, and PrivateGPT-style projects exist. Your *real* moat is the **always-on streaming watcher UX** — no competitor does this. Lean into that, hard. Stop describing CodeWatch as "an offline alternative" and start describing it as "continuous code review, like a linter for AI insight." Reframe the marketing.

**2. Ollama at 7B is genuinely not good enough for most users.** The README admits this. If your only model story is "install Ollama and pull qwen2.5-coder:7b," you will lose every comparison test. Ship a hosted-model adapter (BYOK, user pastes their Anthropic/OpenAI key) within v1.5 or you will permanently underperform on quality. Privacy purists keep Ollama; everyone else gets the upgrade path.

**3. The single-file scope is your biggest functional weakness.** Without cross-file context, your reviewer gives plausible-sounding wrong advice on most non-trivial code. This is not a polish issue — it's the difference between "useful" and "noise." Tree-sitter + a symbol map is non-negotiable.

**4. The current code looks alpha.** Six commits, all "Project skeleton and structure build using claude," generic messages, no CI, no tests on the routers, an XSS in the UI, a path traversal in the API, an unbounded memory cache, and a single open WebSocket port on `0.0.0.0`. A CTO doing due diligence stops here. None of this is hard to fix; you must fix it before pitching anyone.

**5. The streaming feed is cool but borderline a distraction.** Most developers don't want a constantly-streaming review feed in another browser tab. They want results *where they already are* (IDE, terminal, PR). The web feed is fine as a control panel + history view, but if you over-invest in it, you've built the wrong product. Ship the CLI + VS Code extension early.

**6. Do not build "agents."** Resist the temptation. A reviewer that calls tools, plans, retries, and "thinks" is slower, more expensive, and harder to evaluate than one good prompt with retrieved context. Bugbot is not an agent; it's a pipeline. Same here.

**7. You are not going to beat CodeRabbit at the enterprise game.** Don't try. They will out-spend you on integrations, compliance, and SOC 2. Your wedge is "individual developer, privacy, no setup." Win that customer first; resist the urge to chase logos.

**8. "Multi-provider" is a feature; "agentic multi-agent orchestration" is a meme.** Ship the boring useful one.

**9. The PDF in the repo (`Competitive Landscape.pdf`) is a strategic doc that should not be public.** Either gitignore it or move it out. Untracked + at repo root is the worst of both — it'll get accidentally committed.

**10. Cut these now:**
- The Telegram integration as a default surface — it's fiddly to set up and most users won't. Make it a plugin behind a flag.
- The "max_concurrency: 1" cap on a tool whose whole pitch is parallel local model usage. Embarrassing.
- Repo-root `package-lock.json`. Stray. Delete or gitignore.
- Generic skeleton commit history. Squash and rewrite before any external eyes see this.
- The placeholder `docs/screenshot.png` (12 bytes). It's worse than no image — it signals "unfinished."

**11. What you might be overestimating.** That open-source distribution alone is enough. It isn't. You'll need the GitHub Action and VS Code extension to get organic discovery. Plan distribution as deliberately as you plan code.

**12. What you might be underestimating.** Prompt iteration is the actual product. Build the feedback loop in v1 (👍/👎 + rationale stored), or you will be flying blind on the dimension that matters most: review quality.

---

## Critical files (when implementation begins)

- `backend/services/reviewer.py` — split into pipeline; sync→async file read; structured prompt; verifier hook.
- `backend/services/diff.py` — DiffEngine class with bounded LRU.
- `backend/services/queue.py` — durable JobStore-backed queue.
- `backend/core/ws_manager.py` → `backend/api/stream.py` (SSE with resume).
- `backend/services/ollama_client.py` → `backend/llm/{base,ollama,anthropic,...}.py`.
- `backend/routers/reviews.py:90-102` — path traversal fix + auth dep.
- `backend/routers/config.py` — `ollama_url` whitelist + auth dep.
- `backend/main.py` — auth middleware, default `127.0.0.1` bind, structlog wiring.
- `backend/core/database.py:102` — `func.count()` fix; index migration.
- `frontend/src/components/ReviewCard.tsx:14-19,64` and `ReviewDetail.tsx` — replace `dangerouslySetInnerHTML` with sanitized Markdown.
- `frontend/src/hooks/useWebSocket.ts` → `useEventStream.ts` (SSE) with resume.
- `frontend/src/hooks/useReviews.ts` — adopt react-query, virtualize.
- `frontend/src/api/client.ts` → openapi-typescript codegen + Zod runtime checks.
- `.github/workflows/ci.yml` — new.
- `extension/` — new VS Code extension package.

---

## Verification

After each phase, prove it works end-to-end:

- **Security fixes:** unit test path-traversal returns 400; manual XSS test (commit a file with `<img src=x onerror=alert(1)>` content; confirm no script execution); curl `POST /api/config` without bearer returns 401.
- **Quality improvements:** evaluation harness — keep a small held-out set of ~30 known-buggy and ~30 known-clean files; track precision/recall and FP rate per prompt version; require non-regression to merge prompt changes.
- **Performance:** benchmark script that fires 100 file changes and measures p50/p95 review latency, queue depth, RSS memory; record in CI.
- **CI:** `make ci` runs lint + types + tests on every push; PRs block on red.
- **Distribution:** `pre-commit install` in a fresh repo, modify a file, see CodeWatch run; install GitHub Action in a fork, open a PR, see a comment; install VS Code extension, see diagnostics inline.
- **Reliability:** kill `-9` the backend mid-review; restart; confirm pending jobs replay and the diff cache resumes warm.
- **Observability:** verify trace IDs appear in logs across `request → enqueue → worker → ollama → broadcast → save`.

End state for v2.0: a CTO reviewing the repo sees green CI, signed releases, a real demo GIF, security policy, evaluation harness with FP/recall numbers, and a one-line install for CLI / GitHub Action / VS Code. *That* is the version that competes.

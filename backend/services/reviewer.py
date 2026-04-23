from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# Keep strong refs so fire-and-forget tasks (notify) aren't GC'd mid-flight.
_BACKGROUND_TASKS: set[asyncio.Task] = set()

_last_duration_ms: int = 0
_last_tokens_per_sec: float = 0.0

# Keep full-file + diff together whenever the file fits this many lines.
FULL_DIFF_MAX_LINES = 300

# Token batching: coalesce Ollama tokens into ~50ms windows before broadcasting.
# At ~5 tok/s with 50 clients and a 2000-token review that's 500k socket writes;
# batching at 50ms collapses this to ~20 writes/sec per client.
_TOKEN_BATCH_INTERVAL_S = 0.05

# Content-hash → (full_text, severity) cache. A save storm that reverts a
# file to a previous state, a whitespace-only change, or reviewing the same
# generated file across projects all hit here and skip the Ollama call. The
# prompt is the key because it encodes every signal that could change the
# model's output: file content, language, mode, filename, and the current
# system rules text.
_REVIEW_CACHE_MAX = 500
_review_cache: OrderedDict[str, tuple[str, str]] = OrderedDict()


def _prompt_cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8", errors="replace")).hexdigest()


def _cache_lookup(key: str) -> tuple[str, str] | None:
    hit = _review_cache.get(key)
    if hit is not None:
        _review_cache.move_to_end(key)
    return hit


def _cache_store(key: str, full_text: str, severity: str) -> None:
    _review_cache[key] = (full_text, severity)
    _review_cache.move_to_end(key)
    while len(_review_cache) > _REVIEW_CACHE_MAX:
        _review_cache.popitem(last=False)


def get_last_stats() -> tuple[int, float]:
    return _last_duration_ms, _last_tokens_per_sec


class Reviewer:
    async def run(self, job) -> None:
        from backend.core.config import get_config
        from backend.core.database import save_review
        from backend.core.ws_manager import manager
        from backend.models.events import ReviewDone, ReviewStart, ReviewToken, Toast
        from backend.models.review import Review
        from backend.services.notifier import notify
        from backend.services.ollama_client import (
            OllamaModelNotFoundError,
            OllamaUnavailableError,
            get_ollama_client,
        )
        from backend.services.prompt_builder import build_prompt
        from backend.utils.language import get_language

        global _last_duration_ms, _last_tokens_per_sec

        cfg = get_config()
        file_path = Path(job.path)
        project_path = None

        from backend.core.database import get_project_by_id

        project = get_project_by_id(job.project_id)
        if project:
            project_path = Path(project.path)

        try:
            content = await asyncio.to_thread(
                file_path.read_text, encoding="utf-8", errors="replace"
            )
        except Exception as exc:
            logger.warning("Cannot read %s: %s", job.path, exc)
            await manager.broadcast(
                Toast(level="error", message=f"Cannot read {file_path.name}").model_dump()
            )
            return

        language = get_language(str(file_path))
        line_count = content.count("\n") + 1

        mode, payload = self._select_mode(
            cfg.review_mode, project_path, job.project_id, file_path, content, line_count
        )

        prompt = build_prompt(
            filename=file_path.name,
            language=language,
            mode=mode,
            payload=payload,
            max_chars=cfg.prompt_max_chars,
        )

        import uuid

        review_id = str(uuid.uuid4())
        review = Review(
            id=review_id,
            project_id=job.project_id,
            filename=str(file_path).replace("\\", "/"),
            language=language,
            mode=mode,
        )
        save_review(review)

        await manager.broadcast(
            ReviewStart(
                review_id=review_id,
                project_id=job.project_id,
                filename=str(file_path).replace("\\", "/"),
                timestamp=datetime.now(tz=timezone.utc).isoformat(),
            ).model_dump()
        )

        cache_key = _prompt_cache_key(prompt)
        cached = _cache_lookup(cache_key)

        if cached is not None:
            full_text, severity = cached
            token_count = len(full_text.split())
            elapsed_ms = 0
            _last_duration_ms = elapsed_ms
            _last_tokens_per_sec = 0.0
            # Emit the cached body as one token so the UI renders immediately.
            await manager.broadcast(ReviewToken(review_id=review_id, token=full_text).model_dump())
            logger.info(
                "Review cache hit for %s [%s]; skipped Ollama call",
                file_path.name,
                cache_key[:12],
            )
        else:
            client = get_ollama_client()
            full_text = ""
            token_count = 0
            start_time = time.monotonic()
            batch: list[str] = []
            last_flush = time.monotonic()

            try:
                async for token in client.generate_stream(cfg.model, prompt):
                    full_text += token
                    token_count += 1
                    batch.append(token)
                    now = time.monotonic()
                    if now - last_flush >= _TOKEN_BATCH_INTERVAL_S:
                        await manager.broadcast(
                            ReviewToken(review_id=review_id, token="".join(batch)).model_dump()
                        )
                        batch.clear()
                        last_flush = now
                if batch:
                    await manager.broadcast(
                        ReviewToken(review_id=review_id, token="".join(batch)).model_dump()
                    )
                    batch.clear()
            except OllamaUnavailableError as exc:
                logger.error("Ollama unavailable: %s", exc)
                await manager.broadcast(
                    Toast(level="error", message=f"Ollama unavailable: {exc}").model_dump()
                )
                return
            except OllamaModelNotFoundError as exc:
                logger.error("Model not found: %s", exc)
                await manager.broadcast(Toast(level="error", message=str(exc)).model_dump())
                return

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            _last_duration_ms = elapsed_ms
            _last_tokens_per_sec = token_count / max(elapsed_ms / 1000, 0.001)

            severity = _detect_severity(full_text, cfg.min_confidence)
            _cache_store(cache_key, full_text, severity)

        from sqlmodel import Session

        from backend.core.database import engine

        with Session(engine) as session:
            db_review = session.get(Review, review_id)
            if db_review:
                db_review.full_text = full_text
                db_review.severity = severity
                db_review.duration_ms = elapsed_ms
                db_review.prompt_tokens = len(prompt.split())
                db_review.completion_tokens = token_count
                session.commit()

        await manager.broadcast(
            ReviewDone(
                review_id=review_id,
                full_text=full_text,
                severity=severity,
                mode=mode,
            ).model_dump()
        )

        # Notification is a side effect — desktop toast + optional Telegram HTTP.
        # Let ReviewDone land in the UI immediately rather than waiting on a
        # 10s Telegram timeout in the worst case.
        task = asyncio.create_task(notify(severity, str(file_path.name), full_text))
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)

        logger.info(
            "Review done for %s [%s mode=%s] in %dms", file_path.name, severity, mode, elapsed_ms
        )

    @staticmethod
    def _select_mode(review_mode, project_path, project_id, file_path, content, line_count):
        """Return ``(mode, payload)`` for ``build_prompt``.

        In ``auto`` mode we send full-file + diff when the file is small so the
        model keeps architectural context instead of seeing only a 5-line diff.
        """
        from backend.services.diff import compute_diff

        if review_mode == "always_full":
            return "full", content
        if project_path is None:
            return "full", content

        diff_mode, diff_payload = compute_diff(project_id, project_path, file_path, content)

        if review_mode == "always_diff":
            return diff_mode, diff_payload

        # auto: combine full file + diff on small files so the model has both
        # the architectural context and the "what just changed" signal.
        if diff_mode == "diff" and line_count <= FULL_DIFF_MAX_LINES:
            return "full+diff", {"code": content, "diff": diff_payload}

        return diff_mode, diff_payload


def _detect_severity(text: str, min_confidence: float = 0.5) -> str:
    """Pick severity from model output, filtering by confidence."""
    from backend.services.review_parser import classify_severity, parse_issues

    issues = parse_issues(text)
    if issues:
        return classify_severity(issues, min_confidence=min_confidence)

    # Last-resort fallback for free-form output that matched neither JSON
    # nor our header format — detect common critical phrasing.
    import re

    lower = text.lower()
    if re.search(r"\b(vulnerability|exploit|command injection|sql injection|rce)\b", lower):
        return "critical"
    if re.search(r"\b(bug|unsafe|race condition|deadlock|data loss)\b", lower):
        return "warning"
    return "suggestion"


reviewer = Reviewer()

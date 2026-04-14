from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_last_duration_ms: int = 0
_last_tokens_per_sec: float = 0.0


def get_last_stats() -> tuple[int, float]:
    return _last_duration_ms, _last_tokens_per_sec


class Reviewer:
    async def run(self, job) -> None:
        from backend.core.config import get_config
        from backend.core.database import get_review_by_id, save_review
        from backend.core.ws_manager import manager
        from backend.models.events import ReviewDone, ReviewStart, ReviewToken, Toast
        from backend.models.review import Review
        from backend.services.diff import compute_diff
        from backend.services.notifier import notify
        from backend.services.ollama_client import OllamaModelNotFound, OllamaUnavailable, get_ollama_client
        from backend.services.prompt_builder import build_prompt
        from backend.utils.language import get_language

        global _last_duration_ms, _last_tokens_per_sec

        cfg = get_config()
        file_path = Path(job.path)
        project_path = None

        # Find project root
        from backend.core.database import get_project_by_id
        project = get_project_by_id(job.project_id)
        if project:
            project_path = Path(project.path)

        # Read file
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            logger.warning("Cannot read %s: %s", job.path, exc)
            await manager.broadcast(Toast(level="error", message=f"Cannot read {file_path.name}").model_dump())
            return

        language = get_language(str(file_path))

        # Determine mode
        if cfg.review_mode == "always_full":
            mode, payload = "full", content
        elif cfg.review_mode == "always_diff":
            if project_path:
                mode, payload = compute_diff(job.project_id, project_path, file_path, content)
            else:
                mode, payload = "full", content
        else:  # auto
            if project_path:
                mode, payload = compute_diff(job.project_id, project_path, file_path, content)
            else:
                mode, payload = "full", content

        prompt = build_prompt(
            filename=file_path.name,
            language=language,
            mode=mode,
            payload=payload,
            max_chars=cfg.prompt_max_chars,
        )

        # Create review record
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

        await manager.broadcast(ReviewStart(
            review_id=review_id,
            project_id=job.project_id,
            filename=str(file_path).replace("\\", "/"),
            timestamp=datetime.now(tz=timezone.utc).isoformat(),
        ).model_dump())

        # Stream from Ollama
        client = get_ollama_client()
        full_text = ""
        token_count = 0
        start_time = time.monotonic()

        try:
            async for token in client.generate_stream(cfg.model, prompt):
                full_text += token
                token_count += 1
                await manager.broadcast(ReviewToken(review_id=review_id, token=token).model_dump())
        except OllamaUnavailable as exc:
            logger.error("Ollama unavailable: %s", exc)
            await manager.broadcast(Toast(level="error", message=f"Ollama unavailable: {exc}").model_dump())
            return
        except OllamaModelNotFound as exc:
            logger.error("Model not found: %s", exc)
            await manager.broadcast(Toast(level="error", message=str(exc)).model_dump())
            return

        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        _last_duration_ms = elapsed_ms
        _last_tokens_per_sec = token_count / max(elapsed_ms / 1000, 0.001)

        severity = _detect_severity(full_text)

        # Update review in DB
        from backend.core.database import engine
        from sqlmodel import Session
        with Session(engine) as session:
            db_review = session.get(Review, review_id)
            if db_review:
                db_review.full_text = full_text
                db_review.severity = severity
                db_review.duration_ms = elapsed_ms
                db_review.prompt_tokens = len(prompt.split())
                db_review.completion_tokens = token_count
                session.commit()

        await manager.broadcast(ReviewDone(
            review_id=review_id,
            full_text=full_text,
            severity=severity,
        ).model_dump())

        await notify(severity, str(file_path.name), full_text)
        logger.info("Review done for %s [%s] in %dms", file_path.name, severity, elapsed_ms)


def _detect_severity(text: str) -> str:
    lower = text.lower()
    if any(word in lower for word in ("critical", "security", "vulnerability", "exploit", "injection")):
        return "critical"
    if any(word in lower for word in ("warning", "bug", "error", "unsafe", "deprecated")):
        return "warning"
    return "suggestion"


reviewer = Reviewer()

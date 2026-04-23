from __future__ import annotations

import asyncio
import hashlib
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _hash_file(path: Path) -> str | None:
    try:
        content = path.read_bytes()
        if b"\x00" in content[:8192]:  # Binary sniff
            return None
        return hashlib.sha256(content).hexdigest()
    except Exception:
        return None


def _is_binary(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:8192]
        return b"\x00" in chunk
    except Exception:
        return True


class ProjectHandler(FileSystemEventHandler):
    def __init__(self, project, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        from backend.core.config import get_config
        from backend.utils.gitignore import GitignoreMatcher

        self._project = project
        self._project_path = Path(project.path)
        self._loop = loop
        self._cfg = get_config()
        self._debounce_timers: dict[str, threading.Timer] = {}
        self._last_hashes: dict[str, str] = {}
        self._gitignore = GitignoreMatcher(self._project_path)
        self._lock = threading.Lock()

    def _should_process(self, path_str: str) -> bool:
        cfg = self._cfg
        path = Path(path_str)

        # Extension check
        if path.suffix.lower() not in cfg.watch_extensions:
            return False

        # Ignore patterns
        for pattern in cfg.ignore_patterns:
            if pattern in path.parts or pattern in path_str:
                return False

        # Gitignore
        if cfg.respect_gitignore and self._gitignore.is_ignored(path, self._project_path):
            return False

        # Binary check
        if not path.exists():
            return False
        if _is_binary(path):
            return False

        # Line count check
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > cfg.max_file_lines:
                logger.debug(
                    "Skipping %s — exceeds max_file_lines (%d)", path_str, cfg.max_file_lines
                )
                return False
        except Exception:
            return False

        return True

    def _trigger(self, path_str: str) -> None:
        with self._lock:
            timer = self._debounce_timers.pop(path_str, None)
            if timer:
                timer.cancel()

        path = Path(path_str)
        if not self._should_process(path_str):
            return

        # Hash check (skip_unchanged)
        if self._cfg.skip_unchanged:
            current_hash = _hash_file(path)
            if current_hash is None:
                return
            if self._last_hashes.get(path_str) == current_hash:
                logger.debug("Skipping unchanged file: %s", path_str)
                return
            self._last_hashes[path_str] = current_hash

        from backend.services.queue import ReviewJob, review_queue

        job = ReviewJob(project_id=self._project.id, path=path_str)
        asyncio.run_coroutine_threadsafe(review_queue.enqueue(job), self._loop)
        logger.info("Queued review: %s", path_str)

    def _schedule(self, path_str: str) -> None:
        cfg = self._cfg
        with self._lock:
            existing = self._debounce_timers.pop(path_str, None)
            if existing:
                existing.cancel()
            timer = threading.Timer(cfg.debounce_seconds, self._trigger, args=[path_str])
            self._debounce_timers[path_str] = timer
            timer.start()

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._schedule(str(event.src_path))

    def stop(self) -> None:
        with self._lock:
            for timer in self._debounce_timers.values():
                timer.cancel()
            self._debounce_timers.clear()

    def reload_config(self) -> None:
        from backend.core.config import get_config
        from backend.utils.gitignore import GitignoreMatcher

        self._cfg = get_config()
        self._gitignore = GitignoreMatcher(self._project_path)


class WatcherSupervisor:
    def __init__(self) -> None:
        self._observer: Observer = Observer()
        self._handlers: dict[int, tuple[ProjectHandler, object]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started = False

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._observer.start()
        self._started = True
        logger.info("File watcher started")

    def stop(self) -> None:
        if self._started:
            for handler, _ in self._handlers.values():
                handler.stop()
            self._observer.stop()
            self._observer.join()
            self._started = False
            logger.info("File watcher stopped")

    def add_project(self, project) -> None:
        if project.id in self._handlers:
            return
        if self._loop is None:
            return
        handler = ProjectHandler(project, self._loop)
        watch = self._observer.schedule(handler, str(project.path), recursive=True)
        self._handlers[project.id] = (handler, watch)
        logger.info("Watching project '%s' at %s", project.name, project.path)

    def remove_project(self, project_id: int) -> None:
        if project_id not in self._handlers:
            return
        handler, watch = self._handlers.pop(project_id)
        handler.stop()
        self._observer.unschedule(watch)
        logger.info("Stopped watching project %d", project_id)

    def reload_config(self) -> None:
        for handler, _ in self._handlers.values():
            handler.reload_config()

    @property
    def watching_ids(self) -> set[int]:
        return set(self._handlers.keys())


watcher_supervisor = WatcherSupervisor()

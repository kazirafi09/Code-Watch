from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass
class ReviewJob:
    project_id: int
    path: str
    job_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex)


class ReviewQueue:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[ReviewJob] = asyncio.Queue()
        self._pending: dict[tuple[int, str], ReviewJob] = {}
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._reviewer = None

    def set_reviewer(self, reviewer) -> None:
        self._reviewer = reviewer

    async def start(self, max_concurrency: int = 1) -> None:
        self._running = True
        for _ in range(max_concurrency):
            task = asyncio.create_task(self._worker())
            self._workers.append(task)
        logger.info("ReviewQueue started with concurrency=%d", max_concurrency)

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        self._workers.clear()
        logger.info("ReviewQueue stopped")

    async def enqueue(self, job: ReviewJob) -> None:
        key = (job.project_id, job.path)
        if key in self._pending:
            # Replace in-place — worker will see new job_id and skip the stale queued entry;
            # put the replacement on the queue so it actually gets processed.
            self._pending[key] = job
            await self._queue.put(job)
            logger.debug("Replaced pending job for %s", job.path)
        else:
            self._pending[key] = job
            await self._queue.put(job)
            logger.debug("Enqueued review for %s (depth=%d)", job.path, self._queue.qsize())

        await self._broadcast_queue_update()

    async def _worker(self) -> None:
        while self._running:
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            key = (job.project_id, job.path)
            # Only process if this is still the current job for this key
            current = self._pending.get(key)
            if current and current.job_id != job.job_id:
                # Stale job — skip
                self._queue.task_done()
                continue

            self._pending.pop(key, None)
            await self._broadcast_queue_update()

            if self._reviewer:
                try:
                    await self._reviewer.run(job)
                except Exception:
                    logger.exception("Reviewer failed for %s", job.path)

            self._queue.task_done()

    async def _broadcast_queue_update(self) -> None:
        from backend.core.ws_manager import manager
        from backend.models.events import QueueUpdate

        await manager.broadcast(QueueUpdate(depth=self.depth).model_dump())

    @property
    def depth(self) -> int:
        return len(self._pending)

    async def clear(self) -> int:
        count = self._queue.qsize()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        self._pending.clear()
        await self._broadcast_queue_update()
        logger.info("ReviewQueue cleared (%d jobs removed)", count)
        return count

    async def restart_workers(self, max_concurrency: int) -> None:
        await self.stop()
        await self.start(max_concurrency)


review_queue = ReviewQueue()

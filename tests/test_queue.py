from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_queue_deduplication():
    from backend.services.queue import ReviewJob, ReviewQueue

    q = ReviewQueue()
    processed = []

    async def fake_reviewer(job):
        processed.append(job.path)

    class FakeReviewer:
        async def run(self, job):
            await fake_reviewer(job)

    q.set_reviewer(FakeReviewer())

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.core.ws_manager.manager"
    ) as mock_ws:
        mock_ws.broadcast = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()

        await q.start(max_concurrency=1)

        job1 = ReviewJob(project_id=1, path="/project/file.py")
        job2 = ReviewJob(project_id=1, path="/project/file.py")  # duplicate

        await q.enqueue(job1)
        await q.enqueue(job2)

        await asyncio.sleep(0.2)
        await q.stop()

    # Deduplication: only one job should be processed
    assert len(processed) <= 1


@pytest.mark.asyncio
async def test_queue_processes_different_files():
    from backend.services.queue import ReviewJob, ReviewQueue

    q = ReviewQueue()
    processed = []

    class FakeReviewer:
        async def run(self, job):
            processed.append(job.path)

    q.set_reviewer(FakeReviewer())

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "backend.core.ws_manager.manager"
    ) as mock_ws:
        mock_ws.broadcast = __import__("unittest.mock", fromlist=["AsyncMock"]).AsyncMock()

        await q.start(max_concurrency=1)

        await q.enqueue(ReviewJob(project_id=1, path="/project/a.py"))
        await q.enqueue(ReviewJob(project_id=1, path="/project/b.py"))

        await asyncio.sleep(0.3)
        await q.stop()

    assert len(processed) == 2

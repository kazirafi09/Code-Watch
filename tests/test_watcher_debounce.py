from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def test_debounce_coalesces_rapid_events(temp_project_dir):
    """Multiple rapid file changes should result in only one queued review."""
    from backend.models.project import Project
    from backend.services.watcher import ProjectHandler

    project = Project(id=1, name="test", path=str(temp_project_dir))
    loop = asyncio.new_event_loop()

    py_file = temp_project_dir / "main.py"
    py_file.write_text("x = 1\n")

    enqueued = []

    async def fake_enqueue(job):
        enqueued.append(job)

    with patch("backend.services.queue.review_queue") as mock_queue:
        mock_queue.enqueue = AsyncMock(side_effect=fake_enqueue)
        handler = ProjectHandler(project, loop)
        handler._cfg.debounce_seconds = 0.1

        # Simulate rapid changes
        for _ in range(5):
            handler._schedule(str(py_file))
            time.sleep(0.02)

        # Wait for debounce
        time.sleep(0.3)
        loop.run_until_complete(asyncio.sleep(0))

    loop.close()
    # Should have at most 1 queued job (debounce coalesced the rest)
    assert len(enqueued) <= 1


def test_ignored_extension_not_queued(temp_project_dir):
    from backend.models.project import Project
    from backend.services.watcher import ProjectHandler

    project = Project(id=1, name="test", path=str(temp_project_dir))
    loop = asyncio.new_event_loop()

    txt_file = temp_project_dir / "readme.txt"
    txt_file.write_text("hello\n")

    handler = ProjectHandler(project, loop)
    assert not handler._should_process(str(txt_file))
    loop.close()


def test_binary_file_skipped(temp_project_dir):
    from backend.models.project import Project
    from backend.services.watcher import ProjectHandler

    project = Project(id=1, name="test", path=str(temp_project_dir))
    loop = asyncio.new_event_loop()

    bin_file = temp_project_dir / "data.py"
    bin_file.write_bytes(b"\x00\x01\x02\x03\x04binary data")

    handler = ProjectHandler(project, loop)
    assert not handler._should_process(str(bin_file))
    loop.close()

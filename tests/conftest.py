from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from sqlmodel import Session, SQLModel, create_engine

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///./test_codewatch.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def mock_ollama(mocker):
    async def fake_generate_stream(model, prompt):
        tokens = ["This ", "is ", "a ", "test ", "review."]
        for t in tokens:
            yield t

    mock_client = mocker.MagicMock()
    mock_client.health = mocker.AsyncMock(return_value=True)
    mock_client.list_models = mocker.AsyncMock(return_value=["codellama:latest"])
    mock_client.generate_stream = fake_generate_stream
    mocker.patch("backend.services.ollama_client.get_ollama_client", return_value=mock_client)
    return mock_client


@pytest.fixture(autouse=True)
def reset_config_state():
    """Reset module-level config singleton between tests."""
    import backend.core.config as cfg_mod
    original = cfg_mod._config
    yield
    cfg_mod._config = original

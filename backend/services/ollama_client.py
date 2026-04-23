from __future__ import annotations

import contextlib
import json
import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OllamaUnavailableError(Exception):
    pass


class OllamaModelNotFoundError(Exception):
    pass


# Shared connection pool. Constructing a fresh AsyncClient per call re-does TCP
# + TLS handshakes and defeats keep-alive; with a long-lived client every
# Ollama call rides the existing pool.
_POOL_LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)

# Strong refs for fire-and-forget close() tasks so the loop doesn't GC them.
_PENDING_CLOSES: set = set()


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        timeout: int = 120,
        temperature: float = 0.2,
        seed: int | None = 42,
        num_predict: int = 2048,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._temperature = temperature
        self._seed = seed
        self._num_predict = num_predict
        # One pool shared by health/list_models (short timeout) and streaming
        # (long timeout). httpx lets us pass a per-request timeout so a single
        # client is fine.
        self._client = httpx.AsyncClient(timeout=self._timeout, limits=_POOL_LIMITS)

    async def close(self) -> None:
        with contextlib.suppress(Exception):
            await self._client.aclose()

    async def health(self) -> bool:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            resp = await self._client.get(f"{self._base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
        except httpx.ConnectError as e:
            raise OllamaUnavailableError(f"Cannot connect to Ollama at {self._base_url}") from e
        except Exception as e:
            raise OllamaUnavailableError(str(e)) from e

    async def generate_stream(
        self, model: str, prompt: str, think: bool = False
    ) -> AsyncIterator[str]:
        options: dict = {
            "temperature": self._temperature,
            "num_predict": self._num_predict,
        }
        if self._seed is not None:
            options["seed"] = self._seed
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "think": think,
            "options": options,
        }
        try:
            async with self._client.stream(
                "POST",
                f"{self._base_url}/api/generate",
                json=payload,
            ) as resp:
                if resp.status_code == 404:
                    raise OllamaModelNotFoundError(f"Model '{model}' not found in Ollama")
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done"):
                        break
        except (OllamaUnavailableError, OllamaModelNotFoundError):
            raise
        except httpx.ConnectError as e:
            raise OllamaUnavailableError(f"Cannot connect to Ollama at {self._base_url}") from e
        except Exception as e:
            raise OllamaUnavailableError(str(e)) from e


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    from backend.core.config import get_config

    cfg = get_config()
    if (
        _client is None
        or _client._base_url != cfg.ollama_url.rstrip("/")
        or _client._temperature != cfg.ollama_temperature
        or _client._seed != cfg.ollama_seed
        or _client._num_predict != cfg.ollama_num_predict
    ):
        # Drop the old pool rather than leaking its sockets. We can't await
        # here, so schedule the close on the running loop if there is one.
        if _client is not None:
            _schedule_close(_client)
        _client = OllamaClient(
            cfg.ollama_url,
            cfg.ollama_timeout_seconds,
            temperature=cfg.ollama_temperature,
            seed=cfg.ollama_seed,
            num_predict=cfg.ollama_num_predict,
        )
    return _client


def _schedule_close(client: OllamaClient) -> None:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(client.close())
    _PENDING_CLOSES.add(task)
    task.add_done_callback(_PENDING_CLOSES.discard)


def reset_client() -> None:
    global _client
    if _client is not None:
        _schedule_close(_client)
    _client = None

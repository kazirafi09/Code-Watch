from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

import httpx

logger = logging.getLogger(__name__)


class OllamaUnavailable(Exception):
    pass


class OllamaModelNotFound(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                return [m["name"] for m in data.get("models", [])]
        except httpx.ConnectError as e:
            raise OllamaUnavailable(f"Cannot connect to Ollama at {self._base_url}") from e
        except Exception as e:
            raise OllamaUnavailable(str(e)) from e

    async def generate_stream(self, model: str, prompt: str) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/generate",
                    json=payload,
                ) as resp:
                    if resp.status_code == 404:
                        raise OllamaModelNotFound(f"Model '{model}' not found in Ollama")
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
        except (OllamaUnavailable, OllamaModelNotFound):
            raise
        except httpx.ConnectError as e:
            raise OllamaUnavailable(f"Cannot connect to Ollama at {self._base_url}") from e
        except Exception as e:
            raise OllamaUnavailable(str(e)) from e


_client: OllamaClient | None = None


def get_ollama_client() -> OllamaClient:
    global _client
    from backend.core.config import get_config
    cfg = get_config()
    if _client is None or _client._base_url != cfg.ollama_url:
        _client = OllamaClient(cfg.ollama_url, cfg.ollama_timeout_seconds)
    return _client


def reset_client() -> None:
    global _client
    _client = None

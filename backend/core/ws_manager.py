from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Per-client send timeout. A stalled socket must not wedge the review stream.
_SEND_TIMEOUT_S = 2.0


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)
        logger.debug("WebSocket connected. Total: %d", len(self._connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)
        logger.debug("WebSocket disconnected. Total: %d", len(self._connections))

    async def _send_one(self, ws: WebSocket, message: dict[str, Any]) -> None:
        await asyncio.wait_for(ws.send_json(message), timeout=_SEND_TIMEOUT_S)

    async def broadcast(self, message: dict[str, Any]) -> None:
        # Snapshot so a disconnect mid-broadcast does not mutate the list
        # we're iterating, and so one slow client cannot block the others.
        targets = list(self._connections)
        if not targets:
            return
        results = await asyncio.gather(
            *(self._send_one(ws, message) for ws in targets),
            return_exceptions=True,
        )
        for ws, result in zip(targets, results, strict=True):
            if isinstance(result, BaseException):
                if isinstance(result, asyncio.TimeoutError):
                    logger.warning("WS client timed out; dropping")
                self.disconnect(ws)

    async def send_to(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        try:
            await self._send_one(websocket, message)
        except Exception:
            self.disconnect(websocket)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


manager = ConnectionManager()

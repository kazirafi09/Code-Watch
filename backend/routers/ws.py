from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from backend.core.auth import check_ws_token
from backend.core.ws_manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = Query(default=None)) -> None:
    if not check_ws_token(token):
        # 1008 = policy violation. Close before accept so the browser sees
        # the handshake fail rather than an immediate disconnect.
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WS rejected: missing/invalid token")
        return

    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; accept any pings
            data = await websocket.receive_text()
            logger.debug("WS message received: %s", data[:100])
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

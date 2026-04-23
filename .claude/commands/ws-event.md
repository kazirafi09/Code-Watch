# /ws-event — Context for adding WebSocket event types

Load this before adding or modifying WebSocket event types.

## Where events live
- `backend/models/events.py` — Pydantic schemas for every WS event; the union type used for broadcast
- `backend/core/ws_manager.py` — `ConnectionManager`: `connect`, `disconnect`, `broadcast`
- `frontend/src/api/types.ts` — TS union type mirroring the backend event union (keep in sync)
- `frontend/src/hooks/useWebSocket.ts` — dispatches on `event.type`

## Steps to add a new event

1. **Backend** — add a new Pydantic model to `backend/models/events.py` with a `type: Literal["your_event"]` discriminator field. Add it to the union.
2. **Broadcast** — call `await ws_manager.broadcast(event.model_dump())` from the relevant service.
3. **Frontend types** — add the matching TS interface to `frontend/src/api/types.ts` and include it in the `WsEvent` union.
4. **Hook handler** — add a `case "your_event":` branch in `useWebSocket.ts`.

## Invariant
All events must have a `type` string literal field so the frontend discriminated union dispatches correctly. Never broadcast a raw dict without a `type` key.

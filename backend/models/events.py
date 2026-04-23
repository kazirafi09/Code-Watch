from __future__ import annotations

from pydantic import BaseModel


class ReviewStart(BaseModel):
    type: str = "review_start"
    review_id: str
    project_id: int
    filename: str
    timestamp: str


class ReviewToken(BaseModel):
    type: str = "review_token"
    review_id: str
    token: str


class ReviewDone(BaseModel):
    type: str = "review_done"
    review_id: str
    full_text: str
    severity: str
    mode: str = "full"  # "full" | "diff" | "full+diff"


class QueueUpdate(BaseModel):
    type: str = "queue_update"
    depth: int


class StatusUpdate(BaseModel):
    type: str = "status_update"
    ollama_ok: bool
    model: str
    queue_depth: int
    last_duration_ms: int | None = None
    tokens_per_sec: float | None = None


class Toast(BaseModel):
    type: str = "toast"
    level: str  # "error" | "warning" | "info" | "success"
    message: str

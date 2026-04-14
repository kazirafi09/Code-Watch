from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ReviewStatus(str, Enum):
    critical = "critical"
    warning = "warning"
    suggestion = "suggestion"
    pending = "pending"


class Review(SQLModel, table=True):
    __tablename__ = "review"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    project_id: int = Field(foreign_key="project.id", index=True)
    filename: str
    language: str = ""
    full_text: str = ""
    severity: str = ReviewStatus.pending.value
    mode: str = "full"  # "full" | "diff"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReviewRead(SQLModel):
    id: str
    project_id: int
    filename: str
    language: str
    full_text: str
    severity: str
    mode: str
    prompt_tokens: int
    completion_tokens: int
    duration_ms: int
    created_at: datetime

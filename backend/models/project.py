from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    __tablename__ = "project"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)


class ProjectCreate(SQLModel):
    name: str
    path: str


class ProjectRead(SQLModel):
    id: int
    name: str
    path: str
    created_at: datetime
    is_active: bool
    is_watching: bool = False

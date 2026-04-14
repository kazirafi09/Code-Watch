from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.core import database as db
from backend.models.project import Project, ProjectCreate, ProjectRead
from backend.services.watcher import watcher_supervisor

router = APIRouter(prefix="/api/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ProjectRead])
async def list_projects() -> list[ProjectRead]:
    projects = db.get_projects()
    watching = watcher_supervisor.watching_ids
    return [
        ProjectRead(
            id=p.id,
            name=p.name,
            path=p.path,
            created_at=p.created_at,
            is_active=p.is_active,
            is_watching=p.id in watching,
        )
        for p in projects
    ]


@router.post("", response_model=ProjectRead, status_code=201)
async def add_project(body: ProjectCreate) -> ProjectRead:
    path = Path(body.path)
    if not path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {body.path}")
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {body.path}")

    project = Project(name=body.name, path=str(path.resolve()))
    db.add_project(project)

    # Start watching
    watcher_supervisor.add_project(project)

    return ProjectRead(
        id=project.id,
        name=project.name,
        path=project.path,
        created_at=project.created_at,
        is_active=project.is_active,
        is_watching=True,
    )


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int) -> None:
    watcher_supervisor.remove_project(project_id)
    deleted = db.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")

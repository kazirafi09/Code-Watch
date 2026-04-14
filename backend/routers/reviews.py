from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.core import database as db
from backend.models.review import ReviewRead
from backend.services.queue import ReviewJob, review_queue

router = APIRouter(prefix="/api/reviews", tags=["reviews"])
logger = logging.getLogger(__name__)


class ReviewsResponse(BaseModel):
    items: list[ReviewRead]
    total: int
    limit: int
    offset: int


class TriggerRequest(BaseModel):
    project_id: int
    relative_path: str


@router.get("", response_model=ReviewsResponse)
async def list_reviews(
    project_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ReviewsResponse:
    items, total = db.get_reviews(
        project_id=project_id,
        severity=severity,
        search=search,
        limit=limit,
        offset=offset,
    )
    return ReviewsResponse(
        items=[ReviewRead.model_validate(r, from_attributes=True) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{review_id}", response_model=ReviewRead)
async def get_review(review_id: str) -> ReviewRead:
    review = db.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewRead.model_validate(review, from_attributes=True)


@router.delete("/{review_id}", status_code=204)
async def delete_review(review_id: str) -> None:
    if not db.delete_review(review_id):
        raise HTTPException(status_code=404, detail="Review not found")


@router.get("/{review_id}/export")
async def export_review(review_id: str) -> PlainTextResponse:
    review = db.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    md = f"# Code Review: {review.filename}\n\n"
    md += f"**Severity:** {review.severity}  \n"
    md += f"**Language:** {review.language}  \n"
    md += f"**Mode:** {review.mode}  \n"
    md += f"**Date:** {review.created_at.isoformat()}  \n\n"
    md += "---\n\n"
    md += review.full_text

    filename = review.filename.replace("/", "_").replace("\\", "_")
    return PlainTextResponse(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="review_{filename}.md"'},
    )


@router.post("/trigger", status_code=202)
async def trigger_review(body: TriggerRequest) -> dict:
    project = db.get_project_by_id(body.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from pathlib import Path
    full_path = Path(project.path) / body.relative_path
    if not full_path.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {full_path}")

    job = ReviewJob(project_id=body.project_id, path=str(full_path))
    await review_queue.enqueue(job)
    return {"queued": True, "path": str(full_path)}

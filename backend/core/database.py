from __future__ import annotations

from collections.abc import Generator
from typing import TYPE_CHECKING

from sqlmodel import Session, SQLModel, create_engine, select

if TYPE_CHECKING:
    from backend.models.project import Project
    from backend.models.review import Review

DATABASE_URL = "sqlite:///./codewatch.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Project helpers
# ---------------------------------------------------------------------------

def get_projects() -> list:
    from backend.models.project import Project as ProjectModel
    with Session(engine) as session:
        return session.exec(select(ProjectModel)).all()


def add_project(project) -> None:
    with Session(engine) as session:
        session.add(project)
        session.commit()
        session.refresh(project)


def delete_project(project_id: int) -> bool:
    from backend.models.project import Project as ProjectModel
    with Session(engine) as session:
        project = session.get(ProjectModel, project_id)
        if not project:
            return False
        session.delete(project)
        session.commit()
        return True


def get_project_by_id(project_id: int):
    from backend.models.project import Project as ProjectModel
    with Session(engine) as session:
        return session.get(ProjectModel, project_id)


# ---------------------------------------------------------------------------
# Review helpers
# ---------------------------------------------------------------------------

def save_review(review) -> None:
    with Session(engine) as session:
        session.add(review)
        session.commit()
        session.refresh(review)


def get_reviews(
    project_id: int | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list, int]:
    from backend.models.review import Review as ReviewModel
    with Session(engine) as session:
        query = select(ReviewModel)
        count_query = select(ReviewModel)

        if project_id is not None:
            query = query.where(ReviewModel.project_id == project_id)
            count_query = count_query.where(ReviewModel.project_id == project_id)
        if severity:
            query = query.where(ReviewModel.severity == severity)
            count_query = count_query.where(ReviewModel.severity == severity)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                ReviewModel.filename.like(pattern) | ReviewModel.full_text.like(pattern)
            )
            count_query = count_query.where(
                ReviewModel.filename.like(pattern) | ReviewModel.full_text.like(pattern)
            )

        total = len(session.exec(count_query).all())
        query = query.order_by(ReviewModel.created_at.desc()).offset(offset).limit(limit)
        results = session.exec(query).all()
        return results, total


def get_review_by_id(review_id: str):
    from backend.models.review import Review as ReviewModel
    with Session(engine) as session:
        return session.get(ReviewModel, review_id)


def delete_review(review_id: str) -> bool:
    from backend.models.review import Review as ReviewModel
    with Session(engine) as session:
        review = session.get(ReviewModel, review_id)
        if not review:
            return False
        session.delete(review)
        session.commit()
        return True

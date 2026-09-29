"""Эндпоинты курсов: список, поиск, фильтрация, рекомендации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_access
from backend.app.database.session import get_db
from backend.app.domain import Course
from backend.app.repositories.course_repository import CourseRepository
from backend.app.schemas.course import CourseOut
from backend.app.services.recommendations import RecommendationService


def _parse_skill_ids(raw: str | None) -> list[int] | None:
    """Разобрать список id навыков из query-параметра (через запятую)."""
    if not raw:
        return None
    return [int(part) for part in raw.split(",") if part.strip().isdigit()]


router = APIRouter(tags=["courses"])


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    search: str | None = None,
    skills: str | None = Query(None, description="id навыков через запятую"),
    category: str | None = None,
    level: str | None = None,
    price_max: float | None = None,
    format: str | None = Query(None, alias="format"),
    platform: str | None = None,
    db: Session = Depends(get_db),
) -> list[Course]:
    """Список курсов с фильтрацией и поиском."""
    return CourseRepository(db).list_all(
        search=search,
        skill_ids=_parse_skill_ids(skills),
        category=category,
        level=level,
        price_max=price_max,
        format_=format,
        platform=platform,
    )


@router.get("/courses/recommended", response_model=list[CourseOut])
def recommended_courses(
    user_id: int = Query(...),
    search: str | None = None,
    category: str | None = None,
    level: str | None = None,
    price_max: float | None = None,
    format: str | None = Query(None, alias="format"),
    platform: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> list[Course]:
    """Рекомендации курсов на основе пробелов в навыках пользователя."""
    return RecommendationService(db).recommend_courses(
        user_id,
        search=search,
        category=category,
        level=level,
        price_max=price_max,
        format_=format,
        platform=platform,
    )


@router.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: Session = Depends(get_db)) -> Course:
    """Курс по id."""
    return CourseRepository(db).get(course_id)

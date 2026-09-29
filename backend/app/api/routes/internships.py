"""Эндпоинты стажировок: список, поиск, фильтрация, рекомендации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_access
from backend.app.api.responses import OWN_ERRORS
from backend.app.core.audit import log_access
from backend.app.database.session import get_db
from backend.app.domain import Internship
from backend.app.repositories.internship_repository import InternshipRepository
from backend.app.schemas.internship import InternshipOut
from backend.app.services.recommendations import RecommendationService


def _parse_skill_ids(raw: str | None) -> list[int] | None:
    """Разобрать список id навыков из query-параметра (через запятую)."""
    if not raw:
        return None
    return [int(part) for part in raw.split(",") if part.strip().isdigit()]


router = APIRouter(tags=["internships"])


@router.get("/internships", response_model=list[InternshipOut], openapi_extra={"security": []})
def list_internships(
    search: str | None = None,
    direction: str | None = None,
    skills: str | None = Query(None, description="id навыков через запятую"),
    level: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    format: str | None = Query(None, alias="format"),
    db: Session = Depends(get_db),
) -> list[Internship]:
    """Список стажировок с фильтрацией и поиском."""
    return InternshipRepository(db).list_all(
        search=search,
        direction=direction,
        skill_ids=_parse_skill_ids(skills),
        level=level,
        city=city,
        remote=remote,
        format_=format,
    )


@router.get(
    "/internships/directions",
    response_model=list[str],
    openapi_extra={"security": []},
)
def list_internship_directions(db: Session = Depends(get_db)) -> list[str]:
    """Доступные направления стажировок (для фильтров)."""
    return InternshipRepository(db).list_directions()


@router.get("/internships/recommended", response_model=list[InternshipOut], responses=OWN_ERRORS)
def recommended_internships(
    user_id: int = Query(...),
    search: str | None = None,
    direction: str | None = None,
    level: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    format: str | None = Query(None, alias="format"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> list[Internship]:
    """Рекомендации стажировок: совпадение направления и навыков."""
    log_access(
        action="read",
        resource="internship_recommendations",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )
    return RecommendationService(db).recommend_internships(
        user_id,
        search=search,
        direction=direction,
        level=level,
        city=city,
        remote=remote,
        format_=format,
    )


@router.get(
    "/internships/{internship_id}", response_model=InternshipOut, openapi_extra={"security": []}
)
def get_internship(internship_id: int, db: Session = Depends(get_db)) -> Internship:
    """Стажировка по id."""
    return InternshipRepository(db).get(internship_id)

"""Эндпоинты стажировок: список, поиск, фильтрация, рекомендации."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.internship_repository import InternshipRepository
from app.schemas.internship import InternshipOut
from app.services.recommendations import RecommendationService


def _parse_skill_ids(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(part) for part in raw.split(",") if part.strip().isdigit()]


router = APIRouter(tags=["internships"])


@router.get("/internships", response_model=list[InternshipOut])
def list_internships(
    search: str | None = None,
    direction: str | None = None,
    skills: str | None = Query(None, description="id навыков через запятую"),
    level: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    format: str | None = Query(None, alias="format"),
    db: Session = Depends(get_db),
) -> list[InternshipOut]:
    """Список стажировок с фильтрацией и поиском."""
    return InternshipRepository(db).list(
        search=search,
        direction=direction,
        skill_ids=_parse_skill_ids(skills),
        level=level,
        city=city,
        remote=remote,
        format_=format,
    )


@router.get("/internships/recommended", response_model=list[InternshipOut])
def recommended_internships(
    user_id: int = Query(...),
    search: str | None = None,
    direction: str | None = None,
    level: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    format: str | None = Query(None, alias="format"),
    db: Session = Depends(get_db),
) -> list[InternshipOut]:
    """Рекомендации стажировок: совпадение направления и навыков."""
    return RecommendationService(db).recommend_internships(
        user_id,
        search=search,
        direction=direction,
        level=level,
        city=city,
        remote=remote,
        format_=format,
    )


@router.get("/internships/{internship_id}", response_model=InternshipOut)
def get_internship(
    internship_id: int, db: Session = Depends(get_db)
) -> InternshipOut:
    """Стажировка по id."""
    return InternshipRepository(db).get(internship_id)
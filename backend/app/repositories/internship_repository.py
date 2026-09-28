"""Репозиторий стажировок с фильтрацией и поиском."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Internship, InternshipSkill


def _apply_filters(
    query: Select[tuple[Internship]],
    *,
    search: str | None = None,
    skill_ids: list[int] | None = None,
    direction: str | None = None,
    level: str | None = None,
    city: str | None = None,
    remote: bool | None = None,
    format_: str | None = None,
) -> Select[tuple[Internship]]:
    """Применить фильтры стажировок: поиск, навыки, направление, город и т.д."""
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Internship.title).like(like)
            | func.lower(Internship.company).like(like)
            | func.lower(Internship.description).like(like)
        )
    if skill_ids:
        query = query.join(InternshipSkill, InternshipSkill.internship_id == Internship.id).where(
            InternshipSkill.skill_id.in_(skill_ids)
        )
    if direction and direction != "any":
        query = query.where(func.lower(Internship.direction) == direction.strip().lower())
    if level and level != "any":
        query = query.where(Internship.level == level)
    if city and city != "any":
        # SQLite lower() не работает с кириллицей — сравниваем как есть.
        query = query.where(Internship.city == city.strip())
    if remote is not None:
        query = query.where(Internship.remote.is_(remote))
    if format_ and format_ != "any":
        query = query.where(Internship.format == format_)
    return query


class InternshipRepository:
    """Доступ к данным стажировок и связей «стажировка — навык»."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(
        self,
        *,
        search: str | None = None,
        skill_ids: list[int] | None = None,
        direction: str | None = None,
        level: str | None = None,
        city: str | None = None,
        remote: bool | None = None,
        format_: str | None = None,
    ) -> list[Internship]:
        """Стажировки с фильтрацией и поиском (с загруженными навыками)."""
        query = select(Internship).options(selectinload(Internship.skills))
        query = _apply_filters(
            query,
            search=search,
            skill_ids=skill_ids,
            direction=direction,
            level=level,
            city=city,
            remote=remote,
            format_=format_,
        )
        query = query.distinct().order_by(Internship.company, Internship.title)
        return list(self.db.scalars(query))

    def get(self, internship_id: int) -> Internship:
        internship = self.db.scalar(
            select(Internship)
            .where(Internship.id == internship_id)
            .options(selectinload(Internship.skills))
        )
        if internship is None:
            raise NotFoundError(f"Стажировка с id={internship_id} не найдена")
        return internship

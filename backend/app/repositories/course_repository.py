"""Репозиторий курсов с фильтрацией поиском."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Course, CourseSkill


def _apply_filters(query, *, search=None, skill_ids=None, category=None, level=None,
                   price_max=None, format_=None, platform=None):
    """Общие фильтры для курсов."""
    if search:
        like = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Course.title).like(like)
            | func.lower(Course.description).like(like)
        )
    if skill_ids:
        query = query.join(CourseSkill, CourseSkill.course_id == Course.id).where(
            CourseSkill.skill_id.in_(skill_ids)
        )
    if category and category != "any":
        query = query.where(Course.category == category)
    if level and level != "any":
        query = query.where(Course.level == level)
    if price_max is not None:
        query = query.where(Course.cost <= price_max)
    if format_ and format_ != "any":
        query = query.where(Course.format == format_)
    if platform:
        query = query.where(func.lower(Course.platform) == platform.strip().lower())
    return query


class CourseRepository:
    """Доступ к данным курсов и связей «курс — навык»."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        search: str | None = None,
        skill_ids: list[int] | None = None,
        category: str | None = None,
        level: str | None = None,
        price_max: float | None = None,
        format_: str | None = None,
        platform: str | None = None,
    ) -> list[Course]:
        query = (
            select(Course)
            .options(selectinload(Course.skills))
        )
        query = _apply_filters(
            query,
            search=search,
            skill_ids=skill_ids,
            category=category,
            level=level,
            price_max=price_max,
            format_=format_,
            platform=platform,
        )
        query = query.distinct().order_by(Course.title)
        return list(self.db.scalars(query))

    def get(self, course_id: int) -> Course:
        course = self.db.scalar(
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.skills))
        )
        if course is None:
            raise NotFoundError(f"Курс с id={course_id} не найден")
        return course

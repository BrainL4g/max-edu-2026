"""Схемы курсов."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.skill import SkillOut


class CourseOut(BaseModel):
    """Курс (ответ API)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    platform: str
    url: str | None = None
    level: str
    category: str
    cost: float
    format: str
    skills: list[SkillOut] = []
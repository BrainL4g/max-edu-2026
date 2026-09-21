"""Схемы стажировок."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.skill import SkillOut


class InternshipOut(BaseModel):
    """Стажировка (ответ API)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str
    description: str | None = None
    url: str | None = None
    level: str
    city: str | None = None
    remote: bool
    format: str
    requirements: str | None = None
    direction: str | None = None
    skills: list[SkillOut] = []
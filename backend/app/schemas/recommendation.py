"""Схемы рекомендаций."""

from __future__ import annotations

from pydantic import BaseModel

from backend.app.schemas.course import CourseOut
from backend.app.schemas.internship import InternshipOut


class SkillGap(BaseModel):
    """Пробел в навыках: уровень ниже целевого."""

    skill_id: int
    name: str
    category: str
    current_level: int
    target_level: int = 3


class RecommendationOut(BaseModel):
    """Рекомендации: пробелы + подходящие курсы и стажировки."""

    user_id: int
    gaps: list[SkillGap]
    courses: list[CourseOut]
    internships: list[InternshipOut]
    summary: str

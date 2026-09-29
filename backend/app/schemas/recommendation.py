"""Схемы рекомендаций."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "gaps": [
                        {
                            "skill_id": 8,
                            "name": "Docker",
                            "category": "Инструменты",
                            "current_level": 0,
                            "target_level": 3,
                        }
                    ],
                    "courses": [],
                    "internships": [],
                    "summary": "Рекомендуем закрыть пробелы: Docker.",
                }
            ]
        }
    )

    user_id: int
    gaps: list[SkillGap]
    courses: list[CourseOut]
    internships: list[InternshipOut]
    summary: str

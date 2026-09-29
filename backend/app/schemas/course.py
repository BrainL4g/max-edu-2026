"""Схемы курсов."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.skill import SkillOut


class CourseOut(BaseModel):
    """Курс (ответ API)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Python для бэкенда",
                    "description": "Курс по написанию backend-сервисов.",
                    "platform": "Stepik",
                    "url": "https://stepik.org/course/1",
                    "level": "beginner",
                    "category": "backend",
                    "cost": 0.0,
                    "format": "online",
                    "skills": [
                        {
                            "id": 1,
                            "name": "Python",
                            "category": "Программирование",
                            "description": None,
                        }
                    ],
                }
            ]
        },
    )

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

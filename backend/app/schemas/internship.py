"""Схемы стажировок."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.skill import SkillOut


class InternshipOut(BaseModel):
    """Стажировка (ответ API)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "title": "Стажёр Python",
                    "company": "Яндекс",
                    "description": "Участие в разработке сервисов.",
                    "url": "https://yandex.ru/career",
                    "level": "junior",
                    "city": "Москва",
                    "remote": False,
                    "format": "office",
                    "requirements": "Знание Python и SQL",
                    "direction": "backend",
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

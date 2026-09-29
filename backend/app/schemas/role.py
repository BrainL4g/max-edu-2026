"""Схемы целевых ролей и gap-анализа."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RoleSkillOut(BaseModel):
    """Требование роли к навыку."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str
    category: str | None = None
    required_level: int
    importance: float
    is_mandatory: bool


class RoleOut(BaseModel):
    """Целевая карьерная роль."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "Backend Junior",
                    "direction": "backend",
                    "level": "junior",
                    "description": "Junior-разработчик бэкенда на Python",
                    "requirements": [
                        {
                            "skill_id": 1,
                            "name": "Python",
                            "category": "Программирование",
                            "required_level": 3,
                            "importance": 1.0,
                            "is_mandatory": True,
                        }
                    ],
                }
            ]
        },
    )

    id: int
    name: str
    direction: str
    level: str
    description: str | None = None
    requirements: list[RoleSkillOut] = []


class GoalIn(BaseModel):
    """Выбор целевой роли пользователем."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"target_role_id": 1}]})

    target_role_id: int


class GapItemOut(BaseModel):
    """Одно требование роли и текущее состояние пользователя."""

    skill_id: int
    name: str
    category: str | None = None
    current_level: int
    required_level: int
    gap: int
    importance: float
    is_mandatory: bool


class GapAnalysisOut(BaseModel):
    """Gap-анализ пользователя: соответствие роли и пробелы."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "role": {
                        "id": 1,
                        "name": "Backend Junior",
                        "direction": "backend",
                        "level": "junior",
                        "description": None,
                        "requirements": [],
                    },
                    "match_percent": 67,
                    "items": [
                        {
                            "skill_id": 1,
                            "name": "Python",
                            "category": "Программирование",
                            "current_level": 2,
                            "required_level": 3,
                            "gap": 1,
                            "importance": 1.0,
                            "is_mandatory": True,
                        }
                    ],
                    "summary": "До целевой роли не хватает навыков: Python.",
                }
            ]
        }
    )

    user_id: int
    role: RoleOut | None = None
    match_percent: int | None = None
    items: list[GapItemOut]
    summary: str

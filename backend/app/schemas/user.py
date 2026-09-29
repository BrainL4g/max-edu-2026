"""Схемы пользователя."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.skill import SkillMapItem


class UserBase(BaseModel):
    """Поля профиля пользователя."""

    name: str | None = None
    education: str | None = None
    direction: str | None = None
    goal: str | None = None


class UserCreate(UserBase):
    """Создание пользователя."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Иван Иванов",
                    "education": "МГТУ, 3 курс",
                    "direction": "backend",
                    "goal": "Попасть на стажировку",
                }
            ]
        }
    )


class UserByMaxIn(BaseModel):
    """Связка пользователя MAX с платформой."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"max_user_id": 12345, "name": "Иван из MAX"}]}
    )

    max_user_id: int
    name: str | None = None


class UserUpdate(UserBase):
    """Обновление профиля пользователя."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"name": "Иван Петров", "direction": "frontend"}]}
    )


class UserOut(UserBase):
    """Профиль пользователя (ответ API)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "name": "Иван Иванов",
                    "education": "МГТУ, 3 курс",
                    "direction": "backend",
                    "goal": "Попасть на стажировку",
                    "max_user_id": 12345,
                    "target_role_id": 1,
                    "created_at": "2026-09-29T10:00:00",
                }
            ]
        },
    )

    id: int
    max_user_id: int | None = None
    target_role_id: int | None = None
    created_at: datetime


class UserProgressOut(BaseModel):
    """Прогресс пользователя: XP, миссии, средний уровень, Skill Map."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "total_xp": 85,
                    "completed_missions": 3,
                    "total_missions": 43,
                    "skills_count": 3,
                    "average_level": 1.67,
                    "skill_map": [
                        {
                            "skill_id": 1,
                            "name": "Python",
                            "category": "Программирование",
                            "level": 2,
                            "experience": 45,
                            "progress": 0.75,
                            "next_level_xp": 30,
                        }
                    ],
                }
            ]
        }
    )

    user_id: int
    total_xp: int
    completed_missions: int
    total_missions: int
    skills_count: int
    average_level: float
    skill_map: list[SkillMapItem]

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


class UserByMaxIn(BaseModel):
    """Связка пользователя MAX с платформой."""

    max_user_id: int
    name: str | None = None


class UserUpdate(UserBase):
    """Обновление профиля пользователя."""


class UserOut(UserBase):
    """Профиль пользователя (ответ API)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    max_user_id: int | None = None
    target_role_id: int | None = None
    created_at: datetime


class UserProgressOut(BaseModel):
    """Прогресс пользователя: XP, миссии, средний уровень, Skill Map."""

    user_id: int
    total_xp: int
    completed_missions: int
    total_missions: int
    skills_count: int
    average_level: float
    skill_map: list[SkillMapItem]

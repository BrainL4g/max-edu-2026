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

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    direction: str
    level: str
    description: str | None = None
    requirements: list[RoleSkillOut] = []


class GoalIn(BaseModel):
    """Выбор целевой роли пользователем."""

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

    user_id: int
    role: RoleOut | None = None
    match_percent: int | None = None
    items: list[GapItemOut]
    summary: str

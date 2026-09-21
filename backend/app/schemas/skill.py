"""Схемы навыков и диагностики."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SkillOut(BaseModel):
    """Навык (ответ API)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    description: str | None = None


class SkillMapItem(BaseModel):
    """Элемент Skill Map пользователя."""

    skill_id: int
    name: str
    category: str
    level: int
    experience: int
    progress: float
    next_level_xp: int | None = None


class UserSkillOut(BaseModel):
    """Связь пользователя и навыка (уровень/опыт)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    level: int
    experience: int


class AssessmentAnswerIn(BaseModel):
    """Один ответ диагностики."""

    question_id: int
    option_index: int


class AssessmentIn(BaseModel):
    """Ответы на первичную диагностику."""

    answers: list[AssessmentAnswerIn]


class AssessmentOut(BaseModel):
    """Результат диагностики: начальный Skill Map."""

    user_id: int
    evaluated_skills: list[SkillMapItem]
    summary: str
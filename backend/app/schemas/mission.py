"""Схемы игровых миссий и попыток."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MissionOptionOut(BaseModel):
    """Вариант ответа миссии (без флага правильности)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class MissionOut(BaseModel):
    """Миссия (варианты ответов не раскрывают правильный)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_id: int
    skill_name: str
    difficulty: str
    scenario: str
    explanation: str | None = None
    reward_xp: int
    options: list[MissionOptionOut] = []


class MissionAnswerIn(BaseModel):
    """Отправка ответа на миссию."""

    user_id: int
    option_id: int


class AttemptResultOut(BaseModel):
    """Результат проверки ответа на миссию."""

    attempt_id: int
    mission_id: int
    is_correct: bool
    xp_earned: int
    explanation: str | None = None
    correct_option_id: int | None = None
    skill_id: int | None = None
    skill_name: str | None = None
    skill_level_after: int | None = None


class AttemptHistoryItem(BaseModel):
    """Попытка в истории пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    is_correct: bool
    status: str
    xp_earned: int
    created_at: datetime

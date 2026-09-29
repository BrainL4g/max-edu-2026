"""Схемы игровых миссий и попыток."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

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


class MissionNextOut(BaseModel):
    """Следующая миссия по цели: статус, прогресс и сама миссия.

    ``status``:
    - ``ok`` — миссия доступна (поле ``mission`` заполнено);
    - ``no_goal`` — у пользователя нет целевой роли;
    - ``all_done`` — все миссии роли пройдены.
    """

    status: Literal["ok", "no_goal", "all_done"]
    mission: MissionOut | None = None
    done: int = 0
    total: int = 0


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
    correct_option_text: str | None = None
    skill_id: int | None = None
    skill_name: str | None = None
    skill_level_before: int | None = None
    skill_level_after: int | None = None
    already_solved: bool = False


class AttemptHistoryItem(BaseModel):
    """Попытка в истории пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    is_correct: bool
    status: str
    xp_earned: int
    created_at: datetime

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

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "skill_id": 1,
                    "name": "Python",
                    "category": "Программирование",
                    "level": 2,
                    "experience": 45,
                    "progress": 0.75,
                    "next_level_xp": 30,
                }
            ]
        }
    )

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


class AssessmentQuestionOut(BaseModel):
    """Вопрос диагностики (ответ API, без внутренних оценок уровней)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "skill": "Python",
                    "text": "Как вы работаете с Python? Оцените свой уровень.",
                    "options": [
                        "Почти не писал(а): знаю только print",
                        "Писал(а) простые скрипты: циклы, условия, списки",
                    ],
                }
            ]
        }
    )

    id: int
    skill: str
    text: str
    options: list[str]


class AssessmentIn(BaseModel):
    """Ответы на первичную диагностику."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "answers": [
                        {"question_id": 1, "option_index": 2},
                        {"question_id": 2, "option_index": 1},
                    ]
                }
            ]
        }
    )

    answers: list[AssessmentAnswerIn]


class AssessmentOut(BaseModel):
    """Результат диагностики: начальный Skill Map."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "evaluated_skills": [
                        {
                            "skill_id": 1,
                            "name": "Python",
                            "category": "Программирование",
                            "level": 2,
                            "experience": 0,
                            "progress": 0.0,
                            "next_level_xp": 50,
                        }
                    ],
                    "summary": "Ваш стартовый уровень — базовый.",
                }
            ]
        }
    )

    user_id: int
    evaluated_skills: list[SkillMapItem]
    summary: str

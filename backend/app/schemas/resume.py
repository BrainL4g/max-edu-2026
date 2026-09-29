"""Схемы резюме и анализа."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeCreate(BaseModel):
    """Создание резюме из текста."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"text": "Разработчик Python, 2 года опыта...", "filename": "cv.txt"}]
        }
    )

    text: str
    filename: str | None = None


class ResumeOut(BaseModel):
    """Резюме (ответ API)."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "user_id": 1,
                    "filename": "cv.txt",
                    "text": "Разработчик Python, 2 года опыта...",
                    "uploaded_at": "2026-09-29T10:00:00",
                }
            ]
        },
    )

    id: int
    user_id: int
    filename: str | None = None
    text: str
    uploaded_at: datetime


class ResumeAnalysisOut(BaseModel):
    """Результат анализа резюме.

    Поля ``source``, ``ai_score`` и ``ai_summary`` заполняются, когда включена
    интеграция с GigaChat; без неё отчёт остаётся эвристическим.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "resume_id": 1,
                    "found_skills": ["Python", "SQL"],
                    "missing_skills": ["Docker"],
                    "strengths": ["Опыт разработки на Python"],
                    "issues": ["Не указан опыт с Docker"],
                    "recommendations": ["Добавьте раздел про контейнеризацию"],
                    "direction_match": 0.8,
                    "summary": "Резюме подходит под направление backend на 80%.",
                }
            ]
        }
    )

    resume_id: int
    found_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    issues: list[str]
    recommendations: list[str]
    direction_match: float
    summary: str
    source: str = "heuristic"
    ai_score: float | None = None
    ai_summary: str | None = None

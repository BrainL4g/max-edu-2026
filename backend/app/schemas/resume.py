"""Схемы резюме и анализа."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeCreate(BaseModel):
    """Создание резюме из текста."""

    text: str
    filename: str | None = None


class ResumeOut(BaseModel):
    """Резюме (ответ API)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str | None = None
    text: str
    uploaded_at: datetime


class ResumeAnalysisOut(BaseModel):
    """Результат анализа резюме."""

    resume_id: int
    found_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    issues: list[str]
    recommendations: list[str]
    direction_match: float
    summary: str
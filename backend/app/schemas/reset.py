"""Схемы ответов административного сброса тестовых данных."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ResetOut(BaseModel):
    """Результат сброса учебных данных тест-студентов."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "reset": True,
                    "students_affected": 1,
                    "message": "Учебные данные тест-студентов сброшены",
                }
            ]
        }
    )

    reset: bool
    students_affected: int
    message: str

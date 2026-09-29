"""Схемы согласия на обработку персональных данных (152-ФЗ ст. 9)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConsentPolicyOut(BaseModel):
    """Публичный текст политики обработки персональных данных."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"text": "Политика обработки ...", "version": "1.0"}]}
    )

    text: str
    version: str


class ConsentOut(BaseModel):
    """Состояние согласия пользователя на обработку ПД."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": 1,
                    "consent_given": True,
                    "consent_at": "2026-09-29T10:00:00",
                    "policy_version": "1.0",
                }
            ]
        }
    )

    user_id: int
    consent_given: bool
    consent_at: datetime | None = None
    policy_version: str | None = None

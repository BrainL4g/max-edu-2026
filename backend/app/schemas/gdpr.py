"""Схемы для прав субъекта ПД (152-ФЗ)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DataExportOut(BaseModel):
    """Полный экспорт персональных данных пользователя."""

    user_id: int
    name: str | None = None
    education: str | None = None
    direction: str | None = None
    goal: str | None = None
    max_user_id: int | None = None
    target_role_id: int | None = None
    consent_given: bool = False
    consent_at: datetime | None = None
    consent_policy_version: str | None = None
    created_at: datetime


class DeletionOut(BaseModel):
    """Результат удаления данных."""

    user_id: int
    deleted: bool
    message: str

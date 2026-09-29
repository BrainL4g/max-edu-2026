"""API-токены (Bearer) для ролей student/service/admin."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.domain import Base


class ApiToken(Base):
    """Токен доступа: хранится хэшем, роль и владелец.

    ``role`` — ``student`` (доступ только к своим данным), ``service``
    (бот; задаётся переменной окружения) или ``admin`` (чтение и сброс
    тестовых данных). ``is_test`` отмечает токены тестовых учёток,
    созданные скриптом подготовке к приёмке API.
    """

    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(16))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

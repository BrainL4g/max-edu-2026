"""Зависимости аутентификации и авторизации.

Роли:
- ``student`` — доступ только к своим ресурсам (владелец токена);
- ``service`` — бот MAX; может обращаться к любым пользователям
  (токен задаётся переменной окружения ``SERVICE_API_TOKEN``);
- ``admin`` — чтение пользователей и сброс тестовых данных.

Схема: Bearer-токен. Токены ролей student/admin хранятся в таблице
``api_tokens`` хэшем (SHA-256); service-токен сравнивается с настройкой
напрямую (constant-time).
"""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.security import hash_token
from backend.app.database.session import get_db
from backend.app.domain import ApiToken
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.resume_repository import ResumeRepository

_bearer = HTTPBearer(auto_error=False)


class Principal(BaseModel):
    """Аутентифицированный субъект запроса."""

    role: str
    user_id: int | None = None


def get_optional_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer)] = None,
    db: Session = Depends(get_db),
) -> Principal | None:
    """Principal по токену или None (для опциональной аутентификации)."""
    if credentials is None or not credentials.credentials:
        return None
    token = credentials.credentials
    record = db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(token)))
    if record is not None:
        return Principal(role=record.role, user_id=record.user_id)
    if settings.service_api_token and hmac.compare_digest(token, settings.service_api_token):
        return Principal(role="service")
    return None


def get_current_principal(
    principal: Annotated[Principal | None, Depends(get_optional_principal)],
) -> Principal:
    """Требует валидный Bearer-токен, иначе 401."""
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется валидный Bearer-токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_access(
    user_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    """Студент может работать только со своими ресурсами, иначе 403."""
    if principal.role == "student" and principal.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к ресурсу другого пользователя",
        )
    return principal


def require_attempt_owner(
    attempt_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> Principal:
    """Проверка владения попыткой (``attempt.user_id``)."""
    attempt = MissionRepository(db).get_attempt(attempt_id)
    return _require_owner(principal, attempt.user_id)


def require_resume_owner(
    resume_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
) -> Principal:
    """Проверка владения резюме (``resume.user_id``)."""
    resume = ResumeRepository(db).get(resume_id)
    return _require_owner(principal, resume.user_id)


def _require_owner(principal: Principal, owner_id: int) -> Principal:
    if principal.role == "student" and principal.user_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к ресурсу другого пользователя",
        )
    return principal


def require_service(principal: Annotated[Principal, Depends(get_current_principal)]) -> Principal:
    """Доступно только сервисной роли (боту), иначе 403."""
    if principal.role != "service":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только сервисному аккаунту",
        )
    return principal

"""Административные эндпоинты (только роль admin)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_admin
from backend.app.api.responses import FORBIDDEN, UNAUTHORIZED
from backend.app.database.session import get_db
from backend.app.schemas.reset import ResetOut
from backend.app.services.test_accounts import TestAccountsService

router = APIRouter(tags=["admin"])


@router.post(
    "/admin/test-users/reset",
    response_model=ResetOut,
    responses={**UNAUTHORIZED, **FORBIDDEN},
)
def reset_test_users(
    principal: Principal = Depends(require_admin),
    db: Session = Depends(get_db),
) -> ResetOut:
    """Сбросить учебные данные тест-студентов (id и токены сохраняются).

    Очищает попытки, Skill Map, резюме и анализ резюме, снимает целевую
    роль и возвращает профиль к состоянию по умолчанию — чтобы прогоны
    DATA-API были воспроизводимыми. Требует роль ``admin``.
    """
    affected = TestAccountsService(db).reset_test_data()
    return ResetOut(
        reset=True,
        students_affected=affected,
        message="Учебные данные тест-студентов сброшены",
    )

"""Эндпоинты миссий: следующее задание, ответ, результат."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.api.deps import (
    Principal,
    get_current_principal,
    require_access,
    require_attempt_owner,
)
from backend.app.api.responses import AUTH_ERRORS, MISSING_ERRORS, OWN_ERRORS
from backend.app.core.audit import log_access
from backend.app.database.session import get_db
from backend.app.domain import Attempt, Mission
from backend.app.schemas.mission import (
    AttemptHistoryItem,
    AttemptResultOut,
    MissionAnswerIn,
    MissionNextOut,
    MissionOut,
)
from backend.app.services.missions import MissionService

router = APIRouter(tags=["missions"])


@router.get("/missions", response_model=list[MissionOut], responses=AUTH_ERRORS)
def list_missions(
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> list[Mission]:
    """Список всех миссий."""
    return MissionService(db).missions.list_all()


@router.get("/missions/next", response_model=MissionNextOut, responses=OWN_ERRORS)
def next_mission(
    user_id: int = Query(..., description="id пользователя"),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> dict[str, Any]:
    """Следующее задание строго по целевой роли: статус, прогресс, миссия."""
    log_access(
        action="read",
        resource="mission",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )
    return MissionService(db).get_next_mission(user_id)


@router.get("/missions/{mission_id}", response_model=MissionOut, responses=MISSING_ERRORS)
def get_mission(
    mission_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> Mission:
    """Задание по id (варианты ответов не раскрывают правильный)."""
    return MissionService(db).get_mission(mission_id)


@router.post("/missions/{mission_id}/answer", response_model=AttemptResultOut, responses=OWN_ERRORS)
def submit_answer(
    mission_id: int,
    payload: MissionAnswerIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> dict[str, Any]:
    """Отправка ответа: проверка, начисление XP, результат."""
    log_access(
        action="create",
        resource="attempt",
        resource_id=mission_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
        details={"user_id": payload.user_id},
    )
    if principal.role == "student" and principal.user_id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к ресурсу другого пользователя",
        )
    return MissionService(db).submit_answer(
        user_id=payload.user_id, mission_id=mission_id, option_id=payload.option_id
    )


@router.get("/attempts/{attempt_id}", response_model=AttemptResultOut, responses=OWN_ERRORS)
def get_attempt_result(
    attempt_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_attempt_owner),
) -> dict[str, Any]:
    """Результат по конкретной попытке."""
    return MissionService(db).get_result(attempt_id)


@router.get(
    "/users/{user_id}/attempts", response_model=list[AttemptHistoryItem], responses=OWN_ERRORS
)
def user_attempts(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> list[Attempt]:
    """История попыток пользователя."""
    return MissionService(db).get_history(user_id)

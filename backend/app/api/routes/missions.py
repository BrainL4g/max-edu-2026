"""Эндпоинты миссий: следующее задание, ответ, результат."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.mission import (
    AttemptHistoryItem,
    AttemptResultOut,
    MissionAnswerIn,
    MissionOut,
)
from backend.app.services.missions import MissionService

router = APIRouter(tags=["missions"])


@router.get("/missions", response_model=list[MissionOut])
def list_missions(db: Session = Depends(get_db)) -> list[MissionOut]:
    """Список всех миссий."""
    return MissionService(db).missions.list()


@router.get("/missions/next", response_model=MissionOut | None)
def next_mission(
    user_id: int = Query(..., description="id пользователя"),
    db: Session = Depends(get_db),
) -> MissionOut | None:
    """Следующее задание: приоритет — слабые навыки пользователя."""
    mission = MissionService(db).get_next_mission(user_id)
    return mission


@router.get("/missions/{mission_id}", response_model=MissionOut)
def get_mission(mission_id: int, db: Session = Depends(get_db)) -> MissionOut:
    """Задание по id (варианты ответов не раскрывают правильный)."""
    return MissionService(db).get_mission(mission_id)


@router.post("/missions/{mission_id}/answer", response_model=AttemptResultOut)
def submit_answer(
    mission_id: int, payload: MissionAnswerIn, db: Session = Depends(get_db)
) -> AttemptResultOut:
    """Отправка ответа: проверка, начисление XP, результат."""
    result = MissionService(db).submit_answer(
        user_id=payload.user_id, mission_id=mission_id, option_id=payload.option_id
    )
    return AttemptResultOut(**result)


@router.get("/attempts/{attempt_id}", response_model=AttemptResultOut)
def get_attempt_result(
    attempt_id: int, db: Session = Depends(get_db)
) -> AttemptResultOut:
    """Результат по конкретной попытке."""
    result = MissionService(db).get_result(attempt_id)
    return AttemptResultOut(**result)


@router.get("/users/{user_id}/attempts", response_model=list[AttemptHistoryItem])
def user_attempts(
    user_id: int, db: Session = Depends(get_db)
) -> list[AttemptHistoryItem]:
    """История попыток пользователя."""
    return MissionService(db).get_history(user_id)

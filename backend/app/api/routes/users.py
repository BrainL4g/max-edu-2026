"""Эндпоинты пользователей: профиль, диагностика, прогресс."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.domain import Mission, User
from backend.app.repositories.role_repository import RoleRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.role import GapAnalysisOut, GoalIn
from backend.app.schemas.skill import AssessmentIn, AssessmentOut
from backend.app.schemas.user import UserByMaxIn, UserCreate, UserOut, UserProgressOut, UserUpdate
from backend.app.services.assessment import AssessmentService
from backend.app.services.gap_analysis import GapAnalysisService
from backend.app.services.skills import SkillService

router = APIRouter(tags=["users"])


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    """Создание пользователя (студента)."""
    return UserRepository(db).create(
        name=payload.name,
        education=payload.education,
        direction=payload.direction,
        goal=payload.goal,
    )


@router.post("/users/by-max", response_model=UserOut)
def get_or_create_by_max(payload: UserByMaxIn, db: Session = Depends(get_db)) -> User:
    """Связка пользователя MAX: get-or-create по max_user_id."""
    return UserRepository(db).get_or_create_by_max(payload.max_user_id, name=payload.name)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)) -> User:
    """Профиль пользователя."""
    return UserRepository(db).get(user_id)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    """Обновление профиля пользователя."""
    repo = UserRepository(db)
    user = repo.get(user_id)
    return repo.update(
        user,
        name=payload.name,
        education=payload.education,
        direction=payload.direction,
        goal=payload.goal,
    )


@router.put("/users/{user_id}/goal", response_model=UserOut)
def set_goal(user_id: int, payload: GoalIn, db: Session = Depends(get_db)) -> User:
    """Выбор целевой роли пользователя."""
    repo = UserRepository(db)
    role = RoleRepository(db).get(payload.target_role_id)  # 404, если роли нет
    user = repo.get(user_id)
    user.target_role_id = role.id
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}/gap-analysis", response_model=GapAnalysisOut)
def gap_analysis(user_id: int, db: Session = Depends(get_db)) -> GapAnalysisOut:
    """Что не хватает до целевой роли и процент соответствия."""
    return GapAnalysisOut(**GapAnalysisService(db).analyze(user_id))


@router.post("/users/{user_id}/assessment", response_model=AssessmentOut)
def run_assessment(
    user_id: int, payload: AssessmentIn, db: Session = Depends(get_db)
) -> AssessmentOut:
    """Первичная диагностика: ответы → начальный Skill Map."""
    user = UserRepository(db).get(user_id)
    result = AssessmentService(db).run(user, [a.model_dump() for a in payload.answers])
    return AssessmentOut(**result)


@router.get("/users/{user_id}/progress", response_model=UserProgressOut)
def get_progress(user_id: int, db: Session = Depends(get_db)) -> UserProgressOut:
    """Прогресс пользователя: XP, миссии, средний уровень, Skill Map."""
    repo = UserRepository(db)
    repo.get(user_id)
    progress = repo.get_progress(user_id)
    total_missions = db.scalar(select(func.count(Mission.id))) or 0
    skill_map = SkillService(db).get_skill_map(user_id)
    return UserProgressOut(
        user_id=user_id, total_missions=total_missions, skill_map=skill_map, **progress
    )

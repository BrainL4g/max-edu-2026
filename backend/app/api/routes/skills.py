"""Эндпоинты навыков: список, Skill Map, прогресс навыков."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_access
from backend.app.api.responses import OWN_ERRORS
from backend.app.core.audit import log_access
from backend.app.database.session import get_db
from backend.app.domain import Skill
from backend.app.repositories.skill_repository import SkillRepository
from backend.app.schemas.skill import SkillMapItem, SkillOut
from backend.app.services.skills import SkillService

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillOut], openapi_extra={"security": []})
def list_skills(db: Session = Depends(get_db)) -> list[Skill]:
    """Список всех навыков."""
    return SkillRepository(db).list_all()


@router.get("/skills/{skill_id}", response_model=SkillOut, openapi_extra={"security": []})
def get_skill(skill_id: int, db: Session = Depends(get_db)) -> Skill:
    """Навык по id."""
    return SkillRepository(db).get(skill_id)


@router.get("/users/{user_id}/skills", response_model=list[SkillMapItem], responses=OWN_ERRORS)
def user_skill_map(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> list[dict[str, Any]]:
    """Skill Map пользователя: уровень и прогресс по каждому навыку."""
    log_access(
        action="read",
        resource="skill_map",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )
    return SkillService(db).get_skill_map(user_id)

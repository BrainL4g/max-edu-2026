"""Эндпоинты навыков: список, Skill Map, прогресс навыков."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.repositories.skill_repository import SkillRepository
from app.schemas.skill import SkillMapItem, SkillOut
from app.services.skills import SkillService

router = APIRouter(tags=["skills"])


@router.get("/skills", response_model=list[SkillOut])
def list_skills(db: Session = Depends(get_db)) -> list[SkillOut]:
    """Список всех навыков."""
    return SkillRepository(db).list()


@router.get("/skills/{skill_id}", response_model=SkillOut)
def get_skill(skill_id: int, db: Session = Depends(get_db)) -> SkillOut:
    """Навык по id."""
    return SkillRepository(db).get(skill_id)


@router.get("/users/{user_id}/skills", response_model=list[SkillMapItem])
def user_skill_map(
    user_id: int, db: Session = Depends(get_db)
) -> list[SkillMapItem]:
    """Skill Map пользователя: уровень и прогресс по каждому навыку."""
    return SkillService(db).get_skill_map(user_id)
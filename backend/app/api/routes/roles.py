"""Эндпоинты целевых ролей."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.repositories.role_repository import RoleRepository
from backend.app.schemas.role import RoleOut, RoleSkillOut

router = APIRouter(tags=["roles"])


def _to_out(role: Any) -> RoleOut:
    """ORM-роль → схема: требования подтягивают имя навыка."""

    def _skill_out(item: Any) -> RoleSkillOut:
        return RoleSkillOut(
            skill_id=item.skill.id,
            name=item.skill.name,
            category=item.skill.category,
            required_level=item.required_level,
            importance=item.importance,
            is_mandatory=item.is_mandatory,
        )

    return RoleOut(
        id=role.id,
        name=role.name,
        direction=role.direction,
        level=role.level,
        description=role.description,
        requirements=[_skill_out(item) for item in role.requirements],
    )


@router.get("/roles", response_model=list[RoleOut], openapi_extra={"security": []})
def list_roles(db: Session = Depends(get_db)) -> list[RoleOut]:
    """Все целевые роли (с требованиями к навыкам)."""
    return [_to_out(role) for role in RoleRepository(db).list_all()]

"""Репозиторий целевых ролей."""

from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Role, RoleSkill


def _with_requirements(query: Select[tuple[Role]]) -> Select[tuple[Role]]:
    """Жадная загрузка требований роли и их навыков (без N+1 при сериализации)."""
    return query.options(
        selectinload(Role.requirements).selectinload(RoleSkill.skill),
    )


class RoleRepository:
    """Доступ к данным целевых ролей."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Role]:
        """Все роли с требованиями, упорядоченные по названию."""
        return list(self.db.scalars(_with_requirements(select(Role).order_by(Role.name))))

    def get(self, role_id: int) -> Role:
        """Роль по id с требованиями (404, если не найдена)."""
        role = self.db.scalar(_with_requirements(select(Role).where(Role.id == role_id)))
        if role is None:
            raise NotFoundError(f"Роль с id={role_id} не найдена")
        return role

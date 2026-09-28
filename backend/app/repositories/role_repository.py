"""Репозиторий целевых ролей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Role


class RoleRepository:
    """Доступ к данным целевых ролей."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all(self) -> list[Role]:
        """Все роли, упорядоченные по названию."""
        return list(self.db.scalars(select(Role).order_by(Role.name)))

    def get(self, role_id: int) -> Role:
        """Роль по id (404, если не найдена)."""
        role = self.db.get(Role, role_id)
        if role is None:
            raise NotFoundError(f"Роль с id={role_id} не найдена")
        return role

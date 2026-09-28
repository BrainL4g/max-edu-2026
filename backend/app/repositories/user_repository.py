"""Репозиторий пользователей."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Attempt, User, UserSkill


class UserRepository:
    """Доступ к данным пользователей."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User:
        user = self.db.get(User, user_id)
        if user is None:
            raise NotFoundError(f"Пользователь с id={user_id} не найден")
        return user

    def list(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.id)))

    def create(
        self,
        name: str | None = None,
        education: str | None = None,
        direction: str | None = None,
        goal: str | None = None,
    ) -> User:
        user = User(name=name, education=education, direction=direction, goal=goal)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User, **data: str | None) -> User:
        for field, value in data.items():
            if value is not None:
                setattr(user, field, value)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_progress(self, user_id: int) -> dict:
        """Агрегированный прогресс пользователя (XP, миссии, уровень)."""
        total_xp = self.db.scalar(
            select(func.coalesce(func.sum(Attempt.xp_earned), 0)).where(
                Attempt.user_id == user_id
            )
        )
        completed = self.db.scalar(
            select(func.count(Attempt.id)).where(
                Attempt.user_id == user_id, Attempt.is_correct.is_(True)
            )
        )
        skills = list(
            self.db.scalars(select(UserSkill).where(UserSkill.user_id == user_id))
        )
        average_level = round(sum(s.level for s in skills) / len(skills), 2) if skills else 0.0
        return {
            "total_xp": int(total_xp or 0),
            "completed_missions": int(completed or 0),
            "skills_count": len(skills),
            "average_level": average_level,
        }

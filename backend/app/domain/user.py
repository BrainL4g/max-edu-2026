"""Пользователь SkillQuest."""

from __future__ import annotations

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import Base


class User(Base):
    """Пользователь платформы (студент)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120))
    education: Mapped[str | None] = mapped_column(String(200))
    direction: Mapped[str | None] = mapped_column(String(100), index=True)
    goal: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user_skills: Mapped[list[UserSkill]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    attempts: Mapped[list[Attempt]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
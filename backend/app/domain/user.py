"""Пользователь SkillQuest."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base

if TYPE_CHECKING:
    from backend.app.domain.mission import Attempt
    from backend.app.domain.resume import Resume
    from backend.app.domain.skill import UserSkill


class User(Base):
    """Пользователь платформы (студент)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
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

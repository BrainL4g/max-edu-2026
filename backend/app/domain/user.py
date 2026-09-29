"""Пользователь SkillQuest."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base
from backend.app.domain.types import EncryptedString

if TYPE_CHECKING:
    from backend.app.domain.mission import Attempt
    from backend.app.domain.resume import Resume
    from backend.app.domain.role import Role
    from backend.app.domain.skill import UserSkill


class User(Base):
    """Пользователь платформы (студент)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(EncryptedString(120))
    education: Mapped[str | None] = mapped_column(EncryptedString(200))
    direction: Mapped[str | None] = mapped_column(EncryptedString(100), index=True)
    goal: Mapped[str | None] = mapped_column(EncryptedString(300))
    target_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    consent_given: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    consent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_policy_version: Mapped[str | None] = mapped_column(String(10), nullable=True)

    target_role: Mapped[Role | None] = relationship(back_populates="users")
    user_skills: Mapped[list[UserSkill]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    attempts: Mapped[list[Attempt]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[Resume]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

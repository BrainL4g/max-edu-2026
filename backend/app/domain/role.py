"""Целевые роли и их требования к навыкам (для gap-анализа)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base

if TYPE_CHECKING:
    from backend.app.domain.skill import Skill
    from backend.app.domain.user import User


class Role(Base):
    """Целевая карьерная позиция (например, Backend Junior)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(50), index=True)
    level: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    requirements: Mapped[list[RoleSkill]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )
    users: Mapped[list[User]] = relationship(back_populates="target_role")


class RoleSkill(Base):
    """Требование роли к конкретному навыку."""

    __tablename__ = "role_skills"
    __table_args__ = (UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    required_level: Mapped[int] = mapped_column(Integer, default=3)
    importance: Mapped[float] = mapped_column(Float, default=1.0)
    is_mandatory: Mapped[bool] = mapped_column(default=True)

    role: Mapped[Role] = relationship(back_populates="requirements")
    skill: Mapped[Skill] = relationship()

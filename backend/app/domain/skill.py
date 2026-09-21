"""Навыки и связь «пользователь — навык» (Skill Map)."""

from __future__ import annotations

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import Base


class Skill(Base):
    """Навык (появляется в Skill Map и в рекомендациях)."""

    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)

    user_skills: Mapped[list[UserSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    missions: Mapped[list[Mission]] = relationship(
        back_populates="skill", cascade="all, delete-orphan"
    )
    courses: Mapped[list[Course]] = relationship(
        secondary="course_skills", back_populates="skills"
    )
    internships: Mapped[list[Internship]] = relationship(
        secondary="internship_skills", back_populates="skills"
    )


class UserSkill(Base):
    """Уровень пользователя в конкретном навыке."""

    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )
    level: Mapped[int] = mapped_column(default=0)
    experience: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="user_skills")
    skill: Mapped[Skill] = relationship(back_populates="user_skills")
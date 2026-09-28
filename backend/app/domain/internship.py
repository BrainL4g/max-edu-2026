"""Стажировки и связь «стажировка — навык»."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base

if TYPE_CHECKING:
    from backend.app.domain.skill import Skill


class Internship(Base):
    """Стажировка / практика."""

    __tablename__ = "internships"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    company: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(300))
    level: Mapped[str] = mapped_column(String(30), index=True)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    remote: Mapped[bool] = mapped_column(Boolean, default=False)
    format: Mapped[str] = mapped_column(String(30), default="office")
    requirements: Mapped[str | None] = mapped_column(Text)
    direction: Mapped[str | None] = mapped_column(String(100), index=True)

    skills: Mapped[list[Skill]] = relationship(
        secondary="internship_skills", back_populates="internships"
    )


class InternshipSkill(Base):
    """Связь стажировки с требуемыми навыками."""

    __tablename__ = "internship_skills"
    __table_args__ = (UniqueConstraint("internship_id", "skill_id", name="uq_internship_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    internship_id: Mapped[int] = mapped_column(
        ForeignKey("internships.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)

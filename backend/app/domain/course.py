"""Курсы и связь «курс — навык»."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base


class Course(Base):
    """Образовательный курс."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    platform: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str | None] = mapped_column(String(300))
    level: Mapped[str] = mapped_column(String(30), index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    format: Mapped[str] = mapped_column(String(30), default="online")

    skills: Mapped[list[Skill]] = relationship(
        secondary="course_skills", back_populates="courses"
    )


class CourseSkill(Base):
    """Связь курса с развиваемыми навыками."""

    __tablename__ = "course_skills"
    __table_args__ = (UniqueConstraint("course_id", "skill_id", name="uq_course_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), index=True
    )

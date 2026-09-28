"""Игровые миссии, варианты ответов и попытки."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base

if TYPE_CHECKING:
    from backend.app.domain.skill import Skill
    from backend.app.domain.user import User


class Mission(Base):
    """Игровое задание на проверку и прокачку навыка."""

    __tablename__ = "missions"

    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="easy")
    scenario: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str | None] = mapped_column(Text)
    reward_xp: Mapped[int] = mapped_column(Integer, default=20)

    skill: Mapped[Skill] = relationship(back_populates="missions")
    options: Mapped[list[MissionOption]] = relationship(
        back_populates="mission",
        cascade="all, delete-orphan",
        order_by="MissionOption.id",
    )
    attempts: Mapped[list[Attempt]] = relationship(back_populates="mission")

    @property
    def skill_name(self) -> str | None:
        """Имя навыка миссии (удобно для API-сериализации)."""
        return self.skill.name if self.skill else None


class MissionOption(Base):
    """Вариант ответа миссии."""

    __tablename__ = "mission_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    mission: Mapped[Mission] = relationship(back_populates="options")


class Attempt(Base):
    """Попытка пользователя решить миссию."""

    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    mission_id: Mapped[int] = mapped_column(
        ForeignKey("missions.id", ondelete="CASCADE"), index=True
    )
    answer_option_id: Mapped[int | None] = mapped_column(
        ForeignKey("mission_options.id", ondelete="SET NULL")
    )
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="attempts")
    mission: Mapped[Mission] = relationship(back_populates="attempts")

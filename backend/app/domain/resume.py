"""Резюме пользователя и результаты его анализа."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.domain import Base


class Resume(Base):
    """Резюме пользователя (текст или загруженный файл)."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="resumes")
    analysis: Mapped[ResumeAnalysis | None] = relationship(
        back_populates="resume", uselist=False
    )


class ResumeAnalysis(Base):
    """Результат анализа резюме (хранится как JSON)."""

    __tablename__ = "resume_analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), index=True, unique=True
    )
    result: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    resume: Mapped[Resume] = relationship(back_populates="analysis")

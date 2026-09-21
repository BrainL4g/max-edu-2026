"""Репозиторий резюме и результатов анализа."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain import Resume, ResumeAnalysis


class ResumeRepository:
    """Доступ к данным резюме и результатов анализа."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_id: int, text: str, filename: str | None = None) -> Resume:
        resume = Resume(user_id=user_id, text=text, filename=filename)
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)
        return resume

    def get(self, resume_id: int) -> Resume:
        resume = self.db.get(Resume, resume_id)
        if resume is None:
            raise NotFoundError(f"Резюме с id={resume_id} не найдено")
        return resume

    def list_by_user(self, user_id: int) -> list[Resume]:
        return list(
            self.db.scalars(
                select(Resume)
                .where(Resume.user_id == user_id)
                .order_by(Resume.uploaded_at.desc())
            )
        )

    def save_analysis(self, resume_id: int, result: dict) -> ResumeAnalysis:
        """Сохранить (или обновить) результат анализа резюме."""
        analysis = self.get_analysis(resume_id)
        if analysis is None:
            analysis = ResumeAnalysis(resume_id=resume_id, result=result)
            self.db.add(analysis)
        else:
            analysis.result = result
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def get_analysis(self, resume_id: int) -> ResumeAnalysis | None:
        return self.db.scalar(
            select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
        )
"""Эндпоинты диагностики: банк вопросов."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.skill import AssessmentQuestionOut
from backend.app.services.assessment import questions_for_direction

router = APIRouter(tags=["assessment"])


@router.get("/assessment/questions", response_model=list[AssessmentQuestionOut])
def get_assessment_questions(
    user_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[AssessmentQuestionOut]:
    """Банк вопросов диагностики: текст и варианты ответов.

    Если передан ``user_id``, вопросы фильтруются по направлению пользователя
    (``user.direction`` или направлению целевой роли), чтобы, например,
    выбравшему backend не показывались вопросы по фронтенду.
    """
    direction: str | None = None
    if user_id is not None:
        user = UserRepository(db).get(user_id)
        target_role = user.target_role
        direction = user.direction or (target_role.direction if target_role else None)

    return [
        AssessmentQuestionOut(
            id=question.id,
            skill=question.skill,
            text=question.text,
            options=[text for text, _ in question.options],
        )
        for question in questions_for_direction(direction)
    ]

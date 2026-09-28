"""Эндпоинты диагностики: банк вопросов."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.skill import AssessmentQuestionOut
from backend.app.services.assessment import ASSESSMENT_QUESTIONS

router = APIRouter(tags=["assessment"])


@router.get("/assessment/questions", response_model=list[AssessmentQuestionOut])
def get_assessment_questions() -> list[AssessmentQuestionOut]:
    """Банк вопросов диагностики: текст и варианты ответов."""
    return [
        AssessmentQuestionOut(
            id=question.id,
            skill=question.skill,
            text=question.text,
            options=[text for text, _ in question.options],
        )
        for question in ASSESSMENT_QUESTIONS
    ]

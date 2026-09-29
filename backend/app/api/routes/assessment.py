"""Эндпоинты диагностики: банк вопросов."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, get_optional_principal
from backend.app.api.responses import FORBIDDEN, NOT_FOUND, UNAUTHORIZED
from backend.app.core.audit import log_access
from backend.app.database.session import get_db
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.skill import AssessmentQuestionOut
from backend.app.services.assessment import questions_for_direction

router = APIRouter(tags=["assessment"])


@router.get(
    "/assessment/questions",
    response_model=list[AssessmentQuestionOut],
    openapi_extra={"security": []},
    responses={**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND},
)
def get_assessment_questions(
    user_id: int | None = None,
    db: Session = Depends(get_db),
    principal: Principal | None = Depends(get_optional_principal),
) -> list[AssessmentQuestionOut]:
    """Банк вопросов диагностики: текст и варианты ответов.

    Публичный без ``user_id``. С ``user_id`` требуется Bearer-токен
    владельца (иначе 401/403), вопросы фильтруются по направлению целевой
    роли пользователя (``target_role.direction``, иначе ``user.direction``).
    """
    direction: str | None = None
    if user_id is not None:
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Требуется валидный Bearer-токен",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if principal.role == "student" and principal.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к ресурсу другого пользователя",
            )
        user = UserRepository(db).get(user_id)
        log_access(
            action="read",
            resource="assessment_questions",
            resource_id=user_id,
            principal_role=principal.role,
            principal_user_id=principal.user_id,
        )
        target_role = user.target_role
        direction = (target_role.direction if target_role else None) or user.direction

    return [
        AssessmentQuestionOut(
            id=question.id,
            skill=question.skill,
            text=question.text,
            options=[text for text, _ in question.options],
        )
        for question in questions_for_direction(direction)
    ]

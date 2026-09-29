"""Права субъекта персональных данных (152-ФЗ ст. 14, ст. 3 п. 5).

- ``GET /users/{user_id}/data-export`` — копия всех данных (ст. 14);
- ``DELETE /users/{user_id}/data`` — удаление всех данных (право на забвение,
  ст. 3 п. 5), включая резюме, навыки, попытки и токены доступа.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_access
from backend.app.api.responses import OWN_ERRORS
from backend.app.core.audit import log_access
from backend.app.database.session import get_db
from backend.app.domain import ApiToken, Attempt, Resume, ResumeAnalysis, User, UserSkill
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.gdpr import DataExportOut, DeletionOut

router = APIRouter(tags=["privacy"])


@router.get("/users/{user_id}/data-export", response_model=DataExportOut, responses=OWN_ERRORS)
def export_data(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> DataExportOut:
    """Экспорт персональных данных пользователя (152-ФЗ ст. 14)."""
    user = UserRepository(db).get(user_id)
    log_access(
        action="export",
        resource="user_data",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )
    return DataExportOut(
        user_id=user.id,
        name=user.name,
        education=user.education,
        direction=user.direction,
        goal=user.goal,
        max_user_id=user.max_user_id,
        target_role_id=user.target_role_id,
        consent_given=bool(user.consent_given),
        consent_at=user.consent_at,
        consent_policy_version=user.consent_policy_version,
        created_at=user.created_at,
    )


@router.delete("/users/{user_id}/data", response_model=DeletionOut, responses=OWN_ERRORS)
def delete_data(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> DeletionOut:
    """Удалить все персональные данные пользователя (152-ФЗ ст. 3 п. 5).

    Профиль, навыки, попытки, резюме с анализом и токены доступа удаляются
    одной транзакцией. Запись в журнал аудита остаётся, но без связки с
    удалённым субъектом.
    """
    UserRepository(db).get(user_id)
    log_access(
        action="delete",
        resource="user_data",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )

    resume_ids = list(db.scalars(select(Resume.id).where(Resume.user_id == user_id)))
    if resume_ids:
        db.execute(delete(ResumeAnalysis).where(ResumeAnalysis.resume_id.in_(resume_ids)))
        db.execute(delete(Resume).where(Resume.id.in_(resume_ids)))
    db.execute(delete(Attempt).where(Attempt.user_id == user_id))
    db.execute(delete(UserSkill).where(UserSkill.user_id == user_id))
    db.execute(delete(ApiToken).where(ApiToken.user_id == user_id))
    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    return DeletionOut(
        user_id=user_id,
        deleted=True,
        message="Персональные данные пользователя удалены",
    )

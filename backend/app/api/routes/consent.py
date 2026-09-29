"""Эндпоинты согласия на обработку персональных данных (152-ФЗ ст. 9)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import Principal, require_access
from backend.app.api.responses import OWN_ERRORS
from backend.app.core.audit import log_access
from backend.app.core.consent import (
    POLICY_TEXT,
    POLICY_VERSION,
    ai_assessment_enabled,
    consent_timestamp,
)
from backend.app.database.session import get_db
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.consent import ConsentOut, ConsentPolicyOut

router = APIRouter(tags=["privacy"])


@router.get("/consent/policy", response_model=ConsentPolicyOut, openapi_extra={"security": []})
def get_policy() -> ConsentPolicyOut:
    """Текст политики обработки персональных данных (публичный доступ)."""
    return ConsentPolicyOut(
        text=POLICY_TEXT,
        version=POLICY_VERSION,
        ai_assessment_enabled=ai_assessment_enabled(),
    )


@router.get("/users/{user_id}/consent", response_model=ConsentOut, responses=OWN_ERRORS)
def get_consent(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> ConsentOut:
    """Текущее состояние согласия пользователя на обработку ПД."""
    user = UserRepository(db).get(user_id)
    log_access(
        action="read",
        resource="consent",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
    )
    return ConsentOut(
        user_id=user_id,
        consent_given=bool(user.consent_given),
        consent_at=user.consent_at,
        policy_version=user.consent_policy_version,
    )


@router.post("/users/{user_id}/consent", response_model=ConsentOut, responses=OWN_ERRORS)
def give_consent(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> ConsentOut:
    """Зафиксировать согласие на обработку ПД (152-ФЗ ст. 9)."""
    user = UserRepository(db).get(user_id)
    user.consent_given = True
    user.consent_at = consent_timestamp()
    user.consent_policy_version = POLICY_VERSION
    db.commit()
    db.refresh(user)
    log_access(
        action="give_consent",
        resource="consent",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
        details={"policy_version": POLICY_VERSION},
    )
    return ConsentOut(
        user_id=user_id,
        consent_given=True,
        consent_at=user.consent_at,
        policy_version=POLICY_VERSION,
    )


@router.delete("/users/{user_id}/consent", response_model=ConsentOut, responses=OWN_ERRORS)
def withdraw_consent(
    user_id: int,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_access),
) -> ConsentOut:
    """Отозвать согласие на обработку ПД (152-ФЗ ст. 9, п. 6)."""
    user = UserRepository(db).get(user_id)
    user.consent_given = False
    user.consent_at = None
    user.consent_policy_version = None
    db.commit()
    db.refresh(user)
    log_access(
        action="revoke_consent",
        resource="consent",
        resource_id=user_id,
        principal_role=principal.role,
        principal_user_id=principal.user_id,
        details={"policy_version": POLICY_VERSION},
    )
    return ConsentOut(
        user_id=user_id,
        consent_given=False,
        consent_at=None,
        policy_version=None,
    )

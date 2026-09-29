"""Тесты тестовых учёток: сервис, скрипт-сценарии и admin-сброс.

„Честный“ клиент без подмены аутентификации (см. ``auth_client`` в conftest);
уровни доступа: без токена 401, не-админ 403, admin 200.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.app.core.config import settings
from backend.app.core.exceptions import ConflictError
from backend.app.core.security import hash_token
from backend.app.database.session import get_db
from backend.app.domain import (
    ApiToken,
    Attempt,
    Resume,
    ResumeAnalysis,
    Role,
    Skill,
    User,
    UserSkill,
)
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.resume_repository import ResumeRepository
from backend.app.seed import seed_database
from backend.app.services.skills import SkillService
from backend.app.services.test_accounts import (
    ADMIN_NAME,
    STUDENT_DIRECTION,
    STUDENT_GOAL,
    STUDENT_NAME,
)
from backend.app.services.test_accounts import TestAccountsService as AccountsService


@pytest.fixture()
def auth_client(db_session) -> None:
    """TestClient с реальной аутентификацией (без подмены principal)."""
    from backend.app.main import app

    app.dependency_overrides.clear()

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _token_record(db, token: str) -> ApiToken | None:
    return db.scalar(select(ApiToken).where(ApiToken.token_hash == hash_token(token)))


def _create_accounts(db) -> tuple[AccountsService, object]:
    service = AccountsService(db)
    return service, service.create()


# --- сервисный уровень -------------------------------------------------------


def test_create_makes_student_and_admin(db_session):
    service = AccountsService(db_session)
    result = service.create()
    student = _token_record(db_session, result.student.token)
    admin = _token_record(db_session, result.admin.token)
    assert student is not None and student.role == "student" and student.is_test is True
    assert admin is not None and admin.role == "admin" and admin.is_test is False
    student_user = db_session.get(User, result.student.user_id)
    assert student_user.name == STUDENT_NAME
    assert student_user.direction == STUDENT_DIRECTION
    assert student_user.goal == STUDENT_GOAL
    admin_user = db_session.get(User, result.admin.user_id)
    assert admin_user.name == ADMIN_NAME


def test_create_twice_raises_conflict(db_session):
    service = AccountsService(db_session)
    service.create()
    with pytest.raises(ConflictError):
        service.create()


def test_reset_recreates_accounts(db_session):
    service = AccountsService(db_session)
    first = service.create()
    second = service.reset()
    assert second.student.token != first.student.token
    assert second.admin.token != first.admin.token
    assert _token_record(db_session, first.student.token) is None
    assert _token_record(db_session, second.student.token) is not None
    assert db_session.get(User, second.student.user_id) is not None


def test_reset_test_data_clears_progress(db_session):
    seed_database(db_session)
    service = AccountsService(db_session)
    result = service.create()
    user_id = result.student.user_id
    user = db_session.get(User, user_id)
    role = db_session.scalar(select(Role).limit(1))
    user.target_role_id = role.id
    skill = db_session.scalar(select(Skill).limit(1))
    SkillService(db_session).set_initial_skill(user_id, skill.id, 2)
    mission = MissionRepository(db_session).list_all()[0]
    MissionRepository(db_session).create_attempt(user_id, mission.id, None, True, 10)
    resume = ResumeRepository(db_session).create(user_id, "Резюме", "cv.txt")
    ResumeRepository(db_session).save_analysis(resume.id, {"found_skills": []})

    affected = service.reset_test_data()

    assert affected == 1
    assert db_session.scalar(select(func.count()).select_from(Attempt)) == 0
    assert db_session.scalar(select(func.count()).select_from(UserSkill)) == 0
    assert db_session.scalar(select(func.count()).select_from(Resume)) == 0
    assert db_session.scalar(select(func.count()).select_from(ResumeAnalysis)) == 0
    restored = db_session.get(User, user_id)
    assert restored.target_role_id is None
    assert restored.name == STUDENT_NAME
    assert restored.direction == STUDENT_DIRECTION
    assert restored.goal == STUDENT_GOAL
    assert _token_record(db_session, result.student.token) is not None


def test_reset_test_data_keeps_ids_and_tokens(db_session):
    service = AccountsService(db_session)
    result = service.create()
    user_id = result.student.user_id
    assert service.reset_test_data() == 1
    assert db_session.get(User, user_id) is not None
    assert _token_record(db_session, result.student.token) is not None


def test_reset_test_data_without_students_returns_zero(db_session):
    assert AccountsService(db_session).reset_test_data() == 0


def test_reset_test_data_skips_orphan_tokens(db_session):
    service = AccountsService(db_session)
    service.create()
    orphan = ApiToken(token_hash=hash_token("orphan"), role="student", user_id=99999, is_test=True)
    db_session.add(orphan)
    db_session.commit()
    assert service.reset_test_data() == 2
    assert db_session.get(User, 99999) is None


def test_count_students(db_session):
    service = AccountsService(db_session)
    assert service.count_students(db_session) == 0
    service.create()
    assert service.count_students(db_session) == 1


# --- эндпоинт POST /admin/test-users/reset ----------------------------------


def _setup_accounts(db) -> dict[str, str]:
    service = AccountsService(db)
    result = service.create()
    return {
        "student": result.student.token,
        "admin": result.admin.token,
        "student-user-id": str(result.student.user_id),
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_reset_requires_token(auth_client, db_session):
    _setup_accounts(db_session)
    assert auth_client.post("/admin/test-users/reset").status_code == 401


def test_admin_reset_forbidden_for_student(auth_client, db_session):
    tokens = _setup_accounts(db_session)
    response = auth_client.post("/admin/test-users/reset", headers=_auth(tokens["student"]))
    assert response.status_code == 403


def test_admin_reset_forbidden_for_service(auth_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "service_api_token", "service-secret")
    _setup_accounts(db_session)
    response = auth_client.post("/admin/test-users/reset", headers=_auth("service-secret"))
    assert response.status_code == 403


def test_admin_reset_ok(auth_client, db_session):
    tokens = _setup_accounts(db_session)
    response = auth_client.post("/admin/test-users/reset", headers=_auth(tokens["admin"]))
    assert response.status_code == 200
    body = response.json()
    assert body["reset"] is True
    assert body["students_affected"] == 1
    assert body["message"]


def test_admin_reset_keeps_tokens_valid(auth_client, db_session):
    tokens = _setup_accounts(db_session)
    auth_client.post("/admin/test-users/reset", headers=_auth(tokens["admin"]))
    own = auth_client.get(f"/users/{tokens['student-user-id']}", headers=_auth(tokens["student"]))
    assert own.status_code == 200


def test_admin_reset_idempotent(auth_client, db_session):
    tokens = _setup_accounts(db_session)
    first = auth_client.post("/admin/test-users/reset", headers=_auth(tokens["admin"]))
    second = auth_client.post("/admin/test-users/reset", headers=_auth(tokens["admin"]))
    assert first.status_code == second.status_code == 200
    assert second.json()["students_affected"] == 1

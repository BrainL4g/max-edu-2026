"""Тесты авторизации: роли student/service/admin, 401/403, владение.

Используется «честный» клиент без переопределения аутентификации
(в отличие от фикстуры ``client``, которая ходит от имени service).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.core.security import hash_token
from backend.app.database.session import get_db
from backend.app.domain import ApiToken
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.resume_repository import ResumeRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.seed import seed_database


def _add_token(
    db, *, role: str = "student", user_id: int | None = None, token: str = "student-token"
) -> ApiToken:
    record = ApiToken(token_hash=hash_token(token), role=role, user_id=user_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@pytest.fixture()
def auth_client(db_session):
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


def _make_users(db_session) -> tuple[int, int, int]:
    alice = UserRepository(db_session).create(name="Алиса", direction="backend")
    bob = UserRepository(db_session).create(name="Боб", direction="frontend")
    _add_token(db_session, role="student", user_id=alice.id, token="alice-token")
    _add_token(db_session, role="student", user_id=bob.id, token="bob-token")
    _add_token(db_session, role="admin", user_id=alice.id, token="admin-token")
    return alice.id, bob.id, alice.id


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_no_token_on_protected_returns_401(auth_client, db_session):
    _make_users(db_session)
    assert auth_client.get("/users/1").status_code == 401
    assert auth_client.get("/missions").status_code == 401
    assert auth_client.get("/missions/next", params={"user_id": 1}).status_code == 401


def test_invalid_token_returns_401(auth_client, db_session):
    _make_users(db_session)
    assert auth_client.get("/users/1", headers=_auth("wrong-token")).status_code == 401


def test_student_reads_own_profile(auth_client, db_session):
    alice_id, _, _ = _make_users(db_session)
    response = auth_client.get(f"/users/{alice_id}", headers=_auth("alice-token"))
    assert response.status_code == 200
    assert response.json()["id"] == alice_id


def test_student_cannot_read_foreign_user(auth_client, db_session):
    _, bob_id, _ = _make_users(db_session)
    response = auth_client.get(f"/users/{bob_id}", headers=_auth("alice-token"))
    assert response.status_code == 403


def test_student_cannot_modify_foreign_user(auth_client, db_session):
    _, bob_id, _ = _make_users(db_session)
    response = auth_client.put(
        f"/users/{bob_id}/goal", json={"target_role_id": 1}, headers=_auth("alice-token")
    )
    assert response.status_code == 403


def test_student_cannot_answer_mission_for_foreign_user(auth_client, db_session):
    seed_database(db_session)
    _, bob_id, _ = _make_users(db_session)
    mission = MissionRepository(db_session).list_all()[0]
    response = auth_client.post(
        f"/missions/{mission.id}/answer",
        json={"user_id": bob_id, "option_id": mission.options[0].id},
        headers=_auth("alice-token"),
    )
    assert response.status_code == 403


def test_service_token_has_full_access(auth_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "service_api_token", "service-secret")
    _, bob_id, _ = _make_users(db_session)
    response = auth_client.get(f"/users/{bob_id}", headers=_auth("service-secret"))
    assert response.status_code == 200


def test_by_max_requires_service(auth_client, db_session, monkeypatch):
    monkeypatch.setattr(settings, "service_api_token", "service-secret")
    _make_users(db_session)
    payload = {"max_user_id": 777, "name": "Бот-пользователь"}
    denied = auth_client.post("/users/by-max", json=payload, headers=_auth("alice-token"))
    assert denied.status_code == 403
    response = auth_client.post("/users/by-max", json=payload, headers=_auth("service-secret"))
    assert response.status_code == 200
    assert response.json()["max_user_id"] == 777


def test_app_requires_auth(auth_client, db_session):
    _make_users(db_session)
    assert auth_client.post("/users", json={"name": "Новый"}).status_code == 401


def test_public_endpoints_work_without_token(auth_client, db_session):
    seed_database(db_session)
    for path in ("/health", "/", "/roles", "/skills", "/courses", "/internships"):
        assert auth_client.get(path).status_code == 200, path
    assert auth_client.get("/assessment/questions").status_code == 200


def test_assessment_questions_ownership(auth_client, db_session):
    alice_id, bob_id, _ = _make_users(db_session)
    own = auth_client.get(
        "/assessment/questions", params={"user_id": alice_id}, headers=_auth("alice-token")
    )
    assert own.status_code == 200
    assert len(own.json()) > 0
    missing_token = auth_client.get("/assessment/questions", params={"user_id": alice_id})
    assert missing_token.status_code == 401
    foreign = auth_client.get(
        "/assessment/questions", params={"user_id": bob_id}, headers=_auth("alice-token")
    )
    assert foreign.status_code == 403


def test_attempt_ownership(auth_client, db_session):
    seed_database(db_session)
    alice_id, bob_id, _ = _make_users(db_session)
    attempt = MissionRepository(db_session).create_attempt(
        user_id=alice_id,
        mission_id=MissionRepository(db_session).list_all()[0].id,
        answer_option_id=None,
        is_correct=True,
        xp_earned=10,
    )
    own = auth_client.get(f"/attempts/{attempt.id}", headers=_auth("alice-token"))
    assert own.status_code == 200
    foreign = auth_client.get(f"/attempts/{attempt.id}", headers=_auth("bob-token"))
    assert foreign.status_code == 403


def test_resume_ownership(auth_client, db_session):
    alice_id, bob_id, _ = _make_users(db_session)
    resume = ResumeRepository(db_session).create(alice_id, "Резюме Алисы", "cv.txt")
    own = auth_client.get(f"/resumes/{resume.id}", headers=_auth("alice-token"))
    assert own.status_code == 200
    foreign = auth_client.get(f"/resumes/{resume.id}", headers=_auth("bob-token"))
    assert foreign.status_code == 403


def test_admin_reads_any_user(auth_client, db_session):
    _, bob_id, _ = _make_users(db_session)
    response = auth_client.get(f"/users/{bob_id}", headers=_auth("admin-token"))
    assert response.status_code == 200

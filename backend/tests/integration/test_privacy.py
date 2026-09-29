"""Права субъекта персональных данных и шифрование при хранении (152-ФЗ)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.consent import POLICY_VERSION
from backend.app.core.encryption import PREFIX
from backend.app.core.security import hash_token
from backend.app.database.session import get_db
from backend.app.domain import ApiToken
from backend.app.repositories.user_repository import UserRepository
from backend.app.seed import seed_database

SECRET_NAME = "Иванов Иван Иванович"


@pytest.fixture()
def auth_client(db_session):
    """TestClient с реальной аутентификацией (роль student)."""
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


def _make_student(db, *, token: str = "student-token", name: str = SECRET_NAME) -> int:
    """Пользователь, записанный через ORM (значения шифруются)."""
    user_id = UserRepository(db).create(name=name).id
    db.add(ApiToken(token_hash=hash_token(token), role="student", user_id=user_id))
    db.commit()
    return user_id


def _make_legacy_student(db, *, name: str = SECRET_NAME) -> int:
    """Пользователь, записанный в обход ORM: данные остались в plaintext."""
    result = db.execute(
        text("INSERT INTO users (name, created_at) VALUES (:n, CURRENT_TIMESTAMP)"),
        {"n": name},
    )
    return int(result.lastrowid or 0)


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_personal_data_encrypted_at_rest(client, db_session) -> None:
    """В БД имя лежит шифротекстом, а API отдаёт расшифрованное значение."""
    seed_database(db_session)
    created = client.post("/users/by-max", json={"max_user_id": 424242, "name": SECRET_NAME}).json()
    assert created["name"] == SECRET_NAME

    raw = db_session.execute(
        text("SELECT name FROM users WHERE id = :i"), {"i": created["id"]}
    ).scalar()
    assert str(raw).startswith(PREFIX)
    assert SECRET_NAME not in str(raw)


def test_resume_text_encrypted_at_rest(client, db_session) -> None:
    """Текст резюме — персональные данные, тоже шифруется."""
    user = client.post("/users/by-max", json={"max_user_id": 515151}).json()
    client.post(
        f"/users/{user['id']}/resumes", json={"text": "Опыт работы: 3 года", "filename": "cv.txt"}
    )
    rows = db_session.execute(
        text("SELECT text, filename FROM resumes WHERE user_id = :i"), {"i": user["id"]}
    ).all()
    assert rows
    for row in rows:
        assert str(row[0]).startswith(PREFIX)
        assert "Опыт работы" not in str(row[0])


def test_legacy_plaintext_still_readable(client, db_session) -> None:
    """Данные, записанные до включения шифрования, доступны после миграции."""
    seed_database(db_session)
    user_id = _make_legacy_student(db_session)
    raw = db_session.execute(text("SELECT name FROM users WHERE id = :i"), {"i": user_id}).scalar()
    assert str(raw) == SECRET_NAME  # в базе действительно plaintext
    response = client.get(f"/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["name"] == SECRET_NAME


def test_consent_default_is_false(client, db_session) -> None:
    seed_database(db_session)
    user = client.post("/users/by-max", json={"max_user_id": 616161}).json()
    status = client.get(f"/users/{user['id']}/consent").json()
    assert status["consent_given"] is False
    assert status["consent_at"] is None


def test_consent_granted_and_withdrawn(client, db_session) -> None:
    seed_database(db_session)
    user = client.post("/users/by-max", json={"max_user_id": 626262}).json()
    uid = user["id"]

    given = client.post(f"/users/{uid}/consent").json()
    assert given["consent_given"] is True
    assert given["policy_version"] == POLICY_VERSION
    assert given["consent_at"] is not None

    withdrawn = client.delete(f"/users/{uid}/consent").json()
    assert withdrawn["consent_given"] is False
    assert withdrawn["consent_at"] is None
    assert withdrawn["policy_version"] is None


def test_consent_policy_is_public(client) -> None:
    body = client.get("/consent/policy").json()
    assert body["version"] == POLICY_VERSION
    assert "152-ФЗ" in body["text"]
    assert "Права пользователя" in body["text"]


def test_data_export_returns_profile(client, db_session) -> None:
    seed_database(db_session)
    user = client.post("/users/by-max", json={"max_user_id": 636363, "name": SECRET_NAME}).json()
    exported = client.get(f"/users/{user['id']}/data-export").json()
    assert exported["name"] == SECRET_NAME
    assert exported["max_user_id"] == 636363
    assert "consent_given" in exported


def test_delete_data_removes_personal_records(client, db_session) -> None:
    """Удаление стирает профиль, навыки, попытки, резюме и токены (право на забвение)."""
    seed_database(db_session)
    user = client.post("/users/by-max", json={"max_user_id": 646464, "name": SECRET_NAME}).json()
    uid = user["id"]
    client.post(f"/users/{uid}/resumes", json={"text": "Резюме"})
    client.post(
        f"/users/{uid}/assessment", json={"answers": [{"question_id": 1, "option_index": 2}]}
    )

    assert client.get(f"/users/{uid}").status_code == 200
    deleted = client.delete(f"/users/{uid}/data").json()
    assert deleted["deleted"] is True

    for table, column in (
        ("users", "id"),
        ("resumes", "user_id"),
        ("resume_analysis", "resume_id"),
        ("user_skills", "user_id"),
        ("attempts", "user_id"),
        ("api_tokens", "user_id"),
    ):
        count = db_session.execute(
            text(f"SELECT count(*) FROM {table} WHERE {column} = :i"), {"i": uid}
        ).scalar()
        assert count == 0, table
    assert client.get(f"/users/{uid}").status_code == 404


def test_privacy_endpoints_enforce_ownership(auth_client, db_session) -> None:
    """Студент не читает и не удаляет данные другого пользователя."""
    seed_database(db_session)
    alice_id = _make_student(db_session, token="alice-token", name="Алиса")
    bob_id = _make_student(db_session, token="bob-token", name="Борис")

    for path in (f"/users/{bob_id}/consent", f"/users/{bob_id}/data-export"):
        assert auth_client.get(path, headers=_auth("alice-token")).status_code == 403
    assert (
        auth_client.delete(f"/users/{bob_id}/data", headers=_auth("alice-token")).status_code == 403
    )

    own = auth_client.get(f"/users/{alice_id}/data-export", headers=_auth("alice-token"))
    assert own.status_code == 200
    assert own.json()["name"] == "Алиса"


def test_privacy_endpoints_require_auth(auth_client, db_session) -> None:
    seed_database(db_session)
    user_id = _make_student(db_session)
    assert auth_client.get(f"/users/{user_id}/consent").status_code == 401
    assert auth_client.get(f"/users/{user_id}/data-export").status_code == 401
    assert auth_client.delete(f"/users/{user_id}/data").status_code == 401


def test_service_token_keeps_privacy_access(auth_client, db_session, monkeypatch) -> None:
    """Сервисная роль (бот) сохраняет доступ — иначе бот перестанет работать."""
    monkeypatch.setattr(settings, "service_api_token", "service-secret")
    seed_database(db_session)
    user_id = _make_student(db_session)
    response = auth_client.get(f"/users/{user_id}/data-export", headers=_auth("service-secret"))
    assert response.status_code == 200

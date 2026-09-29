"""Контракт DATA-API.yaml: структура, соответствие OpenAPI, исполнение всех проверок.

Запуск: ``python -m pytest tests/contract`` (cwd backend).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.domain import Role
from backend.app.main import app
from backend.app.seed import seed_database
from backend.app.services.data_api_runner import DataApiRunner
from backend.app.services.test_accounts import TestAccountsService

ROOT = Path(__file__).resolve().parents[3]

EXPECTED_KEYS = {
    "name",
    "description",
    "method",
    "path",
    "params",
    "role",
    "expected_status",
    "content_type",
    "required_fields",
}
ALLOWED_ROLES = {"none", "student", "admin", "service"}


def _load_spec() -> dict:
    return yaml.safe_load((ROOT / "DATA-API.yaml").read_text(encoding="utf-8"))


def _load_seed() -> dict:
    return json.loads((ROOT / "tests-data" / "test-data.json").read_text(encoding="utf-8"))


def _openapi_path(check: dict) -> str:
    """Путь проверки в терминах OpenAPI (плейсхолдеры → имена path-параметров)."""
    if check["name"] == "not-found":
        return "/users/{user_id}"
    path = check["path"]
    path = path.replace("{{student.user_id}}", "{user_id}").replace(
        "{{admin.user_id}}", "{user_id}"
    )
    path = path.replace("{{capture.next-mission.mission.id}}", "{mission_id}")
    path = path.replace("{{capture.create-resume.id}}", "{resume_id}")
    return path


# --- структура файла ---------------------------------------------------------


def test_data_api_declares_mandatory_sections() -> None:
    spec = _load_spec()
    for key in ("config_version", "solution", "team_id", "base_url", "api_spec", "keys", "checks"):
        assert key in spec, f"DATA-API.yaml без секции {key}"
    assert spec["keys"]["student"] == "{{student.token}}"
    assert spec["keys"]["admin"] == "{{admin.token}}"
    assert spec["keys"]["service"] == "{{service.token}}"
    assert spec["checks"], "DATA-API.yaml без проверок"


def test_data_api_each_check_has_nine_fields() -> None:
    spec = _load_spec()
    for check in spec["checks"]:
        assert set(check) == EXPECTED_KEYS, f"check {check.get('name')}: не ровно 9 полей"
        assert check["method"] in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert check["role"] in ALLOWED_ROLES
        assert isinstance(check["expected_status"], int)


def test_data_api_paths_exist_in_openapi() -> None:
    spec = _load_spec()
    oas = app.openapi()
    for check in spec["checks"]:
        path = _openapi_path(check)
        assert path in oas["paths"], f"check {check['name']}: пути {path} нет в OpenAPI"
        method = check["method"].lower()
        assert method in oas["paths"][path], f"check {check['name']}: метода {method} нет в OpenAPI"


def test_data_api_target_role_matches_seed(db_session) -> None:
    seed_database(db_session)
    role = db_session.scalar(select(Role).where(Role.name == "Backend Junior"))
    assert role is not None and role.id == _load_seed()["student"]["target_role_id"]


# --- исполнение всех проверок против TestClient ------------------------------


@pytest.fixture()
def api_client(db_session, monkeypatch):
    """TestClient с реальной аутентификацией и демо-данными."""
    monkeypatch.setattr(settings, "service_api_token", "service-secret")
    seed_database(db_session)

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


def test_all_data_api_checks_pass(api_client, db_session) -> None:
    accounts = TestAccountsService(db_session).create()
    runner = DataApiRunner(
        client=api_client,
        accounts={
            "student": {"user_id": accounts.student.user_id, "token": accounts.student.token},
            "admin": {"user_id": accounts.admin.user_id, "token": accounts.admin.token},
            "service": {"token": "service-secret"},
        },
        seed=_load_seed(),
    )
    results = runner.run(_load_spec())
    failed = [result for result in results if not result.passed]
    assert failed == [], "\n".join(
        f"[{result.name}] " + "; ".join(result.errors) for result in failed
    )


# --- юнит-тесты раннера (ветки ошибок) ----------------------------------------


class _FakeResponse:
    def __init__(self, status_code: int = 200, body: object = None) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = {"content-type": "application/json"}

    def json(self) -> object:
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class _FakeClient:
    def __init__(self, responder) -> None:
        self.requests: list[tuple[str, str, dict]] = []
        self._responder = responder

    def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        self.requests.append((method, url, kwargs))
        return self._responder(method, url, kwargs)


def _make_check(**overrides: object) -> dict:
    check = {
        "name": "check",
        "description": "desc",
        "method": "GET",
        "path": "/",
        "params": {},
        "role": "none",
        "expected_status": 200,
        "content_type": "application/json",
        "required_fields": [],
    }
    check.update(overrides)
    return check


def _runner(client: _FakeClient) -> DataApiRunner:
    return DataApiRunner(
        client=client,
        accounts={
            "student": {"user_id": 7, "token": "student-token"},
            "admin": {"user_id": 8, "token": "admin-token"},
        },
        seed=_load_seed(),
    )


def _ok_responder(method: str, url: str, kwargs: dict) -> _FakeResponse:
    if url.startswith("/first"):
        return _FakeResponse(200, {"id": 5, "items": [{"id": 5}]})
    if url.startswith("/list"):
        return _FakeResponse(200, [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])
    return _FakeResponse(200, {"id": 1})


def test_runner_resolves_placeholders() -> None:
    runner = _runner(_FakeClient(_ok_responder))
    assert runner.resolve("{{student.user_id}}") == 7
    assert runner.resolve("/users/{{student.user_id}}") == "/users/7"
    assert runner.resolve({"a": ["{{student.token}}"], "b": "file.txt"}) == {
        "a": ["student-token"],
        "b": "file.txt",
    }
    assert runner.resolve(5) == 5


def test_runner_captures_and_reuses_previous_answers() -> None:
    client = _FakeClient(_ok_responder)
    runner = _runner(client)
    checks = [
        _make_check(name="first", path="/first", required_fields=["id"]),
        _make_check(
            name="second",
            method="POST",
            path="/users/{{capture.first.id}}",
            params={"user_id": "{{student.user_id}}"},
            role="student",
            required_fields=["id"],
        ),
    ]
    results = runner.run({"checks": checks})
    assert results[0].passed and results[1].passed
    method, url, kwargs = client.requests[1]
    assert (method, url) == ("POST", "/users/5")
    assert kwargs["json"] == {"user_id": 7}
    assert kwargs["headers"]["Authorization"] == "Bearer student-token"


def test_runner_reports_status_mismatch() -> None:
    client = _FakeClient(lambda method, url, kwargs: _FakeResponse(500, {}))
    result = _runner(client).run({"checks": [_make_check()]})[0]
    assert not result.passed
    assert any("status 500" in error for error in result.errors)


def test_runner_reports_content_type_mismatch() -> None:
    response = _FakeResponse(200, {})
    response.headers = {"content-type": "text/html"}
    client = _FakeClient(lambda method, url, kwargs: response)
    result = _runner(client).run({"checks": [_make_check()]})[0]
    assert not result.passed
    assert any("text/html" in error for error in result.errors)


def test_runner_reports_missing_field() -> None:
    check = _make_check(required_fields=["id", "name"])
    client = _FakeClient(lambda method, url, kwargs: _FakeResponse(200, {"id": 1}))
    result = _runner(client).run({"checks": [check]})[0]
    assert not result.passed
    assert any("missing field 'name'" in error for error in result.errors)


def test_runner_checks_each_list_item() -> None:
    check = _make_check(required_fields=["id", "name"], path="/list")
    client = _FakeClient(_ok_responder)
    runner = _runner(client)
    result = runner.run({"checks": [check]})[0]
    assert result.passed
    assert runner.captures["check"] == [{"id": 1, "name": "a"}, {"id": 2, "name": "b"}]


def test_runner_supports_nested_required_fields() -> None:
    check = _make_check(required_fields=["items.0.id"], path="/first")
    client = _FakeClient(_ok_responder)
    runner = _runner(client)
    result = runner.run({"checks": [check]})[0]
    assert result.passed


def test_runner_reports_nested_missing_field() -> None:
    check = _make_check(required_fields=["items.9.id"], path="/first")
    client = _FakeClient(_ok_responder)
    result = _runner(client).run({"checks": [check]})[0]
    assert not result.passed
    assert any("missing field 'items.9.id'" in error for error in result.errors)


def test_runner_handles_non_json_body() -> None:
    client = _FakeClient(lambda method, url, kwargs: _FakeResponse(200, ValueError("not json")))
    result = _runner(client).run({"checks": [_make_check(required_fields=["x"])]})[0]
    assert not result.passed
    assert any("missing field 'x'" in error for error in result.errors)


def test_runner_reports_unknown_placeholder_source() -> None:
    check = _make_check(path="/{{someone.token}}")
    client = _FakeClient(_ok_responder)
    result = _runner(client).run({"checks": [check]})[0]
    assert not result.passed
    assert any("Неизвестный источник" in error for error in result.errors)


def test_runner_reports_missing_field_in_placeholder() -> None:
    check = _make_check(path="/{{test-data.student.missing}}")
    client = _FakeClient(_ok_responder)
    result = _runner(client).run({"checks": [check]})[0]
    assert not result.passed
    assert any("Нет поля 'missing'" in error for error in result.errors)


def test_runner_reports_capture_list_index_error() -> None:
    checks = [
        _make_check(name="first", path="/first"),
        _make_check(name="second", path="/{{capture.first.items.5.id}}"),
    ]
    client = _FakeClient(_ok_responder)
    result = _runner(client).run({"checks": checks})[1]
    assert not result.passed
    assert any("Нет элемента '5'" in error for error in result.errors)


def test_runner_requires_capture_check_name() -> None:
    check = _make_check(path="/{{capture}}")
    client = _FakeClient(_ok_responder)
    result = _runner(client).run({"checks": [check]})[0]
    assert not result.passed
    assert any("capture.<check>.<поле>" in error for error in result.errors)

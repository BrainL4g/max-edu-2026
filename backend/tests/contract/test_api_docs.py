"""Синхронизация docs/API.md с кодом: эндпоинты, роли, коды ошибок.

Тест падает, если в приложении появился эндпоинт, которого нет в документации,
или если в документации описан несуществующий путь.

Запуск: ``python -m pytest tests/contract/test_api_docs.py`` (cwd backend).
"""

from __future__ import annotations

import re
from pathlib import Path

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[3]
API_MD = ROOT / "docs" / "API.md"

# Публичные операции без токена (описаны в API.md).
# *recommended требует токена: принимает user_id и отдаёт персональные данные.
PUBLIC_PATHS = {
    "/health",
    "/",
    "/roles",
    "/skills",
    "/skills/{skill_id}",
    "/courses",
    "/courses/{course_id}",
    "/internships",
    "/internships/{internship_id}",
    "/assessment/questions",
}


def _documented_paths() -> set[str]:
    """Пути OpenAPI, встречающиеся в API.md как `METHOD /path` или в inline-коде."""
    text = API_MD.read_text(encoding="utf-8")
    found: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        # Строки вида: `GET /users/{user_id}` или `POST /admin/test-users/reset` → 200
        match = re.match(r"`?(GET|POST|PUT|PATCH|DELETE)\s+(/[\w/{}.-]*)", stripped)
        if match:
            found.add(match.group(2))
            continue
        # curl-команды: curl -s $BASE/users/1/progress
        for curl_path in re.findall(r"\$BASE(/[\w/{}.-]*)", stripped):
            found.add(curl_path)
    return found


def test_api_md_exists() -> None:
    assert API_MD.is_file(), "docs/API.md обязателен для приёмки API"


def test_all_endpoints_documented() -> None:
    """Каждый путь из OpenAPI упомянут в API.md."""
    documented = _documented_paths()
    missing: list[str] = []
    for path in app.openapi()["paths"]:
        if path in documented:
            continue
        # Пути с параметрами запроса вызываются как /path?param=...
        if any(path in candidate for candidate in documented):
            continue
        missing.append(path)
    assert not missing, f"Эндпоинты не описаны в docs/API.md: {missing}"


def _resolve_template(path: str) -> bool:
    """Совпадает ли curl-путь с шаблоном OpenAPI (id вместо имени параметра)."""
    segments = path.split("/")
    for candidate in app.openapi()["paths"]:
        parts = candidate.split("/")
        if len(parts) != len(segments):
            continue
        if all(
            left == right or (left.isdigit() and right.startswith("{") and right.endswith("}"))
            for left, right in zip(segments, parts)
        ):
            return True
    return False


def test_documented_paths_exist() -> None:
    """Каждый путь из API.md существует в приложении (curl-примеры — с 1 вместо id)."""
    paths = set(app.openapi()["paths"])
    for documented in _documented_paths():
        if documented in paths or _resolve_template(documented):
            continue
        raise AssertionError(f"Путь {documented} описан в API.md, но отсутствует в приложении")


def test_api_md_documents_auth_and_errors() -> None:
    text = API_MD.read_text(encoding="utf-8")
    assert "Authorization: Bearer" in text, "API.md должен описывать Bearer-аутентификацию"
    assert "401" in text and "403" in text, "API.md должен описывать 401 и 403"
    assert "422" in text, "API.md должен описывать 422"
    for role in ("student", "admin", "service"):
        assert role in text, f"API.md должен описывать роль {role}"
    assert "Идемпотентность" in text, "API.md должен описывать идемпотентность"
    assert "DATA-API" in text, "API.md должен ссылаться на DATA-API.yaml"


def test_public_paths_have_no_security() -> None:
    """Публичные операции действительно объявлены без security в OpenAPI."""
    schema = app.openapi()
    for path in PUBLIC_PATHS:
        for method, operation in schema["paths"][path].items():
            if method in {"get", "post", "put", "patch", "delete"}:
                assert operation.get("security") == [], f"{method.upper()} {path} не публичен"

"""HTTP-клиент к API SkillQuest.

Клиент переиспользуется между запросами: один пул соединений httpx
(до 10 активных, до 5 keep-alive).
"""

from __future__ import annotations

import os
from typing import Any, cast

import httpx

BASE_URL = os.getenv("SKILLQUEST_API", "http://127.0.0.1:8000")
API_TOKEN = os.getenv("SKILLQUEST_API_TOKEN") or "skillquest-service-token"
TIMEOUT = 15.0
# Анализ резюме может ходить в GigaChat — даём ему больше времени.
ANALYZE_TIMEOUT = 60.0

_client: httpx.AsyncClient | None = None


class ApiError(Exception):
    """Запрос к API SkillQuest завершился ошибкой."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _headers() -> dict[str, str]:
    """Заголовки по умолчанию: Bearer-токен сервисного аккаунта (бот)."""
    return {"Authorization": f"Bearer {API_TOKEN}"} if API_TOKEN else {}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=TIMEOUT,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )
    return _client


async def _req(method: str, path: str, **kwargs: Any) -> Any:
    headers = dict(kwargs.pop("headers", None) or {})
    headers.update(_headers())
    response = await _get_client().request(method, path, headers=headers, **kwargs)
    if response.status_code >= 400:
        raise ApiError(
            f"{method} {path} -> {response.status_code}", response.status_code
        )
    if response.status_code == 204:
        return None
    return response.json()


def _obj(data: Any) -> dict[str, Any]:
    """Узкий тип ответа JSON с произвольной структурой."""
    return cast(dict[str, Any], data)


def _list(data: Any) -> list[dict[str, Any]]:
    """Узкий тип списка объектов из ответа JSON."""
    return cast(list[dict[str, Any]], data)


async def get_user(max_user_id: int, name: str | None = None) -> dict[str, Any]:
    """Get-or-create пользователя платформы по max_user_id."""
    return _obj(
        await _req(
            "POST", "/users/by-max", json={"max_user_id": max_user_id, "name": name}
        )
    )


async def assessment_questions(user_id: int | None = None) -> list[dict[str, Any]]:
    """Банк вопросов диагностики (по направлению пользователя, если задан)."""
    params = {"user_id": user_id} if user_id is not None else None
    return _list(await _req("GET", "/assessment/questions", params=params))


async def submit_assessment(
    user_id: int, answers: list[dict[str, Any]]
) -> dict[str, Any]:
    """Отправить ответы диагностики и получить начальный Skill Map."""
    return _obj(
        await _req("POST", f"/users/{user_id}/assessment", json={"answers": answers})
    )


async def skill_map(user_id: int) -> list[dict[str, Any]]:
    """Skill Map пользователя."""
    return _list(await _req("GET", f"/users/{user_id}/skills"))


async def get_profile(user_id: int) -> dict[str, Any]:
    """Профиль пользователя платформы (цель, направление)."""
    return _obj(await _req("GET", f"/users/{user_id}"))


async def next_mission(user_id: int) -> dict[str, Any]:
    """Следующая миссия по цели: status (ok/no_goal/all_done), прогресс, миссия."""
    return _obj(await _req("GET", "/missions/next", params={"user_id": user_id}))


async def answer_mission(
    user_id: int, mission_id: int, option_id: int
) -> dict[str, Any]:
    """Ответ на миссию: проверка, XP, новый уровень навыка."""
    return _obj(
        await _req(
            "POST",
            f"/missions/{mission_id}/answer",
            json={"user_id": user_id, "option_id": option_id},
        )
    )


async def rec_courses(user_id: int) -> list[dict[str, Any]]:
    """Рекомендации курсов по пробелам в навыках."""
    return _list(await _req("GET", "/courses/recommended", params={"user_id": user_id}))


async def rec_internships(
    user_id: int, direction: str | None = None
) -> list[dict[str, Any]]:
    """Рекомендации стажировок, опционально с фильтром по направлению."""
    params: dict[str, Any] = {"user_id": user_id}
    if direction and direction != "any":
        params["direction"] = direction
    return _list(await _req("GET", "/internships/recommended", params=params))


async def internship_directions() -> list[str]:
    """Доступные направления стажировок (для кнопок фильтра)."""
    return [str(item) for item in await _req("GET", "/internships/directions")]


async def upload_resume(user_id: int, text: str) -> dict[str, Any]:
    """Загрузка резюме текстом."""
    return _obj(await _req("POST", f"/users/{user_id}/resumes", json={"text": text}))


async def upload_resume_file(
    user_id: int, filename: str | None, content: bytes
) -> dict[str, Any]:
    """Загрузка резюме файлом (multipart/form-data)."""
    files = {"file": (filename or "resume.txt", content, "application/octet-stream")}
    return _obj(await _req("POST", f"/users/{user_id}/resumes/upload", files=files))


async def analyze_resume(resume_id: int) -> dict[str, Any]:
    """Запуск анализа резюме (увеличенный таймаут: бэкенд может ходить в GigaChat)."""
    return _obj(
        await _req("POST", f"/resumes/{resume_id}/analyze", timeout=ANALYZE_TIMEOUT)
    )


async def list_roles() -> list[dict[str, Any]]:
    """Все целевые карьерные роли."""
    return _list(await _req("GET", "/roles"))


async def set_goal(user_id: int, target_role_id: int) -> dict[str, Any]:
    """Выбрать целевую роль пользователя."""
    return _obj(
        await _req(
            "PUT",
            f"/users/{user_id}/goal",
            json={"target_role_id": target_role_id},
        )
    )


async def gap_analysis(user_id: int) -> dict[str, Any]:
    """Что не хватает до целевой роли и процент соответствия."""
    return _obj(await _req("GET", f"/users/{user_id}/gap-analysis"))

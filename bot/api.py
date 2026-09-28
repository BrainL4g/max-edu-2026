"""HTTP-клиент к API SkillQuest."""

from __future__ import annotations

import os
from typing import Any

import httpx

BASE_URL = os.getenv("SKILLQUEST_API", "http://127.0.0.1:8000")
TIMEOUT = 15.0

_client: httpx.AsyncClient | None = None


class ApiError(Exception):
    """Запрос к API SkillQuest завершился ошибкой."""


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)
    return _client


async def _req(method: str, path: str, **kwargs: Any) -> Any:
    response = await _get_client().request(method, path, **kwargs)
    if response.status_code >= 400:
        raise ApiError(f"{method} {path} -> {response.status_code}")
    if response.status_code == 204:
        return None
    return response.json()


async def get_user(max_user_id: int, name: str | None = None) -> dict:
    """Get-or-create пользователя платформы по max_user_id."""
    return await _req(
        "POST", "/users/by-max", json={"max_user_id": max_user_id, "name": name}
    )


async def assessment_questions() -> list[dict]:
    """Банк вопросов диагностики."""
    return await _req("GET", "/assessment/questions")


async def submit_assessment(user_id: int, answers: list[dict]) -> dict:
    """Отправить ответы диагностики и получить начальный Skill Map."""
    return await _req(
        "POST", f"/users/{user_id}/assessment", json={"answers": answers}
    )


async def skill_map(user_id: int) -> list[dict]:
    """Skill Map пользователя."""
    return await _req("GET", f"/users/{user_id}/skills")


async def next_mission(user_id: int) -> dict | None:
    """Следующая миссия или None, если все пройдены."""
    mission = await _req("GET", "/missions/next", params={"user_id": user_id})
    return mission or None


async def answer_mission(user_id: int, mission_id: int, option_id: int) -> dict:
    """Ответ на миссию: проверка, XP, новый уровень навыка."""
    return await _req(
        "POST",
        f"/missions/{mission_id}/answer",
        json={"user_id": user_id, "option_id": option_id},
    )


async def rec_courses(user_id: int) -> list[dict]:
    """Рекомендации курсов по пробелам в навыках."""
    return await _req(
        "GET", "/courses/recommended", params={"user_id": user_id}
    )


async def rec_internships(user_id: int) -> list[dict]:
    """Рекомендации стажировок."""
    return await _req(
        "GET", "/internships/recommended", params={"user_id": user_id}
    )


async def upload_resume(user_id: int, text: str) -> dict:
    """Загрузка резюме текстом."""
    return await _req("POST", f"/users/{user_id}/resumes", json={"text": text})


async def analyze_resume(resume_id: int) -> dict:
    """Запуск анализа резюме."""
    return await _req("POST", f"/resumes/{resume_id}/analyze")
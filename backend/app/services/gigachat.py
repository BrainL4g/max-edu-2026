"""Клиент GigaChat: AI-оценка резюме.

Интеграция опциональна. Если в окружении не заданы `GIGACHAT_CREDENTIALS`
(Authorization key) или `GIGACHAT_ACCESS_TOKEN`, клиент считается
несконфигурированным: анализ резюме остаётся эвристическим.

Любая ошибка сети или формата ответа не ломает анализ — клиент логирует
предупреждение и возвращает ``None``.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Any

import httpx

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Промпт: строгий JSON-контракт, чтобы ответ легко разбирался.
RESUME_SYSTEM_PROMPT = (
    "Ты карьерный консультант и технический рекрутер. Оцени резюме студента или "
    "junior-специалиста для отклика на стажировку.\n"
    "Верни ТОЛЬКО валидный JSON без markdown и пояснений:\n"
    "{\n"
    '  "score": 0,\n'
    '  "summary": "краткий вердикт по резюме",\n'
    '  "strengths": ["сильная сторона"],\n'
    '  "issues": ["проблема резюме"],\n'
    '  "recommendations": ["конкретный совет по доработке"]\n'
    "}\n"
    "score — целое число от 0 до 100 (готовность резюме к отклику).\n"
    "strengths, issues и recommendations — от 1 до 5 пунктов, по-русски, "
    "конкретно и без воды."
)

MAX_RESUME_CHARS = 8000
MAX_LIST_ITEMS = 5
MAX_ITEM_CHARS = 300
MAX_SUMMARY_CHARS = 600
JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


class GigaChatClient:
    """Тонкий HTTP-клиент GigaChat для оценки резюме."""

    def __init__(self, http: httpx.Client | None = None) -> None:
        self._http = http
        self._token = ""
        self._expires_at = 0.0

    @property
    def configured(self) -> bool:
        """Заданы ли ключ или готовый токен GigaChat."""
        return bool(settings.gigachat_credentials or settings.gigachat_access_token)

    def evaluate_resume(
        self,
        text: str,
        direction: str | None = None,
        found_skills: list[str] | None = None,
        missing_skills: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Оценить резюме через GigaChat.

        Возвращает словарь ``score/summary/strengths/issues/recommendations``
        или ``None``, если интеграция выключена либо запрос не удался.
        """
        if not self.configured:
            return None
        try:
            return self._evaluate(text, direction, found_skills or [], missing_skills or [])
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
            logger.warning("GigaChat не смог оценить резюме: %s", exc)
            return None

    def _evaluate(
        self,
        text: str,
        direction: str | None,
        found_skills: list[str],
        missing_skills: list[str],
    ) -> dict[str, Any]:
        """Запрос к /chat/completions и разбор JSON-ответа модели."""
        response = self._client().post(
            f"{settings.gigachat_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={
                "model": settings.gigachat_model,
                "temperature": 0.2,
                "messages": [
                    {"role": "system", "content": RESUME_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": _user_prompt(text, direction, found_skills, missing_skills),
                    },
                ],
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_evaluation(str(content))

    def _access_token(self) -> str:
        """Готовый токен из окружения либо OAuth-токен с кэшированием."""
        if settings.gigachat_access_token:
            return settings.gigachat_access_token
        now = time.time()
        if self._token and now < self._expires_at:
            return self._token
        response = self._client().post(
            settings.gigachat_auth_url,
            headers={
                "Authorization": f"Basic {settings.gigachat_credentials}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": settings.gigachat_scope},
        )
        response.raise_for_status()
        data = response.json()
        self._token = str(data["access_token"])
        expires_at = float(data.get("expires_at") or 0) / 1000
        self._expires_at = min(expires_at - 60, now + 1740) if expires_at else now + 1740
        return self._token

    def _client(self) -> httpx.Client:
        """HTTP-клиент (создаётся лениво и переиспользуется)."""
        if self._http is None:
            verify: bool | str = settings.gigachat_ca_bundle or settings.gigachat_verify_ssl
            self._http = httpx.Client(timeout=settings.gigachat_timeout, verify=verify)
        return self._http


def _user_prompt(
    text: str,
    direction: str | None,
    found_skills: list[str],
    missing_skills: list[str],
) -> str:
    """Пользовательский промпт: контекст пользователя и текст резюме."""
    return "\n".join(
        [
            f"Направление пользователя: {direction or 'не указано'}",
            f"Найденные навыки: {', '.join(found_skills) or '—'}",
            f"Не хватает навыков: {', '.join(missing_skills) or '—'}",
            "Текст резюме:",
            text[:MAX_RESUME_CHARS],
        ]
    )


def _parse_evaluation(content: str) -> dict[str, Any]:
    """Разобрать ответ модели: снять markdown-обёртку и прочитать JSON."""
    match = JSON_BLOCK_RE.search(content)
    if match is None:
        raise ValueError("в ответе GigaChat нет JSON")
    data = json.loads(match.group(0))
    score = float(data.get("score") or 0)
    return {
        "score": max(0.0, min(round(score, 1), 100.0)),
        "summary": _as_text(data.get("summary")),
        "strengths": _as_list(data.get("strengths")),
        "issues": _as_list(data.get("issues")),
        "recommendations": _as_list(data.get("recommendations")),
    }


def _as_text(value: Any) -> str:
    """Строка из произвольного значения (с ограничением длины)."""
    return str(value).strip()[:MAX_SUMMARY_CHARS] if value else ""


def _as_list(value: Any) -> list[str]:
    """Список строк из произвольного значения (не более 5 коротких пунктов)."""
    if not isinstance(value, list):
        return []
    items = [str(item).strip()[:MAX_ITEM_CHARS] for item in value if str(item).strip()]
    return items[:MAX_LIST_ITEMS]

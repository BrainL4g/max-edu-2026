"""Тесты клиента GigaChat: кэш access token и fallback на эвристику."""

from __future__ import annotations

import json
import time

import httpx

from backend.app.core.config import settings
from backend.app.services.gigachat import GigaChatClient

_EVAL_CONTENT = json.dumps(
    {
        "score": 85,
        "summary": "Хорошее резюме",
        "strengths": ["Проекты"],
        "issues": ["Нет ссылок"],
        "recommendations": ["Добавьте GitHub"],
    },
    ensure_ascii=False,
)


def _transport(calls: list[str], oauth_status: int = 200) -> httpx.MockTransport:
    """Транспорт: /oauth отдаёт токен, /chat/completions — оценку."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/oauth"):
            if oauth_status != 200:
                return httpx.Response(oauth_status, json={"error": "unauthorized"})
            expires_at = int((time.time() + 1800) * 1000)  # 30 минут, как в API
            return httpx.Response(200, json={"access_token": "tok-1", "expires_at": expires_at})
        return httpx.Response(200, json={"choices": [{"message": {"content": _EVAL_CONTENT}}]})

    return httpx.MockTransport(handler)


def test_access_token_is_cached(monkeypatch) -> None:
    """Токен запрашивается один раз и переиспользуется до истечения (30 минут)."""
    monkeypatch.setattr(settings, "gigachat_credentials", "basic-key")
    monkeypatch.setattr(settings, "gigachat_access_token", "")
    calls: list[str] = []
    client = GigaChatClient(http=httpx.Client(transport=_transport(calls)))

    first = client.evaluate_resume("Python, Docker")
    second = client.evaluate_resume("Python, Docker")

    assert first is not None and first["score"] == 85
    assert second is not None
    assert len([path for path in calls if path.endswith("/oauth")]) == 1
    assert len([path for path in calls if path.endswith("/chat/completions")]) == 2


def test_not_configured_returns_none(monkeypatch) -> None:
    """Без ключа и токена клиент не сконфигурирован — анализа нет, эвристика жива."""
    monkeypatch.setattr(settings, "gigachat_credentials", "")
    monkeypatch.setattr(settings, "gigachat_access_token", "")

    assert GigaChatClient().evaluate_resume("текст резюме") is None  # без сетевых вызовов


def test_oauth_error_returns_none(monkeypatch) -> None:
    """Невалидный Authorization key: OAuth падает → None, анализ остаётся эвристическим."""
    monkeypatch.setattr(settings, "gigachat_credentials", "bad-key")
    monkeypatch.setattr(settings, "gigachat_access_token", "")
    calls: list[str] = []
    client = GigaChatClient(http=httpx.Client(transport=_transport(calls, oauth_status=401)))

    assert client.evaluate_resume("текст резюме") is None
    assert len([path for path in calls if path.endswith("/oauth")]) == 1

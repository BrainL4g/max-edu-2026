"""Тесты клиента GigaChat: кэш access token и fallback на эвристику."""

from __future__ import annotations

import json
import time

import httpx

from backend.app.core.config import settings
from backend.app.services.gigachat import GigaChatClient, _parse_evaluation

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


def test_ready_access_token_skips_oauth(monkeypatch) -> None:
    """Готовый access token используется напрямую, OAuth не вызывается."""
    monkeypatch.setattr(settings, "gigachat_credentials", "basic-key")
    monkeypatch.setattr(settings, "gigachat_access_token", "ready-token")
    calls: list[str] = []
    client = GigaChatClient(http=httpx.Client(transport=_transport(calls)))

    result = client.evaluate_resume("Python, Docker")

    assert result is not None and result["score"] == 85
    assert not [path for path in calls if path.endswith("/oauth")]
    assert client._access_token() == "ready-token"  # noqa: SLF001


def test_expired_token_is_refreshed_and_retried(monkeypatch) -> None:
    """Ответ 401 сбрасывает кэш токена и запрос повторяется один раз."""
    monkeypatch.setattr(settings, "gigachat_credentials", "basic-key")
    monkeypatch.setattr(settings, "gigachat_access_token", "")
    chats: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/oauth"):
            expires_at = int((time.time() + 1800) * 1000)
            return httpx.Response(200, json={"access_token": "tok-1", "expires_at": expires_at})
        chats.append(1)
        if len(chats) == 1:  # первый запрос — с устаревшим токеном
            return httpx.Response(401, json={"error": "token expired"})
        return httpx.Response(200, json={"choices": [{"message": {"content": _EVAL_CONTENT}}]})

    client = GigaChatClient(http=httpx.Client(transport=httpx.MockTransport(handler)))

    result = client.evaluate_resume("Python, Docker")

    assert result is not None and result["score"] == 85
    assert len(chats) == 2


def test_client_created_lazily_with_ca_bundle(monkeypatch) -> None:
    """Клиент собирается один раз и учитывает путь к CA-бандлу."""
    import certifi

    monkeypatch.setattr(settings, "gigachat_ca_bundle", certifi.where())
    client = GigaChatClient()
    built = client._client()  # noqa: SLF001
    assert client._client() is built  # noqa: SLF001


def test_client_created_with_ssl_verification_disabled(monkeypatch) -> None:
    """verify_ssl=False не требует файла CA-бандла."""
    monkeypatch.setattr(settings, "gigachat_ca_bundle", "")
    monkeypatch.setattr(settings, "gigachat_verify_ssl", False)
    assert GigaChatClient()._client() is not None  # noqa: SLF001


def test_parser_tolerates_partial_payload() -> None:
    """Модель может не вернуть все поля — отчёт остаётся корректным."""
    raw = json.dumps({"score": 300, "summary": None, "issues": "не список"})
    parsed = _parse_evaluation(f"```json\n{raw}\n```")
    assert parsed["score"] == 100.0  # обрезано по максимуму
    assert parsed["summary"] == ""
    assert parsed["issues"] == []
    assert parsed["strengths"] == []


def test_response_without_json_block_returns_none(monkeypatch) -> None:
    """Ответ без JSON-объекта: клиент не падает, а отдаёт None."""
    monkeypatch.setattr(settings, "gigachat_credentials", "basic-key")
    monkeypatch.setattr(settings, "gigachat_access_token", "ready-token")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "без json"}}]})

    client = GigaChatClient(http=httpx.Client(transport=httpx.MockTransport(handler)))
    assert client.evaluate_resume("текст") is None

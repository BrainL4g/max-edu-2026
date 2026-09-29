"""Тесты точки входа бота: токен-гард и обработчик ошибок."""

from __future__ import annotations

import asyncio
import importlib
import logging
from types import SimpleNamespace
from typing import Any

import pytest


def test_main_importable_with_token(monkeypatch) -> None:
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    import main as bot_main

    assert bot_main.TOKEN == "test-token"


def test_main_requires_token(monkeypatch) -> None:
    import dotenv

    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)

    import main as bot_main

    monkeypatch.setenv("MAX_BOT_TOKEN", "reload-token")
    importlib.reload(bot_main)  # гарантируем корректное состояние модуля

    monkeypatch.delenv("MAX_BOT_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        importlib.reload(bot_main)

    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    importlib.reload(bot_main)  # восстанавливаем рабочее состояние


def test_error_handler_logs_exception(monkeypatch) -> None:
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    import main as bot_main

    async def _boom() -> None:
        raise ValueError("boom")

    try:
        asyncio.run(_boom())
    except ValueError as exc:
        exception = exc

    records: list[logging.LogRecord] = []

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Collect()
    logger = logging.getLogger("main")
    logger.addHandler(handler)
    try:
        event = SimpleNamespace(router_id="test_router", exception=exception)
        asyncio.run(bot_main.on_event_error(event))
    finally:
        logger.removeHandler(handler)

    assert records
    assert "boom" in records[0].getMessage()
    assert "test_router" in records[0].getMessage()


def test_routers_registered(monkeypatch) -> None:
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    import main as bot_main

    assert len(bot_main.dp.routers) >= 6


def test_register_commands_sets_start_and_help(monkeypatch) -> None:
    """Кнопки «Старт» и «Помощь»: регистрируем /start и /help."""
    monkeypatch.setenv("MAX_BOT_TOKEN", "test-token")
    import main as bot_main

    class _FakeBot:
        def __init__(self) -> None:
            self.commands: list[Any] = []

        async def set_commands(self, *commands: Any) -> None:
            self.commands = list(commands)

    fake = _FakeBot()
    asyncio.run(bot_main.register_commands(fake))
    assert [getattr(c, "name", None) for c in fake.commands] == ["start", "help"]

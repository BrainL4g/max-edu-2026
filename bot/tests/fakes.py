"""Фейковые события MAX-бота: хендлеры тестируются без сети и API-клиента."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class _FakeUser:
    """Мини-замена maxapi.types.User."""

    def __init__(self, user_id: int, first_name: str) -> None:
        self.user_id = user_id
        self.first_name = first_name


class FakeCallbackEvent:
    """Мини-замена MessageCallback: записывает вызовы edit()."""

    def __init__(
        self, payload: str, user_id: int = 123, first_name: str = "Тест"
    ) -> None:
        self.callback = SimpleNamespace(
            payload=payload, user=_FakeUser(user_id, first_name)
        )
        self.edits: list[tuple[str | None, list[Any] | None]] = []

    async def edit(
        self,
        text: str | None = None,
        attachments: list[Any] | None = None,
        **_kwargs: Any,
    ) -> FakeCallbackEvent:
        self.edits.append((text, attachments))
        return self


class FakeMessageCreatedEvent:
    """Мини-замена MessageCreated: sender + body + answer()."""

    def __init__(
        self, user_id: int = 123, first_name: str = "Тест", text: str = ""
    ) -> None:
        self.answers: list[tuple[str | None, list[Any] | None]] = []
        self.message = SimpleNamespace(
            sender=_FakeUser(user_id, first_name),
            body=SimpleNamespace(text=text),
            answer=self._record_answer,
        )

    async def _record_answer(
        self, text: str | None = None, attachments: list[Any] | None = None, **_: Any
    ) -> None:
        self.answers.append((text, attachments))


class FakeBot:
    """Мини-замена Bot: записывает отправленные сообщения."""

    def __init__(self) -> None:
        self.sent: list[tuple[int, str, list[Any] | None]] = []

    async def send_message(
        self,
        chat_id: int,
        text: str,
        attachments: list[Any] | None = None,
        **_: Any,
    ) -> None:
        self.sent.append((chat_id, text, attachments))


class FakeBotStartedEvent:
    """Мини-замена BotStarted."""

    def __init__(self, user_id: int = 123, first_name: str = "Тест") -> None:
        self.chat_id = user_id
        self.user = _FakeUser(user_id, first_name)
        self.bot = FakeBot()


def buttons_from(attachments: list[Any] | None) -> list[Any]:
    """Достать плоский список кнопок из markup-вложений."""
    out: list[Any] = []
    for item in attachments or []:
        payload = getattr(item, "payload", None)
        if payload is None:
            continue
        for row in getattr(payload, "buttons", []) or []:
            out.extend(row)
    return out

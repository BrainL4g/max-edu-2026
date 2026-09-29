"""Фейковые события MAX-бота: хендлеры тестируются без сети и API-клиента."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


class _FakeUser:
    """Мини-замена maxapi.types.User."""

    def __init__(self, user_id: int, first_name: str) -> None:
        self.user_id = user_id
        self.first_name = first_name


class FakeFileAttachment:
    """Мини-замена maxapi File-вложения (имя файла + ссылка)."""

    def __init__(
        self, filename: str = "resume.pdf", url: str | None = "https://max.ru/files/1"
    ) -> None:
        self.filename = filename
        self.size = 1024
        self.payload = SimpleNamespace(url=url)


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
        self,
        user_id: int = 123,
        first_name: str = "Тест",
        text: str = "",
        attachments: list[Any] | None = None,
        file_bytes: bytes = b"",
    ) -> None:
        self.answers: list[tuple[str | None, list[Any] | None]] = []
        self.bot = FakeBot(download_content=file_bytes)
        self.message = SimpleNamespace(
            sender=_FakeUser(user_id, first_name),
            body=SimpleNamespace(text=text, attachments=attachments or []),
            answer=self._record_answer,
            bot=self.bot,
        )

    async def _record_answer(
        self, text: str | None = None, attachments: list[Any] | None = None, **_: Any
    ) -> None:
        self.answers.append((text, attachments))


class FakeBot:
    """Мини-замена Bot: записывает отправленные сообщения и скачивания."""

    def __init__(
        self, download_content: bytes = b"", download_error: Exception | None = None
    ) -> None:
        self.sent: list[tuple[int, str, list[Any] | None]] = []
        self.downloaded: list[str] = []
        self.download_content = download_content
        self.download_error = download_error

    async def send_message(
        self,
        chat_id: int,
        text: str,
        attachments: list[Any] | None = None,
        **_: Any,
    ) -> None:
        self.sent.append((chat_id, text, attachments))

    async def download_bytes(self, url: str) -> bytes:
        """Заглушка скачивания вложения из MAX."""
        self.downloaded.append(url)
        if self.download_error is not None:
            raise self.download_error
        return self.download_content


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

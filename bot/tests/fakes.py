"""Фейковые события MAX-бота: хендлеры тестируются без сети и API-клиента.

Фейки наследуют реальные типы ``maxapi.types``, поэтому хендлеры принимают их
без ``cast``/``type: ignore``, а mypy проверяет сигнатуры ``edit``/``answer``.
Pydantic-модели создаются в обход валидации через ``_pydantic_shell``: поля
подставляются напрямую, чтобы вместо настоящего тела сообщения можно было
подставить ``SimpleNamespace``.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any

from maxapi.types import (
    BotStarted,
    Callback,
    Message,
    MessageCallback,
    MessageCreated,
    User,
)


def _pydantic_shell(self: Any, **values: Any) -> None:
    """Инициализировать pydantic-модель в обход валидации, с указанными полями.

    Поля, не переданные явно, заполняются ``None``. Это позволяет тестам
    подставлять упрощённые объекты вместо вложенных моделей MAX.
    """
    data: dict[str, Any] = {name: None for name in type(self).model_fields}
    data.update(values)
    shell = type(self).model_construct(**data)
    object.__setattr__(self, "__dict__", shell.__dict__)
    object.__setattr__(self, "__pydantic_fields_set__", set())
    object.__setattr__(self, "__pydantic_extra__", None)
    object.__setattr__(self, "__pydantic_private__", None)


class _FakeUser(User):
    """Мини-замена maxapi.types.User."""

    def __init__(self, user_id: int, first_name: str) -> None:
        object.__setattr__(self, "user_id", user_id)
        object.__setattr__(self, "first_name", first_name)


class FakeFileAttachment:
    """Мини-замена maxapi File-вложения (имя файла + ссылка)."""

    def __init__(
        self, filename: str = "resume.pdf", url: str | None = "https://max.ru/files/1"
    ) -> None:
        self.filename = filename
        self.size = 1024
        self.payload = SimpleNamespace(url=url)


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


class FakeCallbackEvent(MessageCallback):
    """Мини-замена MessageCallback: записывает вызовы edit()."""

    callback: Any
    edits: list[tuple[str, list[Any] | None]]

    def __init__(
        self, payload: str, user_id: int = 123, first_name: str = "Тест"
    ) -> None:
        _pydantic_shell(
            self,
            callback=Callback.model_construct(
                timestamp=0,
                callback_id="cb-1",
                payload=payload,
                user=_FakeUser(user_id, first_name),
            ),
        )
        object.__setattr__(self, "edits", [])

    async def edit(
        self,
        text: str | None = None,
        attachments: Sequence[Any] | None = None,
        link: Any = None,
        format: Any = None,
        *,
        notification: str | None = None,
        notify: bool = True,
        raise_if_not_exists: bool = True,
    ) -> Any:
        self.edits.append((text or "", list(attachments) if attachments else None))
        return None


class FakeMessage(Message):
    """Мини-замена Message: записывает вызовы answer() вместо отправки в MAX."""

    sender: Any
    body: Any
    bot: Any
    answers: list[tuple[str, list[Any] | None]]

    def __init__(
        self,
        user_id: int = 123,
        first_name: str = "Тест",
        text: str = "",
        attachments: list[Any] | None = None,
        file_bytes: bytes = b"",
        bot: FakeBot | None = None,
    ) -> None:
        _pydantic_shell(
            self,
            sender=_FakeUser(user_id, first_name),
            body=SimpleNamespace(text=text, attachments=attachments or []),
            bot=bot or FakeBot(download_content=file_bytes),
        )
        object.__setattr__(self, "answers", [])

    async def answer(
        self,
        text: str | None = None,
        attachments: list[Any] | None = None,
        link: Any = None,
        format: Any = None,
        parse_mode: Any = None,
        *,
        notify: bool | None = None,
        disable_link_preview: bool | None = None,
        sleep_after_input_media: bool | None = True,
    ) -> Any:
        self.answers.append((text or "", list(attachments) if attachments else None))
        return None


class FakeMessageCreatedEvent(MessageCreated):
    """Мини-замена MessageCreated: sender + body + answer()."""

    message: FakeMessage
    bot: FakeBot

    def __init__(
        self,
        user_id: int = 123,
        first_name: str = "Тест",
        text: str = "",
        attachments: list[Any] | None = None,
        file_bytes: bytes = b"",
    ) -> None:
        bot = FakeBot(download_content=file_bytes)
        _pydantic_shell(
            self,
            bot=bot,
            message=FakeMessage(
                user_id, first_name, text, attachments, file_bytes, bot=bot
            ),
        )

    @property
    def answers(self) -> list[tuple[str, list[Any] | None]]:
        """Ответы, записанные хендлерами (делегирует ``message.answer``)."""
        return self.message.answers


class FakeBotStartedEvent(BotStarted):
    """Мини-замена BotStarted."""

    user: Any
    bot: Any

    def __init__(self, user_id: int = 123, first_name: str = "Тест") -> None:
        bot = FakeBot()
        _pydantic_shell(
            self, chat_id=user_id, user=_FakeUser(user_id, first_name), bot=bot
        )
        object.__setattr__(self, "sent", bot.sent)


def buttons_from(attachments: Sequence[Any] | None) -> list[Any]:
    """Достать плоский список кнопок из markup-вложений."""
    out: list[Any] = []
    for item in attachments or []:
        payload = getattr(item, "payload", None)
        if payload is None:
            continue
        for row in getattr(payload, "buttons", []) or []:
            out.extend(row)
    return out

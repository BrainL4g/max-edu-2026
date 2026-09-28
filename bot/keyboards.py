"""Inline-клавиатуры бота."""

from __future__ import annotations

from typing import Any

from maxapi.types import CallbackButton, LinkButton
from maxapi.types.attachments import AttachmentButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

TEXT_LIMIT = 40


def _clip(text: str) -> str:
    """Обрезать текст кнопки до видимой ширины, добавляя многоточие."""
    if len(text) <= TEXT_LIMIT:
        return text
    return text[: TEXT_LIMIT - 1] + "…"


def main_menu() -> AttachmentButton:
    """Главное меню."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="🎯 Цель", payload="goal:show"))
    builder.row(CallbackButton(text="🧠 Диагностика", payload="as:start"))
    builder.row(
        CallbackButton(text="🎮 Миссия", payload="ms:next"),
        CallbackButton(text="📊 Skill Map", payload="sm:show"),
    )
    builder.row(
        CallbackButton(text="📚 Курсы", payload="cr:rec"),
        CallbackButton(text="💼 Стажировки", payload="in:rec"),
    )
    builder.row(CallbackButton(text="📄 Резюме", payload="rs:start"))
    return builder.as_markup()


def roles_kb(roles: list[dict[str, Any]]) -> AttachmentButton:
    """Кнопки выбора целевой роли: payload = "goal:pick:{id}"."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for role in roles:
        builder.row(
            CallbackButton(text=role["name"], payload=f"goal:pick:{role['id']}")
        )
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


_OPTION_NUMBERS = ("①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩")


def _option_number(index: int) -> str:
    """Бейдж-номер варианта: ① ② … ⑩, дальше — обычные цифры."""
    if 0 <= index < len(_OPTION_NUMBERS):
        return _OPTION_NUMBERS[index]
    return str(index + 1)


def options_kb(
    prefix: str, options: list[tuple[int, str]], back: bool = True
) -> AttachmentButton:
    """Кнопки-бейджи вариантов по два в ряд: payload = "{prefix}:{id}".

    Полный текст вариантов выводится в сообщении (texts.numbered_options),
    номер на кнопке — позиция варианта (1..N).
    """
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for start in range(0, len(options), 2):
        builder.row(
            *(
                CallbackButton(
                    text=_option_number(index),
                    payload=f"{prefix}:{option_id}",
                )
                for index, (option_id, _) in enumerate(
                    options[start : start + 2], start=start
                )
            )
        )
    if back:
        builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def after_mission_kb() -> AttachmentButton:
    """Кнопки после ответа на миссию."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="➡️ Следующая миссия", payload="ms:next"))
    builder.row(
        CallbackButton(text="📊 Skill Map", payload="sm:show"),
        CallbackButton(text="🏠 Меню", payload="menu:main"),
    )
    return builder.as_markup()


def menu_with_links(links: list[tuple[str, str]]) -> AttachmentButton:
    """Кнопки-ссылки + кнопка «Меню». links — пары (текст, url)."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for title, url in links:
        builder.row(LinkButton(text=_clip(title), url=url))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()

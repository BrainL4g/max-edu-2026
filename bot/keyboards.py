"""Inline-клавиатуры бота."""

from __future__ import annotations

from maxapi.types import CallbackButton, LinkButton
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

TEXT_LIMIT = 64


def main_menu():
    """Главное меню."""
    builder = InlineKeyboardBuilder()
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


def options_kb(
    prefix: str, options: list[tuple[int, str]], back: bool = True
):
    """Варианты ответа по одному на строку: payload = "{prefix}:{id}".

    options — список пар (id/индекс, текст).
    """
    builder = InlineKeyboardBuilder()
    for option_id, text in options:
        builder.row(
            CallbackButton(text=text[:TEXT_LIMIT], payload=f"{prefix}:{option_id}")
        )
    if back:
        builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def after_mission_kb():
    """Кнопки после ответа на миссию."""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="➡️ Следующая миссия", payload="ms:next"))
    builder.row(
        CallbackButton(text="📊 Skill Map", payload="sm:show"),
        CallbackButton(text="🏠 Меню", payload="menu:main"),
    )
    return builder.as_markup()


def menu_with_links(links: list[tuple[str, str]]):
    """Кнопки-ссылки + кнопка «Меню». links — пары (текст, url)."""
    builder = InlineKeyboardBuilder()
    for title, url in links:
        builder.row(LinkButton(text=title[:TEXT_LIMIT], url=url))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()
"""Inline-клавиатуры бота."""

from __future__ import annotations

from collections.abc import Callable
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
    builder.row(CallbackButton(text="🎮 Миссия", payload="ms:next"))
    builder.row(CallbackButton(text="📊 Skill Map", payload="sm:show"))
    builder.row(
        CallbackButton(text="📚 Курсы", payload="cr:rec"),
        CallbackButton(text="💼 Стажировки", payload="in:rec"),
    )
    builder.row(CallbackButton(text="📄 Резюме", payload="rs:start"))
    builder.row(CallbackButton(text="ℹ️ Инструкция", payload="help:show"))
    return builder.as_markup()


def resume_kb() -> AttachmentButton:
    """Экран «Резюме»: возврат в главное меню."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="⬅️ Назад", payload="menu:main"))
    return builder.as_markup()


def resume_report_kb() -> AttachmentButton:
    """Кнопки после отчёта по резюме."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="📄 Другое резюме", payload="rs:start"))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
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


def goal_required_kb() -> AttachmentButton:
    """Кнопки экрана «сначала выбери цель» (диагностика/миссии без цели)."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="🎯 Выбрать цель", payload="goal:show"))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def missions_done_kb() -> AttachmentButton:
    """Кнопки после прохождения всех миссий по цели."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(
        CallbackButton(text="📚 Курсы", payload="cr:rec"),
        CallbackButton(text="📊 Skill Map", payload="sm:show"),
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


def menu_with_links(
    links: list[tuple[str, str]], back_payload: str | None = None
) -> AttachmentButton:
    """Кнопки-ссылки + необязательная кнопка «Назад» и «Меню».

    links — пары (текст, url); back_payload — payload кнопки возврата к списку.
    """
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for title, url in links:
        builder.row(LinkButton(text=_clip(title), url=url))
    if back_payload:
        builder.row(CallbackButton(text="⬅️ Направления", payload=back_payload))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def internship_directions_kb(directions: list[str]) -> AttachmentButton:
    """Кнопки направлений стажировок по два в ряд: payload = "in:dir:{direction}"."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="🌐 Все направления", payload="in:dir:any"))
    for start in range(0, len(directions), 2):
        builder.row(
            *(
                CallbackButton(text=_clip(direction), payload=f"in:dir:{direction}")
                for direction in directions[start : start + 2]
            )
        )
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def _nav_row(
    builder: InlineKeyboardBuilder,
    page: int,
    total_pages: int,
    payload_fn: Callable[[int], str],
) -> None:
    """Добавить ряд навигации «Предыдущая/Следующая», если страниц больше одной."""
    nav_buttons: list[CallbackButton] = []
    if page > 0:
        prev_label = (
            "⬅️ Предыдущая" if page < total_pages - 1 else "⬅️ Предыдущая страница"
        )
        nav_buttons.append(
            CallbackButton(text=prev_label, payload=payload_fn(page - 1))
        )
    if page < total_pages - 1:
        next_label = "Следующая ➡️" if page > 0 else "Следующая страница ➡️"
        nav_buttons.append(
            CallbackButton(text=next_label, payload=payload_fn(page + 1))
        )
    if nav_buttons:
        builder.row(*nav_buttons)


def courses_pagination_kb(
    courses: list[dict[str, Any]],
    page: int,
    total_pages: int,
) -> AttachmentButton:
    """Кнопки курсов со ссылками по названию, пагинация и «Меню»."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for course in courses:
        url = course.get("url")
        if url:
            title = course.get("title") or course.get("platform") or "Курс"
            builder.row(LinkButton(text=_clip(title), url=url))

    _nav_row(builder, page, total_pages, lambda target: f"cr:page:{target}")
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def internships_pagination_kb(
    links: list[tuple[str, str]],
    direction: str | None,
    page: int,
    total_pages: int,
) -> AttachmentButton:
    """Кнопки-ссылки стажировок страницы, пагинация, «Направления» и «Меню»."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    for title, url in links:
        builder.row(LinkButton(text=_clip(title), url=url))

    direction_key = direction or "any"
    _nav_row(
        builder,
        page,
        total_pages,
        lambda target: f"in:dir:{direction_key}:{target}",
    )

    builder.row(CallbackButton(text="⬅️ Направления", payload="in:rec"))
    builder.row(CallbackButton(text="🏠 Меню", payload="menu:main"))
    return builder.as_markup()


def resume_cancel_kb() -> AttachmentButton:
    """Кнопка «Отмена» во время ожидания текста резюме."""
    builder = InlineKeyboardBuilder()  # type: ignore[no-untyped-call]
    builder.row(CallbackButton(text="❌ Отмена", payload="rs:cancel"))
    return builder.as_markup()

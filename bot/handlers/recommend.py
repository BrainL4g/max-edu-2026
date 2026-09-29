"""Рекомендации курсов и стажировок."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()

CARD_LIMIT = 5
PAGE_SIZE = 5


def _cards_links(
    items: list[dict[str, Any]],
    card_fn: Callable[[dict[str, Any], int], str],
    label: str,
) -> tuple[str, list[tuple[str, str]]]:
    cards = [card_fn(item, index + 1) for index, item in enumerate(items[:CARD_LIMIT])]
    links = [
        (f"{label} {index + 1}", item["url"])
        for index, item in enumerate(items[:CARD_LIMIT])
        if item.get("url")
    ]
    return "\n".join(cards), links


@router.message_callback(F.callback.payload == "cr:rec")
@router.message_callback(F.callback.payload.startswith("cr:page:"))
async def recommended_courses(event: MessageCallback) -> None:
    """Рекомендации курсов по пробелам в навыках с пагинацией по 5 элементов."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    courses = await api.rec_courses(user_id)
    if not courses:
        await event.edit(
            "Рекомендаций по курсам пока нет 🤷", attachments=[kbs.main_menu()]
        )
        return

    payload = getattr(getattr(event, "callback", None), "payload", "") or ""
    page = 0
    if payload.startswith("cr:page:"):
        try:
            page = int(payload.split(":", 2)[2])
        except (IndexError, ValueError):
            page = 0

    total_items = len(courses)
    total_pages = max(1, (total_items + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * PAGE_SIZE
    page_courses = courses[start_idx : start_idx + PAGE_SIZE]

    cards = [
        texts.course_card(course, start_idx + index + 1)
        for index, course in enumerate(page_courses)
    ]
    cards_text = "\n".join(cards)

    header = (
        f"📚 Рекомендуемые курсы (страница {page + 1} из {total_pages}):"
        if total_pages > 1
        else "📚 Рекомендуемые курсы:"
    )
    text = f"{header}\n\n{cards_text}"
    await event.edit(
        text,
        attachments=[
            kbs.courses_pagination_kb(page_courses, page=page, total_pages=total_pages)
        ],
    )


@router.message_callback(F.callback.payload == "in:rec")
async def recommended_internships(event: MessageCallback) -> None:
    """Рекомендации стажировок."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    internships = await api.rec_internships(user_id)
    if not internships:
        await event.edit(
            "Рекомендаций по стажировкам пока нет 🤷",
            attachments=[kbs.main_menu()],
        )
        return

    cards, links = _cards_links(
        internships, texts.internship_card, "Открыть стажировку"
    )
    text = f"💼 Рекомендуемые стажировки:\n\n{cards}"
    await event.edit(text, attachments=[kbs.menu_with_links(links)])

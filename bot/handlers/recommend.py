"""Рекомендации курсов и стажировок."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()

CARD_LIMIT = 5


def _cards_links(items: list[dict], card_fn, label: str) -> tuple[str, list]:
    cards = [
        card_fn(item, index + 1) for index, item in enumerate(items[:CARD_LIMIT])
    ]
    links = [
        (f"{label} {index + 1}", item["url"])
        for index, item in enumerate(items[:CARD_LIMIT])
        if item.get("url")
    ]
    return "\n".join(cards), links


@router.message_callback(F.callback.payload == "cr:rec")
async def recommended_courses(event: MessageCallback) -> None:
    """Рекомендации курсов по пробелам в навыках."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    courses = await api.rec_courses(user_id)
    if not courses:
        await event.edit(
            "Рекомендаций по курсам пока нет 🤷", attachments=[kbs.main_menu()]
        )
        return

    cards, links = _cards_links(courses, texts.course_card, "Открыть курс")
    text = f"📚 Рекомендуемые курсы:\n\n{cards}"
    await event.edit(text, attachments=[kbs.menu_with_links(links)])


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
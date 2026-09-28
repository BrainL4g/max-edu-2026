"""Skill Map пользователя: уровни и прогресс по навыкам."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()


@router.message_callback(F.callback.payload == "sm:show")
async def show_skill_map(event: MessageCallback) -> None:
    """Показать текущие уровни навыков."""
    await event.ack()
    user_id = await sessions.ensure_user_from(event.callback.user)
    items = await api.skill_map(user_id)
    await event.message.answer(
        texts.skill_map_text(items), attachments=[kbs.main_menu()]
    )
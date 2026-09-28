"""Целевая роль: выбор роли и gap-анализ «чего не хватает»."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()


@router.message_callback(F.callback.payload == "goal:show")
async def goal_show(event: MessageCallback) -> None:
    """Показать список целевых ролей для выбора."""
    roles = await api.list_roles()
    if not roles:
        await event.edit("Ролей пока нет 🤷", attachments=[kbs.main_menu()])
        return
    await event.edit(texts.roles_question_text(), attachments=[kbs.roles_kb(roles)])


@router.message_callback(F.callback.payload.startswith("goal:pick:"))
async def goal_pick(event: MessageCallback) -> None:
    """Сохранить выбранную роль и показать gap-анализ."""
    payload = event.callback.payload
    if payload is None or not payload.startswith("goal:pick:"):
        return
    user_id = await sessions.ensure_user_from(event.callback.user)
    role_id = int(payload.rsplit(":", 1)[1])
    await api.set_goal(user_id, role_id)
    analysis = await api.gap_analysis(user_id)
    await event.edit(
        texts.gap_analysis_text(analysis),
        attachments=[kbs.main_menu()],
    )

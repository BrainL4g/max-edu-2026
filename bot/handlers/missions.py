"""Игровые миссии: следующее задание и проверка ответа."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()


@router.message_callback(F.callback.payload == "ms:next")
async def mission_next(event: MessageCallback) -> None:
    """Следующая миссия для пользователя."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    mission = await api.next_mission(user_id)
    if not mission:
        await event.edit("Все миссии пройдены! 🏆", attachments=[kbs.main_menu()])
        return

    text = (
        f"🎮 {mission['skill_name']} · {mission['difficulty']} · "
        f"+{mission['reward_xp']} XP\n\n{mission['scenario']}\n\n"
        f"{texts.numbered_options([option['text'] for option in mission['options']])}"
    )
    options = [(option["id"], option["text"]) for option in mission["options"]]
    kb = kbs.options_kb(f"ms:ans:{mission['id']}", options)
    await event.edit(text, attachments=[kb])


@router.message_callback(F.callback.payload.startswith("ms:ans:"))
async def mission_answer(event: MessageCallback) -> None:
    """Проверка ответа: XP, уровень навыка, объяснение."""
    payload = event.callback.payload
    if payload is None or not payload.startswith("ms:ans:"):
        return
    _, _, mission_id, option_id = payload.split(":")
    user_id = await sessions.ensure_user_from(event.callback.user)
    result = await api.answer_mission(user_id, int(mission_id), int(option_id))

    head = "✅ Верно!" if result["is_correct"] else "❌ Не совсем"
    skill_name = result.get("skill_name") or "—"
    text = (
        f"{head} +{result['xp_earned']} XP\n"
        f"Навык «{skill_name}»: уровень {result.get('skill_level_after')}"
    )
    if result.get("explanation"):
        text += f"\n\n{result['explanation']}"
    await event.edit(text, attachments=[kbs.after_mission_kb()])

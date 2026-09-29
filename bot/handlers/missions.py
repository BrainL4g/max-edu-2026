"""Игровые миссии: следующее задание и проверка ответа."""

from __future__ import annotations

from typing import Any

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()


def _display_order(mission: dict[str, Any]) -> list[dict[str, Any]]:
    """Порядок вариантов для показа: детерминированный сдвиг, чтобы верный
    ответ не всегда стоял первым. Ответ идёт по option_id, поэтому сдвиг
    не ломает проверку."""
    options = mission.get("options") or []
    if len(options) < 2:
        return options
    offset = mission["id"] % (len(options) - 1) + 1
    return options[offset:] + options[:offset]


@router.message_callback(F.callback.payload == "ms:next")
async def mission_next(event: MessageCallback) -> None:
    """Следующая миссия строго по цели пользователя."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    data = await api.next_mission(user_id)

    status = data.get("status")
    done, total = data.get("done", 0), data.get("total", 0)
    if status == "no_goal":
        await event.edit(texts.need_goal_text(), attachments=[kbs.goal_required_kb()])
        return
    if status == "all_done" or not data.get("mission"):
        await event.edit(
            texts.missions_done_text(done, total), attachments=[kbs.missions_done_kb()]
        )
        return

    mission = data["mission"]
    options = _display_order(mission)
    text = (
        f"🎮 Миссия {done + 1}/{total} по цели · {mission['skill_name']} · "
        f"{mission['difficulty']} · +{mission['reward_xp']} XP\n\n"
        f"{mission['scenario']}\n\n"
        f"{texts.numbered_options([option['text'] for option in options])}"
    )
    kb = kbs.options_kb(
        f"ms:ans:{mission['id']}",
        [(option["id"], option["text"]) for option in options],
    )
    await event.edit(text, attachments=[kb])


@router.message_callback(F.callback.payload.startswith("ms:ans:"))
async def mission_answer(event: MessageCallback) -> None:
    """Проверка ответа: XP, уровень навыка, правильный ответ, объяснение."""
    payload = event.callback.payload
    if payload is None or not payload.startswith("ms:ans:"):
        return
    _, _, mission_id, option_id = payload.split(":")
    user_id = await sessions.ensure_user_from(event.callback.user)
    result = await api.answer_mission(user_id, int(mission_id), int(option_id))

    already = bool(result.get("already_solved"))
    if already:
        head = "🔁 Уже решено"
    else:
        head = "✅ Верно!" if result["is_correct"] else "❌ Не совсем"

    lines = [head]
    if already:
        lines.append("Повторный ответ XP не приносит.")
    else:
        xp = result.get("xp_earned") or 0
        if xp > 0:
            lines.append(f"+{xp} XP")
        if not result["is_correct"] and result.get("correct_option_text"):
            lines.append(f"✅ Правильный ответ: {result['correct_option_text']}")

    skill_name = result.get("skill_name") or "—"
    lines.append(f"Навык «{skill_name}»: уровень {result.get('skill_level_after')}")

    level_before = result.get("skill_level_before")
    level_after = result.get("skill_level_after")
    if (
        not already
        and level_before is not None
        and level_after is not None
        and level_after > level_before
    ):
        lines.append(f"🔺 {level_before} → {level_after}")

    if result.get("explanation"):
        lines.append(f"\n{result['explanation']}")
    await event.edit("\n".join(lines), attachments=[kbs.after_mission_kb()])

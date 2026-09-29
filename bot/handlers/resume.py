"""Резюме: старт и отмена режима кнопками; текст принимает fallback-хендлер."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import keyboards as kbs
import sessions

router = Router()

RESUME_PROMPT = "Пришли текст резюме одним сообщением 📄"


@router.message_callback(F.callback.payload == "rs:start")
async def ask_resume(event: MessageCallback) -> None:
    """Пользователь нажал «Резюме» — ждём текст следующим сообщением."""
    item = sessions.session_for(event.callback.user.user_id)
    item["resume"] = True
    await event.edit(RESUME_PROMPT, attachments=[kbs.resume_cancel_kb()])


@router.message_callback(F.callback.payload == "rs:cancel")
async def cancel_resume(event: MessageCallback) -> None:
    """Отмена режима резюме — возврат в главное меню."""
    item = sessions.session_for(event.callback.user.user_id)
    item["resume"] = False
    await event.edit("Отменил 🙌", attachments=[kbs.main_menu()])

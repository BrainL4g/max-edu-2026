"""Резюме: приём текста и отчёт анализа."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback, MessageCreated

import api
import keyboards as kbs
import sessions
import texts

router = Router()


@router.message_callback(F.callback.payload == "rs:start")
async def ask_resume(event: MessageCallback) -> None:
    """Пользователь нажал «Резюме» — ждём текст следующим сообщением."""
    item = sessions.session_for(event.callback.user.user_id)
    item["resume"] = True
    await event.edit("Пришли текст резюме одним сообщением 📄", attachments=[])


@router.message_created(F.message.body.text)
async def capture_resume_text(event: MessageCreated) -> None:
    """Ловим текстовое сообщение: если ждали резюме — анализируем."""
    sender = event.message.sender
    body = event.message.body
    if sender is None or body is None or not body.text:
        return
    item = sessions.session_for(sender.user_id)
    if not item["resume"]:
        return
    item["resume"] = False

    user_id = item["uid"] or await sessions.ensure_user(
        sender.user_id, sender.first_name or ""
    )
    upload = await api.upload_resume(user_id, body.text)
    analysis = await api.analyze_resume(upload["id"])
    await event.message.answer(
        texts.resume_report(analysis), attachments=[kbs.main_menu()]
    )

"""Свободный текст и неизвестные команды: приём резюме либо подсказка с меню.

Единый обработчик текстовых сообщений. В режиме резюме (флаг сессии "resume")
текст уходит в API как резюме либо отменяет режим по ключевому слову; в остальных
случаях отвечаем подсказкой с главным меню, чтобы свободный текст не терялся.
"""

from __future__ import annotations

from typing import Any

from maxapi import F, Router
from maxapi.types import MessageCreated

import api
import keyboards as kbs
import sessions
import texts

router = Router()

CANCEL_WORDS = frozenset({"отмена", "отменить", "стоп", "cancel", "/cancel"})


@router.message_created(F.message.body.text)
async def on_text(event: MessageCreated) -> None:
    """Обработка любого текстового сообщения: резюме либо меню-подсказка."""
    sender = event.message.sender
    body = event.message.body
    if sender is None or body is None or not body.text:
        return
    item = sessions.session_for(sender.user_id)
    if item["resume"]:
        await _capture_resume(
            event, body.text, sender.user_id, sender.first_name or "", item
        )
        return
    await event.message.answer(texts.fallback_text(), attachments=[kbs.main_menu()])


async def _capture_resume(
    event: MessageCreated,
    text: str,
    max_user_id: int,
    name: str,
    item: dict[str, Any],
) -> None:
    """Завершить режим резюме: отмена ключевым словом или отправить текст в API."""
    if text.strip().lower() in CANCEL_WORDS:
        item["resume"] = False
        await event.message.answer(
            "Отменил 🙌 Возвращаемся в меню:", attachments=[kbs.main_menu()]
        )
        return
    item["resume"] = False
    user_id = item["uid"] or await sessions.ensure_user(max_user_id, name)
    upload = await api.upload_resume(int(user_id), text)
    analysis = await api.analyze_resume(upload["id"])
    await event.message.answer(
        texts.resume_report(analysis), attachments=[kbs.main_menu()]
    )

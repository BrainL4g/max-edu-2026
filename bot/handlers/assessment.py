"""Диагностика: пошаговые вопросы, отправка ответов, итоговый Skill Map."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions

router = Router()


@router.message_callback(F.callback.payload == "as:start")
async def start_assessment(event: MessageCallback) -> None:
    """Начало диагностики: сброс ответов и первый вопрос."""
    await event.ack()
    await sessions.ensure_user_from(event.callback.user)
    item = sessions.session_for(event.callback.user.user_id)
    item["answers"] = []
    await _ask(event, 0)


async def _ask(event: MessageCallback, index: int) -> None:
    """Показать вопрос под номером index (0-based)."""
    questions = await api.assessment_questions()
    question = questions[index]
    kb = kbs.options_kb(
        f"asq:{question['id']}", list(enumerate(question["options"]))
    )
    await event.message.answer(
        f"Вопрос {index + 1}/{len(questions)}\n{question['text']}",
        attachments=[kb],
    )


@router.message_callback(F.callback.payload.startswith("asq:"))
async def assessment_answer(event: MessageCallback) -> None:
    """Сохранение ответа и переход к следующему вопросу либо итог."""
    await event.ack()
    _, question_id, option_index = event.callback.payload.split(":")
    item = sessions.session_for(event.callback.user.user_id)
    item["answers"].append(
        {"question_id": int(question_id), "option_index": int(option_index)}
    )

    questions = await api.assessment_questions()
    if len(item["answers"]) < len(questions):
        await _ask(event, len(item["answers"]))
        return

    result = await api.submit_assessment(item["uid"], item["answers"])
    item["answers"] = []
    text = f"Диагностика завершена 🎉\n\n{result.get('summary') or ''}".strip()
    await event.message.answer(text, attachments=[kbs.main_menu()])
"""Диагностика: пошаговые вопросы, отправка ответов, итоговый Skill Map."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import MessageCallback

import api
import keyboards as kbs
import sessions
import texts

router = Router()


@router.message_callback(F.callback.payload == "as:start")
async def start_assessment(event: MessageCallback) -> None:
    """Начало диагностики: сброс ответов и первый вопрос (только с целью)."""
    user_id = await sessions.ensure_user_from(event.callback.user)
    profile = await api.get_profile(user_id)
    if profile.get("target_role_id") is None:
        await event.edit(texts.need_goal_text(), attachments=[kbs.goal_required_kb()])
        return
    item = sessions.session_for(event.callback.user.user_id)
    item["answers"] = []
    await _ask(event, 0)


async def _ask(event: MessageCallback, index: int) -> None:
    """Показать вопрос под номером index (0-based).

    В заголовке подсказывается навык, который оценивает вопрос.
    """
    item = sessions.session_for(event.callback.user.user_id)
    questions = await api.assessment_questions(item["uid"])
    question = questions[index]
    options = question["options"]
    kb = kbs.options_kb(f"asq:{question['id']}", list(enumerate(options)))
    skill = question.get("skill")
    header = f"Вопрос {index + 1}/{len(questions)}"
    if skill:
        header = f"{header}\n📌 Навык: {skill}"
    body = (
        f"🧠 Диагностика\n{header}\n\n"
        f"{question['text']}\n\n"
        f"{texts.numbered_options(options)}"
    )
    await event.edit(body, attachments=[kb])


@router.message_callback(F.callback.payload.startswith("asq:"))
async def assessment_answer(event: MessageCallback) -> None:
    """Сохранение ответа и переход к следующему вопросу либо итог."""
    payload = event.callback.payload
    if payload is None or not payload.startswith("asq:"):
        return
    _, question_id, option_index = payload.split(":")
    item = sessions.session_for(event.callback.user.user_id)
    item["answers"].append(
        {"question_id": int(question_id), "option_index": int(option_index)}
    )

    questions = await api.assessment_questions(item["uid"])
    if len(item["answers"]) < len(questions):
        await _ask(event, len(item["answers"]))
        return

    result = await api.submit_assessment(item["uid"], item["answers"])
    item["answers"] = []
    text = f"Диагностика завершена 🎉\n\n{result.get('summary') or ''}".strip()
    await event.edit(text, attachments=[kbs.main_menu()])

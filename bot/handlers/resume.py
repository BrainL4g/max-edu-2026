"""Резюме: приём файла или текста и отчёт анализа (в т.ч. оценка GigaChat)."""

from __future__ import annotations

import logging
from typing import Any

from maxapi import F, Router
from maxapi.types import MessageCallback, MessageCreated

import api
import keyboards as kbs
import sessions
import texts

logger = logging.getLogger(__name__)

router = Router()

FILE_ANSWER = "сервис анализа вернул ошибку"
BAD_FORMAT_ANSWER = "формат не поддерживается, нужен PDF, DOCX или TXT"


@router.message_callback(F.callback.payload == "rs:start")
async def ask_resume(event: MessageCallback) -> None:
    """Пользователь нажал «Резюме» — ждём файл или текст следующим сообщением."""
    item = sessions.session_for(event.callback.user.user_id)
    item["resume"] = True
    await event.edit(texts.resume_prompt_text(), attachments=[kbs.resume_kb()])


def _first_file(attachments: list[Any] | None) -> Any | None:
    """Первое файловое вложение сообщения (PDF, DOCX, TXT)."""
    for attachment in attachments or []:
        if getattr(attachment, "filename", None):
            return attachment
    return None


def _attachment_url(attachment: Any) -> str | None:
    """URL для скачивания вложения (может отсутствовать)."""
    url = getattr(getattr(attachment, "payload", None), "url", None)
    return url if isinstance(url, str) and url else None


async def _fail(event: MessageCreated, reason: str) -> None:
    """Понятная ошибка приёма резюме + кнопка возврата."""
    await event.message.answer(
        texts.resume_file_error_text(reason), attachments=[kbs.resume_kb()]
    )


@router.message_created(F.message.body.attachments)
async def capture_resume_file(event: MessageCreated) -> None:
    """Ловим файл резюме: скачиваем из MAX, отправляем на анализ, показываем отчёт."""
    sender = event.message.sender
    body = event.message.body
    if sender is None or body is None:
        return
    item = sessions.session_for(sender.user_id)
    if not item["resume"]:
        return
    item["resume"] = False

    attachment = _first_file(body.attachments)
    bot = event.message.bot
    if attachment is None or bot is None:
        await _fail(event, "в сообщении нет файла с резюме")
        return
    url = _attachment_url(attachment)
    if url is None:
        await _fail(event, "у файла нет ссылки на скачивание")
        return

    filename = getattr(attachment, "filename", None) or "resume.txt"
    try:
        content = await bot.download_bytes(url)
        user_id = item["uid"] or await sessions.ensure_user(
            sender.user_id, sender.first_name or ""
        )
        upload = await api.upload_resume_file(user_id, filename, content)
        analysis = await api.analyze_resume(upload["id"])
    except api.ApiError as exc:
        logger.warning("API не принял резюме: %s", exc)
        await _fail(event, BAD_FORMAT_ANSWER if exc.status_code == 422 else FILE_ANSWER)
        return
    except Exception as exc:  # noqa: BLE001 - ошибка скачивания файла из MAX
        logger.warning("Не удалось скачать файл резюме: %s", exc)
        await _fail(event, "файл не удалось скачать")
        return

    await event.message.answer(
        texts.resume_report(analysis), attachments=[kbs.resume_report_kb()]
    )


@router.message_created(F.message.body.text)
async def capture_resume_text(event: MessageCreated) -> None:
    """Ловим текстовое сообщение: если ждали резюме — анализируем."""
    sender = event.message.sender
    body = event.message.body
    if sender is None or body is None or not body.text:
        return
    if body.attachments:
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
        texts.resume_report(analysis), attachments=[kbs.resume_report_kb()]
    )

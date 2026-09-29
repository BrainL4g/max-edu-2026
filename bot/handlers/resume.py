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
    """Кнопка «Резюме»: сначала согласие на обработку ПД, потом приём резюме.

    Без явного согласия (152-ФЗ ст. 9) резюме не принимается: текст с
    телефоном, почтой и историей работы — это персональные данные.
    """
    item = sessions.session_for(event.callback.user.user_id)
    if not item["consent"]:
        await event.edit(
            texts.resume_consent_text(), attachments=[kbs.resume_consent_kb()]
        )
        return
    item["resume"] = True
    await event.edit(texts.resume_prompt_text(), attachments=[kbs.resume_prompt_kb()])


@router.message_callback(F.callback.payload == "rs:consent:yes")
async def accept_consent(event: MessageCallback) -> None:
    """Пользователь согласился: фиксируем согласие и просим резюме.

    Согласие пишется в API до отправки резюме. Если запрос не прошёл,
    резюме не принимаем — обработка без зафиксированного согласия
    недопустима.
    """
    user = event.callback.user
    item = sessions.session_for(user.user_id)
    item["resume"] = False
    try:
        user_id = item["uid"] or await sessions.ensure_user_from(user)
        await api.give_consent(user_id)
    except api.ApiError as exc:
        logger.warning("Не удалось зафиксировать согласие: %s", exc)
        await event.edit(texts.consent_error_text(), attachments=[kbs.resume_kb()])
        return
    item["consent"] = True
    item["resume"] = True
    await event.edit(texts.resume_prompt_text(), attachments=[kbs.resume_prompt_kb()])


@router.message_callback(F.callback.payload == "rs:consent:no")
async def decline_consent(event: MessageCallback) -> None:
    """Пользователь отказался: резюме не отправляем и не обрабатываем."""
    item = sessions.session_for(event.callback.user.user_id)
    item["consent"] = False
    item["resume"] = False
    await event.edit(
        texts.resume_consent_declined_text(), attachments=[kbs.resume_consent_kb()]
    )


@router.message_callback(F.callback.payload == "rs:policy")
async def show_policy(event: MessageCallback) -> None:
    """Текст политики обработки персональных данных."""
    await event.edit(texts.privacy_policy_text(), attachments=[kbs.resume_consent_kb()])


@router.message_callback(F.callback.payload == "rs:consent:revoke")
async def revoke_consent(event: MessageCallback) -> None:
    """Отзыв согласия (152-ФЗ ст. 9, п. 6): резюме больше не принимаем."""
    item = sessions.session_for(event.callback.user.user_id)
    item["consent"] = False
    item["resume"] = False
    if item["uid"]:
        try:
            await api.revoke_consent(item["uid"])
        except api.ApiError as exc:
            logger.warning("Не удалось отозвать согласие в API: %s", exc)
    await event.edit(texts.consent_revoked_text(), attachments=[kbs.main_menu()])


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
    if not item["resume"] or not item["consent"]:
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
    if not item["resume"] or not item["consent"]:
        return
    item["resume"] = False

    user_id = item["uid"] or await sessions.ensure_user_from(sender)
    upload = await api.upload_resume(user_id, body.text)
    analysis = await api.analyze_resume(upload["id"])
    await event.message.answer(
        texts.resume_report(analysis), attachments=[kbs.resume_report_kb()]
    )

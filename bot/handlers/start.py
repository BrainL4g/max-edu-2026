"""Старт бота: приветствие, /start, главное меню."""

from __future__ import annotations

from maxapi import F, Router
from maxapi.types import BotStarted, Command, MessageCallback, MessageCreated

import keyboards as kbs
import sessions

router = Router()


@router.bot_started()
async def on_bot_started(event: BotStarted) -> None:
    """Бот добавлен/запущен пользователем."""
    bot = event.bot
    if bot is None:
        return
    first_name = event.user.first_name or "друг"
    await bot.send_message(
        chat_id=event.chat_id,
        text=f"Привет, {first_name}! Я SkillQuest 🎮 Нажми /start",
    )


@router.message_created(Command("start"))
async def cmd_start(event: MessageCreated) -> None:
    """Команда /start: связываем пользователя и показываем меню."""
    sender = event.message.sender
    if sender is None:
        return
    await sessions.ensure_user(sender.user_id, sender.first_name or "")
    await event.message.answer("Что делаем? 🎮", attachments=[kbs.main_menu()])


@router.message_callback(F.callback.payload == "menu:main")
async def back_to_menu(event: MessageCallback) -> None:
    """Кнопка «Меню»: возврат в главное меню."""
    await event.edit("Главное меню 🎮", attachments=[kbs.main_menu()])

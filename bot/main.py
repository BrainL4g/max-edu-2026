"""Точка входа MAX-бота SkillQuest (polling)."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from maxapi import Bot, Dispatcher
from maxapi.types import BotCommand, ErrorEvent

from handlers import (
    assessment,
    fallback,
    goal,
    missions,
    recommend,
    resume,
    skillmap,
    start,
)

load_dotenv()
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("MAX_BOT_TOKEN")
if not TOKEN:
    raise SystemExit("MAX_BOT_TOKEN не задан. Добавьте его в .env (см. .env.example).")

bot = Bot(TOKEN)
dp = Dispatcher()
dp.include_routers(
    start.router,
    goal.router,
    missions.router,
    assessment.router,
    skillmap.router,
    recommend.router,
    resume.router,
    fallback.router,
)


@dp.errors()
async def on_event_error(event: ErrorEvent) -> None:
    """Логируем ошибки хендлеров, чтобы polling продолжал работать."""
    logging.getLogger(__name__).error(
        "Handler error in %s: %s",
        event.router_id,
        event.exception,
        exc_info=(
            type(event.exception),
            event.exception,
            event.exception.__traceback__,
        ),
    )


async def register_commands(bot: Bot) -> None:
    """Зарегистрировать команды бота — так в чате появляется кнопка «Старт»."""
    await bot.set_commands(
        BotCommand(name="start", description="Открыть главное меню"),
        BotCommand(name="help", description="Инструкция по использованию"),
    )


async def main() -> None:
    await register_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

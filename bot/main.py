"""Точка входа MAX-бота SkillQuest (polling)."""

from __future__ import annotations

import asyncio
import logging
import os

from dotenv import load_dotenv
from maxapi import Bot, Dispatcher
from maxapi.types import ErrorEvent

from handlers import (
    assessment,
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
    missions.router,
    assessment.router,
    skillmap.router,
    recommend.router,
    resume.router,
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


async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

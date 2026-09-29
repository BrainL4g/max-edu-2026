"""Точка входа FastAPI-приложения SkillQuest."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.database.session import engine
from backend.app.domain import Base


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Старт: создание таблиц и демо-данных для быстрого прототипа."""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        from backend.app.seed import seed_if_empty

        seed_if_empty()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Игровой бэкенд SkillQuest: диагностика навыков, игровые миссии, "
        "рекомендации курсов и стажировок, анализ резюме. "
        "Защищённые операции требуют Bearer-токен (см. security и docs/API.md)."
    ),
    lifespan=lifespan,
    servers=[{"url": "/"}],
    contact={"name": "SkillQuest Team", "url": "https://github.com/BrainL4g/max-edu-2026"},
    openapi_tags=[
        {"name": "users", "description": "Профиль, диагностика, прогресс, целевая роль"},
        {"name": "skills", "description": "Навыки и Skill Map пользователя"},
        {"name": "roles", "description": "Целевые карьерные роли и их требования"},
        {"name": "assessment", "description": "Банк вопросов первичной диагностики"},
        {"name": "missions", "description": "Игровые миссии: следующее задание, ответ, попытки"},
        {"name": "courses", "description": "Курсы: каталог и рекомендации по пробелам"},
        {"name": "internships", "description": "Стажировки: каталог и рекомендации"},
        {"name": "resumes", "description": "Резюме: загрузка, анализ, результат"},
        {
            "name": "privacy",
            "description": (
                "Права субъекта персональных данных (152-ФЗ): согласие на обработку, "
                "экспорт и удаление данных"
            ),
        },
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)

_default_openapi = app.openapi


def custom_openapi() -> dict[str, Any]:
    """OpenAPI-схема с поправкой на условную публичность вопросов диагностики.

    ``GET /assessment/questions`` использует опциональную аутентификацию
    (токен нужен только при передаче ``user_id``), поэтому в спецификации
    операция помечается как публичная (``security: []``), а условие
    описывается в ``description``.
    """
    schema = _default_openapi()
    questions = schema["paths"]["/assessment/questions"]["get"]
    questions["security"] = []
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/health", openapi_extra={"security": []})
def health() -> dict[str, str]:
    """Health-check."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/", openapi_extra={"security": []})
def root() -> dict[str, str]:
    """Корневая страница со ссылками."""
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}

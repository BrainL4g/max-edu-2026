"""Точка входа FastAPI-приложения SkillQuest."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.database.session import engine
from backend.app.domain import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Старт: создание таблиц и демо-данных для быстрого прототипа."""
    if settings.auto_create_tables:
        Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        from backend.app.seed import seed_if_empty

        seed_if_empty()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Игровой бэкенд: диагностика навыков, миссии, курсы и стажировки.",
    lifespan=lifespan,
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


@app.get("/health")
def health() -> dict[str, str]:
    """Health-check."""
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/")
def root() -> dict[str, str]:
    """Корневая страница со ссылками."""
    return {"app": settings.app_name, "docs": "/docs", "health": "/health"}

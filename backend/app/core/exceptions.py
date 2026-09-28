"""Общие исключения приложения и их обработка."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class SkillQuestError(Exception):
    """Базовое исключение SkillQuest."""


class NotFoundError(SkillQuestError):
    """Ресурс не найден."""


class InvalidDataError(SkillQuestError):
    """Некорректные входные данные."""


class ConflictError(SkillQuestError):
    """Конфликт данных (например, дубликат)."""


def register_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики доменных исключений в FastAPI-приложении."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})

    @app.exception_handler(InvalidDataError)
    async def invalid_data_handler(request: Request, exc: InvalidDataError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})

"""Общие описания ошибок для OpenAPI (responses роутеров).

Доменные ошибки (404/409/422 в формате ``ErrorOut``) описаны здесь;
422 от валидации pydantic остаётся автоматическим (``HTTPValidationError``)
и в этих словарях не указывается.
"""

from __future__ import annotations

from typing import Any

from backend.app.schemas.error import ErrorOut

ResponseMap = dict[int | str, dict[str, Any]]

UNAUTHORIZED: ResponseMap = {
    401: {
        "model": ErrorOut,
        "description": "Нет или невалидный Bearer-токен",
    }
}

FORBIDDEN: ResponseMap = {
    403: {
        "model": ErrorOut,
        "description": "Доступ запрещён: не свой ресурс или не та роль",
    }
}

NOT_FOUND: ResponseMap = {
    404: {
        "model": ErrorOut,
        "description": "Ресурс не найден",
    }
}

CONFLICT: ResponseMap = {
    409: {
        "model": ErrorOut,
        "description": "Конфликт данных (например, тестовая учётка уже существует)",
    }
}

AUTH_ERRORS: ResponseMap = {**UNAUTHORIZED, **FORBIDDEN}
OWN_ERRORS: ResponseMap = {**UNAUTHORIZED, **FORBIDDEN, **NOT_FOUND}
MISSING_ERRORS: ResponseMap = {**UNAUTHORIZED, **NOT_FOUND}

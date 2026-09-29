"""Единый формат ошибок API."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorOut(BaseModel):
    """Ошибка API: человекочитаемое сообщение в поле ``detail``."""

    detail: str

"""Лёгкое in-memory состояние пользователей бота.

Сессия: max_user_id → {"uid": id на платформе, "answers": [...], "resume": False,
"welcomed": bool}, где `resume` — флаг ожидания резюме (файл или текст) после
кнопки «Резюме», а `welcomed` — признак отправленного приветствия.
"""

from __future__ import annotations

from typing import Any, cast

from maxapi.types import User

import api

sessions: dict[int, dict[str, Any]] = {}


def session_for(max_user_id: int) -> dict[str, Any]:
    """Состояние пользователя (с гарантированными ключами)."""
    return sessions.setdefault(
        max_user_id,
        {"uid": None, "answers": [], "resume": False, "welcomed": False},
    )


async def ensure_user(max_user_id: int, name: str) -> int:
    """Вернуть id пользователя на платформе (get-or-create при первом обращении)."""
    item = session_for(max_user_id)
    if item["uid"] is None:
        item["uid"] = (await api.get_user(max_user_id, name))["id"]
    return cast(int, item["uid"])


async def ensure_user_from(user: User) -> int:
    """Как ensure_user, но принимает maxapi.types.User."""
    return await ensure_user(user.user_id, user.first_name or "")

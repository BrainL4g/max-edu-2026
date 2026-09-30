"""Тесты in-memory сессий и привязки пользователя."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from maxapi.types import User

import api
import sessions


def test_session_for_creates_defaults() -> None:
    item = sessions.session_for(7)
    assert item == {
        "uid": None,
        "answers": [],
        "resume": False,
        "greeted_at": None,
        "consent": False,
    }
    assert sessions.session_for(7) is item


def test_ensure_user_caches_platform_id(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[int, str | None]] = []

    async def fake_get_user(
        max_user_id: int, name: str | None = None
    ) -> dict[str, Any]:
        calls.append((max_user_id, name))
        return {"id": max_user_id * 10}

    monkeypatch.setattr(api, "get_user", fake_get_user)

    async def run() -> tuple[int, int]:
        first = await sessions.ensure_user(7, "Ваня")
        second = await sessions.ensure_user(7, "Ваня")
        return first, second

    first, second = asyncio.run(run())
    assert (first, second) == (70, 70)
    assert calls == [(7, "Ваня")]


def test_ensure_user_from_takes_user_object(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_get_user(
        max_user_id: int, name: str | None = None
    ) -> dict[str, Any]:
        return {"id": 999}

    monkeypatch.setattr(api, "get_user", fake_get_user)

    user = User.model_construct(
        user_id=5, first_name="Петя", is_bot=False, last_activity_time=0
    )
    assert asyncio.run(sessions.ensure_user_from(user)) == 999
    assert sessions.session_for(5)["uid"] == 999

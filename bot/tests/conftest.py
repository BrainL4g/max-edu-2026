"""Фикстуры тестов MAX-бота: sys.path, изоляция сессий, фейк-события."""

from __future__ import annotations

import sys
from collections.abc import Generator
from pathlib import Path

import pytest

BOT_DIR = Path(__file__).resolve().parent.parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

import sessions


@pytest.fixture(autouse=True)
def _clear_sessions() -> Generator[None, None, None]:
    """Каждый тест работает с пустым in-memory хранилищем сессий."""
    sessions.sessions.clear()
    yield
    sessions.sessions.clear()

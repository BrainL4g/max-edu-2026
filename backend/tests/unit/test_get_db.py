"""Тесты FastAPI-зависимости ``get_db`` (yield + закрытие сессии)."""

from __future__ import annotations

import pytest

from backend.app.database import session


class _FakeSession:
    """Минимальная подмена сессии: запоминает факт закрытия."""

    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_get_db_yields_session_and_closes_it(monkeypatch) -> None:
    fake = _FakeSession()
    monkeypatch.setattr(session, "SessionLocal", lambda: fake)

    generator = session.get_db()
    assert next(generator) is fake

    with pytest.raises(StopIteration):
        next(generator)

    assert fake.closed is True

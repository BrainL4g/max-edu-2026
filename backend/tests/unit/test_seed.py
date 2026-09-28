"""Тесты сидера демо-данных и его идемпотентности."""

from __future__ import annotations

from backend.app import seed
from backend.app.database import session as db_session_module
from backend.app.seed import seed_database


def test_seed_database_fills_once(db_session):
    added = seed_database(db_session)
    assert added > 0
    # повторное наполнение — пусто: база уже не пустая
    assert seed_database(db_session) == 0


def test_seed_if_empty_uses_session_local(db_session, monkeypatch):
    monkeypatch.setattr(db_session_module, "SessionLocal", lambda: db_session)
    assert seed.seed_if_empty() > 0
    assert seed.seed_if_empty() == 0

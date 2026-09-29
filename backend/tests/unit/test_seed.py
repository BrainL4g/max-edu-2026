"""Тесты сидера демо-данных и его идемпотентности."""

from __future__ import annotations

from sqlalchemy import func, select

from backend.app import seed
from backend.app.database import session as db_session_module
from backend.app.domain import Role
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


def test_seed_roles_into_existing_database(db_session):
    """Уже наполненная база без ролей получает только роли (обратная совместимость)."""
    seed_database(db_session)
    for role in db_session.scalars(select(Role)):
        db_session.delete(role)
    db_session.commit()
    assert db_session.scalar(select(func.count(Role.id))) == 0

    added = seed_database(db_session)
    assert added > 0
    roles = list(db_session.scalars(select(Role)))
    assert len(roles) == len(seed.SEED_ROLES)
    assert all(role.requirements for role in roles)
    # повторный вызов больше ничего не добавляет
    assert seed_database(db_session) == 0


def test_seed_roles_helper_is_idempotent(db_session):
    """Прямой вызов _seed_roles на уже наполненной базе ничего не создаёт."""
    seed_database(db_session)
    assert seed._seed_roles(db_session, {}) == 0


def test_seed_missions_correct_option_not_always_first():
    """Правильный ответ в миссиях не должен всегда стоять первым."""
    first_is_correct = [mission["options"][0][1] for mission in seed.SEED_MISSIONS]
    assert not all(first_is_correct)
    # каждый вариант ровно один раз: правильный ровно один
    for mission in seed.SEED_MISSIONS:
        correct = [option for option in mission["options"] if option[1]]
        assert len(correct) == 1

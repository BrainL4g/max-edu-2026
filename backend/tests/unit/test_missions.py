"""Тесты игровой системы миссий."""

from __future__ import annotations

from backend.app.domain import Mission, MissionOption, Skill, User
from backend.app.services.missions import MissionService


def _seed(db, skill_names=("Python", "SQL")):
    skills = {
        name: Skill(name=name, category="Программирование" if name == "Python" else "Данные")
        for name in skill_names
    }
    db.add_all(skills.values())
    db.commit()

    mission_a = Mission(
        skill_id=skills["Python"].id,
        difficulty="easy",
        scenario="Вывести сумму 1..n",
        explanation="sum(range(1, n+1))",
        reward_xp=40,
    )
    mission_a.options.append(MissionOption(text="sum(range(1, n + 1))", is_correct=True))
    mission_a.options.append(MissionOption(text="sum(n)", is_correct=False))
    db.add(mission_a)

    mission_b = Mission(
        skill_id=skills["SQL"].id,
        difficulty="medium",
        scenario="Посчитать заказы по клиентам",
        explanation="GROUP BY",
        reward_xp=45,
    )
    mission_b.options.append(MissionOption(text="GROUP BY", is_correct=True))
    mission_b.options.append(MissionOption(text="WHERE", is_correct=False))
    db.add(mission_b)
    db.commit()
    return skills, mission_a, mission_b


def _user(db) -> User:
    user = User(name="Тест", direction="backend")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_get_next_mission_returns_unsolved(db_session):
    _seed(db_session)
    user = _user(db_session)
    mission = MissionService(db_session).get_next_mission(user.id)
    assert mission is not None
    assert mission.options  # варианты загружены


def test_submit_correct_answer(db_session):
    _, mission_a, _ = _seed(db_session)
    user = _user(db_session)
    correct_option = mission_a.options[0]

    result = MissionService(db_session).submit_answer(user.id, mission_a.id, correct_option.id)

    assert result["is_correct"] is True
    assert result["xp_earned"] == 40  # easy без бонуса
    assert result["explanation"] == "sum(range(1, n+1))"
    assert result["correct_option_id"] == correct_option.id
    assert result["skill_name"] == "Python"
    assert result["skill_level_after"] == 0  # 40 XP < порога 100


def test_submit_wrong_answer(db_session):
    _, mission_a, _ = _seed(db_session)
    user = _user(db_session)
    wrong_option = mission_a.options[1]

    result = MissionService(db_session).submit_answer(user.id, mission_a.id, wrong_option.id)

    assert result["is_correct"] is False
    assert result["xp_earned"] == max(3, 40 // 5) == 8
    assert result["correct_option_id"] == mission_a.options[0].id


def test_next_mission_excludes_solved(db_session):
    _, mission_a, mission_b = _seed(db_session)
    user = _user(db_session)
    svc = MissionService(db_session)

    svc.submit_answer(user.id, mission_a.id, mission_a.options[0].id)
    svc.submit_answer(user.id, mission_b.id, mission_b.options[0].id)

    assert svc.get_next_mission(user.id) is None


def test_submit_answer_creates_attempt(db_session):
    _, mission_a, _ = _seed(db_session)
    user = _user(db_session)
    svc = MissionService(db_session)

    svc.submit_answer(user.id, mission_a.id, mission_a.options[0].id)

    history = svc.get_history(user.id)
    assert len(history) == 1
    assert history[0].is_correct is True
    assert history[0].xp_earned == 40

"""Тесты игровой системы миссий: цель, статусы, XP и прогресс."""

from __future__ import annotations

from backend.app.domain import Mission, MissionOption, Role, RoleSkill, Skill, User
from backend.app.services.missions import MissionService


def _seed(db):
    python = Skill(name="Python", category="Программирование")
    sql = Skill(name="SQL", category="Данные")
    extra = Skill(name="JavaScript", category="Фронтенд")
    db.add_all([python, sql, extra])
    db.commit()

    role = Role(
        name="Backend Junior",
        direction="backend",
        level="junior",
        description="Бэкенд",
    )
    db.add(role)
    db.commit()
    db.add_all(
        [
            RoleSkill(
                role_id=role.id,
                skill_id=python.id,
                required_level=3,
                importance=0.9,
                is_mandatory=True,
            ),
            RoleSkill(
                role_id=role.id,
                skill_id=sql.id,
                required_level=2,
                importance=0.6,
                is_mandatory=True,
            ),
        ]
    )
    db.commit()

    mission_a = Mission(
        skill_id=python.id,
        difficulty="easy",
        scenario="Вывести сумму 1..n",
        explanation="sum(range(1, n+1))",
        reward_xp=120,
    )
    mission_a.options.append(MissionOption(text="sum(range(1, n + 1))", is_correct=True))
    mission_a.options.append(MissionOption(text="sum(n)", is_correct=False))
    db.add(mission_a)

    mission_c = Mission(
        skill_id=python.id,
        difficulty="medium",
        scenario="Список квадратов",
        explanation="[x ** 2 for x in range(n)]",
        reward_xp=35,
    )
    mission_c.options.append(MissionOption(text="[x ** 2 for x in range(n)]", is_correct=True))
    mission_c.options.append(MissionOption(text="[x * n for x in range(n)]", is_correct=False))
    db.add(mission_c)

    mission_b = Mission(
        skill_id=sql.id,
        difficulty="medium",
        scenario="Посчитать заказы по клиентам",
        explanation="GROUP BY",
        reward_xp=45,
    )
    mission_b.options.append(MissionOption(text="GROUP BY", is_correct=True))
    mission_b.options.append(MissionOption(text="WHERE", is_correct=False))
    db.add(mission_b)

    mission_extra = Mission(
        skill_id=extra.id,
        difficulty="easy",
        scenario="Кнопка на странице",
        explanation="onclick",
        reward_xp=20,
    )
    mission_extra.options.append(MissionOption(text="onclick", is_correct=True))
    db.add(mission_extra)
    db.commit()
    return role, python, mission_a, mission_c, mission_b, mission_extra


def _user(db, role: Role | None) -> User:
    user = User(name="Тест", direction="backend")
    db.add(user)
    db.commit()
    if role is not None:
        user.target_role_id = role.id
        db.commit()
    db.refresh(user)
    return user


def _correct_option(mission: Mission) -> MissionOption:
    return next(o for o in mission.options if o.is_correct)


def test_get_next_mission_returns_unsolved(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    data = MissionService(db_session).get_next_mission(user.id)
    assert data["status"] == "ok"
    assert data["done"] == 0
    assert data["total"] == 3
    assert data["mission"] is not None
    assert data["mission"].id in {mission_a.id}
    assert data["mission"].options


def test_get_next_mission_no_goal(db_session):
    _seed(db_session)
    user = _user(db_session, None)
    data = MissionService(db_session).get_next_mission(user.id)
    assert data["status"] == "no_goal"
    assert data["mission"] is None


def test_get_next_mission_only_role_skills_and_all_done(db_session):
    role, _, mission_a, mission_c, mission_b, mission_extra = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)

    seen = []
    for _ in range(10):
        data = svc.get_next_mission(user.id)
        if data["status"] != "ok":
            break
        mission = data["mission"]
        assert mission.id != mission_extra.id
        seen.append(mission.id)
        svc.submit_answer(user.id, mission.id, _correct_option(mission).id)

    assert set(seen) == {mission_a.id, mission_c.id, mission_b.id}
    data = svc.get_next_mission(user.id)
    assert data["status"] == "all_done"
    assert data["done"] == 3
    assert data["total"] == 3


def test_next_mission_progress_counts(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)

    first = svc.get_next_mission(user.id)
    assert first["done"] == 0
    assert first["total"] == 3

    svc.submit_answer(user.id, mission_a.id, _correct_option(mission_a).id)
    second = svc.get_next_mission(user.id)
    assert second["status"] == "ok"
    assert second["done"] == 1
    assert second["total"] == 3


def test_submit_correct_answer(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    result = MissionService(db_session).submit_answer(
        user.id, mission_a.id, _correct_option(mission_a).id
    )
    assert result["is_correct"] is True
    assert result["xp_earned"] == 120
    assert result["skill_level_before"] == 0
    assert result["skill_level_after"] == 1
    assert result["already_solved"] is False
    assert result["correct_option_text"] == "sum(range(1, n + 1))"


def test_submit_wrong_answer_gives_no_xp(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    wrong = next(o for o in mission_a.options if not o.is_correct)
    result = MissionService(db_session).submit_answer(user.id, mission_a.id, wrong.id)
    assert result["is_correct"] is False
    assert result["xp_earned"] == 0
    assert result["correct_option_text"] == "sum(range(1, n + 1))"
    assert result["skill_level_before"] == 0
    assert result["skill_level_after"] == 0


def test_next_mission_different_after_wrong_answer(db_session):
    role, _, mission_a, mission_c, _, _ = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)

    first = svc.get_next_mission(user.id)
    assert first["mission"].id == mission_a.id

    wrong = next(o for o in mission_a.options if not o.is_correct)
    svc.submit_answer(user.id, mission_a.id, wrong.id)

    second = svc.get_next_mission(user.id)
    assert second["mission"].id != mission_a.id
    assert second["mission"].skill_id == mission_a.skill_id
    assert second["mission"].id == mission_c.id


def test_submit_already_solved_returns_result_without_new_attempt(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)
    correct = _correct_option(mission_a)

    first = svc.submit_answer(user.id, mission_a.id, correct.id)
    attempts_after_first = len(svc.get_history(user.id))

    second = svc.submit_answer(user.id, mission_a.id, correct.id)
    assert second["already_solved"] is True
    assert second["xp_earned"] == 0
    assert second["attempt_id"] == first["attempt_id"]
    assert attempts_after_first == 1


def test_next_mission_excludes_solved(db_session):
    role, _, mission_a, _, mission_b, _ = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)
    svc.submit_answer(user.id, mission_a.id, _correct_option(mission_a).id)
    svc.submit_answer(user.id, mission_b.id, _correct_option(mission_b).id)

    data = svc.get_next_mission(user.id)
    assert data["status"] == "ok"
    assert data["mission"].id != mission_a.id


def test_submit_answer_creates_attempt(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    user = _user(db_session, role)
    svc = MissionService(db_session)
    result = svc.submit_answer(user.id, mission_a.id, _correct_option(mission_a).id)
    history = svc.get_history(user.id)
    assert len(history) == 1
    assert history[0].id == result["attempt_id"]
    assert history[0].xp_earned == 120


def test_get_mission_without_options(db_session):
    role, _, mission_a, _, _, _ = _seed(db_session)
    _user(db_session, role)
    mission = MissionService(db_session).get_mission(mission_a.id)
    assert mission.scenario == "Вывести сумму 1..n"

"""Миссии строго по цели: фильтрация ролей, статусы и прогресс через API."""

from __future__ import annotations

from sqlalchemy import select

from backend.app.domain import MissionOption, Role, RoleSkill, Skill
from backend.app.seed import seed_database

ROLE_SKILLS = {
    "Backend Junior": {"Python", "SQL", "FastAPI", "Git", "Docker"},
    "Frontend Junior": {"JavaScript", "HTML/CSS", "React", "Git"},
}


def _set_goal(client, user_id: int, role_name: str) -> None:
    roles = client.get("/roles").json()
    role = next(role for role in roles if role["name"] == role_name)
    response = client.put(f"/users/{user_id}/goal", json={"target_role_id": role["id"]})
    assert response.status_code == 200


def _correct_option_id(db, mission_id: int) -> int:
    option = db.scalar(
        select(MissionOption).where(
            MissionOption.mission_id == mission_id, MissionOption.is_correct.is_(True)
        )
    )
    assert option is not None
    return option.id


def _solve_until_done(client, db, user_id: int, attempts: int = 50):
    """Решать миссии правильными ответами, пока не придёт all_done."""
    skills_seen: set[str] = set()
    for _ in range(attempts):
        data = client.get("/missions/next", params={"user_id": user_id}).json()
        if data["status"] != "ok":
            return data, skills_seen
        mission = data["mission"]
        skills_seen.add(mission["skill_name"])
        correct_id = _correct_option_id(db, mission["id"])
        response = client.post(
            f"/missions/{mission['id']}/answer",
            json={"user_id": user_id, "option_id": correct_id},
        )
        assert response.status_code == 200
        assert response.json()["is_correct"] is True
    assert False, "миссии не закрылись за отведённое число попыток"


def test_backend_junior_gets_only_role_missions(client, db_session):
    seed_database(db_session)
    user = client.post("/users", json={"name": "Бэкендер"}).json()
    _set_goal(client, user["id"], "Backend Junior")

    data, skills_seen = _solve_until_done(client, db_session, user["id"])

    assert data["status"] == "all_done"
    assert data["done"] == data["total"] and data["total"] > 0
    assert skills_seen <= ROLE_SKILLS["Backend Junior"]
    assert not (skills_seen & {"UI/UX", "Figma", "React", "Machine Learning"})


def test_frontend_junior_gets_only_own_missions(client, db_session):
    seed_database(db_session)
    user = client.post("/users", json={"name": "Фронтендер"}).json()
    _set_goal(client, user["id"], "Frontend Junior")

    data, skills_seen = _solve_until_done(client, db_session, user["id"])

    assert data["status"] == "all_done"
    assert skills_seen <= ROLE_SKILLS["Frontend Junior"]
    assert "Python" not in skills_seen


def test_no_goal_is_no_goal_status(client, db_session):
    seed_database(db_session)
    user = client.post("/users", json={"name": "Без цели"}).json()

    data = client.get("/missions/next", params={"user_id": user["id"]}).json()

    assert data["status"] == "no_goal"
    assert data["mission"] is None


def test_answered_mission_path(client, db_session):
    """После ответа миссия либо закрывается, либо перепредлагается иначе."""
    seed_database(db_session)
    user = client.post("/users", json={"name": "Решатель"}).json()
    _set_goal(client, user["id"], "Backend Junior")

    first = client.get("/missions/next", params={"user_id": user["id"]}).json()["mission"]
    wrong = first["options"][0]
    result = client.post(
        f"/missions/{first['id']}/answer",
        json={"user_id": user["id"], "option_id": wrong["id"]},
    ).json()
    assert result["is_correct"] is False
    assert result["xp_earned"] == 0

    second = client.get("/missions/next", params={"user_id": user["id"]}).json()["mission"]
    assert second["id"] != first["id"]

    correct_id = _correct_option_id(db_session, first["id"])
    correct = client.post(
        f"/missions/{first['id']}/answer",
        json={"user_id": user["id"], "option_id": correct_id},
    ).json()
    assert correct["is_correct"] is True
    repeat = client.post(
        f"/missions/{first['id']}/answer",
        json={"user_id": user["id"], "option_id": correct_id},
    ).json()
    assert repeat["already_solved"] is True
    assert repeat["xp_earned"] == 0


def test_role_with_no_missions_is_all_done(client, db_session):
    """Роль без миссий по своим навыкам — сразу all_done (пустое множество)."""
    seed_database(db_session)
    soft = db_session.scalar(select(Skill).where(Skill.name == "Тайм-менеджмент"))
    assert soft is not None
    role = Role(
        name="Софт-навыки",
        direction="soft",
        level="junior",
        description="Только софт-скиллы",
    )
    db_session.add(role)
    db_session.commit()
    db_session.add(
        RoleSkill(
            role_id=role.id,
            skill_id=soft.id,
            required_level=3,
            importance=0.9,
            is_mandatory=True,
        )
    )
    db_session.commit()

    user = client.post("/users", json={"name": "Организатор"}).json()
    assert (
        client.put(f"/users/{user['id']}/goal", json={"target_role_id": role.id}).status_code == 200
    )

    data = client.get("/missions/next", params={"user_id": user["id"]}).json()
    assert data["status"] == "all_done"
    assert data["total"] == 0


def test_mission_progress_visible_in_api(client, db_session):
    seed_database(db_session)
    user = client.post("/users", json={"name": "Счётчик"}).json()
    _set_goal(client, user["id"], "Backend Junior")

    data = client.get("/missions/next", params={"user_id": user["id"]}).json()
    assert data["status"] == "ok"
    assert data["done"] == 0
    total = data["total"]
    mission = data["mission"]
    correct_id = _correct_option_id(db_session, mission["id"])
    client.post(
        f"/missions/{mission['id']}/answer",
        json={"user_id": user["id"], "option_id": correct_id},
    )

    after = client.get("/missions/next", params={"user_id": user["id"]}).json()
    assert after["done"] == 1
    assert after["total"] == total

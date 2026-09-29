"""Целевые роли: список, выбор цели и gap-анализ пользователя."""

from __future__ import annotations

from backend.app.domain import UserSkill
from backend.app.seed import seed_database
from backend.app.services.skills import LEVEL_THRESHOLDS


def _create_user(client, name: str = "Студент") -> dict:
    response = client.post("/users", json={"name": name})
    assert response.status_code == 201
    return response.json()


def test_roles_list_seeded_with_requirements(client, db_session):
    seed_database(db_session)
    roles = client.get("/roles").json()

    assert len(roles) >= 4
    names = {role["name"] for role in roles}
    assert "Backend Junior" in names
    assert "Frontend Junior" in names
    assert "QA Junior" in names

    backend = next(role for role in roles if role["name"] == "Backend Junior")
    assert backend["direction"] == "backend"
    assert backend["level"] == "junior"
    assert backend["description"]
    assert backend["requirements"]
    requirement = next(req for req in backend["requirements"] if req["name"] == "Python")
    assert requirement["required_level"] == 3
    assert requirement["importance"] == 0.9
    assert requirement["is_mandatory"] is True


def test_set_goal_and_gap_analysis_flow(client, db_session):
    seed_database(db_session)
    user = _create_user(client, name="Маша")
    roles = client.get("/roles").json()
    backend = next(role for role in roles if role["name"] == "Backend Junior")

    response = client.put(f"/users/{user['id']}/goal", json={"target_role_id": backend["id"]})
    assert response.status_code == 200
    assert response.json()["target_role_id"] == backend["id"]

    skills = {skill["name"]: skill["id"] for skill in client.get("/skills").json()}
    db_session.add(
        UserSkill(
            user_id=user["id"],
            skill_id=skills["Python"],
            experience=LEVEL_THRESHOLDS[3],
            level=3,
        )
    )
    db_session.commit()

    analysis = client.get(f"/users/{user['id']}/gap-analysis").json()
    assert analysis["user_id"] == user["id"]
    assert analysis["role"]["name"] == "Backend Junior"
    assert 0 < analysis["match_percent"] < 100

    python_item = next(item for item in analysis["items"] if item["name"] == "Python")
    assert python_item["current_level"] == 3
    assert python_item["gap"] == 0

    sql_item = next(item for item in analysis["items"] if item["name"] == "SQL")
    assert sql_item["gap"] == sql_item["required_level"]
    assert "Не хватает" in analysis["summary"]


def test_full_match_gap_analysis(client, db_session):
    seed_database(db_session)
    user = _create_user(client, name="Иван")
    roles = client.get("/roles").json()
    backend = next(role for role in roles if role["name"] == "Backend Junior")
    client.put(f"/users/{user['id']}/goal", json={"target_role_id": backend["id"]})

    skills = {skill["name"]: skill["id"] for skill in client.get("/skills").json()}
    for name, level in [
        ("Python", 3),
        ("SQL", 3),
        ("FastAPI", 2),
        ("Git", 2),
        ("Docker", 1),
        ("Алгоритмы и структуры данных", 2),
    ]:
        db_session.add(
            UserSkill(
                user_id=user["id"],
                skill_id=skills[name],
                experience=LEVEL_THRESHOLDS[level],
                level=level,
            )
        )
    db_session.commit()

    analysis = client.get(f"/users/{user['id']}/gap-analysis").json()
    assert analysis["match_percent"] == 100
    assert all(item["gap"] == 0 for item in analysis["items"])
    assert "🎉" in analysis["summary"]


def test_gap_analysis_without_goal(client):
    user = _create_user(client, name="Петя")
    analysis = client.get(f"/users/{user['id']}/gap-analysis").json()

    assert analysis["role"] is None
    assert analysis["match_percent"] is None
    assert analysis["items"] == []
    assert "не выбрана" in analysis["summary"]


def test_set_goal_unknown_role_returns_404(client):
    user = _create_user(client, name="Оля")
    response = client.put(f"/users/{user['id']}/goal", json={"target_role_id": 999999})
    assert response.status_code == 404


def test_set_goal_unknown_user_returns_404(client, db_session):
    seed_database(db_session)
    role_id = client.get("/roles").json()[0]["id"]
    assert client.put("/users/999999/goal", json={"target_role_id": role_id}).status_code == 404

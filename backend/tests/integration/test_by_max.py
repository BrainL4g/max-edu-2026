"""Эндпоинты интеграции с MAX: связка пользователя и банк вопросов."""

from __future__ import annotations

from backend.app.seed import seed_database
from backend.app.services.assessment import ASSESSMENT_QUESTIONS


def test_assessment_questions_exposed(client):
    response = client.get("/assessment/questions")
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) == len(ASSESSMENT_QUESTIONS)
    assert questions[0]["id"] == 1
    assert questions[0]["skill"]
    assert questions[0]["text"]
    assert len(questions[0]["options"]) >= 2
    assert all(isinstance(option, str) for option in questions[0]["options"])


def test_user_by_max_get_or_create(client, db_session):
    payload = {"max_user_id": 918273645, "name": "MAX-студент"}
    first_response = client.post("/users/by-max", json=payload)
    assert first_response.status_code == 200
    first = first_response.json()
    assert first["max_user_id"] == 918273645
    assert first["name"] == "MAX-студент"

    second_response = client.post(
        "/users/by-max", json={"max_user_id": 918273645, "name": "Другое имя"}
    )
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["id"] == first["id"]
    assert second["name"] == "MAX-студент"

    assert client.get(f"/users/{first['id']}").status_code == 200


def test_user_by_max_path_compatible_with_plain_creation(client):
    """get-or-create не ломает обычное создание/чтение пользователей."""
    created = client.post(
        "/users", json={"name": "Обычный студент", "direction": "frontend"}
    ).json()
    assert client.get(f"/users/{created['id']}").status_code == 200
    assert created["max_user_id"] is None


def test_user_by_max_can_run_assessment(client, db_session):
    seed_database(db_session)
    created = client.post("/users/by-max", json={"max_user_id": 555, "name": "Новичок"}).json()
    response = client.post(
        f"/users/{created['id']}/assessment",
        json={"answers": [{"question_id": 1, "option_index": 1}]},
    )
    assert response.status_code == 200
    assert response.json()["evaluated_skills"]


def test_assessment_questions_filtered_by_user_direction(client, db_session):
    created = client.post("/users", json={"name": "Аня", "direction": "backend"}).json()
    response = client.get("/assessment/questions", params={"user_id": created["id"]})
    assert response.status_code == 200
    skills = {q["skill"] for q in response.json()}
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "JavaScript" not in skills
    assert "Figma" not in skills


def test_assessment_questions_filtered_by_target_role_direction(client, db_session):
    seed_database(db_session)
    created = client.post("/users", json={"name": "Борис"}).json()
    roles = client.get("/roles").json()
    frontend = next(role for role in roles if role["direction"] == "frontend")
    goal_response = client.put(
        f"/users/{created['id']}/goal", json={"target_role_id": frontend["id"]}
    )
    assert goal_response.status_code == 200

    response = client.get("/assessment/questions", params={"user_id": created["id"]})
    assert response.status_code == 200
    skills = {q["skill"] for q in response.json()}
    assert "JavaScript" in skills
    assert "Python" not in skills


def test_assessment_questions_role_direction_wins_over_user_direction(client, db_session):
    """Целевая роль приоритетнее направления пользователя при фильтрации."""
    seed_database(db_session)
    created = client.post("/users", json={"name": "Вера", "direction": "backend"}).json()
    roles = client.get("/roles").json()
    frontend = next(role for role in roles if role["direction"] == "frontend")
    assert (
        client.put(
            f"/users/{created['id']}/goal", json={"target_role_id": frontend["id"]}
        ).status_code
        == 200
    )

    response = client.get("/assessment/questions", params={"user_id": created["id"]})
    assert response.status_code == 200
    skills = {q["skill"] for q in response.json()}
    assert "JavaScript" in skills
    assert "Python" not in skills


def test_assessment_questions_404_for_missing_user(client):
    response = client.get("/assessment/questions", params={"user_id": 999999})
    assert response.status_code == 404

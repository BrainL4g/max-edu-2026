"""Дополнительные API-тесты: отдельные эндпоинты, 404 и валидация."""

from __future__ import annotations

from backend.app.seed import seed_database


def _create_user(client, name: str = "Студент") -> dict:
    response = client.post("/users", json={"name": name, "direction": "backend"})
    assert response.status_code == 201
    return response.json()


def test_skills_by_id_and_404(client, db_session):
    seed_database(db_session)
    skills = client.get("/skills").json()
    assert skills

    response = client.get(f"/skills/{skills[0]['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == skills[0]["id"]
    assert client.get("/skills/999999").status_code == 404


def test_courses_by_id_and_filters(client, db_session):
    seed_database(db_session)
    courses = client.get("/courses").json()
    assert courses

    assert client.get(f"/courses/{courses[0]['id']}").status_code == 200
    assert client.get("/courses/999999").status_code == 404

    assert client.get("/courses", params={"format": "online"}).status_code == 200
    assert client.get("/courses", params={"price_max": 0}).status_code == 200
    assert client.get("/courses", params={"platform": "Stepik"}).status_code == 200
    # «skills» содержит мусор — разбирается только числовая часть
    assert client.get("/courses", params={"skills": "1,2,abc"}).status_code == 200


def test_internships_by_id_and_filters(client, db_session):
    seed_database(db_session)
    internships = client.get("/internships").json()
    assert internships

    assert client.get(f"/internships/{internships[0]['id']}").status_code == 200
    assert client.get("/internships/999999").status_code == 404

    assert client.get("/internships", params={"city": "Москва"}).status_code == 200
    assert client.get("/internships", params={"format": "remote"}).status_code == 200
    assert client.get("/internships", params={"direction": "frontend"}).status_code == 200
    assert client.get("/internships", params={"skills": "1,2,abc"}).status_code == 200


def test_missions_full_flow(client, db_session):
    seed_database(db_session)
    user = _create_user(client)

    missions = client.get("/missions").json()
    assert missions
    assert client.get(f"/missions/{missions[0]['id']}").status_code == 200
    assert client.get("/missions/999999").status_code == 404

    # Без цели — статус no_goal.
    no_goal = client.get("/missions/next", params={"user_id": user["id"]}).json()
    assert no_goal["status"] == "no_goal"
    assert no_goal["mission"] is None

    # С целью (Backend Junior) — статус ok и миссия по навыкам роли.
    roles = client.get("/roles").json()
    backend_role = next(role for role in roles if role["name"] == "Backend Junior")
    assert (
        client.put(
            f"/users/{user['id']}/goal", json={"target_role_id": backend_role["id"]}
        ).status_code
        == 200
    )
    next_mission = client.get("/missions/next", params={"user_id": user["id"]}).json()
    assert next_mission["status"] == "ok"
    assert next_mission["mission"] is not None
    assert next_mission["total"] > 0
    mission = next_mission["mission"]

    answer = client.post(
        f"/missions/{mission['id']}/answer",
        json={"user_id": user["id"], "option_id": mission["options"][0]["id"]},
    )
    assert answer.status_code == 200
    assert "xp_earned" in answer.json()
    assert "already_solved" in answer.json()

    attempts = client.get(f"/users/{user['id']}/attempts").json()
    assert len(attempts) == 1

    attempt_result = client.get(f"/attempts/{attempts[0]['id']}")
    assert attempt_result.status_code == 200
    assert attempt_result.json()["attempt_id"] == attempts[0]["id"]
    assert client.get("/attempts/999999").status_code == 404


def test_update_user_and_skills(client, db_session):
    seed_database(db_session)
    user = _create_user(client, name="Стажёр")

    response = client.patch(f"/users/{user['id']}", json={"name": "Senior", "direction": "backend"})
    assert response.status_code == 200
    assert response.json()["name"] == "Senior"

    assert client.get(f"/users/{user['id']}/progress").status_code == 200
    # у нового пользователя Skill Map пуст
    assert client.get(f"/users/{user['id']}/skills").json() == []


def test_assessment_validation_errors(client, db_session):
    seed_database(db_session)
    user = _create_user(client, name="Новичок")

    response = client.post(f"/users/{user['id']}/assessment", json={"answers": []})
    assert response.status_code == 422

    response = client.post(
        f"/users/{user['id']}/assessment",
        json={"answers": [{"question_id": 999, "option_index": 0}]},
    )
    assert response.status_code == 422


def test_resume_endpoints_and_404(client, db_session):
    seed_database(db_session)
    user = _create_user(client, name="Автор")

    created = client.post(
        f"/users/{user['id']}/resumes",
        json={"text": "Резюме без анализа", "filename": "cv.txt"},
    )
    assert created.status_code == 201
    resume_id = created.json()["id"]

    assert client.get(f"/users/{user['id']}/resumes").status_code == 200
    assert client.get(f"/resumes/{resume_id}").status_code == 200
    assert client.get("/resumes/999999").status_code == 404
    # анализ ещё не запускался
    assert client.get(f"/resumes/{resume_id}/analysis").status_code == 404
    assert client.post("/resumes/999999/analyze").status_code == 404

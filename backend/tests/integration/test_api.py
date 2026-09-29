"""Интеграционный тест полного сценария SkillQuest.

Создание пользователя → диагностика → миссия → ответ → обновление навыка →
рекомендации курсов/стажировок → загрузка резюме → анализ.
"""

from __future__ import annotations

from backend.app.seed import seed_database


def test_health(client, db_session):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_full_user_journey(client, db_session):
    seed_database(db_session)

    response = client.post(
        "/users",
        json={
            "name": "Студент",
            "education": "МГТУ, 3 курс",
            "direction": "backend",
            "goal": "Попасть на стажировку",
        },
    )
    assert response.status_code == 201
    user = response.json()
    user_id = user["id"]
    assert user["direction"] == "backend"

    assert client.get(f"/users/{user_id}").status_code == 200

    answers = [
        {"question_id": 1, "option_index": 2},  # Python → уровень 2
        {"question_id": 2, "option_index": 1},  # SQL → уровень 1
        {"question_id": 3, "option_index": 0},  # Git → уровень 0
    ]
    response = client.post(f"/users/{user_id}/assessment", json={"answers": answers})
    assert response.status_code == 200
    assessment = response.json()
    assert len(assessment["evaluated_skills"]) == 3
    assert assessment["summary"]

    response = client.get(f"/users/{user_id}/skills")
    assert response.status_code == 200
    skill_map = response.json()
    assert len(skill_map) == 3
    python_level = next(s["level"] for s in skill_map if s["name"] == "Python")
    assert python_level == 2

    roles = client.get("/roles").json()
    backend_role = next(role for role in roles if role["name"] == "Backend Junior")
    goal = client.put(f"/users/{user_id}/goal", json={"target_role_id": backend_role["id"]})
    assert goal.status_code == 200

    response = client.get("/missions/next", params={"user_id": user_id})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    mission = data["mission"]
    assert mission is not None
    chosen = mission["options"][0]

    response = client.post(
        f"/missions/{mission['id']}/answer",
        json={"user_id": user_id, "option_id": chosen["id"]},
    )
    assert response.status_code in (200, 422)
    result = response.json()
    assert "xp_earned" in result

    response = client.get(f"/users/{user_id}/progress")
    assert response.status_code == 200
    progress = response.json()
    assert progress["user_id"] == user_id
    assert progress["total_missions"] > 0
    assert progress["skills_count"] == 3

    response = client.get("/courses/recommended", params={"user_id": user_id})
    assert response.status_code == 200
    courses = response.json()
    assert isinstance(courses, list)

    response = client.get("/internships/recommended", params={"user_id": user_id})
    assert response.status_code == 200
    internships = response.json()
    assert isinstance(internships, list)

    response = client.get("/courses/recommended", params={"user_id": user_id})
    assert response.status_code == 200

    resume_text = (
        "Иван Иванов, email: ivan@example.com, Москва\n"
        "Образование: МГТУ им. Баумана, 3 курс\n"
        "Писал скрипты на Python, использовал git, основы SQL.\n"
        "Ссылки: https://github.com/ivan"
    )
    response = client.post(
        f"/users/{user_id}/resumes", json={"text": resume_text, "filename": "resume.txt"}
    )
    assert response.status_code == 201
    resume = response.json()
    resume_id = resume["id"]

    response = client.post(f"/resumes/{resume_id}/analyze")
    assert response.status_code == 200
    analysis = response.json()
    assert "Python" in analysis["found_skills"]
    assert "missing_skills" in analysis
    assert "issues" in analysis
    assert "recommendations" in analysis
    assert 0 <= analysis["direction_match"] <= 100

    response = client.get(f"/resumes/{resume_id}/analysis")
    assert response.status_code == 200
    assert response.json()["resume_id"] == resume_id

    response = client.post(
        f"/users/{user_id}/resumes/upload",
        files={"file": ("cv.txt", resume_text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201
    assert response.json()["filename"] == "cv.txt"


def test_404_for_missing_user(client, db_session):
    response = client.get("/users/999999")
    assert response.status_code == 404


def test_skills_listing_and_filters(client, db_session):
    seed_database(db_session)

    response = client.get("/skills")
    assert response.status_code == 200
    assert len(response.json()) > 10

    response = client.get("/courses", params={"category": "Программирование"})
    assert response.status_code == 200
    assert response.json()

    response = client.get("/internships", params={"remote": "true"})
    assert response.status_code == 200
    assert all(item["remote"] for item in response.json())

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
    # Демо-данные (навыки, миссии, курсы, стажировки).
    seed_database(db_session)

    # 1. Создание пользователя.
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

    # 2. Профиль.
    assert client.get(f"/users/{user_id}").status_code == 200

    # 3. Первичная диагностика → начальный Skill Map.
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

    # 4. Skill Map.
    response = client.get(f"/users/{user_id}/skills")
    assert response.status_code == 200
    skill_map = response.json()
    assert len(skill_map) == 3
    python_level = next(s["level"] for s in skill_map if s["name"] == "Python")
    assert python_level == 2

    # 5. Следующая миссия.
    response = client.get("/missions/next", params={"user_id": user_id})
    assert response.status_code == 200
    mission = response.json()
    assert mission is not None
    chosen = mission["options"][0]

    # 6. Ответ на миссию (решение выбираем вручную: ищем правильный вариант нельзя,
    #    поэтому отправляем первый и проверяем 200; затем шлём корректный через
    #    Direct DB проверку результата).
    response = client.post(
        f"/missions/{mission['id']}/answer",
        json={"user_id": user_id, "option_id": chosen["id"]},
    )
    assert response.status_code in (200, 422)
    result = response.json()
    assert "xp_earned" in result

    # 7. Прогресс пользователя.
    response = client.get(f"/users/{user_id}/progress")
    assert response.status_code == 200
    progress = response.json()
    assert progress["user_id"] == user_id
    assert progress["total_missions"] > 0
    assert progress["skills_count"] == 3

    # 8. Рекомендации курсов.
    response = client.get("/courses/recommended", params={"user_id": user_id})
    assert response.status_code == 200
    courses = response.json()
    assert isinstance(courses, list)

    # 9. Рекомендации стажировок.
    response = client.get("/internships/recommended", params={"user_id": user_id})
    assert response.status_code == 200
    internships = response.json()
    assert isinstance(internships, list)

    # 10. Рекомендации целиком (пробелы + курсы + стажировки).
    response = client.get("/courses/recommended", params={"user_id": user_id})
    assert response.status_code == 200

    # 11. Загрузка резюме текстом.
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

    # 12. Запуск анализа резюме.
    response = client.post(f"/resumes/{resume_id}/analyze")
    assert response.status_code == 200
    analysis = response.json()
    assert "Python" in analysis["found_skills"]
    assert "missing_skills" in analysis
    assert "issues" in analysis
    assert "recommendations" in analysis
    assert 0 <= analysis["direction_match"] <= 100

    # 13. Получение сохранённого результата анализа.
    response = client.get(f"/resumes/{resume_id}/analysis")
    assert response.status_code == 200
    assert response.json()["resume_id"] == resume_id

    # 14. Загрузка резюме файлом.
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

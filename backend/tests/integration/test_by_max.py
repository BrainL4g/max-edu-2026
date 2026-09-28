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
    # наружу отдаются только тексты вариантов, без внутренней оценки уровня
    assert all(isinstance(option, str) for option in questions[0]["options"])


def test_user_by_max_get_or_create(client, db_session):
    payload = {"max_user_id": 918273645, "name": "MAX-студент"}
    first_response = client.post("/users/by-max", json=payload)
    assert first_response.status_code == 200
    first = first_response.json()
    assert first["max_user_id"] == 918273645
    assert first["name"] == "MAX-студент"

    # Повторный вызов — тот же пользователь, имя не перезаписывается.
    second_response = client.post(
        "/users/by-max", json={"max_user_id": 918273645, "name": "Другое имя"}
    )
    assert second_response.status_code == 200
    second = second_response.json()
    assert second["id"] == first["id"]
    assert second["name"] == "MAX-студент"

    # Связанный пользователь доступен обычным профилем.
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
    created = client.post(
        "/users/by-max", json={"max_user_id": 555, "name": "Новичок"}
    ).json()
    response = client.post(
        f"/users/{created['id']}/assessment",
        json={"answers": [{"question_id": 1, "option_index": 1}]},
    )
    assert response.status_code == 200
    assert response.json()["evaluated_skills"]

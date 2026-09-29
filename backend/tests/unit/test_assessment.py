"""Тесты первичной диагностики."""

from __future__ import annotations

from backend.app.domain import Skill, User
from backend.app.services.assessment import (
    ASSESSMENT_QUESTIONS,
    AssessmentService,
    questions_for_direction,
)


def test_questions_for_direction_backend_excludes_frontend():
    questions = questions_for_direction("backend")
    skills = {q.skill for q in questions}
    assert "Python" in skills
    assert "JavaScript" not in skills
    assert "Figma" not in skills
    assert "FastAPI" in skills
    assert "Docker" in skills


def test_questions_for_direction_frontend_excludes_backend():
    questions = questions_for_direction("frontend")
    skills = {q.skill for q in questions}
    assert "JavaScript" in skills
    assert "React" in skills
    assert "Python" not in skills
    assert "SQL" not in skills
    assert "Git" in skills


def test_questions_for_direction_none_returns_all():
    assert len(questions_for_direction(None)) == len(ASSESSMENT_QUESTIONS)


def test_questions_for_direction_unknown_returns_all():
    assert len(questions_for_direction("чепуха")) == len(ASSESSMENT_QUESTIONS)


def _user(db, direction: str = "backend") -> User:
    user = User(name="Тест", direction=direction)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _skills(db) -> None:
    db.add_all(
        [
            Skill(name="Python", category="Программирование", description="Язык"),
            Skill(name="SQL", category="Данные", description="Базы данных"),
        ]
    )
    db.commit()


def test_assessment_creates_initial_skill_map(db_session):
    _skills(db_session)
    user = _user(db_session)

    result = AssessmentService(db_session).run(
        user,
        [
            {"question_id": 1, "option_index": 3},  # Python → уровень 3
            {"question_id": 2, "option_index": 1},  # SQL → уровень 1
        ],
    )

    assert result["user_id"] == user.id
    assert len(result["evaluated_skills"]) == 2
    by_name = {item["name"]: item for item in result["evaluated_skills"]}
    assert by_name["Python"]["level"] == 3
    assert by_name["SQL"]["level"] == 1
    assert by_name["SQL"]["experience"] > 0
    assert result["summary"]


def test_assessment_averages_options(db_session):
    _skills(db_session)
    user = _user(db_session)

    result = AssessmentService(db_session).run(
        user,
        [
            {"question_id": 1, "option_index": 1},
            {"question_id": 1, "option_index": 3},
        ],
    )

    by_name = {item["name"]: item for item in result["evaluated_skills"]}
    assert by_name["Python"]["level"] == 2


def test_assessment_rejects_unknown_question(db_session):
    _skills(db_session)
    user = _user(db_session)
    svc = AssessmentService(db_session)

    try:
        svc.run(user, [{"question_id": 999, "option_index": 0}])
        assert False, "должно быть исключение"
    except Exception as exc:  # noqa: BLE001
        assert "999" in str(exc)


def test_assessment_rejects_wrong_option_index(db_session):
    _skills(db_session)
    user = _user(db_session)
    svc = AssessmentService(db_session)

    try:
        svc.run(user, [{"question_id": 1, "option_index": 99}])
        assert False, "должно быть исключение"
    except Exception as exc:  # noqa: BLE001
        assert "99" in str(exc)

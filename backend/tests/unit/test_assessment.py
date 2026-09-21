"""Тесты первичной диагностики."""

from __future__ import annotations

from app.domain import Skill, User
from app.services.assessment import AssessmentService


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

    # Python дважды: уровень 1 и уровень 3 → среднее 2.
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
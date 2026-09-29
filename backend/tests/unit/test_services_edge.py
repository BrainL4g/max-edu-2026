"""Крайние ветки сервисов: ошибки валидации, итоги и пустые сценарии."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import InvalidDataError, NotFoundError
from backend.app.domain import (
    Mission,
    MissionOption,
    Resume,
    Skill,
    User,
    UserSkill,
)
from backend.app.services.assessment import AssessmentService
from backend.app.services.missions import MissionService
from backend.app.services.recommendations import RecommendationService
from backend.app.services.resume_analysis import ResumeAnalysisService


def _skill(db, name: str = "Python", category: str = "Программирование") -> Skill:
    skill = Skill(name=name, category=category)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def _user(db, direction: str | None = "backend") -> User:
    user = User(name="Тест", direction=direction)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _resume(db, user: User, text: str) -> Resume:
    resume = Resume(user_id=user.id, text=text)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def test_assessment_empty_answers_rejected(db_session):
    user = _user(db_session)
    with pytest.raises(InvalidDataError):
        AssessmentService(db_session).run(user, [])


def test_assessment_unknown_question_and_option_rejected(db_session):
    user = _user(db_session)
    _skill(db_session)
    svc = AssessmentService(db_session)
    with pytest.raises(InvalidDataError) as exc:
        svc.run(user, [{"question_id": 999, "option_index": 0}])
    assert "999" in str(exc.value)

    with pytest.raises(InvalidDataError) as exc:
        svc.run(user, [{"question_id": 1, "option_index": 100}])
    assert "некорректный" in str(exc.value)


def test_assessment_skips_skills_not_in_database(db_session):
    """Вопрос относится к навыку, которого нет в базе → нечего оценивать."""
    user = _user(db_session)
    with pytest.raises(InvalidDataError) as exc:
        AssessmentService(db_session).run(user, [{"question_id": 1, "option_index": 0}])
    assert "оценить" in str(exc.value)


@pytest.mark.parametrize(
    ("average", "expected"),
    [
        (0.5, "начальный"),
        (1.5, "базовый"),
        (2.5, "средний"),
        (3.0, "высокий"),
    ],
)
def test_assessment_summary_branches(average: float, expected: str) -> None:
    assert expected in AssessmentService._summary(average)


def _mission(db, correct_text: str = "Верно") -> Mission:
    skill = _skill(db)
    mission = Mission(
        skill_id=skill.id,
        difficulty="easy",
        scenario="Задание",
        explanation="Объяснение",
    )
    mission.options.append(MissionOption(text=correct_text, is_correct=True))
    mission.options.append(MissionOption(text="Неверно", is_correct=False))
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def test_mission_submit_invalid_option_rejected(db_session):
    mission = _mission(db_session)
    user = _user(db_session)
    with pytest.raises(InvalidDataError):
        MissionService(db_session).submit_answer(user.id, mission.id, 999999)


def test_mission_get_result_by_attempt_id(db_session):
    mission = _mission(db_session)
    user = _user(db_session)
    svc = MissionService(db_session)

    submitted = svc.submit_answer(user.id, mission.id, mission.options[0].id)
    fetched = svc.get_result(submitted["attempt_id"])

    assert fetched["attempt_id"] == submitted["attempt_id"]
    assert fetched["is_correct"] is True
    assert fetched["skill_name"] == "Python"
    assert fetched["skill_level_after"] == 0


def test_mission_get_history_unknown_user(db_session):
    with pytest.raises(NotFoundError):
        MissionService(db_session).get_history(999999)


def test_recommend_no_gaps_summary(db_session):
    required = [
        ("Python", "Программирование"),
        ("SQL", "Данные"),
        ("Git", "Инструменты"),
        ("Алгоритмы и структуры данных", "Программирование"),
        ("Docker", "Инструменты"),
    ]
    skills = [_skill(db_session, name, category) for name, category in required]
    user = _user(db_session)
    for skill in skills:
        db_session.add(UserSkill(user_id=user.id, skill_id=skill.id, level=3, experience=600))
    db_session.commit()

    svc = RecommendationService(db_session)
    result = svc.recommend(user.id)

    assert result["gaps"] == []
    assert "не выявлены" in result["summary"].lower()
    assert result["courses"] == []
    assert result["internships"] == []


def test_analyze_short_resume_collects_issues(db_session):
    _skill(db_session, "Python")
    _skill(db_session, "SQL", "Данные")
    user = _user(db_session)
    resume = _resume(db_session, user, "Питон и SQL — мои навыки.")

    result = ResumeAnalysisService(db_session).analyze(resume.id)

    issues = " ".join(result["issues"])
    assert "контактные" in issues
    assert "короткое" in issues
    assert "ссылок" in issues
    assert "образование" in issues
    assert "направлением" in issues


def test_analyze_without_any_skills(db_session):
    user = _user(db_session)
    resume = _resume(db_session, user, "Резюме без навыков, только текст о себе.")

    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert result["found_skills"] == []
    assert "профессиональные навыки" in " ".join(result["issues"])


def test_analyze_without_direction(db_session):
    _skill(db_session, "Python")
    user = _user(db_session, direction=None)
    resume = _resume(
        db_session,
        user,
        (
            "Иван +7 999 123-45-67 ivan@example.com\n"
            "Образование: МГТУ, 3 курс\n"
            "Писал скрипты на Python, git, sql.\n"
            "https://github.com/ivan"
        ),
    )

    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert "Укажите направление" in result["summary"]


def test_analyze_full_direction_match(db_session):
    for name, category in [
        ("Python", "Программирование"),
        ("SQL", "Данные"),
        ("Git", "Инструменты"),
        ("Docker", "Инструменты"),
        ("Алгоритмы и структуры данных", "Программирование"),
    ]:
        _skill(db_session, name, category)
    user = _user(db_session)
    body = (
        "Проекты на Python и SQL: автоматизация, JOIN-запросы, GROUP BY. "
        "Версионирование в Git (GitHub). Контейнеризация Docker. "
        "Алгоритмы и структуры данных: сортировки, графы. "
    ) * 6
    resume = _resume(
        db_session,
        user,
        (
            "Иван, +7 999 123-45-67, ivan@example.com\n"
            "Образование: МГТУ, 3 курс\n"
            f"{body}\nСсылки: https://github.com/ivan"
        ),
    )

    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert result["missing_skills"] == []
    assert result["direction_match"] >= 70
    assert "отлично соответствует" in result["summary"]
    recommendations = " ".join(result["recommendations"])
    assert "обязательные навыки" in recommendations

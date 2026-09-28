"""Тесты рекомендаций: пробелы → курсы + стажировки."""

from __future__ import annotations

from backend.app.domain import Course, Internship, Skill, User, UserSkill
from backend.app.services.recommendations import RecommendationService


def _seed(db):
    python = Skill(name="Python", category="Программирование")
    sql = Skill(name="SQL", category="Данные")
    docker = Skill(name="Docker", category="Инструменты")
    db.add_all([python, sql, docker])
    db.commit()

    course_python = Course(
        title="Python Pro",
        platform="Stepik",
        level="intermediate",
        category="Программирование",
        cost=0.0,
        format="online",
    )
    course_python.skills = [python]
    course_docker = Course(
        title="Docker и контейнеры",
        platform="OTUS",
        level="advanced",
        category="Инструменты",
        cost=3000.0,
        format="online",
    )
    course_docker.skills = [docker, python]
    db.add_all([course_python, course_docker])

    internship = Internship(
        title="Python-стажировка",
        company="Яндекс",
        level="beginner",
        city="Москва",
        remote=False,
        format="office",
        direction="backend",
    )
    internship.skills = [python, sql]
    db.add(internship)
    db.commit()

    user = User(name="Студент", direction="backend")
    db.add(user)
    db.commit()
    # Python — уровень 1 (пробел до целевого 3), SQL — пропущен (пробел по направлению).
    db.add(UserSkill(user_id=user.id, skill_id=python.id, level=1, experience=100))
    db.commit()
    db.refresh(user)
    return user, python, sql, docker


def test_recommendations_find_gaps(db_session):
    user, python, sql, _ = _seed(db_session)
    svc = RecommendationService(db_session)

    gaps = svc._gaps(user)
    names = {gap["name"] for gap in gaps}
    assert "Python" in names
    assert "SQL" in names  # требуемый направлением навык отсутствует
    by_name = {gap["name"]: gap for gap in gaps}
    assert by_name["Python"]["current_level"] == 1


def test_recommended_courses_cover_gaps(db_session):
    user, _, _, _ = _seed(db_session)
    svc = RecommendationService(db_session)

    courses = svc.recommend_courses(user.id)

    assert len(courses) == 2
    titles = [course.title for course in courses]
    assert "Python Pro" in titles


def test_recommended_internships_match_direction(db_session):
    user, _, _, _ = _seed(db_session)
    svc = RecommendationService(db_session)

    internships = svc.recommend_internships(user.id)

    assert len(internships) == 1
    assert internships[0].company == "Яндекс"


def test_recommend_full_payload(db_session):
    user, _, _, _ = _seed(db_session)
    svc = RecommendationService(db_session)

    result = svc.recommend(user.id)

    assert result["user_id"] == user.id
    assert result["gaps"]
    assert result["courses"]
    assert result["internships"]
    assert result["summary"]

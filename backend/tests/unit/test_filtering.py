"""Тесты фильтрации курсов и стажировок."""

from __future__ import annotations

from backend.app.domain import Course, Internship, Skill
from backend.app.repositories.course_repository import CourseRepository
from backend.app.repositories.internship_repository import InternshipRepository


def _seed_courses(db):
    python = Skill(name="Python", category="Программирование")
    sql = Skill(name="SQL", category="Данные")
    git = Skill(name="Git", category="Инструменты")
    db.add_all([python, sql, git])
    db.commit()

    courses = [
        Course(
            title="Python с нуля",
            description="Базовый Python",
            platform="Stepik",
            level="beginner",
            category="Программирование",
            cost=0.0,
            format="online",
        ),
        Course(
            title="Анализ данных",
            description="SQL и Python для анализа",
            platform="Coursera",
            level="intermediate",
            category="Данные",
            cost=1500.0,
            format="online",
        ),
        Course(
            title="Git за один день",
            description="Офлайн-интенсив",
            platform="YouTube",
            level="beginner",
            category="Инструменты",
            cost=0.0,
            format="offline",
        ),
    ]
    courses[0].skills = [python]
    courses[1].skills = [python, sql]
    courses[2].skills = [git]
    db.add_all(courses)
    db.commit()
    return python, sql, git, courses


def test_course_filter_by_category(db_session):
    _, _, _, courses = _seed_courses(db_session)
    result = CourseRepository(db_session).list(category="Программирование")
    assert [c.title for c in result] == ["Python с нуля"]


def test_course_filter_by_platform(db_session):
    _seed_courses(db_session)
    result = CourseRepository(db_session).list(platform="youtube")
    assert [c.title for c in result] == ["Git за один день"]


def test_course_filter_by_price(db_session):
    _seed_courses(db_session)
    result = CourseRepository(db_session).list(price_max=100)
    assert {c.title for c in result} == {"Python с нуля", "Git за один день"}


def test_course_search(db_session):
    _seed_courses(db_session)
    result = CourseRepository(db_session).list(search="данных")
    assert [c.title for c in result] == ["Анализ данных"]


def test_course_filter_by_skill(db_session):
    _, sql, _, _ = _seed_courses(db_session)
    result = CourseRepository(db_session).list(skill_ids=[sql.id])
    assert [c.title for c in result] == ["Анализ данных"]


def _seed_internships(db):
    python = Skill(name="Python", category="Программирование")
    sql = Skill(name="SQL", category="Данные")
    testing = Skill(name="Testing", category="QA")
    db.add_all([python, sql, testing])
    db.commit()

    internships = [
        Internship(
            title="Python-стажёр",
            company="Яндекс",
            level="beginner",
            city="Москва",
            remote=False,
            format="office",
            direction="backend",
        ),
        Internship(
            title="Аналитик удалённо",
            company="Т-Банк",
            level="intermediate",
            city=None,
            remote=True,
            format="remote",
            direction="data",
        ),
        Internship(
            title="QA-инженер",
            company="Ozon",
            level="beginner",
            city="Казань",
            remote=False,
            format="office",
            direction="qa",
        ),
    ]
    internships[0].skills = [python, sql]
    internships[1].skills = [sql]
    internships[2].skills = [testing, sql]
    db.add_all(internships)
    db.commit()
    return python, sql, internships


def test_internship_filter_by_direction(db_session):
    _seed_internships(db_session)
    result = InternshipRepository(db_session).list(direction="backend")
    assert [i.company for i in result] == ["Яндекс"]


def test_internship_filter_by_remote(db_session):
    _seed_internships(db_session)
    result = InternshipRepository(db_session).list(remote=True)
    assert [i.company for i in result] == ["Т-Банк"]


def test_internship_filter_by_city(db_session):
    _seed_internships(db_session)
    result = InternshipRepository(db_session).list(city="Казань")
    assert [i.company for i in result] == ["Ozon"]


def test_internship_filter_by_skill(db_session):
    _, sql, _ = _seed_internships(db_session)
    result = InternshipRepository(db_session).list(skill_ids=[sql.id])
    assert {i.company for i in result} == {"Яндекс", "Т-Банк", "Ozon"}


def test_internship_search(db_session):
    _seed_internships(db_session)
    result = InternshipRepository(db_session).list(search="удалённо")
    assert [i.company for i in result] == ["Т-Банк"]

"""Тесты рекомендаций: пробелы → курсы + стажировки."""

from __future__ import annotations

from backend.app.domain import Course, Internship, Role, RoleSkill, Skill, User, UserSkill
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


def test_gaps_use_role_requirements(db_session):
    """Пробелы считаются по требованиям целевой роли, а не по общему уровню 3."""
    python = Skill(name="Python", category="Программирование")
    sql = Skill(name="SQL", category="Данные")
    db_session.add_all([python, sql])
    db_session.commit()

    role = Role(name="Junior Python", direction="backend", level="junior", description="Роль")
    db_session.add(role)
    db_session.commit()
    db_session.add_all(
        [
            RoleSkill(
                role_id=role.id,
                skill_id=python.id,
                required_level=2,
                importance=0.9,
                is_mandatory=True,
            ),
            RoleSkill(
                role_id=role.id,
                skill_id=sql.id,
                required_level=4,
                importance=0.5,
                is_mandatory=False,
            ),
        ]
    )
    db_session.commit()

    user = User(name="Целевой", direction="frontend")
    db_session.add(user)
    db_session.commit()
    user.target_role_id = role.id
    db_session.commit()
    db_session.add(UserSkill(user_id=user.id, skill_id=python.id, level=2, experience=250))
    db_session.commit()

    svc = RecommendationService(db_session)
    # Python уже на 2 (требование 2) — пробела нет; SQL ниже 4 — пробел есть.
    gaps = svc._gaps(user)
    by_name = {gap["name"]: gap for gap in gaps}
    assert "Python" not in by_name
    assert by_name["SQL"]["target_level"] == 4
    assert by_name["SQL"]["current_level"] == 0


def test_recommend_internships_use_role_direction_bonus(db_session):
    user, python, sql, _ = _seed(db_session)
    frontend_internship = Internship(
        title="Frontend-стажировка",
        company="ВК",
        level="beginner",
        city="СПб",
        remote=True,
        format="remote",
        direction="frontend",
    )
    frontend_internship.skills = [python, sql]
    db_session.add(frontend_internship)
    db_session.commit()

    # Бонус направления берётся из роли, а не из user.direction.
    role = Role(name="Backend Trainee", direction="backend", level="junior", description="Бэкенд")
    db_session.add(role)
    db_session.commit()
    user.target_role_id = role.id
    user.direction = "frontend"
    db_session.commit()

    internships = RecommendationService(db_session).recommend_internships(user.id)
    assert internships[0].company == "Яндекс"


def test_recommend_internships_without_direction_bonus(db_session):
    user, _, _, _ = _seed(db_session)
    # Направление дизайна не совпадает — бонус не начисляется, но стажировка живёт.
    user.direction = "design"
    db_session.commit()

    internships = RecommendationService(db_session).recommend_internships(user.id)
    assert internships[0].company == "Яндекс"


def test_gaps_unknown_direction_are_empty(db_session):
    user, _, _, _ = _seed(db_session)
    user.direction = "неизвестно"
    db_session.commit()

    assert RecommendationService(db_session)._gaps(user) == []

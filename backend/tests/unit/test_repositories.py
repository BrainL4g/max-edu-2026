"""Тесты репозиториев: получение объектов, обновление и ветки ошибок."""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import (
    Attempt,
    Course,
    Internship,
    Mission,
    Resume,
    Role,
    RoleSkill,
    Skill,
    User,
)
from backend.app.repositories.course_repository import CourseRepository
from backend.app.repositories.internship_repository import InternshipRepository
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.resume_repository import ResumeRepository
from backend.app.repositories.role_repository import RoleRepository
from backend.app.repositories.skill_repository import SkillRepository
from backend.app.repositories.user_repository import UserRepository


def _user(db) -> User:
    user = User(name="Тест", direction="backend")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _skill(db) -> Skill:
    skill = Skill(name="Python", category="Программирование")
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


# --- SkillRepository ----------------------------------------------------------


def test_skill_repository_get_found_and_missing(db_session):
    skill = _skill(db_session)
    repo = SkillRepository(db_session)
    assert repo.get(skill.id).name == "Python"
    assert repo.get_by_name("Python").id == skill.id
    assert repo.get_by_name("нет такого") is None
    with pytest.raises(NotFoundError):
        repo.get(999999)


def test_skill_repository_get_by_ids(db_session):
    skill = _skill(db_session)
    other = Skill(name="SQL", category="Данные")
    db_session.add(other)
    db_session.commit()
    by_id = SkillRepository(db_session).get_by_ids([skill.id, other.id, 999999])
    assert set(by_id) == {skill.id, other.id}


def test_user_skill_queries_and_upsert(db_session):
    user = _user(db_session)
    skill = _skill(db_session)
    repo = SkillRepository(db_session)

    assert repo.get_user_skill(user.id, skill.id) is None
    assert repo.get_user_skills(user.id) == []

    created = repo.upsert_user_skill(user.id, skill.id, level=2, experience=150)
    assert created.id is not None
    assert repo.get_user_skill(user.id, skill.id).level == 2

    updated = repo.upsert_user_skill(user.id, skill.id, level=3, experience=250)
    assert updated.id == created.id
    assert updated.level == 3
    assert updated.experience == 250

    loaded = repo.get_user_skills(user.id)
    assert len(loaded) == 1
    assert loaded[0].skill.name == "Python"  # selectinload навыка


# --- UserRepository -----------------------------------------------------------


def test_user_repository_list_and_update(db_session):
    db_session.add_all([User(name="Первый"), User(name="Второй")])
    db_session.commit()
    repo = UserRepository(db_session)

    assert {u.name for u in repo.list()} == {"Первый", "Второй"}

    first = repo.list()[0]
    updated = repo.update(first, name="Новое имя", goal=None)
    assert updated.name == "Новое имя"
    assert repo.get(first.id).goal is None


def test_get_or_create_by_max_recovers_from_race(db_session, monkeypatch):
    """Конкурентная запись: коммит падает, но существующий пользователь находится."""
    existing = User(max_user_id=777, name="Гонщик")
    db_session.add(existing)
    db_session.commit()
    existing_id = existing.id

    real_scalar = db_session.scalar
    calls = 0

    def fake_scalar(stmt):
        nonlocal calls
        if calls == 0:
            calls += 1
            return None  # имитируем гонку: запись ещё «не видна»
        return real_scalar(stmt)

    def fake_commit() -> None:
        raise IntegrityError("INSERT INTO users", {}, Exception("duplicate"))

    monkeypatch.setattr(db_session, "scalar", fake_scalar)
    monkeypatch.setattr(db_session, "commit", fake_commit)

    user = UserRepository(db_session).get_or_create_by_max(777, "Гонщик")
    assert user.id == existing_id


def test_get_or_create_by_max_reraises_when_race_lost(db_session, monkeypatch):
    """Если после отката записи всё ещё нет — пробрасываем IntegrityError."""
    calls = 0

    def fake_scalar(stmt):
        nonlocal calls
        calls += 1
        return None

    def fake_commit() -> None:
        raise IntegrityError("INSERT INTO users", {}, Exception("duplicate"))

    monkeypatch.setattr(db_session, "scalar", fake_scalar)
    monkeypatch.setattr(db_session, "commit", fake_commit)

    with pytest.raises(IntegrityError):
        UserRepository(db_session).get_or_create_by_max(888, "Новичок")


# --- MissionRepository --------------------------------------------------------


def _mission(db) -> Mission:
    skill = _skill(db)
    mission = Mission(skill_id=skill.id, difficulty="easy", scenario="Задание")
    db.add(mission)
    db.commit()
    db.refresh(mission)
    return mission


def test_mission_repository_get_and_missing(db_session):
    mission = _mission(db_session)
    repo = MissionRepository(db_session)
    assert repo.get(mission.id).id == mission.id
    with pytest.raises(NotFoundError):
        repo.get(999999)
    with pytest.raises(NotFoundError):
        repo.get_with_options(999999)


def test_mission_repository_attempts(db_session):
    user = _user(db_session)
    mission = _mission(db_session)
    attempt = Attempt(
        user_id=user.id,
        mission_id=mission.id,
        answer_option_id=1,
        is_correct=True,
        xp_earned=10,
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(attempt)

    repo = MissionRepository(db_session)
    assert repo.get_attempt(attempt.id).id == attempt.id
    with pytest.raises(NotFoundError):
        repo.get_attempt(999999)

    history = repo.list_attempts(user.id)
    assert len(history) == 1
    assert history[0].id == attempt.id


# --- CourseRepository ---------------------------------------------------------


def test_course_repository_get_and_filters(db_session):
    python = _skill(db_session)
    course = Course(
        title="Курс по Python",
        description="Введение в Python",
        platform="Stepik",
        level="beginner",
        category="Программирование",
        cost=100.0,
        format="offline",
    )
    course.skills = [python]
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    repo = CourseRepository(db_session)
    assert repo.get(course.id).id == course.id
    with pytest.raises(NotFoundError):
        repo.get(999999)

    assert repo.list_all(platform="stepik")[0].id == course.id
    assert repo.list_all(search="python")[0].id == course.id
    assert repo.list_all(skill_ids=[python.id])[0].id == course.id
    assert repo.list_all(format_="online") == []
    assert repo.list_all(level="intermediate") == []
    assert repo.list_all(price_max=50) == []
    assert repo.list_all(category="any")


# --- InternshipRepository -----------------------------------------------------


def test_internship_repository_get_and_filters(db_session):
    python = _skill(db_session)
    internship = Internship(
        title="Python-стажировка",
        company="Яндекс",
        level="beginner",
        city="Москва",
        remote=True,
        format="remote",
        direction="backend",
    )
    internship.skills = [python]
    db_session.add(internship)
    db_session.commit()
    db_session.refresh(internship)

    repo = InternshipRepository(db_session)
    assert repo.get(internship.id).id == internship.id
    with pytest.raises(NotFoundError):
        repo.get(999999)

    assert repo.list_all(direction="backend")[0].id == internship.id
    assert repo.list_all(city="Казань") == []
    assert repo.list_all(format_="office") == []
    assert repo.list_all(level="advanced") == []
    assert repo.list_all(remote=True)[0].id == internship.id
    assert repo.list_all(search="стажир")[0].id == internship.id
    assert repo.list_all(skill_ids=[python.id])[0].id == internship.id


# --- ResumeRepository ---------------------------------------------------------


def test_resume_repository_get_and_analysis(db_session):
    user = _user(db_session)
    resume = Resume(user_id=user.id, text="Текст резюме")
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    repo = ResumeRepository(db_session)
    assert repo.get(resume.id).id == resume.id
    with pytest.raises(NotFoundError):
        repo.get(999999)
    assert [r.id for r in repo.list_by_user(user.id)] == [resume.id]

    saved = repo.save_analysis(resume.id, {"found_skills": ["Python"]})
    assert saved.result["found_skills"] == ["Python"]
    assert repo.get_analysis(resume.id).result["found_skills"] == ["Python"]

    # повторный вызов обновляет существующую запись анализа
    updated = repo.save_analysis(resume.id, {"found_skills": ["SQL"]})
    assert updated.id == saved.id
    assert updated.result["found_skills"] == ["SQL"]


# --- RoleRepository -----------------------------------------------------------


def _role(db, name: str = "Backend Junior") -> Role:
    skill = Skill(name=f"Навык {name}", category="Программирование")
    role = Role(name=name, direction="backend", level="junior")
    role.requirements.append(
        RoleSkill(
            skill=skill,
            required_level=3,
            importance=0.9,
            is_mandatory=True,
        )
    )
    db.add(skill)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def test_role_repository_get_and_list(db_session):
    first = _role(db_session, name="Backend Junior")
    second = _role(db_session, name="QA Junior")

    repo = RoleRepository(db_session)
    assert [r.id for r in repo.list_all()] == [first.id, second.id]

    assert repo.get(first.id).name == "Backend Junior"
    assert len(repo.get(first.id).requirements) == 1
    with pytest.raises(NotFoundError):
        repo.get(999999)

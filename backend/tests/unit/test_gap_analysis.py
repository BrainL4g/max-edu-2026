"""Тесты gap-анализа: соответствие роли, пробелы и пустые состояния."""

from __future__ import annotations

import pytest

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Role, RoleSkill, Skill, User, UserSkill
from backend.app.services.gap_analysis import GapAnalysisService
from backend.app.services.skills import LEVEL_THRESHOLDS


def _user(db) -> User:
    user = User(name="Маша")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _skill(db, name: str = "Python") -> Skill:
    skill = Skill(name=name, category="Программирование")
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def _role_with_two_skills(db, python: Skill, sql: Skill) -> Role:
    role = Role(name="Backend Junior", direction="backend", level="junior")
    role.requirements.append(
        RoleSkill(skill=python, required_level=3, importance=0.9, is_mandatory=True)
    )
    role.requirements.append(
        RoleSkill(skill=sql, required_level=2, importance=0.6, is_mandatory=True)
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def test_analyze_without_target_role(db_session):
    user = _user(db_session)
    result = GapAnalysisService(db_session).analyze(user.id)

    assert result["user_id"] == user.id
    assert result["role"] is None
    assert result["match_percent"] is None
    assert result["items"] == []
    assert "не выбрана" in result["summary"]


def test_analyze_unknown_user_raises(db_session):
    with pytest.raises(NotFoundError):
        GapAnalysisService(db_session).analyze(999999)


def test_analyze_with_gaps_and_match_percent(db_session):
    user = _user(db_session)
    python = _skill(db_session, "Python")
    sql = _skill(db_session, "SQL")
    role = _role_with_two_skills(db_session, python, sql)
    user.target_role_id = role.id
    db_session.add(
        UserSkill(
            experience=LEVEL_THRESHOLDS[3],
            level=3,
            user_id=user.id,
            skill_id=python.id,
        )
    )
    db_session.commit()

    result = GapAnalysisService(db_session).analyze(user.id)

    assert result["role"]["name"] == "Backend Junior"
    assert result["match_percent"] == 60  # 0.9*1 + 0.6*0 из суммы 1.5
    assert len(result["items"]) == 2

    python_item = next(item for item in result["items"] if item["name"] == "Python")
    assert python_item["current_level"] == 3
    assert python_item["required_level"] == 3
    assert python_item["gap"] == 0
    assert python_item["importance"] == 0.9
    assert python_item["is_mandatory"] is True

    sql_item = next(item for item in result["items"] if item["name"] == "SQL")
    assert sql_item["current_level"] == 0
    assert sql_item["gap"] == 2
    assert result["items"][0]["name"] == "SQL"
    assert "Не хватает" in result["summary"] and "SQL" in result["summary"]


def test_analyze_full_match(db_session):
    user = _user(db_session)
    python = _skill(db_session, "Python")
    sql = _skill(db_session, "SQL")
    role = _role_with_two_skills(db_session, python, sql)
    user.target_role_id = role.id
    db_session.add(
        UserSkill(
            experience=LEVEL_THRESHOLDS[3],
            level=3,
            user_id=user.id,
            skill_id=python.id,
        )
    )
    db_session.add(
        UserSkill(
            experience=LEVEL_THRESHOLDS[2],
            level=2,
            user_id=user.id,
            skill_id=sql.id,
        )
    )
    db_session.commit()

    result = GapAnalysisService(db_session).analyze(user.id)

    assert result["match_percent"] == 100
    assert all(item["gap"] == 0 for item in result["items"])
    assert "🎉" in result["summary"]


def test_analyze_non_mandatory_skill_counts_less(db_session):
    user = _user(db_session)
    python = _skill(db_session, "Python")
    docker = _skill(db_session, "Docker")
    role = Role(name="Backend Junior", direction="backend", level="junior")
    role.requirements.append(
        RoleSkill(skill=python, required_level=3, importance=0.9, is_mandatory=True)
    )
    role.requirements.append(
        RoleSkill(skill=docker, required_level=1, importance=0.4, is_mandatory=False)
    )
    db_session.add(role)
    db_session.commit()
    user.target_role_id = role.id
    db_session.add(
        UserSkill(
            experience=LEVEL_THRESHOLDS[3],
            level=3,
            user_id=user.id,
            skill_id=python.id,
        )
    )
    db_session.commit()

    result = GapAnalysisService(db_session).analyze(user.id)

    docker_item = next(item for item in result["items"] if item["name"] == "Docker")
    assert docker_item["is_mandatory"] is False
    assert result["match_percent"] == round(0.9 / 1.3 * 100)

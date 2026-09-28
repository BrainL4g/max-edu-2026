"""Тесты расчёта навыков и Skill Map."""

from __future__ import annotations

import pytest

from backend.app.domain import Mission, Skill, User, UserSkill
from backend.app.services.skills import (
    LEVEL_THRESHOLDS,
    SkillService,
    level_from_xp,
    progress_for_level,
)


def test_level_from_xp_thresholds():
    assert level_from_xp(0) == 0
    assert level_from_xp(99) == 0
    assert level_from_xp(100) == 1
    assert level_from_xp(250) == 2
    assert level_from_xp(1000) == 5
    assert level_from_xp(5000) == 5


def test_progress_for_level():
    assert progress_for_level(0, 0) == 0.0
    assert progress_for_level(1, 150) == pytest.approx(33.3, abs=0.1)
    assert progress_for_level(5, 1000) == 100.0


def test_apply_mission_result_levels_up(db_session):
    skill = Skill(name="Python", category="Программирование")
    db_session.add(skill)
    db_session.commit()

    user = User(name="Тест", direction="backend")
    db_session.add(user)
    db_session.commit()

    db_session.add(UserSkill(user_id=user.id, skill_id=skill.id, level=0, experience=80))
    db_session.commit()

    mission = Mission(skill_id=skill.id, difficulty="easy", scenario="Задание", reward_xp=40)
    db_session.add(mission)
    db_session.commit()

    xp_gained, new_level, total_xp = SkillService(db_session).apply_mission_result(
        user, mission, True
    )

    assert xp_gained == 40  # без бонуса за easy
    assert total_xp == 120
    assert new_level == 1  # порог 100 перейдён


def test_apply_mission_result_wrong_answer_gives_small_xp(db_session):
    skill = Skill(name="Python", category="Программирование")
    db_session.add(skill)
    db_session.commit()
    user = User(name="Тест")
    db_session.add(user)
    db_session.commit()
    mission = Mission(skill_id=skill.id, difficulty="hard", scenario="Задание", reward_xp=50)
    db_session.add(mission)
    db_session.commit()

    xp_gained, _, _ = SkillService(db_session).apply_mission_result(user, mission, False)
    assert xp_gained == max(3, 50 // 5) == 10


def test_skill_map_shape(db_session):
    skill = Skill(name="SQL", category="Данные")
    db_session.add(skill)
    db_session.commit()
    user = User(name="Тест")
    db_session.add(user)
    db_session.commit()
    db_session.add(UserSkill(user_id=user.id, skill_id=skill.id, level=0, experience=200))
    db_session.commit()

    skill_map = SkillService(db_session).get_skill_map(user.id)

    assert len(skill_map) == 1
    item = skill_map[0]
    assert item["name"] == "SQL"
    assert item["level"] == 1
    assert 0 <= item["progress"] <= 100
    assert item["next_level_xp"] == LEVEL_THRESHOLDS[2] - 200

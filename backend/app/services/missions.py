"""Игровая система: получить миссию → принять ответ → проверить → XP → результат."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import InvalidDataError
from backend.app.domain import Attempt, Mission, UserSkill
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.skills import SkillService


class MissionService:
    """Сервис игровых миссий."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.missions = MissionRepository(db)
        self.users = UserRepository(db)
        self.skill_service = SkillService(db)

    def get_next_mission(self, user_id: int) -> Mission | None:
        """Следующая миссия: приоритет — слабые навыки и непройденные задания."""
        self.users.get(user_id)
        solved = self.missions.solved_mission_ids(user_id)

        user_skills = {
            row.skill_id: row
            for row in self.db.scalars(select(UserSkill).where(UserSkill.user_id == user_id))
        }

        candidates = [m for m in self.missions.list_all() if m.id not in solved]
        if not candidates:
            return None

        def priority(mission: Mission) -> tuple[int, int]:
            user_skill = user_skills.get(mission.skill_id)
            level = user_skill.level if user_skill else 0
            difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
            return level, difficulty_order.get(mission.difficulty, 1)

        best = min(candidates, key=priority)
        return self.missions.get_with_options(best.id)

    def get_mission(self, mission_id: int) -> Mission:
        """Задание по id с вариантами ответов."""
        return self.missions.get_with_options(mission_id)

    def submit_answer(self, user_id: int, mission_id: int, option_id: int) -> dict[str, Any]:
        """Проверить ответ, начислить XP и вернуть результат."""
        user = self.users.get(user_id)
        mission = self.missions.get_with_options(mission_id)

        option = next((o for o in mission.options if o.id == option_id), None)
        if option is None:
            raise InvalidDataError(f"Вариант ответа {option_id} не принадлежит миссии {mission_id}")

        is_correct = option.is_correct
        xp_gained, new_level, _ = self.skill_service.apply_mission_result(user, mission, is_correct)
        attempt = self.missions.create_attempt(
            user_id=user_id,
            mission_id=mission_id,
            answer_option_id=option_id,
            is_correct=is_correct,
            xp_earned=xp_gained,
        )
        correct_option = next((o for o in mission.options if o.is_correct), None)
        return {
            "attempt_id": attempt.id,
            "mission_id": mission.id,
            "is_correct": is_correct,
            "xp_earned": xp_gained,
            "explanation": mission.explanation,
            "correct_option_id": correct_option.id if correct_option else None,
            "skill_id": mission.skill_id,
            "skill_name": mission.skill.name,
            "skill_level_after": new_level,
        }

    def get_result(self, attempt_id: int) -> dict[str, Any]:
        """Результат по конкретной попытке."""
        attempt = self.missions.get_attempt(attempt_id)
        mission = self.missions.get_with_options(attempt.mission_id)
        correct_option = next((o for o in mission.options if o.is_correct), None)

        user_skill = self.db.scalar(
            select(UserSkill).where(
                UserSkill.user_id == attempt.user_id,
                UserSkill.skill_id == mission.skill_id,
            )
        )
        level_after = user_skill.level if user_skill else 0
        return {
            "attempt_id": attempt.id,
            "mission_id": attempt.mission_id,
            "is_correct": attempt.is_correct,
            "xp_earned": attempt.xp_earned,
            "explanation": mission.explanation,
            "correct_option_id": correct_option.id if correct_option else None,
            "skill_id": mission.skill_id,
            "skill_name": mission.skill.name,
            "skill_level_after": level_after,
        }

    def get_history(self, user_id: int) -> list[Attempt]:
        """История попыток пользователя."""
        self.users.get(user_id)
        return self.missions.list_attempts(user_id)

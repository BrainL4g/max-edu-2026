"""Игровая система: получить миссию → принять ответ → проверить → XP → результат."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import InvalidDataError
from backend.app.domain import Attempt, Mission, UserSkill
from backend.app.repositories.mission_repository import DIFFICULTY_RANK, MissionRepository
from backend.app.repositories.role_repository import RoleRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.skills import SkillService


class MissionService:
    """Сервис игровых миссий."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.missions = MissionRepository(db)
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.skill_service = SkillService(db)

    def get_next_mission(self, user_id: int) -> dict[str, Any]:
        """Следующая миссия строго по целевой роли.

        Пул кандидатов — только миссии по навыкам из требований роли. Приоритет:
        навыки с пробелом (обязательные раньше, затем по убыванию
        gap × importance), внутри навыка — ещё не пробованные раньше тех, на
        которых была ошибка, затем сложность, затем id. Когда по цели пройдено
        всё — ``all_done``; без цели — ``no_goal``.
        """
        user = self.users.get(user_id)
        if user.target_role_id is None:
            return {"status": "no_goal", "done": 0, "total": 0, "mission": None}

        role = self.roles.get(user.target_role_id)
        role_skill = {requirement.skill_id: requirement for requirement in role.requirements}

        user_levels = {
            row.skill_id: row.level
            for row in self.db.scalars(select(UserSkill).where(UserSkill.user_id == user_id))
        }

        missions = [m for m in self.missions.list_all() if m.skill_id in role_skill]
        role_ids = {m.id for m in missions}
        solved = self.missions.solved_mission_ids(user_id)
        done = len(solved & role_ids)
        total = len(role_ids)

        candidates = [m for m in missions if m.id not in solved]
        if not candidates:
            return {"status": "all_done", "done": done, "total": total, "mission": None}

        failed = self.missions.error_mission_ids(user_id)

        def priority(mission: Mission) -> tuple[int, int, float, int, int, int]:
            requirement = role_skill[mission.skill_id]
            gap = max(0, requirement.required_level - user_levels.get(mission.skill_id, 0))
            return (
                0 if gap > 0 else 1,  # навыки с пробелом — первыми
                0 if requirement.is_mandatory else 1,
                -(gap * requirement.importance),  # больший пробел × важность — раньше
                1 if mission.id in failed else 0,  # не пробованные — раньше ошибочных
                DIFFICULTY_RANK.get(mission.difficulty, 1),
                mission.id,
            )

        best = min(candidates, key=priority)
        return {
            "status": "ok",
            "done": done,
            "total": total,
            "mission": self.missions.get_with_options(best.id),
        }

    def get_mission(self, mission_id: int) -> Mission:
        """Задание по id с вариантами ответов."""
        return self.missions.get_with_options(mission_id)

    def submit_answer(self, user_id: int, mission_id: int, option_id: int) -> dict[str, Any]:
        """Проверить ответ и начислить XP (за верный ответ — один раз).

        Уже решённая верно миссия повторно XP не приносит и не создаёт новых
        записей: возвращается ``already_solved=true``. Обновление навыка и
        создание попытки выполняются одной транзакцией.
        """
        user = self.users.get(user_id)
        mission = self.missions.get_with_options(mission_id)

        option = next((o for o in mission.options if o.id == option_id), None)
        if option is None:
            raise InvalidDataError(f"Вариант ответа {option_id} не принадлежит миссии {mission_id}")

        correct_option = next((o for o in mission.options if o.is_correct), None)
        correct_id = correct_option.id if correct_option else None
        correct_text = correct_option.text if correct_option else None

        previous = self.missions.latest_correct_attempt(user_id, mission_id)
        if previous is not None:
            level = self._skill_level(user_id, mission.skill_id)
            return {
                "attempt_id": previous.id,
                "mission_id": mission.id,
                "is_correct": True,
                "xp_earned": 0,
                "explanation": mission.explanation,
                "correct_option_id": correct_id,
                "correct_option_text": correct_text,
                "skill_id": mission.skill_id,
                "skill_name": mission.skill.name,
                "skill_level_before": level,
                "skill_level_after": level,
                "already_solved": True,
            }

        level_before = self._skill_level(user_id, mission.skill_id)
        is_correct = option.is_correct

        xp_gained, new_level, _ = self.skill_service.apply_mission_result(
            user, mission, is_correct, commit=False
        )
        attempt = self.missions.create_attempt(
            user_id=user_id,
            mission_id=mission_id,
            answer_option_id=option_id,
            is_correct=is_correct,
            xp_earned=xp_gained,
            commit=False,
        )
        self.db.commit()

        return {
            "attempt_id": attempt.id,
            "mission_id": mission.id,
            "is_correct": is_correct,
            "xp_earned": xp_gained,
            "explanation": mission.explanation,
            "correct_option_id": correct_id,
            "correct_option_text": correct_text,
            "skill_id": mission.skill_id,
            "skill_name": mission.skill.name,
            "skill_level_before": level_before,
            "skill_level_after": new_level,
            "already_solved": False,
        }

    def get_result(self, attempt_id: int) -> dict[str, Any]:
        """Результат по конкретной попытке."""
        attempt = self.missions.get_attempt(attempt_id)
        mission = self.missions.get_with_options(attempt.mission_id)
        correct_option = next((o for o in mission.options if o.is_correct), None)

        level_after = self._skill_level(attempt.user_id, mission.skill_id)
        return {
            "attempt_id": attempt.id,
            "mission_id": attempt.mission_id,
            "is_correct": attempt.is_correct,
            "xp_earned": attempt.xp_earned,
            "explanation": mission.explanation,
            "correct_option_id": correct_option.id if correct_option else None,
            "correct_option_text": correct_option.text if correct_option else None,
            "skill_id": mission.skill_id,
            "skill_name": mission.skill.name,
            "skill_level_after": level_after,
        }

    def get_history(self, user_id: int) -> list[Attempt]:
        """История попыток пользователя."""
        self.users.get(user_id)
        return self.missions.list_attempts(user_id)

    def _skill_level(self, user_id: int, skill_id: int) -> int:
        """Текущий уровень навыка пользователя (0, если ещё не оценён)."""
        user_skill = self.db.scalar(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id)
        )
        return user_skill.level if user_skill else 0

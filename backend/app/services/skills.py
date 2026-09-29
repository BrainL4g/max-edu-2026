"""Расчёт и обновление навыков.

Результат задания → изменение опыта и уровня навыка → обновление Skill Map.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domain import Mission, Skill, User, UserSkill

# Кумулятивный опыт, необходимый для ДОСТИЖЕНИЯ каждого уровня (0..5).
LEVEL_THRESHOLDS: tuple[int, ...] = (0, 100, 250, 450, 700, 1000)
MAX_LEVEL = len(LEVEL_THRESHOLDS) - 1
TARGET_LEVEL = 3

# Бонус к опыту за сложность миссии.
DIFFICULTY_BONUS: dict[str, int] = {"easy": 0, "medium": 10, "hard": 20}


def level_from_xp(xp: int) -> int:
    """Уровень по накопленному опыту."""
    level = 0
    for idx, threshold in enumerate(LEVEL_THRESHOLDS):
        if xp >= threshold:
            level = idx
    return level


def progress_for_level(level: int, xp: int) -> float:
    """Процент прогресса до следующего уровня (0..100)."""
    if level >= MAX_LEVEL:
        return 100.0
    base = LEVEL_THRESHOLDS[level]
    next_threshold = LEVEL_THRESHOLDS[level + 1]
    return round((xp - base) / (next_threshold - base) * 100, 1)


def initial_xp_for_level(level: int) -> int:
    """Стартовый опыт для заданного уровня (только достигнут порог)."""
    return LEVEL_THRESHOLDS[min(max(level, 0), MAX_LEVEL)]


class SkillService:
    """Сервис навыков: начисление опыта, уровни, Skill Map."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_or_create_user_skill(self, user_id: int, skill_id: int) -> UserSkill:
        user_skill = self.db.scalar(
            select(UserSkill).where(UserSkill.user_id == user_id, UserSkill.skill_id == skill_id)
        )
        if user_skill is None:
            user_skill = UserSkill(user_id=user_id, skill_id=skill_id, level=0, experience=0)
            self.db.add(user_skill)
        return user_skill

    def apply_mission_result(
        self,
        user: User,
        mission: Mission,
        is_correct: bool,
        *,
        commit: bool = True,
    ) -> tuple[int, int, int]:
        """Начислить опыт за миссию.

        За верный ответ — награда миссии + бонус за сложность; за неверный —
        0 XP. Возвращает (полученный опыт, новый уровень, новый суммарный опыт).
        При ``commit=False`` запись и коммит делает вызывающий код (единая
        транзакция с другими операциями).
        """
        if is_correct:
            xp_gained = mission.reward_xp + DIFFICULTY_BONUS.get(mission.difficulty, 0)
        else:
            # Честный XP: за неверный ответ опыт не начисляется.
            xp_gained = 0

        user_skill = self._get_or_create_user_skill(user.id, mission.skill_id)
        new_xp = user_skill.experience + xp_gained
        new_level = level_from_xp(new_xp)
        user_skill.experience = new_xp
        user_skill.level = new_level
        if commit:
            self.db.commit()
        return xp_gained, new_level, new_xp

    def set_initial_skill(self, user_id: int, skill_id: int, level: int) -> UserSkill:
        """Начальный уровень навыка по результатам диагностики.

        Повторная диагностика не понижает уже накопленный прогресс: опыт
        берётся как максимум из текущего и стартового порога уровня.
        """
        safe_level = min(max(level, 0), MAX_LEVEL)
        user_skill = self._get_or_create_user_skill(user_id, skill_id)
        user_skill.experience = max(user_skill.experience or 0, initial_xp_for_level(safe_level))
        user_skill.level = level_from_xp(user_skill.experience)
        self.db.commit()
        return user_skill

    def get_skill_map(self, user_id: int) -> list[dict[str, Any]]:
        """Skill Map пользователя: уровень и прогресс по каждому навыку."""
        rows = self.db.execute(
            select(UserSkill, Skill)
            .join(Skill, Skill.id == UserSkill.skill_id)
            .where(UserSkill.user_id == user_id)
            .order_by(Skill.category, Skill.name)
        ).all()

        items: list[dict[str, Any]] = []
        for user_skill, skill in rows:
            level = level_from_xp(user_skill.experience)
            items.append(
                {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "category": skill.category,
                    "level": level,
                    "experience": user_skill.experience,
                    "progress": progress_for_level(level, user_skill.experience),
                    "next_level_xp": (
                        LEVEL_THRESHOLDS[level + 1] - user_skill.experience
                        if level < MAX_LEVEL
                        else None
                    ),
                }
            )
        return items

"""Gap-анализ: что не хватает до целевой роли и процент соответствия.

Каждое требование роли (skills → required_level) сравнивается с текущим
уровнем пользователя. Процент соответствия — взвешенная «готовность» по
всем требованиям (importance), где требование считается выполненным на
``min(level / required, 1)``.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domain import RoleSkill, Skill, UserSkill
from backend.app.repositories.role_repository import RoleRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.skills import level_from_xp


def _role_dict(role: Any) -> dict[str, Any]:
    """ORM-роль → dict для схемы (требования подтягивают имя навыка)."""
    return {
        "id": role.id,
        "name": role.name,
        "direction": role.direction,
        "level": role.level,
        "description": role.description,
        "requirements": [
            {
                "skill_id": item.skill.id,
                "name": item.skill.name,
                "category": item.skill.category,
                "required_level": item.required_level,
                "importance": item.importance,
                "is_mandatory": item.is_mandatory,
            }
            for item in role.requirements
        ],
    }


class GapAnalysisService:
    """Построение gap-анализа пользователя относительно целевой роли."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)

    def analyze(self, user_id: int) -> dict[str, Any]:
        """Анализ: роль, процент соответствия, требования и пробелы."""
        user = self.users.get(user_id)
        role = user.target_role
        if role is None:
            return {
                "user_id": user.id,
                "role": None,
                "match_percent": None,
                "items": [],
                "summary": "Целевая роль не выбрана. Нажми «🎯 Цель» в меню, чтобы выбрать.",
            }

        rows = self.db.execute(
            select(RoleSkill, Skill)
            .join(Skill, Skill.id == RoleSkill.skill_id)
            .where(RoleSkill.role_id == role.id)
        ).all()

        user_levels = {
            user_skill.skill_id: level_from_xp(user_skill.experience)
            for user_skill in self.db.execute(
                select(UserSkill).where(UserSkill.user_id == user.id)
            ).scalars()
        }

        items: list[dict[str, Any]] = []
        total_weight = 0.0
        weighted_ready = 0.0
        for role_skill, skill in rows:
            current = user_levels.get(skill.id, 0)
            required = role_skill.required_level
            gap = max(0, required - current)
            readiness = min(current / required, 1.0) if required else 1.0
            items.append(
                {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "category": skill.category,
                    "current_level": current,
                    "required_level": required,
                    "gap": gap,
                    "importance": role_skill.importance,
                    "is_mandatory": role_skill.is_mandatory,
                }
            )
            total_weight += role_skill.importance
            weighted_ready += readiness * role_skill.importance

        items.sort(key=lambda item: (-item["gap"], item["name"]))
        match_percent = round(weighted_ready / total_weight * 100) if total_weight else 100

        gaps = [item for item in items if item["gap"] > 0]
        if gaps:
            names = ", ".join(item["name"] for item in gaps[:5])
            summary = (
                f"Для роли «{role.name}» соответствие {match_percent}%. " f"Не хватает: {names}."
            )
        else:
            summary = f"Ты полностью соответствуешь роли «{role.name}» 🎉 ({match_percent}%)."

        return {
            "user_id": user.id,
            "role": _role_dict(role),
            "match_percent": match_percent,
            "items": items,
            "summary": summary,
        }

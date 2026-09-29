"""Рекомендательный механизм.

Skill Map → пробелы в навыках → подходящие курсы и стажировки.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domain import (
    Course,
    Internship,
    RoleSkill,
    Skill,
    User,
    UserSkill,
)
from backend.app.repositories.course_repository import CourseRepository
from backend.app.repositories.internship_repository import InternshipRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.skills import TARGET_LEVEL, level_from_xp

# Необходимые навыки по направлениям (используется и при анализе резюме).
DIRECTION_REQUIRED_SKILLS: dict[str, list[str]] = {
    "backend": ["Python", "SQL", "Git", "Алгоритмы и структуры данных", "Docker"],
    "frontend": ["JavaScript", "HTML/CSS", "React", "Git"],
    "data": ["Python", "SQL", "Pandas", "Machine Learning"],
    "design": ["Figma", "UI/UX"],
    "qa": ["Testing", "SQL", "Git"],
    "analytics": ["SQL", "Pandas", "Python"],
}


class RecommendationService:
    """Построение рекомендаций на основе Skill Map и фильтров пользователя."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.courses = CourseRepository(db)
        self.internships = InternshipRepository(db)

    def _requirements(self, user: User) -> dict[int, dict[str, Any]]:
        """Требования к навыкам: требования целевой роли; фоллбэк — по направлению."""
        if user.target_role is not None:
            rows = self.db.execute(
                select(RoleSkill, Skill)
                .join(Skill, Skill.id == RoleSkill.skill_id)
                .where(RoleSkill.role_id == user.target_role.id)
            ).all()
            return {
                role_skill.skill_id: {
                    "name": skill.name,
                    "category": skill.category,
                    "required_level": role_skill.required_level,
                    "importance": role_skill.importance,
                    "is_mandatory": role_skill.is_mandatory,
                }
                for role_skill, skill in rows
            }

        direction = (user.direction or "").strip().lower()
        names = DIRECTION_REQUIRED_SKILLS.get(direction, [])
        if not names:
            return {}
        by_name = {
            skill.name: skill
            for skill in self.db.scalars(select(Skill).where(Skill.name.in_(names)))
        }
        result: dict[int, dict[str, Any]] = {}
        for name in names:
            skill = by_name.get(name)
            if skill is None:
                continue
            result[skill.id] = {
                "name": skill.name,
                "category": skill.category,
                "required_level": TARGET_LEVEL,
                "importance": 1.0,
                "is_mandatory": True,
            }
        return result

    def _gaps(self, user: User) -> list[dict[str, Any]]:
        """Пробелы: текущий уровень ниже требования роли/направления."""
        requirements = self._requirements(user)
        if not requirements:
            return []

        levels = {
            skill_id: level_from_xp(experience)
            for skill_id, experience in self.db.execute(
                select(UserSkill.skill_id, UserSkill.experience).where(UserSkill.user_id == user.id)
            ).all()
        }

        gaps: list[dict[str, Any]] = []
        for skill_id, requirement in requirements.items():
            current = levels.get(skill_id, 0)
            target = requirement["required_level"]
            if current < target:
                gaps.append(
                    {
                        "skill_id": skill_id,
                        "name": requirement["name"],
                        "category": requirement["category"],
                        "current_level": current,
                        "target_level": target,
                    }
                )
        return sorted(gaps, key=lambda gap: (gap["current_level"], gap["name"]))

    def recommend_courses(self, user_id: int, **filters: Any) -> list[Course]:
        """Курсы, закрывающие пробелы пользователя."""
        user = self.users.get(user_id)
        gap_set = {gap["skill_id"] for gap in self._gaps(user)}
        if not gap_set:
            return []

        courses = self.courses.list_all(**filters)
        courses.sort(
            key=lambda course: (
                len({skill.id for skill in course.skills} & gap_set),
                -course.cost,
            ),
            reverse=True,
        )
        return courses

    def recommend_internships(self, user_id: int, **filters: Any) -> list[Internship]:
        """Стажировки: бонус за направление роли и закрытие пробелов."""
        user = self.users.get(user_id)
        gap_set = {gap["skill_id"] for gap in self._gaps(user)}
        role = user.target_role
        direction = ((role.direction if role else None) or user.direction or "").strip().lower()

        internships = self.internships.list_all(**filters)

        def score(internship: Internship) -> int:
            overlap = len({skill.id for skill in internship.skills} & gap_set)
            direction_bonus = (
                3
                if direction
                and internship.direction
                and internship.direction.strip().lower() == direction
                else 0
            )
            return overlap + direction_bonus

        internships.sort(key=score, reverse=True)
        return internships

    def recommend(self, user_id: int) -> dict[str, Any]:
        """Сводка: рекомендации курсов и стажировок + текстовая выжимка."""
        user = self.users.get(user_id)
        gaps = self._gaps(user)
        gap_names = [gap["name"] for gap in gaps]
        return {
            "user_id": user_id,
            "gaps": gaps,
            "summary": (
                "Закрывайте пробелы: " + ", ".join(gap_names)
                if gap_names
                else "Пробелы не выявлены — отличная подготовка!"
            ),
            "courses": self.recommend_courses(user_id),
            "internships": self.recommend_internships(user_id),
        }

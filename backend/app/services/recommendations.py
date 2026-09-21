"""Рекомендательный механизм.

Skill Map → пробелы в навыках → подходящие курсы и стажировки.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Skill, User, UserSkill
from app.repositories.course_repository import CourseRepository
from app.repositories.internship_repository import InternshipRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.user_repository import UserRepository
from app.services.skills import TARGET_LEVEL, level_from_xp

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
        self.skills = SkillRepository(db)

    def _user_skill_levels(self, user_id: int) -> dict[int, int]:
        rows = self.db.scalars(
            select(UserSkill).where(UserSkill.user_id == user_id)
        )
        return {row.skill_id: level_from_xp(row.experience) for row in rows}

    def _gaps(self, user: User) -> list[dict]:
        """Пробелы: навыки ниже целевого уровня + недостающие по направлению."""
        levels = self._user_skill_levels(user.id)
        gap_map: dict[int, dict] = {}

        for row in self.db.execute(
            select(UserSkill, Skill)
            .join(Skill, Skill.id == UserSkill.skill_id)
            .where(UserSkill.user_id == user.id)
        ).all():
            user_skill, skill = row
            level = level_from_xp(user_skill.experience)
            if level < TARGET_LEVEL:
                gap_map[skill.id] = {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "category": skill.category,
                    "current_level": level,
                    "target_level": TARGET_LEVEL,
                }

        direction = (user.direction or "").strip().lower()
        for name in DIRECTION_REQUIRED_SKILLS.get(direction, []):
            skill = self.skills.get_by_name(name)
            if skill is None:
                continue
            if skill.id not in gap_map:
                gap_map[skill.id] = {
                    "skill_id": skill.id,
                    "name": skill.name,
                    "category": skill.category,
                    "current_level": 0,
                    "target_level": TARGET_LEVEL,
                }

        return sorted(
            gap_map.values(), key=lambda g: (g["current_level"], g["name"])
        )

    def recommend_courses(self, user_id: int, **filters) -> list:
        """Курсы, закрывающие пробелы в навыках (с учётом фильтров)."""
        user = self.users.get(user_id)
        gap_ids = [gap["skill_id"] for gap in self._gaps(user)]
        if not gap_ids:
            return self.courses.list(**filters)

        gap_set = set(gap_ids)
        courses = self.courses.list(skill_ids=gap_ids, **filters)
        courses.sort(key=lambda c: c.cost)
        courses.sort(
            key=lambda c: len({s.id for s in c.skills} & gap_set), reverse=True
        )
        return courses

    def recommend_internships(self, user_id: int, **filters) -> list:
        """Стажировки: совпадение направления и закрытие пробелов в навыках."""
        user = self.users.get(user_id)
        gap_set = {gap["skill_id"] for gap in self._gaps(user)}
        direction = (user.direction or "").strip().lower()

        internships = self.internships.list(**filters)

        def score(internship) -> int:
            overlap = len({s.id for s in internship.skills} & gap_set)
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

    def recommend(
        self,
        user_id: int,
        course_filters: dict | None = None,
        internship_filters: dict | None = None,
    ) -> dict:
        """Полный ответ: пробелы + курсы + стажировки + резюме."""
        user = self.users.get(user_id)
        gaps = self._gaps(user)
        courses = self.recommend_courses(user_id, **(course_filters or {}))
        internships = self.recommend_internships(user_id, **(internship_filters or {}))

        gap_names = ", ".join(gap["name"] for gap in gaps[:5])
        if gaps:
            summary = (
                f"Выявлено пробелов: {len(gaps)} ({gap_names}). "
                f"Подобрано курсов: {len(courses)}, стажировок: {len(internships)}."
            )
        else:
            summary = (
                f"Пробелы не выявлены. Подобрано курсов: {len(courses)}, "
                f"стажировок: {len(internships)}."
            )
        return {
            "user_id": user.id,
            "gaps": gaps,
            "courses": courses,
            "internships": internships,
            "summary": summary,
        }
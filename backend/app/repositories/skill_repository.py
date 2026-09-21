"""Репозиторий навыков и Skill Map."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.domain import Skill, UserSkill


class SkillRepository:
    """Доступ к данным навыков и связей «пользователь — навык»."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Skill]:
        return list(self.db.scalars(select(Skill).order_by(Skill.category, Skill.name)))

    def get(self, skill_id: int) -> Skill:
        skill = self.db.get(Skill, skill_id)
        if skill is None:
            raise NotFoundError(f"Навык с id={skill_id} не найден")
        return skill

    def get_by_name(self, name: str) -> Skill | None:
        return self.db.scalar(select(Skill).where(Skill.name == name))

    def get_by_ids(self, skill_ids: list[int]) -> dict[int, Skill]:
        skills = self.db.scalars(select(Skill).where(Skill.id.in_(skill_ids)))
        return {skill.id: skill for skill in skills}

    def get_user_skill(self, user_id: int, skill_id: int) -> UserSkill | None:
        return self.db.scalar(
            select(UserSkill).where(
                UserSkill.user_id == user_id, UserSkill.skill_id == skill_id
            )
        )

    def get_user_skills(self, user_id: int) -> list[UserSkill]:
        return list(
            self.db.scalars(
                select(UserSkill)
                .where(UserSkill.user_id == user_id)
                .options(selectinload(UserSkill.skill))
                .order_by(UserSkill.skill_id)
            )
        )

    def upsert_user_skill(
        self, user_id: int, skill_id: int, level: int = 0, experience: int = 0
    ) -> UserSkill:
        """Создать или обновить связь «пользователь — навык»."""
        user_skill = self.get_user_skill(user_id, skill_id)
        if user_skill is None:
            user_skill = UserSkill(
                user_id=user_id, skill_id=skill_id, level=level, experience=experience
            )
            self.db.add(user_skill)
        else:
            user_skill.level = level
            user_skill.experience = experience
        self.db.commit()
        self.db.refresh(user_skill)
        return user_skill
"""Доменные сущности SkillQuest (SQLAlchemy ORM).

Здесь же объявлен базовый класс ``Base`` для всех моделей.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей SkillQuest."""


from backend.app.domain.api_token import ApiToken  # noqa: E402
from backend.app.domain.course import Course, CourseSkill  # noqa: E402
from backend.app.domain.internship import Internship, InternshipSkill  # noqa: E402
from backend.app.domain.mission import Attempt, Mission, MissionOption  # noqa: E402
from backend.app.domain.resume import Resume, ResumeAnalysis  # noqa: E402
from backend.app.domain.role import Role, RoleSkill  # noqa: E402
from backend.app.domain.skill import Skill, UserSkill  # noqa: E402
from backend.app.domain.user import User  # noqa: E402

__all__ = [
    "Base",
    "ApiToken",
    "User",
    "Skill",
    "UserSkill",
    "Mission",
    "MissionOption",
    "Attempt",
    "Course",
    "CourseSkill",
    "Internship",
    "InternshipSkill",
    "Resume",
    "ResumeAnalysis",
    "Role",
    "RoleSkill",
]

"""Все ORM-модели в одном месте.

Используется Alembic (``target_metadata``) и кодом, которому нужен ``Base``
(например, ``Base.metadata.create_all`` при быстром старте).
"""

from __future__ import annotations

from backend.app.domain import (  # noqa: F401
    Attempt,
    Base,
    Course,
    CourseSkill,
    Internship,
    InternshipSkill,
    Mission,
    MissionOption,
    Resume,
    ResumeAnalysis,
    Role,
    RoleSkill,
    Skill,
    User,
    UserSkill,
)

metadata = Base.metadata

__all__ = [name for name in globals() if not name.startswith("_")]

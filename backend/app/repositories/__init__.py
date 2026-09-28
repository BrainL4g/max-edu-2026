"""Репозитории: слой доступа к данным.

Services работают с репозиториями, а не напрямую с SQLite.
"""

from __future__ import annotations

from backend.app.repositories.course_repository import CourseRepository
from backend.app.repositories.internship_repository import InternshipRepository
from backend.app.repositories.mission_repository import MissionRepository
from backend.app.repositories.resume_repository import ResumeRepository
from backend.app.repositories.skill_repository import SkillRepository
from backend.app.repositories.user_repository import UserRepository

__all__ = [
    "UserRepository",
    "SkillRepository",
    "MissionRepository",
    "CourseRepository",
    "InternshipRepository",
    "ResumeRepository",
]

"""Репозитории: слой доступа к данным.

Services работают с репозиториями, а не напрямую с SQLite.
"""

from __future__ import annotations

from app.repositories.user_repository import UserRepository
from app.repositories.skill_repository import SkillRepository
from app.repositories.mission_repository import MissionRepository
from app.repositories.course_repository import CourseRepository
from app.repositories.internship_repository import InternshipRepository
from app.repositories.resume_repository import ResumeRepository

__all__ = [
    "UserRepository",
    "SkillRepository",
    "MissionRepository",
    "CourseRepository",
    "InternshipRepository",
    "ResumeRepository",
]
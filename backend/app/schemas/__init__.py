"""Pydantic-схемы API. Domain model ≠ API request/response."""

from __future__ import annotations

from backend.app.schemas.course import CourseOut
from backend.app.schemas.internship import InternshipOut
from backend.app.schemas.mission import (
    AttemptHistoryItem,
    AttemptResultOut,
    MissionAnswerIn,
    MissionOptionOut,
    MissionOut,
)
from backend.app.schemas.recommendation import RecommendationOut, SkillGap
from backend.app.schemas.resume import ResumeAnalysisOut, ResumeCreate, ResumeOut
from backend.app.schemas.skill import AssessmentIn, AssessmentOut, SkillMapItem, SkillOut
from backend.app.schemas.user import UserCreate, UserOut, UserProgressOut, UserUpdate

__all__ = [
    "UserCreate",
    "UserOut",
    "UserUpdate",
    "UserProgressOut",
    "AssessmentIn",
    "AssessmentOut",
    "SkillMapItem",
    "SkillOut",
    "AttemptHistoryItem",
    "AttemptResultOut",
    "MissionAnswerIn",
    "MissionOptionOut",
    "MissionOut",
    "CourseOut",
    "InternshipOut",
    "RecommendationOut",
    "SkillGap",
    "ResumeAnalysisOut",
    "ResumeCreate",
    "ResumeOut",
]

"""Pydantic-схемы API. Domain model ≠ API request/response."""

from __future__ import annotations

from app.schemas.user import UserCreate, UserOut, UserProgressOut, UserUpdate
from app.schemas.skill import AssessmentIn, AssessmentOut, SkillMapItem, SkillOut
from app.schemas.mission import (
    AttemptHistoryItem,
    AttemptResultOut,
    MissionAnswerIn,
    MissionOptionOut,
    MissionOut,
)
from app.schemas.course import CourseOut
from app.schemas.internship import InternshipOut
from app.schemas.recommendation import RecommendationOut, SkillGap
from app.schemas.resume import ResumeAnalysisOut, ResumeCreate, ResumeOut

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
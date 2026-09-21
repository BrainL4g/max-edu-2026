"""Сервисы — основная бизнес-логика SkillQuest."""

from __future__ import annotations

from app.services.skills import SkillService
from app.services.assessment import AssessmentService
from app.services.missions import MissionService
from app.services.recommendations import RecommendationService
from app.services.resume_analysis import ResumeAnalysisService

__all__ = [
    "SkillService",
    "AssessmentService",
    "MissionService",
    "RecommendationService",
    "ResumeAnalysisService",
]
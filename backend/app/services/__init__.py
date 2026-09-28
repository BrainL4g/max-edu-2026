"""Сервисы — основная бизнес-логика SkillQuest."""

from __future__ import annotations

from backend.app.services.assessment import AssessmentService
from backend.app.services.missions import MissionService
from backend.app.services.recommendations import RecommendationService
from backend.app.services.resume_analysis import ResumeAnalysisService
from backend.app.services.skills import SkillService

__all__ = [
    "SkillService",
    "AssessmentService",
    "MissionService",
    "RecommendationService",
    "ResumeAnalysisService",
]

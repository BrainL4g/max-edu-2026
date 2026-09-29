"""Общий API-роутер: подключает все endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.routes import (
    admin,
    assessment,
    courses,
    internships,
    missions,
    resumes,
    roles,
    skills,
    users,
)

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(admin.router)
api_router.include_router(skills.router)
api_router.include_router(roles.router)
api_router.include_router(assessment.router)
api_router.include_router(missions.router)
api_router.include_router(courses.router)
api_router.include_router(internships.router)
api_router.include_router(resumes.router)

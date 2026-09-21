"""Общий API-роутер: подключает все endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import courses, internships, missions, resumes, skills, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(skills.router)
api_router.include_router(missions.router)
api_router.include_router(courses.router)
api_router.include_router(internships.router)
api_router.include_router(resumes.router)
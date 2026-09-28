"""Эндпоинты резюме: загрузка, запуск анализа, получение результата."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.database.session import get_db
from backend.app.repositories.resume_repository import ResumeRepository
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.resume import ResumeAnalysisOut, ResumeCreate, ResumeOut
from backend.app.services.resume_analysis import ResumeAnalysisService

router = APIRouter(tags=["resumes"])


@router.post("/users/{user_id}/resumes", response_model=ResumeOut, status_code=201)
def create_resume(
    user_id: int, payload: ResumeCreate, db: Session = Depends(get_db)
) -> ResumeOut:
    """Загрузка резюме текстом."""
    UserRepository(db).get(user_id)
    return ResumeRepository(db).create(user_id, payload.text, payload.filename)


@router.post(
    "/users/{user_id}/resumes/upload", response_model=ResumeOut, status_code=201
)
async def upload_resume(
    user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ResumeOut:
    """Загрузка резюме файлом (txt/md и др. текстовые форматы)."""
    UserRepository(db).get(user_id)
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    return ResumeRepository(db).create(user_id, text, file.filename)


@router.get("/users/{user_id}/resumes", response_model=list[ResumeOut])
def list_resumes(user_id: int, db: Session = Depends(get_db)) -> list[ResumeOut]:
    """Резюме пользователя."""
    return ResumeRepository(db).list_by_user(user_id)


@router.get("/resumes/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)) -> ResumeOut:
    """Резюме по id."""
    return ResumeRepository(db).get(resume_id)


@router.post("/resumes/{resume_id}/analyze", response_model=ResumeAnalysisOut)
def analyze_resume(
    resume_id: int, db: Session = Depends(get_db)
) -> ResumeAnalysisOut:
    """Запуск анализа резюме."""
    result = ResumeAnalysisService(db).analyze(resume_id)
    return ResumeAnalysisOut(**result)


@router.get("/resumes/{resume_id}/analysis", response_model=ResumeAnalysisOut)
def get_analysis(resume_id: int, db: Session = Depends(get_db)) -> ResumeAnalysisOut:
    """Результат анализа резюме."""
    analysis = ResumeRepository(db).get_analysis(resume_id)
    if analysis is None or not analysis.result:
        raise NotFoundError(f"Анализ для резюме {resume_id} ещё не выполнен")
    return ResumeAnalysisOut(**analysis.result)

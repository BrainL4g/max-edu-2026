"""Тесты анализа резюме."""

from __future__ import annotations

from backend.app.domain import Resume, Skill, User
from backend.app.services.resume_analysis import ResumeAnalysisService


def _seed(db):
    db.add_all(
        [
            Skill(name="Python", category="Программирование"),
            Skill(name="SQL", category="Данные"),
            Skill(name="Git", category="Инструменты"),
        ]
    )
    user = User(name="Студент", direction="backend")
    db.add(user)
    db.commit()
    db.refresh(user)
    resume = Resume(
        user_id=user.id,
        filename="resume.txt",
        text=(
            "Иван Иванов, +7 999 123-45-67, Москва\n"
            "\n"
            "Образование: МГТУ им. Баумана, 3 курс\n"
            "\n"
            "Python: писал скрипты для автоматизации, использовал git на учебных проектах.\n"
            "Знаком с основами SQL и запросов.\n"
            "\n"
            "Ссылки: https://github.com/ivan"
        ),
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return user, resume


def test_analyze_detects_skills(db_session):
    user, resume = _seed(db_session)
    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert "Python" in result["found_skills"]
    assert "Git" in result["found_skills"]
    assert "SQL" in result["found_skills"]  # алиас "sql"


def test_analyze_finds_missing_skills(db_session):
    _, resume = _seed(db_session)
    result = ResumeAnalysisService(db_session).analyze(resume.id)

    missing = set(result["missing_skills"])
    assert "Docker" in missing


def test_analyze_direction_match(db_session):
    _, resume = _seed(db_session)
    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert isinstance(result["direction_match"], float)
    assert 0 <= result["direction_match"] <= 100


def test_analyze_issues_and_recommendations(db_session):
    _, resume = _seed(db_session)
    result = ResumeAnalysisService(db_session).analyze(resume.id)

    assert isinstance(result["issues"], list)
    assert isinstance(result["recommendations"], list)
    assert result["strengths"]
    assert result["summary"]

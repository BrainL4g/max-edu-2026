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


def test_analyze_uses_gigachat_verdict(db_session):
    """Настроенный GigaChat дополняет эвристический отчёт."""
    _, resume = _seed(db_session)
    ai = GigaChatClientStub(
        {
            "score": 88,
            "summary": "Сильное резюме",
            "strengths": ["Петпроекты"],
            "issues": ["Нет Docker"],
            "recommendations": ["Добавьте Docker"],
        }
    )
    service = ResumeAnalysisService(db_session, ai=ai)

    result = service.analyze(resume.id)

    assert result["source"] == "gigachat"
    assert result["ai_score"] == 88
    assert result["ai_summary"] == "Сильное резюме"
    assert result["strengths"] == ["Петпроекты"]
    assert result["recommendations"] == ["Добавьте Docker"]


def test_analyze_keeps_heuristics_when_ai_returns_nothing(db_session):
    """Пустой ответ модели не затирает эвристический отчёт."""
    _, resume = _seed(db_session)
    service = ResumeAnalysisService(db_session, ai=GigaChatClientStub(None))

    result = service.analyze(resume.id)

    assert result["source"] == "heuristic"
    assert result["ai_score"] is None


def test_with_ai_ignores_empty_lists() -> None:
    """Пустые списки от модели не подменяют найденные эвристикой."""
    base = {"strengths": ["Python"], "issues": ["нет контактов"], "recommendations": ["совет"]}
    merged = ResumeAnalysisService._with_ai(base, {"score": 10, "strengths": []})  # noqa: SLF001

    assert merged["strengths"] == ["Python"]
    assert merged["issues"] == ["нет контактов"]
    assert merged["ai_summary"] is None


class GigaChatClientStub:
    """Заглушка GigaChat: возвращает заранее заданный вердикт."""

    def __init__(self, verdict: dict | None) -> None:
        self.verdict = verdict
        self.calls: list[tuple] = []

    def evaluate_resume(self, text, direction=None, found_skills=None, missing_skills=None):
        self.calls.append((text, direction, found_skills, missing_skills))
        return self.verdict

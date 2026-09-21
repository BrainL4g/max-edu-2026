"""Анализ резюме: извлечение навыков → поиск пробелов → рекомендации.

Результат показывает найденные навыки, недостающие навыки, сильные стороны,
проблемы резюме, рекомендации и соответствие выбранному направлению.
"""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import Skill
from app.repositories.resume_repository import ResumeRepository
from app.repositories.user_repository import UserRepository
from app.services.recommendations import DIRECTION_REQUIRED_SKILLS

# Алиасы для поиска навыков в тексте резюме (нижний регистр).
SKILL_ALIASES: dict[str, list[str]] = {
    "Python": ["python", "питон"],
    "SQL": ["sql", "postgresql", "postgres", "mysql", "sqlite", "бд"],
    "Git": ["git", "github", "gitlab"],
    "JavaScript": ["javascript", "js", "typescript"],
    "HTML/CSS": ["html", "css"],
    "React": ["react"],
    "FastAPI": ["fastapi"],
    "Docker": ["docker", "контейнер"],
    "Алгоритмы и структуры данных": ["алгоритм", "структуры данных", "leetcode"],
    "Pandas": ["pandas", "numpy"],
    "Machine Learning": ["machine learning", "машинное обучение", "нейросет"],
    "Testing": ["тест", "pytest", "selenium", "юнит"],
    "Figma": ["figma"],
    "UI/UX": ["ui", "ux", "интерфейс"],
    "Коммуникация": ["коммуникац"],
    "Тайм-менеджмент": ["тайм-менеджмент", "управление временем"],
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(\+7|8)[\s\-()]*\d{3}[\s\-()]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}")
LINK_RE = re.compile(r"(https?://|github\.com|linkedin\.com|behance\.net|t\.me)")

_ISSUE_ADVICE = {
    "контакт": "Добавьте почту и телефон в «шапку» резюме",
    "короткое": "Раскройте учебные проекты, технологии и обязанности",
    "ссылок": "Добавьте ссылки на GitHub, портфолио или LinkedIn",
    "образование": "Укажите вуз, факультет и год окончания",
    "направлением": "Опишите, чем занимались в выбранном направлении",
    "навыков": "Перечислите технологии и инструменты, с которыми работали",
}


class ResumeAnalysisService:
    """Сервис анализа резюме."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.resumes = ResumeRepository(db)
        self.users = UserRepository(db)

    def analyze(self, resume_id: int) -> dict:
        """Проанализировать резюме и сохранить результат."""
        resume = self.resumes.get(resume_id)
        user = self.users.get(resume.user_id)
        text = resume.text
        text_lower = text.lower()

        skills = list(self.db.scalars(select(Skill).order_by(Skill.name)))
        found = [s.name for s in skills if self._skill_matches(s.name, text_lower)]

        direction = (user.direction or "").strip().lower()
        required = DIRECTION_REQUIRED_SKILLS.get(direction, [])
        missing = [name for name in required if name not in found]

        issues = self._collect_issues(text, text_lower, found, direction, required)
        recommendations = self._build_recommendations(
            missing, issues, direction, required
        )
        direction_match = (
            round(len([name for name in required if name in found]) / len(required) * 100, 1)
            if required
            else 50.0
        )

        result = {
            "resume_id": resume_id,
            "found_skills": found,
            "missing_skills": missing,
            "strengths": found[:5],
            "issues": issues,
            "recommendations": recommendations,
            "direction_match": direction_match,
            "summary": self._summary(found, missing, direction_match, direction),
        }
        self.resumes.save_analysis(resume_id, result)
        return result

    def _skill_matches(self, name: str, text_lower: str) -> bool:
        patterns = SKILL_ALIASES.get(name, [name.lower()])
        return any(pattern in text_lower for pattern in patterns)

    def _collect_issues(
        self,
        text: str,
        text_lower: str,
        found: list[str],
        direction: str,
        required: list[str],
    ) -> list[str]:
        issues = []
        if not EMAIL_RE.search(text) and not PHONE_RE.search(text):
            issues.append("Не указаны контактные данные (почта или телефон)")
        if len(text.strip()) < 400:
            issues.append("Резюме слишком короткое — добавьте больше деталей")
        if not LINK_RE.search(text_lower):
            issues.append("Нет ссылок на GitHub/LinkedIn/портфолио/Telegram")
        if not any(keyword in text_lower for keyword in ("образован", "учеб", "вуз", "университет")):
            issues.append("Не указано образование")
        if direction and not (
            direction in text_lower
            or (required and required[0].lower() in text_lower)
        ):
            issues.append(f"Резюме слабо связано с направлением «{direction}»")
        if not found:
            issues.append(
                "Не удалось обнаружить профессиональные навыки — используйте ключевые слова"
            )
        return issues

    def _build_recommendations(
        self, missing: list[str], issues: list[str], direction: str, required: list[str]
    ) -> list[str]:
        recommendations = [f"Добавьте в резюме навык «{name}»" for name in missing]
        if required and not missing:
            recommendations.append(
                "Все обязательные навыки направления найдены — усильте формулировки и проекты"
            )
        if direction:
            recommendations.append(f"Явно укажите направление «{direction}» в разделе «О себе»")
        for issue in issues:
            for key, advice in _ISSUE_ADVICE.items():
                if key.lower() in issue.lower():
                    recommendations.append(advice)
                    break
        return recommendations

    @staticmethod
    def _summary(
        found: list[str], missing: list[str], direction_match: float, direction: str
    ) -> str:
        if not direction:
            return (
                f"Найдено навыков: {len(found)}. Укажите направление в профиле, "
                "чтобы получить точные рекомендации."
            )
        if not missing and direction_match >= 70:
            return (
                f"Резюме отлично соответствует направлению «{direction}» "
                f"({direction_match}%). Вы готовы к стажировкам!"
            )
        return (
            f"Соответствие направлению «{direction}»: {direction_match}%. "
            f"Не хватает навыков: {', '.join(missing) or '—'}. "
            "Доработайте резюме по рекомендациям ниже."
        )
"""Тесты форматирования текстовых ответов бота."""

from __future__ import annotations

import texts


def test_progress_bar() -> None:
    assert texts.progress_bar(30, 10) == "▓▓▓░░░░░░░"
    assert texts.progress_bar(0) == "░" * 10
    assert texts.progress_bar(100, 5) == "▓" * 5


def test_skill_map_text_empty() -> None:
    assert "не оценены" in texts.skill_map_text([])


def test_skill_map_text_with_items() -> None:
    items = [{"name": "Python", "level": 2, "progress": 50.0, "next_level_xp": 125}]
    text = texts.skill_map_text(items)
    assert "Python" in text
    assert "уровень 2" in text
    assert "50%" in text
    assert "125 XP" in text


def test_skill_map_text_without_next_xp() -> None:
    text = texts.skill_map_text([{"name": "Git", "level": 5, "progress": 100.0}])
    assert "до 6" not in text
    assert "Git" in text


def test_course_card_free_with_skills() -> None:
    course = {
        "title": "FastAPI",
        "platform": "Stepik",
        "level": "junior",
        "format": "online",
        "cost": 0,
        "description": "Курс про бэкенд",
        "skills": [{"name": "Python"}, {"name": "SQL"}],
    }
    card = texts.course_card(course, 1)
    assert "1. FastAPI" in card
    assert "бесплатно" in card
    assert "Python, SQL" in card
    assert "Курс про бэкенд" in card


def test_course_card_paid_without_skills() -> None:
    course = {
        "title": "Курс",
        "platform": "Платформа",
        "level": "mid",
        "format": "offline",
        "cost": 1000,
        "skills": [],
    }
    card = texts.course_card(course)
    assert "1000 ₽" in card
    assert "Навыки: —" in card


def test_internship_card_remote() -> None:
    item = {
        "title": "Стажёр",
        "company": "Яндекс",
        "level": "beginner",
        "remote": True,
        "format": "remote",
        "skills": [{"name": "Go"}],
    }
    card = texts.internship_card(item, 2)
    assert "2. Стажёр @ Яндекс" in card
    assert "🌍 Удалённо" in card
    assert "Go" in card


def test_internship_card_office_with_requirements() -> None:
    item = {
        "title": "Аналитик",
        "company": "Сбер",
        "level": "mid",
        "remote": False,
        "city": "Казань",
        "format": "office",
        "requirements": "Знание SQL",
        "skills": [],
    }
    card = texts.internship_card(item)
    assert "Казань" in card
    assert "Знание SQL" in card
    assert "Навыки: —" in card


def test_resume_report_full() -> None:
    analysis = {
        "direction_match": 90,
        "found_skills": ["Python"],
        "missing_skills": ["Docker"],
        "strengths": ["Проекты"],
        "issues": ["Нет ссылок"],
        "recommendations": ["Совет 1", "Совет 2"],
    }
    report = texts.resume_report(analysis)
    assert "90%" in report
    assert "Python" in report
    assert "Docker" in report
    assert "Проекты" in report
    assert "Нет ссылок" in report
    assert "Совет 1" in report


def test_resume_report_empty() -> None:
    report = texts.resume_report({})
    assert "0%" in report
    assert "Найдено: —" in report
    assert "Не хватает: —" in report

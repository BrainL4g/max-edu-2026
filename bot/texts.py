"""Форматирование текстовых ответов бота."""

from __future__ import annotations

from typing import Any

LEVEL_EMOJI = ("⬛", "🟥", "🟧", "🟨", "🟩", "🟦")


def progress_bar(percent: float, width: int = 10) -> str:
    """Полоска прогресса: ▓▓▓░░░░░░░ 30%."""
    filled = round(percent / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def skill_map_text(items: list[dict[str, Any]]) -> str:
    """Skill Map пользователя текстом."""
    if not items:
        return "Навыки ещё не оценены. Пройдите диагностику или миссии 🎮"
    lines = ["📊 Skill Map\n"]
    for item in items:
        level = min(int(item["level"]), len(LEVEL_EMOJI) - 1)
        percent = float(item.get("progress") or 0)
        line = (
            f"{LEVEL_EMOJI[level]} {item['name']} — уровень {item['level']} · "
            f"{progress_bar(percent)} {percent:.0f}%"
        )
        next_xp = item.get("next_level_xp")
        if next_xp is not None and int(next_xp) > 0:
            line += f" (до {item['level'] + 1}: {next_xp} XP)"
        lines.append(line)
    return "\n".join(lines)


def course_card(course: dict[str, Any], index: int = 0) -> str:
    """Карточка курса."""
    skills = ", ".join(s["name"] for s in course.get("skills", [])) or "—"
    cost = "бесплатно" if not course.get("cost") else f"{course['cost']:.0f} ₽"
    lines = [
        f"{index}. {course['title']}",
        f"   {course['platform']} · {course['level']} · {course['format']} · {cost}",
        f"   Навыки: {skills}",
    ]
    if course.get("description"):
        lines.append(f"   {course['description']}")
    return "\n".join(lines)


def internship_card(item: dict[str, Any], index: int = 0) -> str:
    """Карточка стажировки."""
    skills = ", ".join(s["name"] for s in item.get("skills", [])) or "—"
    location = "🌍 Удалённо" if item.get("remote") else (item.get("city") or "Офис")
    lines = [
        f"{index}. {item['title']} @ {item['company']}",
        f"   {item['level']} · {location} · {item['format']}",
        f"   Навыки: {skills}",
    ]
    details = item.get("requirements") or item.get("description") or ""
    if details:
        lines.append(f"   {details}")
    return "\n".join(lines)


def resume_report(analysis: dict[str, Any]) -> str:
    """Отчёт анализа резюме."""
    found = ", ".join(analysis.get("found_skills") or []) or "—"
    missing = ", ".join(analysis.get("missing_skills") or []) or "—"
    lines = [
        f"📄 Соответствие направлению: {round(analysis.get('direction_match', 0))}%",
        "",
        f"✅ Найдено: {found}",
        f"➕ Не хватает: {missing}",
    ]
    if analysis.get("strengths"):
        lines += ["", "💪 Сильные стороны:"]
        lines += [f"• {item}" for item in analysis["strengths"]]
    if analysis.get("issues"):
        lines += ["", "⚠️ Проблемы:"]
        lines += [f"• {item}" for item in analysis["issues"]]
    if analysis.get("recommendations"):
        lines += ["", "💡 Советы:"]
        lines += [f"• {item}" for item in analysis["recommendations"][:5]]
    return "\n".join(lines)

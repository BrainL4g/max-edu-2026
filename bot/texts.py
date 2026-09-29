"""Форматирование текстовых ответов бота."""

from __future__ import annotations

from typing import Any

LEVEL_EMOJI = ("⬛", "🟥", "🟧", "🟨", "🟩", "🟦")


def progress_bar(percent: float, width: int = 10) -> str:
    """Полоска прогресса: ▓▓▓░░░░░░░ 30%."""
    filled = round(percent / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def numbered_options(options: list[str]) -> str:
    """Нумерованный список вариантов ответа (1..N) для текста вопроса."""
    return "\n".join(f"{i + 1}. {text}" for i, text in enumerate(options))


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


def roles_question_text() -> str:
    """Текст экрана выбора целевой роли."""
    return (
        "🎯 Какую цель выбираешь?\n\n"
        "Выбери роль — я покажу, чего не хватает до неё, "
        "и подберу шаги для подготовки."
    )


def gap_analysis_text(analysis: dict[str, Any]) -> str:
    """Gap-анализ: цель, процент соответствия и чего не хватает."""
    role = analysis.get("role")
    if not role:
        return (
            "🎯 Целевая роль ещё не выбрана.\n\n"
            "Выбери роль в меню ниже — я покажу, чего не хватает до неё."
        )

    match = analysis.get("match_percent")
    lines = [f"🎯 Цель: {role['name']}", f"Совпадение с ролью: {match}%\n"]

    gaps = [item for item in analysis["items"] if item["gap"] > 0]
    closed = [item for item in analysis["items"] if item["gap"] == 0]
    if gaps:
        lines.append("🚧 Не хватает:")
        for item in gaps[:6]:
            mark = "❗" if item["is_mandatory"] else "·"
            lines.append(
                f"{mark} {item['name']} — {item['current_level']} из "
                f"{item['required_level']}"
            )
    else:
        lines.append("Всё закрыто — можно откликаться! 🎉")
    if closed:
        lines.append("\n✅ Уже в норме:")
        lines += [
            f"· {item['name']} — {item['current_level']} из {item['required_level']}"
            for item in closed
        ]
    return "\n".join(lines)


def course_card(course: dict[str, Any], index: int = 0) -> str:
    """Карточка курса."""
    skills = ", ".join(s["name"] for s in course.get("skills", [])) or "—"
    lines = [
        f"{index}. {course['title']}",
        f"   {course['platform']} · {course['level']} · {course['format']}",
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


def internship_link_title(item: dict[str, Any], index: int) -> str:
    """Подпись ссылки стажировки: номер карточки, компания и направление."""
    company = item.get("company") or item.get("title") or "Стажировка"
    direction = item.get("direction")
    title = f"{company} · {direction}" if direction else company
    return f"{index}. {title}"


def internship_directions_text() -> str:
    """Текст экрана выбора направления стажировок."""
    return (
        "💼 Стажировки\n\n"
        "Выбери направление — подберу подходящие стажировки "
        "с учётом твоих навыков."
    )


def internships_header(
    direction: str | None, page: int = 0, total_pages: int = 1
) -> str:
    """Заголовок списка стажировок: направление и номер страницы (если их больше одной)."""
    title = (
        f"💼 Рекомендуемые стажировки — {direction}"
        if direction
        else "💼 Рекомендуемые стажировки"
    )
    if total_pages > 1:
        return f"{title} (страница {page + 1} из {total_pages}):"
    return f"{title}:"


def internships_empty_text(direction: str | None) -> str:
    """Сообщение, когда по фильтру стажировок не нашлось."""
    if direction:
        return f"По направлению «{direction}» стажировок пока нет 🤷"
    return "Рекомендаций по стажировкам пока нет 🤷"


def resume_prompt_text() -> str:
    """Экран загрузки резюме (файлом или текстом)."""
    return (
        "📄 Пришли резюме файлом (PDF, DOCX или TXT) "
        "или текстом одним сообщением.\n\n"
        "Отправлю его в GigaChat и покажу оценку, сильные стороны и советы."
    )


def resume_file_error_text(reason: str) -> str:
    """Ошибка приёма резюме."""
    return (
        f"Не получилось разобрать резюме: {reason}.\n\n"
        "Пришли PDF, DOCX или TXT — либо текст резюме сообщением."
    )


def resume_report(analysis: dict[str, Any]) -> str:
    """Отчёт анализа резюме: эвристика + оценка GigaChat, если она есть."""
    found = ", ".join(analysis.get("found_skills") or []) or "—"
    missing = ", ".join(analysis.get("missing_skills") or []) or "—"
    score = analysis.get("ai_score")
    summary = analysis.get("ai_summary")
    lines = [
        f"📄 Соответствие направлению: {round(analysis.get('direction_match', 0))}%"
    ]
    if score is not None:
        lines.append(f"🤖 Оценка GigaChat: {round(float(score))}/100")
    if summary:
        lines.append(str(summary))
    lines += ["", f"✅ Найдено: {found}", f"➕ Не хватает: {missing}"]
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

"""Форматирование текстовых ответов бота."""

from __future__ import annotations

from typing import Any

LEVEL_EMOJI = ("⬛", "🟥", "🟧", "🟨", "🟩", "🟦")


def progress_bar(percent: float, width: int = 10) -> str:
    """Полоска прогресса: ▓▓▓░░░░░░░ 30%."""
    filled = round(percent / 100 * width)
    return "▓" * filled + "░" * (width - filled)


def help_text() -> str:
    """Инструкция по использованию бота."""
    return (
        "ℹ️ Как пользоваться SkillQuest\n\n"
        "1. 🎯 Цель — выбери роль, к которой стремишься. "
        "Я покажу, чего не хватает.\n"
        "2. 🧠 Диагностика — ответь на вопросы по навыкам. "
        "Вопросы подбираются под твоё направление.\n"
        "3. 🎮 Миссия — решай задания и прокачивай навыки за XP. "
        "Варианты ответов перемешиваются — думай, а не угадывай 🙂\n"
        "4. 📊 Skill Map — уровни навыков и прогресс до следующего уровня.\n"
        "5. 📚 Курсы и 💼 Стажировки — рекомендации под твою цель.\n"
        "6. 📄 Резюме — пришли текст резюме, я найду сильные стороны "
        "и пробелы.\n\n"
        "Начни с Цели или Диагностики. Вопросы миссий и диагностики "
        "отвечай кнопками под сообщением."
    )


def fallback_text() -> str:
    """Подсказка на свободный текст и неизвестные команды."""
    return (
        "Я умею команды и кнопки меню 🙂\n"
        "Произвольный текст принимаю только в режиме «📄 Резюме». "
        "Вот что можно сделать:"
    )


def need_goal_text() -> str:
    """Экран «сначала выбери цель» (диагностика и миссии без цели)."""
    return (
        "🎯 Сначала выбери цель.\n\n"
        "От цели зависят вопросы диагностики и подбор миссий. "
        "Выбери роль — и продолжим!"
    )


def missions_done_text(done: int, total: int) -> str:
    """Экран «по цели всё пройдено»."""
    return f"По цели пройдено всё 🏆 ({done}/{total} миссий)."


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
    lines.append("\n💡 Пройди миссии, чтобы прокачать навыки до нужного уровня.")
    return "\n".join(lines)


def roles_question_text() -> str:
    """Текст экрана выбора целевой роли."""
    return (
        "🎯 Какую цель выбираешь?\n\n"
        "Направление определяет вопросы диагностики и миссии. "
        "Выбери роль, к которой стремишься, — я покажу, чего не хватает, "
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
        lines.append("\n💡 Закрой пробелы миссиями и курсами.")
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

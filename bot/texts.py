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
    )


def resume_consent_text(ai_enabled: bool) -> str:
    """Запрос согласия на обработку ПД перед отправкой резюме (152-ФЗ ст. 9).

    ``ai_enabled`` — передаётся ли резюме в GigaChat; утверждение о передаче
    всегда безусловное, в соответствии с фактической настройкой сервера.
    """
    if ai_enabled:
        transfer = (
            "🤖 Оценку резюме делает внешний сервис GigaChat (ПАО Сбербанк). "
            "Ему уходят текст резюме (до 8000 символов), найденные навыки "
            "и выбранное направление — на api.giga.chat."
        )
    else:
        transfer = "🤖 AI-оценка не подключена: резюме разбирается на сервере, текст никуда не уходит."
    return (
        "🔐 Прежде чем прислать резюме — нужно ваше согласие "
        "на обработку персональных данных (152-ФЗ).\n\n"
        "📄 Что попадёт в резюме: имя, телефон, e-mail, образование, "
        "прошлые места работы и проекты.\n"
        "🎯 Зачем: я найду навыки и пробелы и подберу курсы и стажировки.\n"
        "🔒 Как: данные шифруются при хранении, доступны только вам.\n"
        f"{transfer}\n"
        "🗑 Отозвать согласие можно в любой момент — тогда резюме "
        "обрабатывать не буду.\n\n"
        "Согласны на обработку персональных данных?"
    )


def resume_consent_declined_text() -> str:
    """Отказ от согласия: резюме не отправляется и не обрабатывается."""
    return (
        "🙂 Хорошо, без согласия резюме я обрабатывать не буду — "
        "так и положено по закону.\n\n"
        "Остальные разделы работают: Цель, Диагностика, Миссии, "
        "Skill Map, Курсы и Стажировки.\n\n"
        "Передумаешь — нажми «Резюме» ещё раз."
    )


def consent_revoked_text() -> str:
    """Подтверждение отзыва согласия."""
    return (
        "🚫 Согласие на обработку персональных данных отозвано.\n\n"
        "Новые резюме я больше не принимаю. Загруженные ранее остаются "
        "в базе — их можно стереть, написав мне об этом."
    )


def consent_error_text() -> str:
    """Согласие не зафиксировалось — резюме не отправляем (fail closed)."""
    return (
        "⚠️ Не удалось зафиксировать согласие, поэтому резюме я не принял.\n\n"
        "Попробуй ещё раз через минуту — данные должны уйти только "
        "с вашего согласия."
    )


def privacy_policy_text(ai_enabled: bool) -> str:
    """Краткая выжимка политики обработки персональных данных."""
    if ai_enabled:
        transfer = (
            "🤖 Оценку резюме делает GigaChat (ПАО Сбербанк) — третье лицо. "
            "Передаются текст резюме (до 8000 символов), найденные навыки и "
            "направление, адрес api.giga.chat. Прочая передача третьим лицам "
            "не производится."
        )
    else:
        transfer = "🤖 AI-оценка не подключена: резюме никуда не передаётся."
    return (
        "📄 Политика обработки персональных данных\n"
        "Редакция 1.0\n\n"
        "Кто обрабатывает: SkillQuest.\n\n"
        "Какие данные: имя и идентификатор в мессенджере MAX, сведения "
        "об образовании и направлении, целевая роль, результаты "
        "диагностики и игрового прогресса, а по резюме — телефон, e-mail, "
        "прошлые места работы и проекты. Специальные категории данных "
        "и биометрия не обрабатываются.\n\n"
        "Цели: диагностика навыков, игровые миссии, подбор курсов "
        "и стажировок, анализ резюме.\n\n"
        "Правовое основание: ваше согласие, статья 9 152-ФЗ.\n\n"
        "Защита: шифрование полей при хранении, передача по защищённому "
        "каналу, доступ только владельцу данных, журналирование обращений.\n\n"
        f"{transfer}\n\n"
        "Сроки: до отзыва согласия или удаления аккаунта.\n\n"
        "Ваши права (статьи 14, 17, 18):\n"
        "• получить копию своих данных;\n"
        "• потребовать исправления неточностей;\n"
        "• удалить все свои данные;\n"
        "• отозвать согласие;\n"
        "• обжаловать действия в Роскомнадзоре или в суде.\n\n"
        "Вопросы: privacy@skillquest.example.com"
    )


def resume_cancelled_text() -> str:
    """Отмена ожидания резюме по кнопке."""
    return "Отменил 🙌 Возвращаемся в меню."


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
        lines.append(f"🤖 Оценка : {round(float(score))}/100")
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

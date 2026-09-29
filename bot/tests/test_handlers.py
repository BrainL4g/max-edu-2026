"""Тесты хендлеров MAX-бота на фейк-событиях (без сети и API)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest

import api
import sessions
from handlers import (
    assessment,
    fallback,
    goal,
    missions,
    recommend,
    resume,
    skillmap,
    start,
)
from tests.fakes import (
    FakeBotStartedEvent,
    FakeCallbackEvent,
    FakeFileAttachment,
    FakeMessageCreatedEvent,
    buttons_from,
)

USER_ID = 123


def _run(coro: Any) -> Any:
    """Запустить корутину синхронно."""
    return asyncio.run(coro)


def _payloads(buttons: list[Any]) -> list[str | None]:
    return [getattr(b, "payload", None) for b in buttons]


def _async_result(value: Any) -> Callable[..., Any]:
    """Заглушка API-функции, возвращающая фиксированный результат."""

    async def _fake(*args: Any, **kwargs: Any) -> Any:
        return value

    return _fake


def _stub_get_user(platform_id: int = 42) -> Callable[..., Any]:
    """Заглушка get-or-create пользователя на платформе."""

    async def _fake(max_user_id: int, name: str | None = None) -> dict[str, Any]:
        return {"id": platform_id}

    return _fake


def _failing_api_error(status: int) -> Callable[..., Any]:
    """Заглушка API-функции, поднимающая ApiError с HTTP-кодом."""

    async def _fake(*args: Any, **kwargs: Any) -> Any:
        raise api.ApiError(f"boom -> {status}", status)

    return _fake


def _fake_user(monkeypatch: pytest.MonkeyPatch, platform_id: int = 42) -> None:
    monkeypatch.setattr(api, "get_user", _stub_get_user(platform_id))


def test_on_bot_started_sends_greeting() -> None:
    event = FakeBotStartedEvent(USER_ID, "Аня")
    _run(start.on_bot_started(event))
    chat_id, text, attachments = event.bot.sent[0]
    assert (chat_id, text) == (
        USER_ID,
        "Привет, Аня! Я SkillQuest 🎮 Выбирай, что делаем:",
    )
    payloads = _payloads(buttons_from(attachments))
    assert "as:start" in payloads
    assert "ms:next" in payloads


def test_on_bot_started_skips_without_bot() -> None:
    event = FakeBotStartedEvent(USER_ID, "Аня")
    event.bot = None
    _run(start.on_bot_started(event))  # не должно бросить исключение


def test_cmd_start_ensures_user_and_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch, platform_id=9)
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    _run(start.cmd_start(event))
    assert len(event.answers) == 1
    text, attachments = event.answers[0]
    assert "Что делаем?" in text
    assert attachments
    assert sessions.session_for(USER_ID)["uid"] == 9


def test_cmd_start_skipped_right_after_bot_started(monkeypatch) -> None:
    _fake_user(monkeypatch, platform_id=9)
    sessions.session_for(USER_ID)["welcomed"] = True
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    _run(start.cmd_start(event))
    assert event.answers == []
    assert sessions.session_for(USER_ID)["uid"] == 9
    assert sessions.session_for(USER_ID)["welcomed"] is False


def test_cmd_start_skips_without_sender(monkeypatch) -> None:
    _fake_user(monkeypatch)
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    event.message.sender = None
    _run(start.cmd_start(event))
    assert event.answers == []


def test_cmd_help_answers_instruction() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    _run(start.cmd_help(event))
    assert len(event.answers) == 1
    text, attachments = event.answers[0]
    assert "Как пользоваться" in text
    assert attachments
    assert "help:show" in _payloads(buttons_from(attachments))


def test_show_help_edits_instruction() -> None:
    event = FakeCallbackEvent("help:show")
    _run(start.show_help(event))
    text, attachments = event.edits[0]
    assert "Как пользоваться" in text
    assert "help:show" in _payloads(buttons_from(attachments))


def test_back_to_menu_edits() -> None:
    event = FakeCallbackEvent("menu:main")
    _run(start.back_to_menu(event))
    assert len(event.edits) == 1
    assert "Главное меню" in event.edits[0][0]


def test_show_skill_map(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    items = [{"name": "Python", "level": 2, "progress": 50.0, "next_level_xp": 125}]
    monkeypatch.setattr(api, "skill_map", _async_result(items))

    event = FakeCallbackEvent("sm:show")
    _run(skillmap.show_skill_map(event))
    text = event.edits[0][0]
    assert "Python" in text
    assert "уровень 2" in text


def test_mission_next_shows_question(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    mission = {
        "id": 3,
        "skill_name": "Python",
        "difficulty": "medium",
        "reward_xp": 25,
        "scenario": "Напишите дебаггер.",
        "options": [{"id": 10, "text": "продолжить"}, {"id": 11, "text": "прервать"}],
    }
    monkeypatch.setattr(
        api,
        "next_mission",
        _async_result({"status": "ok", "done": 2, "total": 7, "mission": mission}),
    )

    event = FakeCallbackEvent("ms:next")
    _run(missions.mission_next(event))
    text, attachments = event.edits[0]
    assert "Миссия 3/7 по цели" in text
    assert "Python" in text
    assert "+25 XP" in text
    assert "1. прервать" in text
    assert "2. продолжить" in text
    payloads = _payloads(buttons_from(attachments))
    assert "ms:ans:3:10" in payloads
    assert "ms:ans:3:11" in payloads
    assert [b.text for b in buttons_from(attachments)[:-1]] == ["①", "②"]


def test_mission_display_order_single_option_not_shifted() -> None:
    options = missions._display_order(
        {"id": 3, "options": [{"id": 10, "text": "один"}]}
    )
    assert [o["id"] for o in options] == [10]


def test_mission_display_order_is_deterministic() -> None:
    mission = {
        "id": 3,
        "options": [
            {"id": 10, "text": "а"},
            {"id": 11, "text": "б"},
            {"id": 12, "text": "в"},
            {"id": 13, "text": "г"},
        ],
    }
    first = missions._display_order(mission)
    second = missions._display_order(mission)
    assert [o["id"] for o in first] == [o["id"] for o in second]


def test_mission_next_all_done(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(
        api,
        "next_mission",
        _async_result({"status": "all_done", "done": 7, "total": 7, "mission": None}),
    )

    event = FakeCallbackEvent("ms:next")
    _run(missions.mission_next(event))
    text, attachments = event.edits[0]
    assert "пройдено всё" in text
    payloads = _payloads(buttons_from(attachments))
    assert "cr:rec" in payloads
    assert "sm:show" in payloads


def test_mission_next_no_goal(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(
        api,
        "next_mission",
        _async_result({"status": "no_goal", "done": 0, "total": 0, "mission": None}),
    )

    event = FakeCallbackEvent("ms:next")
    _run(missions.mission_next(event))
    text, attachments = event.edits[0]
    assert "Сначала выбери цель" in text
    payloads = _payloads(buttons_from(attachments))
    assert "goal:show" in payloads


def test_mission_answer_correct(monkeypatch) -> None:
    _fake_user(monkeypatch)
    result = {
        "is_correct": True,
        "xp_earned": 25,
        "skill_name": "Python",
        "skill_level_before": 1,
        "skill_level_after": 2,
        "explanation": "Верно!",
    }
    monkeypatch.setattr(api, "answer_mission", _async_result(result))

    event = FakeCallbackEvent("ms:ans:3:10")
    _run(missions.mission_answer(event))
    text, _ = event.edits[0]
    assert "✅ Верно!" in text
    assert "+25 XP" in text
    assert "уровень 2" in text
    assert "1 → 2" in text
    assert "Верно!" in text


def test_mission_answer_wrong_without_skill_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    result = {
        "is_correct": False,
        "xp_earned": 0,
        "skill_name": None,
        "skill_level_before": 0,
        "skill_level_after": 0,
        "explanation": "",
        "correct_option_text": "Правильный вариант",
    }
    monkeypatch.setattr(api, "answer_mission", _async_result(result))

    event = FakeCallbackEvent("ms:ans:3:11")
    _run(missions.mission_answer(event))
    text, _ = event.edits[0]
    assert "❌ Не совсем" in text
    assert "Правильный вариант" in text
    assert "Навык «—»" in text


def test_mission_answer_already_solved(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    result = {
        "is_correct": True,
        "xp_earned": 0,
        "skill_name": "Python",
        "skill_level_before": 2,
        "skill_level_after": 2,
        "already_solved": True,
        "explanation": "Уже решено",
    }
    monkeypatch.setattr(api, "answer_mission", _async_result(result))

    event = FakeCallbackEvent("ms:ans:3:10")
    _run(missions.mission_answer(event))
    text, _ = event.edits[0]
    assert "🔁 Уже решено" in text
    assert "XP не приносит" in text
    assert "Навык «Python»: уровень 2" in text


def test_mission_answer_ignores_other_payloads() -> None:
    event = FakeCallbackEvent("ms:other")
    _run(missions.mission_answer(event))
    assert event.edits == []


def _stub_profile(target_role_id: int | None) -> Callable[..., Any]:
    """Заглушка профиля платформы (цель задана или нет)."""

    async def _fake(user_id: int) -> dict[str, Any]:
        return {"id": user_id, "target_role_id": target_role_id}

    return _fake


def _fake_profile(
    monkeypatch: pytest.MonkeyPatch, target_role_id: int | None = 1
) -> None:
    monkeypatch.setattr(api, "get_profile", _stub_profile(target_role_id))


def test_start_assessment_shows_first_question(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    _fake_profile(
        monkeypatch,
    )
    questions = [
        {"id": 1, "text": "Python?", "options": ["Нет", "Да"]},
        {"id": 2, "text": "SQL?", "options": ["Нет", "Да"]},
    ]
    monkeypatch.setattr(api, "assessment_questions", _async_result(questions))

    event = FakeCallbackEvent("as:start")
    _run(assessment.start_assessment(event))
    text, attachments = event.edits[0]
    assert "Вопрос 1/2" in text
    assert "1. Нет" in text
    assert "2. Да" in text
    assert "asq:1:0" in _payloads(buttons_from(attachments))
    assert "asq:1:1" in _payloads(buttons_from(attachments))
    assert sessions.session_for(USER_ID)["answers"] == []


def test_start_assessment_without_goal_asks_goal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    _fake_profile(monkeypatch, target_role_id=None)

    event = FakeCallbackEvent("as:start")
    _run(assessment.start_assessment(event))
    text, attachments = event.edits[0]
    assert "Сначала выбери цель" in text
    payloads = _payloads(buttons_from(attachments))
    assert "goal:show" in payloads


def test_assessment_question_shows_skill_label(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    _fake_profile(
        monkeypatch,
    )
    questions = [
        {"id": 1, "skill": "Python", "text": "Оцените знания", "options": ["Нет", "Да"]}
    ]
    monkeypatch.setattr(api, "assessment_questions", _async_result(questions))

    event = FakeCallbackEvent("as:start")
    _run(assessment.start_assessment(event))
    text, _ = event.edits[0]
    assert "Вопрос 1/1" in text
    assert "📌 Навык: Python" in text


def test_assessment_answer_ignores_other_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    event = FakeCallbackEvent("as:other")
    _run(assessment.assessment_answer(event))
    assert event.edits == []


def test_assessment_answer_goes_to_next_question(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    questions = [
        {"id": 1, "text": "Q1", "options": ["a", "b"]},
        {"id": 2, "text": "Q2", "options": ["a", "b"]},
    ]
    monkeypatch.setattr(api, "assessment_questions", _async_result(questions))

    event = FakeCallbackEvent("asq:1:1")
    _run(assessment.assessment_answer(event))
    assert "Вопрос 2/2" in event.edits[0][0]
    assert sessions.session_for(USER_ID)["answers"] == [
        {"question_id": 1, "option_index": 1}
    ]


def test_assessment_answer_finishes_and_submits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    questions = [{"id": 1, "text": "Q1", "options": ["a", "b"]}]
    monkeypatch.setattr(api, "assessment_questions", _async_result(questions))
    submitted: dict[str, Any] = {}

    async def fake_submit(
        user_id: int, answers: list[dict[str, Any]]
    ) -> dict[str, Any]:
        submitted["answers"] = answers
        return {"summary": "Вы Python-разработчик"}

    monkeypatch.setattr(api, "submit_assessment", fake_submit)

    sessions.session_for(USER_ID)["uid"] = 7  # uid уже известен — submit сразу
    event = FakeCallbackEvent("asq:1:1")
    _run(assessment.assessment_answer(event))
    assert submitted["answers"] == [{"question_id": 1, "option_index": 1}]
    text = event.edits[0][0]
    assert "Диагностика завершена" in text
    assert "Вы Python-разработчик" in text
    assert sessions.session_for(USER_ID)["answers"] == []


def _course() -> dict[str, Any]:
    return {
        "id": 1,
        "title": "FastAPI",
        "platform": "Stepik",
        "level": "junior",
        "format": "online",
        "cost": 0,
        "url": "https://stepik.org/1",
        "skills": [],
    }


def test_recommended_courses_with_items(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_courses", _async_result([_course()]))

    event = FakeCallbackEvent("cr:rec")
    _run(recommend.recommended_courses(event))
    text, attachments = event.edits[0]
    assert "Рекомендуемые курсы" in text
    assert "FastAPI" in text
    assert "бесплатно" not in text
    assert "₽" not in text
    buttons = buttons_from(attachments)
    urls = [getattr(b, "url", None) for b in buttons]
    assert "https://stepik.org/1" in urls
    assert buttons[0].text == "FastAPI"


def test_recommended_courses_pagination_next_and_prev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    items = [
        {
            "id": i,
            "title": f"Course {i}",
            "platform": "Stepik",
            "level": "junior",
            "format": "online",
            "cost": 0,
            "url": f"https://stepik.org/{i}",
            "skills": [],
        }
        for i in range(1, 8)
    ]
    monkeypatch.setattr(api, "rec_courses", _async_result(items))

    # Страница 1
    event_p0 = FakeCallbackEvent("cr:rec")
    _run(recommend.recommended_courses(event_p0))
    text0, att0 = event_p0.edits[0]
    assert "страница 1 из 2" in text0
    assert "1. Course 1" in text0
    assert "5. Course 5" in text0
    assert "6. Course 6" not in text0
    buttons0 = buttons_from(att0)
    assert buttons0[0].text == "Course 1"
    assert buttons0[5].text == "Следующая страница ➡️"
    assert buttons0[5].payload == "cr:page:1"

    # Страница 2
    event_p1 = FakeCallbackEvent("cr:page:1")
    _run(recommend.recommended_courses(event_p1))
    text1, att1 = event_p1.edits[0]
    assert "страница 2 из 2" in text1
    assert "6. Course 6" in text1
    assert "7. Course 7" in text1
    buttons1 = buttons_from(att1)
    assert buttons1[0].text == "Course 6"
    assert buttons1[2].text == "⬅️ Предыдущая страница"
    assert buttons1[2].payload == "cr:page:0"


def test_recommended_courses_invalid_page(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_courses", _async_result([_course()]))

    # Невалидный номер страницы — откат на 0
    event = FakeCallbackEvent("cr:page:invalid")
    _run(recommend.recommended_courses(event))
    text, _ = event.edits[0]
    assert "FastAPI" in text

    # Запредельный номер страницы — ограничение максимальной страницей
    event_overflow = FakeCallbackEvent("cr:page:999")
    _run(recommend.recommended_courses(event_overflow))
    text_ov, _ = event_overflow.edits[0]
    assert "FastAPI" in text_ov


def test_recommended_courses_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_courses", _async_result([]))

    event = FakeCallbackEvent("cr:rec")
    _run(recommend.recommended_courses(event))
    assert "пока нет" in event.edits[0][0]


def _rec_internships_stub(
    store: dict[str, Any], items: list[dict[str, Any]]
) -> Callable[..., Any]:
    """Заглушка rec_internships, запоминающая выбранное направление."""

    async def _fake(user_id: int, direction: str | None = None) -> list[dict[str, Any]]:
        store["direction"] = direction
        return items

    return _fake


def _internship_item() -> dict[str, Any]:
    return {
        "title": "Стажёр",
        "company": "Яндекс",
        "level": "beginner",
        "remote": True,
        "format": "remote",
        "url": "https://ya.ru/vacancy",
        "skills": [],
    }


def _internships(count: int, direction: str = "backend") -> list[dict[str, Any]]:
    """Список стажировок для проверки пагинации."""
    return [
        {
            "title": f"Стажировка {i}",
            "company": f"Компания {i}",
            "level": "beginner",
            "remote": False,
            "city": "Москва",
            "format": "office",
            "url": f"https://jobs/{i}",
            "direction": direction,
            "skills": [],
        }
        for i in range(1, count + 1)
    ]


def test_internship_filters_shows_directions(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(
        api, "internship_directions", _async_result(["backend", "frontend"])
    )

    event = FakeCallbackEvent("in:rec")
    _run(recommend.internship_filters(event))
    text, attachments = event.edits[0]
    assert "Выбери направление" in text
    assert _payloads(buttons_from(attachments)) == [
        "in:dir:any",
        "in:dir:backend",
        "in:dir:frontend",
        "menu:main",
    ]


def test_internship_filters_without_directions_falls_back_to_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    store: dict[str, Any] = {}
    monkeypatch.setattr(api, "internship_directions", _async_result([]))
    monkeypatch.setattr(
        api, "rec_internships", _rec_internships_stub(store, [_internship_item()])
    )

    event = FakeCallbackEvent("in:rec")
    _run(recommend.internship_filters(event))
    assert "Стажёр @ Яндекс" in event.edits[0][0]
    assert store["direction"] is None


def test_internships_by_direction_filters(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    store: dict[str, Any] = {}
    monkeypatch.setattr(
        api, "rec_internships", _rec_internships_stub(store, [_internship_item()])
    )

    event = FakeCallbackEvent("in:dir:backend")
    _run(recommend.internships_by_direction(event))
    text, attachments = event.edits[0]
    assert "Стажёр @ Яндекс" in text
    assert "backend" in text
    assert store["direction"] == "backend"
    buttons = buttons_from(attachments)
    # Направление не задано — подпись ссылки без направления
    assert buttons[0].text == "1. Яндекс"
    assert buttons[0].url == "https://ya.ru/vacancy"
    assert _payloads(buttons[1:]) == ["in:rec", "menu:main"]


def test_internships_by_direction_any(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    store: dict[str, Any] = {}
    monkeypatch.setattr(
        api, "rec_internships", _rec_internships_stub(store, [_internship_item()])
    )

    event = FakeCallbackEvent("in:dir:any")
    _run(recommend.internships_by_direction(event))
    text = event.edits[0][0]
    assert store["direction"] is None
    assert "Рекомендуемые стажировки" in text
    assert "Все направления" not in text


def test_internships_pagination_next_and_prev(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    store: dict[str, Any] = {}
    monkeypatch.setattr(
        api, "rec_internships", _rec_internships_stub(store, _internships(7))
    )

    # Страница 1: «Все направления» — все стажировки по 5 на страницу
    event_p0 = FakeCallbackEvent("in:dir:any")
    _run(recommend.internships_by_direction(event_p0))
    text0, att0 = event_p0.edits[0]
    assert store["direction"] is None
    assert "страница 1 из 2" in text0
    assert "1. Стажировка 1 @ Компания 1" in text0
    assert "5. Стажировка 5" in text0
    assert "6. Стажировка 6" not in text0
    buttons0 = buttons_from(att0)
    assert buttons0[0].text == "1. Компания 1 · backend"
    assert buttons0[0].url == "https://jobs/1"
    assert buttons0[5].text == "Следующая страница ➡️"
    assert buttons0[5].payload == "in:dir:any:1"
    assert buttons0[6].payload == "in:rec"
    assert buttons0[7].payload == "menu:main"

    # Страница 2: направление backend — сквозная нумерация и возврат назад
    event_p1 = FakeCallbackEvent("in:dir:backend:1")
    _run(recommend.internships_by_direction(event_p1))
    text1, att1 = event_p1.edits[0]
    assert store["direction"] == "backend"
    assert "— backend (страница 2 из 2)" in text1
    assert "6. Стажировка 6 @ Компания 6" in text1
    assert "7. Стажировка 7" in text1
    buttons1 = buttons_from(att1)
    assert buttons1[0].text == "6. Компания 6 · backend"
    assert buttons1[2].text == "⬅️ Предыдущая страница"
    assert buttons1[2].payload == "in:dir:backend:0"
    assert buttons1[3].payload == "in:rec"


def test_internships_pagination_invalid_and_overflow_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_internships", _async_result(_internships(2)))

    # Невалидный номер страницы — первая страница
    event = FakeCallbackEvent("in:dir:any:invalid")
    _run(recommend.internships_by_direction(event))
    text, _ = event.edits[0]
    assert "1. Стажировка 1" in text
    assert "страница" not in text

    # Запредельный номер страницы — ограничение последней страницей
    event_overflow = FakeCallbackEvent("in:dir:any:999")
    _run(recommend.internships_by_direction(event_overflow))
    assert "2. Стажировка 2" in event_overflow.edits[0][0]
    assert "страница" not in event_overflow.edits[0][0]


def test_internships_single_page_has_no_nav(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_internships", _async_result(_internships(1)))

    event = FakeCallbackEvent("in:dir:backend")
    _run(recommend.internships_by_direction(event))
    assert "страница" not in event.edits[0][0]
    assert _payloads(buttons_from(event.edits[0][1])) == [
        None,
        "in:rec",
        "menu:main",
    ]


def test_internships_by_direction_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_internships", _async_result([]))

    event = FakeCallbackEvent("in:dir:qa")
    _run(recommend.internships_by_direction(event))
    text, attachments = event.edits[0]
    assert "qa" in text
    assert "пока нет" in text
    assert _payloads(buttons_from(attachments)) == ["in:rec", "menu:main"]


def test_parse_direction_payload() -> None:
    assert recommend._parse_direction("in:dir:backend") == "backend"
    assert recommend._parse_direction("in:dir:backend:2") == "backend"
    assert recommend._parse_direction("in:dir:any") is None
    assert recommend._parse_direction("in:dir:any:2") is None
    assert recommend._parse_direction("in:dir:") is None
    assert recommend._parse_direction("in:dir") is None


def test_parse_page_payload() -> None:
    assert recommend._parse_page("in:dir:any") == 0
    assert recommend._parse_page("in:dir:any:2") == 2
    assert recommend._parse_page("in:dir:backend:invalid") == 0
    assert recommend._parse_page("in:dir:backend:") == 0


def test_cards_links_numbers_with_offset() -> None:
    items = [{"title": f"Курс {i}", "url": f"https://x/{i}"} for i in range(3)]

    def card_fn(item: dict[str, Any], index: int) -> str:
        return f"{index}. {item['title']}"

    cards, links = recommend._cards_links(
        items, card_fn, lambda item, index: f"{index}. {item['title']}", offset=5
    )
    assert cards.split("\n") == ["6. Курс 0", "7. Курс 1", "8. Курс 2"]
    assert links == [
        ("6. Курс 0", "https://x/0"),
        ("7. Курс 1", "https://x/1"),
        ("8. Курс 2", "https://x/2"),
    ]


def test_cards_links_skips_missing_url() -> None:
    items = [{"title": "A", "url": "https://a"}, {"title": "B"}]
    cards, links = recommend._cards_links(
        items, lambda item, index: "x", lambda item, index: "L"
    )
    assert links == [("L", "https://a")]
    assert cards == "x\nx"


def test_ask_resume_sets_waiting_flag() -> None:
    sessions.session_for(USER_ID)["consent"] = True
    event = FakeCallbackEvent("rs:start")
    _run(resume.ask_resume(event))
    assert sessions.session_for(USER_ID)["resume"] is True
    text, attachments = event.edits[0]
    assert "Пришли резюме" in text
    buttons = buttons_from(attachments)
    assert [b.payload for b in buttons] == [
        "rs:consent:revoke",
        "menu:main",
    ]


def test_delete_resume_removes_uploaded_document(monkeypatch) -> None:
    """В отчёте кнопка удаляет загруженное резюме."""
    deleted: list[int] = []

    async def fake_delete(resume_id: int) -> None:
        deleted.append(resume_id)

    monkeypatch.setattr(api, "delete_resume", fake_delete)

    event = FakeCallbackEvent("rs:del:12")
    _run(resume.delete_resume(event))

    assert deleted == [12]
    assert "удалено" in event.edits[0][0]


def test_delete_resume_reports_api_error(monkeypatch) -> None:
    """Ошибка удаления не роняет хендлер, а объясняется."""

    async def boom(resume_id: int) -> None:
        raise api.ApiError("DELETE /resumes/12 -> 500", 500)

    monkeypatch.setattr(api, "delete_resume", boom)

    event = FakeCallbackEvent("rs:del:12")
    _run(resume.delete_resume(event))

    assert "Не получилось удалить" in event.edits[0][0]


def test_delete_resume_ignores_broken_payloads() -> None:
    """Мусорный payload игнорируется, а не роняет хендлер."""
    for payload in ("rs:del:", "rs:del:abc", "rs:other"):
        event = FakeCallbackEvent(payload)
        _run(resume.delete_resume(event))
        assert event.edits == []


def _stub_ai(enabled: bool):
    """Заглушка проверки статуса AI-оценки: всегда заданный ответ."""

    async def _fake() -> bool:
        return enabled

    return _fake


def test_ask_resume_asks_consent_first(monkeypatch) -> None:
    """Без согласия резюме не принимаем — показываем экран согласия (152-ФЗ ст. 9)."""
    monkeypatch.setattr(api, "ai_assessment_enabled", _stub_ai(enabled=True))
    event = FakeCallbackEvent("rs:start")
    _run(resume.ask_resume(event))

    assert sessions.session_for(USER_ID)["resume"] is False
    text, attachments = event.edits[0]
    assert "согласие" in text
    assert "152-ФЗ" in text
    assert [b.payload for b in buttons_from(attachments)] == [
        "rs:consent:yes",
        "rs:consent:no",
        "rs:policy",
        "menu:main",
    ]


def test_consent_text_states_gigachat_transfer_as_fact(monkeypatch) -> None:
    """При включённой AI-оценке согласие утверждает передачу, а не возможность."""
    monkeypatch.setattr(api, "ai_assessment_enabled", _stub_ai(enabled=True))
    event = FakeCallbackEvent("rs:start")
    _run(resume.ask_resume(event))

    text = event.edits[0][0]
    assert "GigaChat" in text
    assert "ПАО Сбербанк" in text
    assert "8000" in text
    assert "Если" not in text


def test_consent_text_without_ai_says_no_transfer(monkeypatch) -> None:
    """Без AI-оценки согласие прямо говорит, что текст не передаётся."""
    monkeypatch.setattr(api, "ai_assessment_enabled", _stub_ai(enabled=False))
    event = FakeCallbackEvent("rs:start")
    _run(resume.ask_resume(event))

    text = event.edits[0][0]
    assert "не подключена" in text
    assert "никуда не уходит" in text
    assert "GigaChat" not in text


def test_accept_consent_records_and_asks_resume(monkeypatch) -> None:
    _fake_user(monkeypatch, platform_id=5)
    calls: list[int] = []

    async def fake_give(uid: int) -> dict[str, Any]:
        calls.append(uid)
        return {"user_id": uid, "consent_given": True}

    monkeypatch.setattr(api, "give_consent", fake_give)

    event = FakeCallbackEvent("rs:consent:yes")
    _run(resume.accept_consent(event))

    assert calls == [5]
    item = sessions.session_for(USER_ID)
    assert item["consent"] is True
    assert item["resume"] is True
    assert "Пришли резюме" in event.edits[0][0]


def test_accept_consent_reuses_known_user(monkeypatch) -> None:
    sessions.session_for(USER_ID)["uid"] = 3
    calls: list[int] = []

    async def fake_give(uid: int) -> dict[str, Any]:
        calls.append(uid)
        return {"user_id": uid, "consent_given": True}

    monkeypatch.setattr(api, "give_consent", fake_give)

    _run(resume.accept_consent(FakeCallbackEvent("rs:consent:yes")))

    assert calls == [3]


def test_accept_consent_fails_closed(monkeypatch) -> None:
    """Не зафиксировали согласие в API — резюме не принимаем."""
    _fake_user(monkeypatch, platform_id=5)

    async def boom(uid: int) -> dict[str, Any]:
        raise api.ApiError("POST /users/5/consent -> 500", 500)

    monkeypatch.setattr(api, "give_consent", boom)

    event = FakeCallbackEvent("rs:consent:yes")
    _run(resume.accept_consent(event))

    item = sessions.session_for(USER_ID)
    assert item["consent"] is False
    assert item["resume"] is False
    assert "Не удалось зафиксировать согласие" in event.edits[0][0]


def test_decline_consent_blocks_resume() -> None:
    sessions.session_for(USER_ID)["consent"] = True
    sessions.session_for(USER_ID)["resume"] = True

    event = FakeCallbackEvent("rs:consent:no")
    _run(resume.decline_consent(event))

    item = sessions.session_for(USER_ID)
    assert item["consent"] is False
    assert item["resume"] is False
    assert "обрабатывать не буду" in event.edits[0][0]


def test_show_policy_lists_rights(monkeypatch) -> None:
    monkeypatch.setattr(api, "ai_assessment_enabled", _stub_ai(enabled=True))
    event = FakeCallbackEvent("rs:policy")
    _run(resume.show_policy(event))

    text = event.edits[0][0]
    assert "Политика обработки персональных данных" in text
    assert "Роскомнадзоре" in text
    assert "отозвать согласие" in text
    assert "GigaChat" in text
    assert "8000" in text


def test_show_policy_without_ai_has_no_gigachat(monkeypatch) -> None:
    monkeypatch.setattr(api, "ai_assessment_enabled", _stub_ai(enabled=False))
    event = FakeCallbackEvent("rs:policy")
    _run(resume.show_policy(event))

    text = event.edits[0][0]
    assert "не подключена" in text
    assert "GigaChat" not in text


def test_revoke_consent_clears_flag_and_calls_api(monkeypatch) -> None:
    sessions.session_for(USER_ID)["uid"] = 3
    sessions.session_for(USER_ID)["consent"] = True
    sessions.session_for(USER_ID)["resume"] = True
    calls: list[int] = []

    async def fake_revoke(uid: int) -> dict[str, Any]:
        calls.append(uid)
        return {"user_id": uid, "consent_given": False}

    monkeypatch.setattr(api, "revoke_consent", fake_revoke)

    event = FakeCallbackEvent("rs:consent:revoke")
    _run(resume.revoke_consent(event))

    assert calls == [3]
    item = sessions.session_for(USER_ID)
    assert item["consent"] is False
    assert item["resume"] is False
    assert "отозвано" in event.edits[0][0]


def test_revoke_consent_without_uid_and_api_error(monkeypatch) -> None:
    """Без известного uid и при ошибке API чат не падает."""
    sessions.session_for(USER_ID)["consent"] = True

    async def boom(uid: int) -> dict[str, Any]:
        raise api.ApiError("DELETE -> 500", 500)

    sessions.session_for(USER_ID)["uid"] = 9
    monkeypatch.setattr(api, "revoke_consent", boom)
    _run(resume.revoke_consent(FakeCallbackEvent("rs:consent:revoke")))
    assert sessions.session_for(USER_ID)["consent"] is False

    sessions.session_for(USER_ID)["uid"] = None
    _run(resume.revoke_consent(FakeCallbackEvent("rs:consent:revoke")))
    assert sessions.session_for(USER_ID)["consent"] is False


def test_resume_not_accepted_without_consent(monkeypatch) -> None:
    """Защита в обработчике: без согласия текст резюме наружу не уходит."""
    item = sessions.session_for(USER_ID)
    item["resume"] = True
    item["consent"] = False
    uploaded: list[str] = []

    async def fake_upload(uid: int, body: str) -> dict[str, Any]:
        uploaded.append(body)
        return {"id": 1}

    monkeypatch.setattr(api, "upload_resume", fake_upload)

    _run(
        resume.capture_resume_text(
            FakeMessageCreatedEvent(USER_ID, "Ваня", "Моё резюме")
        )
    )

    assert uploaded == []


def _resume_analysis() -> dict[str, Any]:
    return {
        "resume_id": 12,
        "direction_match": 75,
        "found_skills": ["Python"],
        "missing_skills": [],
        "strengths": ["Проекты"],
        "issues": [],
        "recommendations": [],
        "ai_score": 82,
        "ai_summary": "Хорошее резюме для стажировки",
    }


def _waiting_for_resume(uid: int = 7) -> None:
    """Перевести сессию пользователя в режим ожидания резюме (с согласием)."""
    item = sessions.session_for(USER_ID)
    item["resume"] = True
    item["consent"] = True
    item["uid"] = uid


def test_capture_resume_file_uploads_and_analyzes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake_user(monkeypatch)
    _waiting_for_resume()
    uploaded: list[tuple[int, str | None, bytes]] = []

    async def fake_upload(
        user_id: int, filename: str | None, content: bytes
    ) -> dict[str, Any]:
        uploaded.append((user_id, filename, content))
        return {"id": 12}

    monkeypatch.setattr(api, "upload_resume_file", fake_upload)
    monkeypatch.setattr(api, "analyze_resume", _async_result(_resume_analysis()))

    event = FakeMessageCreatedEvent(
        USER_ID,
        "Ваня",
        attachments=[FakeFileAttachment(filename="cv.pdf")],
        file_bytes=b"%PDF-1.4 resume",
    )
    _run(resume.capture_resume_file(event))

    assert event.bot.downloaded == ["https://max.ru/files/1"]
    assert uploaded == [(7, "cv.pdf", b"%PDF-1.4 resume")]
    assert sessions.session_for(USER_ID)["resume"] is False
    text, attachments = event.answers[0]
    assert "75%" in text
    assert "Оценка : 82/100" in text
    payloads = _payloads(buttons_from(attachments))
    assert "rs:start" in payloads
    assert "menu:main" in payloads


def test_capture_resume_file_ignores_when_not_waiting() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", attachments=[FakeFileAttachment()])
    _run(resume.capture_resume_file(event))
    assert event.answers == []
    assert event.bot.downloaded == []


def test_capture_resume_file_skips_without_sender() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", attachments=[FakeFileAttachment()])
    event.message.sender = None
    _run(resume.capture_resume_file(event))
    assert event.answers == []


def test_capture_resume_file_without_file_attachment() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", attachments=[SimpleNamespace(filename=None)]
    )
    _run(resume.capture_resume_file(event))
    text, attachments = event.answers[0]
    assert "нет файла" in text
    assert _payloads(buttons_from(attachments)) == ["menu:main"]


def test_capture_resume_file_without_bot() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", attachments=[FakeFileAttachment()])
    event.message.bot = None
    _run(resume.capture_resume_file(event))
    assert "нет файла" in event.answers[0][0]


def test_capture_resume_file_without_url() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", attachments=[FakeFileAttachment(url=None)]
    )
    _run(resume.capture_resume_file(event))
    assert "ссылки на скачивание" in event.answers[0][0]


def test_capture_resume_file_bad_format(monkeypatch: pytest.MonkeyPatch) -> None:
    _waiting_for_resume()
    monkeypatch.setattr(api, "upload_resume_file", _failing_api_error(422))

    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", attachments=[FakeFileAttachment()], file_bytes=b"png"
    )
    _run(resume.capture_resume_file(event))
    assert "формат не поддерживается" in event.answers[0][0]
    assert sessions.session_for(USER_ID)["resume"] is False


def test_capture_resume_file_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _waiting_for_resume()
    monkeypatch.setattr(api, "upload_resume_file", _async_result({"id": 12}))
    monkeypatch.setattr(api, "analyze_resume", _failing_api_error(500))

    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", attachments=[FakeFileAttachment()], file_bytes=b"txt"
    )
    _run(resume.capture_resume_file(event))
    assert "сервис анализа вернул ошибку" in event.answers[0][0]


def test_capture_resume_file_download_error() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", attachments=[FakeFileAttachment()], file_bytes=b"txt"
    )
    event.bot.download_error = RuntimeError("нет сети")
    _run(resume.capture_resume_file(event))
    assert "файл не удалось скачать" in event.answers[0][0]


def test_on_text_resume_mode_analyzes(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    _waiting_for_resume()
    monkeypatch.setattr(api, "upload_resume", _async_result({"id": 12}))
    monkeypatch.setattr(api, "analyze_resume", _async_result(_resume_analysis()))

    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "Моё резюме...")
    _run(fallback.on_text(event))
    assert len(event.answers) == 1
    text, _ = event.answers[0]
    assert "75%" in text
    assert sessions.session_for(USER_ID)["resume"] is False


def test_capture_resume_text_analyzes_without_uid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Текст резюме без uid в сессии: пользователь создаётся через get-or-create."""
    _fake_user(monkeypatch, platform_id=42)
    uploads: list[tuple[int, str]] = []

    async def fake_upload(user_id: int, text: str) -> dict[str, Any]:
        uploads.append((user_id, text))
        return {"id": 13}

    sessions.session_for(USER_ID)["resume"] = True
    sessions.session_for(USER_ID)["consent"] = True
    monkeypatch.setattr(api, "upload_resume", fake_upload)
    monkeypatch.setattr(api, "analyze_resume", _async_result(_resume_analysis()))

    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "Моё резюме...")
    _run(resume.capture_resume_text(event))

    assert uploads == [(42, "Моё резюме...")]
    text, attachments = event.answers[0]
    assert "Оценка : 82/100" in text
    assert _payloads(buttons_from(attachments)) == [
        "rs:start",
        "rs:del:12",
        "menu:main",
    ]
    assert sessions.session_for(USER_ID)["uid"] == 42


def test_on_text_resume_mode_cancels_by_word(monkeypatch: pytest.MonkeyPatch) -> None:
    sessions.session_for(USER_ID)["resume"] = True
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "Отмена")
    _run(fallback.on_text(event))
    assert sessions.session_for(USER_ID)["resume"] is False
    assert "Отменил" in event.answers[0][0]
    assert "help:show" in _payloads(buttons_from(event.answers[0][1]))


def test_on_text_fallback_replies_menu() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "просто текст")
    _run(fallback.on_text(event))
    assert len(event.answers) == 1
    text, attachments = event.answers[0]
    assert "кнопки меню" in text
    assert "help:show" in _payloads(buttons_from(attachments))


def test_capture_resume_text_ignores_outside_resume_mode() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "просто текст")
    _run(resume.capture_resume_text(event))
    assert event.answers == []


def test_capture_resume_text_skips_messages_with_attachments() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(
        USER_ID, "Ваня", "подпись к файлу", attachments=[FakeFileAttachment()]
    )
    _run(resume.capture_resume_text(event))
    assert event.answers == []


def test_capture_resume_text_skips_without_sender() -> None:
    _waiting_for_resume()
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "текст")
    event.message.sender = None
    _run(resume.capture_resume_text(event))
    assert event.answers == []


def test_on_text_skips_without_sender() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "текст")
    event.message.sender = None
    _run(fallback.on_text(event))
    assert event.answers == []


def test_on_text_skips_empty_text() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    event.message.body.text = None
    _run(fallback.on_text(event))
    assert event.answers == []


def _roles() -> list[dict[str, Any]]:
    return [
        {"id": 1, "name": "Backend Junior"},
        {"id": 2, "name": "Data Analyst Junior"},
    ]


def _gap_analysis() -> dict[str, Any]:
    return {
        "role": {"id": 1, "name": "Backend Junior"},
        "match_percent": 43,
        "items": [
            {
                "name": "SQL",
                "current_level": 2,
                "required_level": 3,
                "gap": 1,
                "is_mandatory": True,
            },
            {
                "name": "Python",
                "current_level": 3,
                "required_level": 3,
                "gap": 0,
                "is_mandatory": True,
            },
        ],
        "summary": "Соответствие 43%",
    }


def test_goal_show_lists_roles(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "list_roles", _async_result(_roles()))

    event = FakeCallbackEvent("goal:show")
    _run(goal.goal_show(event))
    text, attachments = event.edits[0]
    assert "Какую цель выбираешь?" in text
    buttons = buttons_from(attachments)
    assert [getattr(b, "text", None) for b in buttons[:2]] == [
        "Backend Junior",
        "Data Analyst Junior",
    ]
    assert [b.payload for b in buttons[:2]] == ["goal:pick:1", "goal:pick:2"]
    assert buttons[-1].payload == "menu:main"


def test_goal_show_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "list_roles", _async_result([]))

    event = FakeCallbackEvent("goal:show")
    _run(goal.goal_show(event))
    assert "Ролей пока нет" in event.edits[0][0]


def test_goal_pick_sets_goal_and_shows_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(api, "gap_analysis", _async_result(_gap_analysis()))

    async def fake_set_goal(user_id: int, target_role_id: int) -> dict[str, Any]:
        calls.append((user_id, target_role_id))
        return {"id": user_id, "target_role_id": target_role_id}

    monkeypatch.setattr(api, "set_goal", fake_set_goal)

    event = FakeCallbackEvent("goal:pick:1")
    _run(goal.goal_pick(event))
    assert calls == [(42, 1)]
    text, attachments = event.edits[0]
    assert "Цель: Backend Junior" in text
    assert "43%" in text
    assert "SQL" in text
    payloads = _payloads(buttons_from(attachments))
    assert "goal:show" in payloads  # показано главное меню


def test_goal_pick_ignores_other_payloads(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_user(monkeypatch)
    event = FakeCallbackEvent("goal:wrong")
    _run(goal.goal_pick(event))
    assert event.edits == []

"""Тесты хендлеров MAX-бота на фейк-событиях (без сети и API)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import api
import sessions
from handlers import assessment, goal, missions, recommend, resume, skillmap, start
from tests.fakes import (
    FakeBotStartedEvent,
    FakeCallbackEvent,
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


def _fake_user(monkeypatch, platform_id: int = 42) -> None:
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


def test_cmd_start_ensures_user_and_answers(monkeypatch) -> None:
    _fake_user(monkeypatch, platform_id=9)
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    _run(start.cmd_start(event))
    assert len(event.answers) == 1
    text, attachments = event.answers[0]
    assert "Что делаем?" in text
    assert attachments
    assert sessions.session_for(USER_ID)["uid"] == 9


def test_cmd_start_skips_without_sender(monkeypatch) -> None:
    _fake_user(monkeypatch)
    event = FakeMessageCreatedEvent(USER_ID, "Ваня")
    event.message.sender = None
    _run(start.cmd_start(event))
    assert event.answers == []


def test_back_to_menu_edits() -> None:
    event = FakeCallbackEvent("menu:main")
    _run(start.back_to_menu(event))
    assert len(event.edits) == 1
    assert "Главное меню" in event.edits[0][0]


def test_show_skill_map(monkeypatch) -> None:
    _fake_user(monkeypatch)
    items = [{"name": "Python", "level": 2, "progress": 50.0, "next_level_xp": 125}]
    monkeypatch.setattr(api, "skill_map", _async_result(items))

    event = FakeCallbackEvent("sm:show")
    _run(skillmap.show_skill_map(event))
    text = event.edits[0][0]
    assert "Python" in text
    assert "уровень 2" in text


def test_mission_next_shows_question(monkeypatch) -> None:
    _fake_user(monkeypatch)
    mission = {
        "id": 3,
        "skill_name": "Python",
        "difficulty": "medium",
        "reward_xp": 25,
        "scenario": "Напишите дебаггер.",
        "options": [{"id": 10, "text": "продолжить"}, {"id": 11, "text": "прервать"}],
    }
    monkeypatch.setattr(api, "next_mission", _async_result(mission))

    event = FakeCallbackEvent("ms:next")
    _run(missions.mission_next(event))
    text, attachments = event.edits[0]
    assert "Python" in text
    assert "+25 XP" in text
    assert "1. продолжить" in text
    assert "2. прервать" in text
    payloads = _payloads(buttons_from(attachments))
    assert "ms:ans:3:10" in payloads
    assert "ms:ans:3:11" in payloads
    assert [b.text for b in buttons_from(attachments)[:-1]] == ["①", "②"]


def test_mission_next_all_done(monkeypatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "next_mission", _async_result(None))

    event = FakeCallbackEvent("ms:next")
    _run(missions.mission_next(event))
    assert "Все миссии пройдены" in event.edits[0][0]


def test_mission_answer_correct(monkeypatch) -> None:
    _fake_user(monkeypatch)
    result = {
        "is_correct": True,
        "xp_earned": 25,
        "skill_name": "Python",
        "skill_level_after": 2,
        "explanation": "Верно!",
    }
    monkeypatch.setattr(api, "answer_mission", _async_result(result))

    event = FakeCallbackEvent("ms:ans:3:10")
    _run(missions.mission_answer(event))
    text, _ = event.edits[0]
    assert "✅ Верно!" in text
    assert "уровень 2" in text
    assert "Верно!" in text


def test_mission_answer_wrong_without_skill_name(monkeypatch) -> None:
    _fake_user(monkeypatch)
    result = {
        "is_correct": False,
        "xp_earned": 0,
        "skill_name": None,
        "skill_level_after": 0,
        "explanation": "",
    }
    monkeypatch.setattr(api, "answer_mission", _async_result(result))

    event = FakeCallbackEvent("ms:ans:3:11")
    _run(missions.mission_answer(event))
    text, _ = event.edits[0]
    assert "❌ Не совсем" in text
    assert "Навык «—»" in text


def test_start_assessment_shows_first_question(monkeypatch) -> None:
    _fake_user(monkeypatch)
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


def test_assessment_answer_goes_to_next_question(monkeypatch) -> None:
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


def test_assessment_answer_finishes_and_submits(monkeypatch) -> None:
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


def test_recommended_courses_with_items(monkeypatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_courses", _async_result([_course()]))

    event = FakeCallbackEvent("cr:rec")
    _run(recommend.recommended_courses(event))
    text, attachments = event.edits[0]
    assert "Рекомендуемые курсы" in text
    assert "FastAPI" in text
    urls = [getattr(b, "url", None) for b in buttons_from(attachments)]
    assert "https://stepik.org/1" in urls


def test_recommended_courses_empty(monkeypatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_courses", _async_result([]))

    event = FakeCallbackEvent("cr:rec")
    _run(recommend.recommended_courses(event))
    assert "пока нет" in event.edits[0][0]


def test_recommended_internships(monkeypatch) -> None:
    _fake_user(monkeypatch)
    item = {
        "title": "Стажёр",
        "company": "Яндекс",
        "level": "beginner",
        "remote": True,
        "format": "remote",
        "url": "https://ya.ru/vacancy",
        "skills": [],
    }
    monkeypatch.setattr(api, "rec_internships", _async_result([item]))

    event = FakeCallbackEvent("in:rec")
    _run(recommend.recommended_internships(event))
    text, _ = event.edits[0]
    assert "Стажёр @ Яндекс" in text


def test_recommended_internships_empty(monkeypatch) -> None:
    _fake_user(monkeypatch)
    monkeypatch.setattr(api, "rec_internships", _async_result([]))

    event = FakeCallbackEvent("in:rec")
    _run(recommend.recommended_internships(event))
    assert "пока нет" in event.edits[0][0]


def test_cards_links_limit_to_five() -> None:
    items = [{"title": f"Курс {i}", "url": f"https://x/{i}"} for i in range(7)]

    def card_fn(item: dict[str, Any], index: int) -> str:
        return f"{index}. {item['title']}"

    cards, links = recommend._cards_links(items, card_fn, "Открыть")
    assert len(cards.split("\n")) == 5
    assert len(links) == 5
    assert links[0] == ("Открыть 1", "https://x/0")


def test_cards_links_skips_missing_url() -> None:
    items = [{"title": "A", "url": "https://a"}, {"title": "B"}]
    cards, links = recommend._cards_links(items, lambda item, index: "x", "L")
    assert len(links) == 1
    assert cards == "x\nx"


def test_ask_resume_sets_waiting_flag() -> None:
    event = FakeCallbackEvent("rs:start")
    _run(resume.ask_resume(event))
    assert sessions.session_for(USER_ID)["resume"] is True
    assert "Пришли текст резюме" in event.edits[0][0]


def test_capture_resume_text_analyzes(monkeypatch) -> None:
    _fake_user(monkeypatch)
    item = sessions.session_for(USER_ID)
    item["resume"] = True
    item["uid"] = 7
    monkeypatch.setattr(api, "upload_resume", _async_result({"id": 12}))
    analysis = {
        "direction_match": 75,
        "found_skills": ["Python"],
        "missing_skills": [],
        "strengths": [],
        "issues": [],
        "recommendations": [],
    }
    monkeypatch.setattr(api, "analyze_resume", _async_result(analysis))

    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "Моё резюме...")
    _run(resume.capture_resume_text(event))
    assert len(event.answers) == 1
    text, _ = event.answers[0]
    assert "75%" in text
    assert sessions.session_for(USER_ID)["resume"] is False


def test_capture_resume_text_ignores_when_not_waiting() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "просто текст")
    _run(resume.capture_resume_text(event))
    assert event.answers == []


def test_capture_resume_text_skips_without_sender() -> None:
    event = FakeMessageCreatedEvent(USER_ID, "Ваня", "текст")
    event.message.sender = None
    _run(resume.capture_resume_text(event))
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


def test_goal_show_lists_roles(monkeypatch) -> None:
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


def test_goal_show_empty(monkeypatch) -> None:
    monkeypatch.setattr(api, "list_roles", _async_result([]))

    event = FakeCallbackEvent("goal:show")
    _run(goal.goal_show(event))
    assert "Ролей пока нет" in event.edits[0][0]


def test_goal_pick_sets_goal_and_shows_gap(monkeypatch) -> None:
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


def test_goal_pick_ignores_other_payloads(monkeypatch) -> None:
    _fake_user(monkeypatch)
    event = FakeCallbackEvent("goal:wrong")
    _run(goal.goal_pick(event))
    assert event.edits == []

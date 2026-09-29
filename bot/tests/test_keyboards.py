"""Тесты inline-клавиатур бота."""

from __future__ import annotations

from typing import Any

import keyboards as kbs
from tests.fakes import buttons_from


def _payloads(buttons: list) -> list[str | None]:
    return [getattr(b, "payload", None) for b in buttons]


def _rows(attachments: list[Any] | None) -> list[list[Any]]:
    """Ряды кнопок без сплющивания (для проверки раскладки)."""
    rows: list[list[Any]] = []
    for item in attachments or []:
        payload = getattr(item, "payload", None)
        if payload is None:
            continue
        rows.extend(getattr(payload, "buttons", []) or [])
    return rows


def test_main_menu_payloads() -> None:
    buttons = buttons_from([kbs.main_menu()])
    payloads = _payloads(buttons)
    for expected in (
        "goal:show",
        "as:start",
        "ms:next",
        "sm:show",
        "cr:rec",
        "in:rec",
        "rs:start",
    ):
        assert expected in payloads, payloads
    assert "menu:main" not in payloads


def test_roles_kb_payloads_and_names() -> None:
    roles = [
        {"id": 1, "name": "Backend Junior"},
        {"id": 2, "name": "Data Analyst Junior"},
    ]
    buttons = buttons_from([kbs.roles_kb(roles)])
    assert [b.text for b in buttons[:2]] == ["Backend Junior", "Data Analyst Junior"]
    assert [b.payload for b in buttons[:2]] == ["goal:pick:1", "goal:pick:2"]
    assert buttons[-1].payload == "menu:main"


def test_options_kb_payloads_and_back() -> None:
    buttons = buttons_from([kbs.options_kb("asq", [(10, "Да"), (11, "Нет")])])
    assert set(_payloads(buttons)) == {"asq:10", "asq:11", "menu:main"}


def test_options_kb_without_back() -> None:
    buttons = buttons_from([kbs.options_kb("p", [(1, "x")], back=False)])
    assert _payloads(buttons) == ["p:1"]


def test_options_kb_numbered_short_buttons() -> None:
    """Длинные тексты ответов не уходят в кнопки — там только бейджи."""
    buttons = buttons_from([kbs.options_kb("p", [(10, "д" * 200), (11, "кот")])])
    assert [b.text for b in buttons] == ["①", "②", "🏠 Меню"]
    assert [b.payload for b in buttons[:-1]] == ["p:10", "p:11"]


def test_options_kb_grid_two_per_row() -> None:
    rows = _rows([kbs.options_kb("p", [(1, "a"), (2, "b"), (3, "c"), (4, "d")])])
    assert [b.text for b in rows[0]] == ["①", "②"]
    assert [b.text for b in rows[1]] == ["③", "④"]
    assert rows[2][0].text == "🏠 Меню"
    assert len(rows) == 3


def test_options_kb_fallback_beyond_ten() -> None:
    options = [(i, "x") for i in range(11)]
    buttons = buttons_from([kbs.options_kb("p", options, back=False)])
    assert buttons[-1].text == "11"


def test_after_mission_kb() -> None:
    buttons = buttons_from([kbs.after_mission_kb()])
    payloads = _payloads(buttons)
    assert "ms:next" in payloads
    assert "sm:show" in payloads
    assert "menu:main" in payloads


def test_menu_with_links() -> None:
    buttons = buttons_from([kbs.menu_with_links([("Открыть курс", "https://x.ru")])])
    assert buttons[0].url == "https://x.ru"
    assert buttons[-1].payload == "menu:main"


def test_menu_with_links_clips_long_title() -> None:
    buttons = buttons_from([kbs.menu_with_links([("д" * 100, "https://x.ru")])])
    assert buttons[0].text == "д" * (kbs.TEXT_LIMIT - 1) + "…"


def test_courses_pagination_kb_first_page() -> None:
    courses = [
        {"title": "FastAPI", "url": "https://fastapi.tiangolo.com"},
        {"title": "Python Basics", "url": "https://python.org"},
    ]
    attachments = [kbs.courses_pagination_kb(courses, page=0, total_pages=2)]
    buttons = buttons_from(attachments)
    assert [b.text for b in buttons[:2]] == ["FastAPI", "Python Basics"]
    assert buttons[0].url == "https://fastapi.tiangolo.com"
    assert buttons[2].text == "Следующая страница ➡️"
    assert buttons[2].payload == "cr:page:1"
    assert buttons[3].payload == "menu:main"


def test_courses_pagination_kb_middle_page() -> None:
    courses = [{"title": "Course 3", "url": "https://x.ru"}]
    attachments = [kbs.courses_pagination_kb(courses, page=1, total_pages=3)]
    rows = _rows(attachments)
    nav_row = rows[1]
    assert len(nav_row) == 2
    assert nav_row[0].text == "⬅️ Предыдущая"
    assert nav_row[0].payload == "cr:page:0"
    assert nav_row[1].text == "Следующая ➡️"
    assert nav_row[1].payload == "cr:page:2"
    assert rows[2][0].payload == "menu:main"


def test_courses_pagination_kb_last_page() -> None:
    courses = [{"title": "Course Last", "url": "https://x.ru"}]
    attachments = [kbs.courses_pagination_kb(courses, page=2, total_pages=3)]
    buttons = buttons_from(attachments)
    assert buttons[1].text == "⬅️ Предыдущая страница"
    assert buttons[1].payload == "cr:page:1"
    assert buttons[2].payload == "menu:main"


def test_courses_pagination_kb_single_page() -> None:
    courses = [{"title": "Only One", "url": "https://x.ru"}]
    buttons = buttons_from([kbs.courses_pagination_kb(courses, page=0, total_pages=1)])
    payloads = _payloads(buttons)
    assert payloads == [None, "menu:main"]
    assert buttons[0].text == "Only One"


def test_courses_pagination_kb_clips_long_title() -> None:
    courses = [{"title": "К" * 100, "url": "https://x.ru"}]
    buttons = buttons_from([kbs.courses_pagination_kb(courses, page=0, total_pages=1)])
    assert buttons[0].text == "К" * (kbs.TEXT_LIMIT - 1) + "…"


def test_courses_pagination_kb_skips_no_url() -> None:
    courses = [{"title": "No URL", "url": None}]
    buttons = buttons_from([kbs.courses_pagination_kb(courses, page=0, total_pages=1)])
    assert len(buttons) == 1
    assert buttons[0].payload == "menu:main"

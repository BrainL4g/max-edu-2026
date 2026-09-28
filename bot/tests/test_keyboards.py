"""Тесты inline-клавиатур бота."""

from __future__ import annotations

import keyboards as kbs
from tests.fakes import buttons_from


def _payloads(buttons: list) -> list[str | None]:
    return [getattr(b, "payload", None) for b in buttons]


def test_main_menu_payloads() -> None:
    buttons = buttons_from([kbs.main_menu()])
    payloads = _payloads(buttons)
    for expected in ("as:start", "ms:next", "sm:show", "cr:rec", "in:rec", "rs:start"):
        assert expected in payloads, payloads
    assert "menu:main" not in payloads


def test_options_kb_payloads_and_back() -> None:
    buttons = buttons_from([kbs.options_kb("asq", [(10, "Да"), (11, "Нет")])])
    assert set(_payloads(buttons)) == {"asq:10", "asq:11", "menu:main"}


def test_options_kb_without_back() -> None:
    buttons = buttons_from([kbs.options_kb("p", [(1, "x")], back=False)])
    assert _payloads(buttons) == ["p:1"]


def test_options_kb_truncates_long_text_with_ellipsis() -> None:
    buttons = buttons_from([kbs.options_kb("p", [(1, "д" * 200)])])
    assert buttons[0].text == "д" * (kbs.TEXT_LIMIT - 1) + "…"


def test_options_kb_keeps_short_text() -> None:
    buttons = buttons_from([kbs.options_kb("p", [(1, "Да"), (2, "Нет")])])
    assert [b.text for b in buttons[:2]] == ["Да", "Нет"]


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

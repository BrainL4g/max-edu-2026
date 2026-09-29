"""Тесты HTTP-клиента бота на MockTransport (без сети)."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from httpx import MockTransport, Response

import api


def _client(routes: dict[tuple[str, str], Response]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> Response:
        key = (request.method, request.url.path)
        if key in routes:
            return routes[key]
        return Response(404, json={"detail": "not found"})

    return httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")


def test_get_user(monkeypatch) -> None:
    client = _client({("POST", "/users/by-max"): Response(200, json={"id": 1})})
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.get_user(5, "Имя")) == {"id": 1}


def test_questions_and_mission_flows(monkeypatch) -> None:
    routes = {
        ("GET", "/assessment/questions"): Response(
            200, json=[{"id": 1, "text": "Вопрос", "options": ["Нет", "Да"]}]
        ),
        ("GET", "/users/1/skills"): Response(
            200, json=[{"name": "Python", "level": 2}]
        ),
    }
    client = _client(routes)
    monkeypatch.setattr(api, "_get_client", lambda: client)

    questions = asyncio.run(api.assessment_questions())
    assert questions[0]["id"] == 1
    assert asyncio.run(api.skill_map(1))[0]["level"] == 2


def test_assessment_questions_sends_user_id(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> Response:
        captured["query"] = str(request.url.query)
        return Response(200, json=[])

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.assessment_questions(42)) == []
    assert "user_id=42" in captured["query"]


def test_assessment_questions_without_user_id_no_query(monkeypatch) -> None:
    captured: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> Response:
        captured["query"] = request.url.query
        return Response(200, json=[])

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.assessment_questions()) == []
    assert captured["query"] == b""


def test_next_mission_none_when_empty(monkeypatch) -> None:
    # сервер отвечает JSON-null, когда все миссии пройдены
    client = _client({("GET", "/missions/next"): Response(200, content=b"null")})
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.next_mission(1)) is None


def test_answer_mission_sends_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> Response:
        captured["method"] = request.method
        captured["path"] = str(request.url.path)
        captured["body"] = request.content.decode()
        return Response(200, json={"is_correct": True, "xp_earned": 25})

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    result = asyncio.run(api.answer_mission(3, 4, 5))
    assert result == {"is_correct": True, "xp_earned": 25}
    assert captured["method"] == "POST"
    assert captured["path"] == "/missions/4/answer"
    assert "user_id" in captured["body"]


def test_submit_assessment_sends_answers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> Response:
        captured["method"] = request.method
        captured["path"] = str(request.url.path)
        captured["body"] = request.content.decode()
        return Response(200, json={"summary": "ok", "evaluated_skills": []})

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    result = asyncio.run(
        api.submit_assessment(9, [{"question_id": 1, "option_index": 2}])
    )
    assert result["summary"] == "ok"
    assert captured["method"] == "POST"
    assert captured["path"] == "/users/9/assessment"
    assert "question_id" in captured["body"]


def test_recommended_uses_user_id_in_query(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> Response:
        captured["query"] = str(request.url.query)
        return Response(200, json=[])

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.rec_courses(9)) == []
    assert "user_id=9" in captured["query"]
    assert asyncio.run(api.rec_internships(9)) == []


def test_resume_upload_and_analyze(monkeypatch) -> None:
    routes = {
        ("POST", "/users/7/resumes"): Response(201, json={"id": 12}),
        ("POST", "/resumes/12/analyze"): Response(
            200, json={"direction_match": 80, "found_skills": []}
        ),
    }
    client = _client(routes)
    monkeypatch.setattr(api, "_get_client", lambda: client)

    upload = asyncio.run(api.upload_resume(7, "текст резюме"))
    assert upload["id"] == 12
    analysis = asyncio.run(api.analyze_resume(12))
    assert analysis["direction_match"] == 80


def test_roles_and_goal_api(monkeypatch) -> None:
    roles = [
        {
            "id": 1,
            "name": "Backend Junior",
            "direction": "backend",
            "level": "junior",
            "requirements": [],
        },
    ]
    routes = {
        ("GET", "/roles"): Response(200, json=roles),
        ("PUT", "/users/5/goal"): Response(
            200, json={"id": 5, "name": "Маша", "target_role_id": 1}
        ),
        ("GET", "/users/5/gap-analysis"): Response(
            200,
            json={
                "user_id": 5,
                "role": roles[0],
                "match_percent": 43,
                "items": [],
                "summary": "Соответствие 43%",
            },
        ),
    }
    client = _client(routes)
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api.list_roles())[0]["name"] == "Backend Junior"
    assert asyncio.run(api.set_goal(5, 1))["target_role_id"] == 1
    analysis = asyncio.run(api.gap_analysis(5))
    assert analysis["match_percent"] == 43
    assert analysis["role"]["name"] == "Backend Junior"


def test_set_goal_sends_payload(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> Response:
        captured["body"] = request.content.decode()
        return Response(200, json={"id": 5, "target_role_id": 2})

    client = httpx.AsyncClient(transport=MockTransport(handler), base_url="http://test")
    monkeypatch.setattr(api, "_get_client", lambda: client)

    asyncio.run(api.set_goal(5, 2))
    assert "target_role_id" in captured["body"]


def test_http_error_raises_api_error(monkeypatch) -> None:
    client = _client({("GET", "/boom"): Response(500, json={"detail": "x"})})
    monkeypatch.setattr(api, "_get_client", lambda: client)

    with pytest.raises(api.ApiError):
        asyncio.run(api._req("GET", "/boom"))


def test_unknown_route_raises_api_error(monkeypatch) -> None:
    client = _client({})
    monkeypatch.setattr(api, "_get_client", lambda: client)

    with pytest.raises(api.ApiError):
        asyncio.run(api._req("GET", "/unknown"))


def test_204_returns_none(monkeypatch) -> None:
    client = _client({("DELETE", "/x"): Response(204)})
    monkeypatch.setattr(api, "_get_client", lambda: client)

    assert asyncio.run(api._req("DELETE", "/x")) is None


def test_client_is_cached_and_reused(monkeypatch) -> None:
    monkeypatch.setattr(api, "_client", None)
    first = api._get_client()
    assert api._get_client() is first  # повторные вызовы используют один клиент

    fake = httpx.AsyncClient(base_url="http://test")
    monkeypatch.setattr(api, "_client", fake)
    assert api._get_client() is fake

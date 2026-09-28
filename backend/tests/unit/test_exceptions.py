"""Тесты обработчиков доменных исключений (HTTP-ответы)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.exceptions import (
    ConflictError,
    InvalidDataError,
    NotFoundError,
    register_exception_handlers,
)


def _client_raising(error_type: type[Exception]) -> TestClient:
    """TestClient с маршрутом, который всегда бросает переданное исключение."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise error_type("boom")

    return TestClient(app)


def test_not_found_handler_returns_404() -> None:
    with _client_raising(NotFoundError) as client:
        response = client.get("/boom")
    assert response.status_code == 404
    assert response.json() == {"detail": "boom"}


def test_invalid_data_handler_returns_422() -> None:
    with _client_raising(InvalidDataError) as client:
        response = client.get("/boom")
    assert response.status_code == 422
    assert response.json() == {"detail": "boom"}


def test_conflict_handler_returns_409() -> None:
    with _client_raising(ConflictError) as client:
        response = client.get("/boom")
    assert response.status_code == 409
    assert response.json() == {"detail": "boom"}

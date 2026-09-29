"""Контракт OpenAPI: закоммиченные файлы совпадают с app.openapi() и валидны.

Запуск: ``python -m pytest tests/contract`` (cwd backend).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from openapi_spec_validator import validate

from backend.app.main import app

ROOT = Path(__file__).resolve().parents[3]


def test_committed_openapi_matches_app() -> None:
    schema = app.openapi()

    committed_yaml = yaml.safe_load((ROOT / "openapi.yaml").read_text(encoding="utf-8"))
    assert committed_yaml == schema, "openapi.yaml устарел — запустите scripts/export_openapi.py"

    committed_json = json.loads((ROOT / "openapi.json").read_text(encoding="utf-8"))
    assert committed_json == schema, "openapi.json устарел — запустите scripts/export_openapi.py"


def test_openapi_declares_required_sections() -> None:
    schema = app.openapi()

    assert schema["openapi"] in ("3.0.0", "3.0.1", "3.0.2", "3.0.3", "3.1.0")
    assert schema["servers"][0]["url"]
    assert schema["info"]["version"]
    assert schema["info"]["description"]
    assert schema["info"]["contact"]["name"]

    schemes = schema["components"]["securitySchemes"]
    assert "bearerAuth" in schemes
    assert schemes["bearerAuth"] == {"type": "http", "scheme": "bearer"}

    errors = schema["components"]["schemas"].get("ErrorOut")
    assert errors is not None
    assert "detail" in errors["properties"]

    for path, operations in schema["paths"].items():
        for operation in operations.values():
            summary = operation.get("summary", "")
            assert summary, f"Операция {operation.get('operationId')} без summary"
            assert operation.get("operationId"), f"Операция {path} без operationId"
            assert "security" in operation, f"Операция {path} не объявляет security"


def test_assessment_questions_is_public_in_schema() -> None:
    questions = app.openapi()["paths"]["/assessment/questions"]["get"]
    assert questions["security"] == []
    assert list(questions["responses"]) == ["200", "401", "403", "404", "422"]


def test_openapi_validates_with_spec_validator() -> None:
    validate(app.openapi())

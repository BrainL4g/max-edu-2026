"""Экспорт OpenAPI-схемы приложения в openapi.yaml и openapi.json.

Источник правды — ``app.openapi()``; файлы фиксируются в репозитории,
поэтому после изменения API их нужно перегенерировать:

    python scripts/export_openapi.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from backend.app.main import app  # noqa: E402


def main() -> None:
    """Записать openapi.yaml и openapi.json в корень репозитория."""
    schema = app.openapi()
    (ROOT / "openapi.yaml").write_text(
        yaml.safe_dump(schema, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (ROOT / "openapi.json").write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"openapi.yaml: {ROOT / 'openapi.yaml'}")
    print(f"openapi.json: {ROOT / 'openapi.json'}")


if __name__ == "__main__":
    main()
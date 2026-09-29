"""Создание тестовых учётных записей для приёмки API.

Примеры запуска (из корня репозитория):

    python -X utf8 scripts/seed_test_accounts.py
    python -X utf8 scripts/seed_test_accounts.py --reset

Идемпотентность: повторный запуск без ``--reset`` завершается ошибкой
(токены хранятся хэшем и невосстановимы), с ``--reset`` учётки удаляются
и создаются заново с новыми id и токенами. Токены печатаются только
в момент создания.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from backend.app.core.exceptions import ConflictError  # noqa: E402
from backend.app.database.session import SessionLocal  # noqa: E402
from backend.app.services.test_accounts import TestAccountsService  # noqa: E402


def main() -> None:
    """Парсинг аргументов, создание/пересоздание учёток и печать токенов."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="удалить существующие тестовые учётки и создать новые",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        service = TestAccountsService(db)
        try:
            result = service.reset() if args.reset else service.create()
        except ConflictError as exc:
            print(f"Конфликт: {exc}")
            sys.exit(1)
        _print_account("student", result.student.user_id, result.student.token)
        _print_account("admin", result.admin.user_id, result.admin.token)


def _print_account(role: str, user_id: int, token: str) -> None:
    print(f"{role}: user_id={user_id} token={token}")


if __name__ == "__main__":
    main()
"""Прогон проверок DATA-API.yaml по HTTP (curl-совместимый клиент).

Примеры запуска (из корня репозитория):

    python -X utf8 scripts/run_data_api.py --base-url http://localhost \\
        --token student=<токен> --token admin=<токен> --token service=<токен> \\
        --user-id 1 --admin-id 2

Токены берутся из ``scripts/seed_test_accounts.py`` (печатаются один раз).
Без ``--token`` роль ``student``/``admin``/``service`` пропускается, а
проверки с такой ролью считаются пропущенными (не ошибками).
Код возврата: 0 — все проверки прошли, 1 — есть ошибки, 2 — нет токенов.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from backend.app.services.data_api_runner import CheckResult, DataApiRunner  # noqa: E402


class _CurlResponse:
    """Минимальный ответ: ``status_code``, ``headers`` и ``json()``."""

    def __init__(self, status_code: int, content_type: str, body: str) -> None:
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self._body = body

    def json(self) -> Any:
        return json.loads(self._body)


class _CurlClient:
    """HTTP-клиент на ``urllib.request`` с тем же интерфейсом, что и ``TestClient``."""

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self, method: str, url: str, *, headers: dict[str, str] | None = None, **kwargs: Any
    ) -> _CurlResponse:
        import urllib.error
        import urllib.parse
        import urllib.request

        target = f"{self.base_url}{url}"
        params = kwargs.get("params")
        if params:
            target = f"{target}?{urllib.parse.urlencode(params, doseq=True)}"
        payload: bytes | None = None
        request_headers = dict(headers or {})
        if kwargs.get("json") is not None:
            payload = json.dumps(kwargs["json"]).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            target, data=payload, headers=request_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return _CurlResponse(
                    response.status,
                    response.headers.get("content-type", ""),
                    response.read().decode("utf-8", errors="replace"),
                )
        except urllib.error.HTTPError as error:
            return _CurlResponse(
                error.code,
                error.headers.get("content-type", ""),
                error.read().decode("utf-8", errors="replace"),
            )


def _parse_tokens(items: list[str]) -> dict[str, str]:
    tokens: dict[str, str] = {}
    for item in items:
        role, _, value = item.partition("=")
        if not value:
            raise ValueError(f"Ожидался формат <роль>=<токен>, получено: {item}")
        tokens[role.strip()] = value.strip()
    return tokens


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main() -> None:
    """Разобрать аргументы, выполнить все проверки DATA-API и отчитаться."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="базовый URL API (например, http://localhost)")
    parser.add_argument(
        "--token",
        action="append",
        default=[],
        metavar="РОЛЬ=ТОКЕН",
        help="Bearer-токен роли student/admin/service (можно указать несколько раз)",
    )
    parser.add_argument("--user-id", type=int, default=1, help="user_id тест-студента")
    parser.add_argument("--admin-id", type=int, default=2, help="user_id тест-администратора")
    parser.add_argument(
        "--spec", default=str(ROOT / "DATA-API.yaml"), help="путь к DATA-API.yaml"
    )
    parser.add_argument(
        "--seed", default=str(ROOT / "tests-data" / "test-data.json"), help="путь к тест-данным"
    )
    args = parser.parse_args()

    try:
        tokens = _parse_tokens(args.token)
    except ValueError as error:
        print(f"Ошибка: {error}")
        sys.exit(1)

    spec = _load_yaml(Path(args.spec))
    seed = _load_yaml(Path(args.seed))
    runner = DataApiRunner(
        client=_CurlClient(args.base_url),
        accounts={
            "student": {"user_id": args.user_id, "token": tokens.get("student", "")},
            "admin": {"user_id": args.admin_id, "token": tokens.get("admin", "")},
            "service": {"token": tokens.get("service", "")},
        },
        seed=seed,
    )

    results: list[CheckResult] = runner.run(spec)
    failed = [result for result in results if not result.passed]
    for result in results:
        mark = "OK  " if result.passed else "FAIL"
        print(f"[{mark}] {result.name}")
        for error in result.errors:
            print(f"        {error}")

    print(f"\n{len(results) - len(failed)}/{len(results)} проверок пройдено")
    if not tokens.get("student"):
        print("Внимание: токен student не передан — проверки с ролью student не проходят")
        sys.exit(2)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
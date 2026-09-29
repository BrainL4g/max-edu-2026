"""Прогон проверок DATA-API (контракт приёмки API) против HTTP-клиента.

Каждая проверка из ``checks`` исполняется строго по 9 полям: ``name``,
``description``, ``method``, ``path``, ``params``, ``role``,
``expected_status``, ``content_type``, ``required_fields``.

Плейсхолдеры ``{{...}}`` резолвятся из:
- тестовых учёток (``student.user_id``, ``student.token``,
  ``admin.user_id``, ``admin.token``, ``service.token``);
- ``test-data.<key>`` — значений из ``tests-data/test-data.json``;
- ``capture.<check-name>.<поле.поле>`` — полей из ответа предыдущей
  проверки (числовой сегмент пути = индекс элемента списка).

Клиент — любой объект с методом ``request(method, url, **kwargs)``
(FastAPI TestClient или httpx.Client), поэтому один и тот же файл
DATA-API.yaml исполняется локально и по публичному адресу.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

_PLACEHOLDER = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")

_QUERY_METHODS = {"GET", "DELETE"}


@dataclass(frozen=True)
class CheckResult:
    """Результат одной проверки DATA-API."""

    name: str
    passed: bool
    errors: list[str] = field(default_factory=list)


class DataApiRunner:
    """Исполняет ``checks`` из DATA-API.yaml и собирает результаты."""

    def __init__(
        self,
        *,
        client: Any,
        accounts: Mapping[str, Mapping[str, Any]],
        seed: Mapping[str, Any],
        base_url: str = "",
    ) -> None:
        self.client = client
        self.context: dict[str, Any] = {**accounts, "test-data": dict(seed)}
        self.base_url = base_url
        self.captures: dict[str, Any] = {}

    def run(self, spec: Mapping[str, Any]) -> list[CheckResult]:
        """Исполнить все проверки строго в порядке объявления."""
        return [self._run_check(check) for check in spec["checks"]]

    def _run_check(self, check: Mapping[str, Any]) -> CheckResult:
        name = str(check["name"])
        try:
            method = str(check["method"]).upper()
            path = self.resolve(check["path"])
            params = self.resolve(check["params"]) if check["params"] else None
            headers: dict[str, str] = {}
            role = str(check["role"])
            if role != "none":
                token = str(self._lookup(f"{role}.token"))
                headers["Authorization"] = f"Bearer {token}"
            kwargs: dict[str, Any] = {"headers": headers}
            if method in _QUERY_METHODS:
                if params:
                    kwargs["params"] = params
            else:
                kwargs["json"] = params
            response = self.client.request(method, f"{self.base_url}{path}", **kwargs)
            return self._verify(check, response)
        except Exception as exc:  # noqa: BLE001 — любая ошибка падает в результат
            return CheckResult(name=name, passed=False, errors=[f"{type(exc).__name__}: {exc}"])

    def _verify(self, check: Mapping[str, Any], response: Any) -> CheckResult:
        """Проверить статус, content-type и обязательные поля ответа."""
        name = str(check["name"])
        errors: list[str] = []
        status = int(response.status_code)
        if status != int(check["expected_status"]):
            errors.append(f"status {status} != {check['expected_status']}")
        content_type = str(response.headers.get("content-type", "")).split(";")[0]
        if content_type != str(check["content_type"]):
            errors.append(f"content-type {content_type!r} != {check['content_type']!r}")
        body = self._json(response)
        for item_index, item in enumerate(self._targets(body)):
            for path in check["required_fields"]:
                if not self._has_field(item, str(path)):
                    errors.append(f"item #{item_index}: missing field '{path}'")
        if not errors:
            self.captures[name] = body
        return CheckResult(name=name, passed=not errors, errors=errors)

    def resolve(self, value: Any) -> Any:
        """Рекурсивно подставить плейсхолдеры в строках, списках и словарях."""
        if isinstance(value, str):
            full = _PLACEHOLDER.fullmatch(value)
            if full:
                return self._lookup(full.group(1))
            if _PLACEHOLDER.search(value) is not None:
                return _PLACEHOLDER.sub(lambda match: str(self._lookup(match.group(1))), value)
            return value
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, dict):
            return {key: self.resolve(item) for key, item in value.items()}
        return value

    def _lookup(self, token: str) -> Any:
        """Достать значение по точечному пути (''capture'' — из ответов)."""
        parts = token.split(".")
        if parts[0] == "capture":
            if len(parts) < 2:
                raise ValueError(f"Плейсхолдер '{{{{{token}}}}}' требует capture.<check>.<поле>")
            value: Any = self.captures[parts[1]]
            rest = parts[2:]
        else:
            if parts[0] not in self.context:
                raise ValueError(f"Неизвестный источник плейсхолдера: '{parts[0]}'")
            value = self.context[parts[0]]
            rest = parts[1:]
        for part in rest:
            if isinstance(value, list):
                try:
                    value = value[int(part)]
                except (ValueError, IndexError) as exc:
                    raise ValueError(f"Нет элемента '{part}' в списке '{token}'") from exc
            else:
                try:
                    value = value[part]
                except (KeyError, TypeError) as exc:
                    raise ValueError(f"Нет поля '{part}' в '{token}'") from exc
        return value

    def _json(self, response: Any) -> Any:
        try:
            return response.json()
        except Exception:  # noqa: BLE001 — тело не JSON, поля проверить нельзя
            return {}

    @staticmethod
    def _targets(body: Any) -> list[Any]:
        return body if isinstance(body, list) else [body]

    @staticmethod
    def _has_field(item: Any, path: str) -> bool:
        try:
            value: Any = item
            for part in path.split("."):
                if isinstance(value, list):
                    value = value[int(part)]
                else:
                    value = value[part]
            return True
        except (KeyError, IndexError, TypeError, ValueError):
            return False

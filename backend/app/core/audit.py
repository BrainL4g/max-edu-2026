"""Аудит доступа к персональным данным (152-ФЗ ст. 19).

Логирует все операции чтения/записи/удаления персональных данных:
кто (роль + user_id), когда, какой ресурс, какая операция.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("skillquest.audit")


def log_access(
    action: str,
    resource: str,
    resource_id: int | None = None,
    principal_role: str | None = None,
    principal_user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Записать событие аудита доступа к ПД."""
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "principal_role": principal_role,
        "principal_user_id": principal_user_id,
        "details": details or {},
    }
    logger.info("AUDIT: %s", entry)

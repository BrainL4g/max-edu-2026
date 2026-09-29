"""Хэширование API-токенов.

В базе хранится только SHA-256 хэш; открытый текст токена печатается
один раз при создании (см. scripts/seed_test_accounts.py).
"""

from __future__ import annotations

import hashlib


def hash_token(token: str) -> str:
    """SHA-256 хэш токена (hex) для хранения в базе."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

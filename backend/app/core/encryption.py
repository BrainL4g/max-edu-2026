"""Шифрование персональных данных при хранении (152-ФЗ ст. 19).

Используется Fernet (AES-128-CBC + HMAC-SHA256). Ключ берётся из переменной
окружения ``DATA_ENCRYPTION_KEY`` (base64url-encoded, 32 байта).

Правила:

- шифрование **всегда включено** — молчаливого режима «без ключа» нет;
- ``APP_ENV=production`` без корректного ключа — ошибка на старте;
- в остальных окружениях без ключа генерируется временный ключ процесса и
  пишется предупреждение: данные перестанут читаться после перезапуска.

Формат хранения — ``enc:v1:< Fernet >``. Префикс ``enc:v1:`` позволяет
отличить зашифрованное значение от незашифрованного, оставшегося в базе до
включения шифрования: такие значения читаются как есть и перешифровываются
при следующей записи.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

PREFIX = "enc:v1:"
# Служебная часть токена Fernet: версия (1) + время (8) + nonce (16) + HMAC (32).
TOKEN_OVERHEAD = 57
# Блочное шифрование AES добавляет до одного блока (16 байт) выравнивания.
PADDING = 16
# Кириллица в UTF-8 занимает 2 байта, эмодзи и иероглифы — до 4 байт.
MAX_BYTES_PER_CHAR = 4
# Запас на округление base64 вверх.
_MARGIN = 8


def encrypted_length(plaintext_length: int) -> int:
    """Длина колонки, достаточная для хранения зашифрованного значения.

    Считается по худшему случаю: каждый символ исходного текста занимает
    до 4 байт в UTF-8, поэтому колонка заметно шире исходной.
    """
    worst_bytes = plaintext_length * MAX_BYTES_PER_CHAR + TOKEN_OVERHEAD + PADDING
    base64_chars = -(-worst_bytes * 4 // 3)
    return base64_chars + len(PREFIX) + _MARGIN


def _build_fernet() -> tuple[Fernet, bool]:
    """Построить шифратор. Возвращает (шифратор, ключ временный)."""
    key = settings.data_encryption_key.strip()
    if not key:
        if settings.app_env == "production":
            raise RuntimeError(
                "DATA_ENCRYPTION_KEY обязателен при APP_ENV=production: без него "
                "персональные данные не шифруются при хранении (152-ФЗ ст. 19). "
                "Сгенерируйте ключ командой: "
                "python -m backend.app.core.encryption"
            )
        generated = Fernet.generate_key().decode("utf-8")
        logger.warning(
            "DATA_ENCRYPTION_KEY не задан (APP_ENV=%s): используется временный "
            "ключ процесса. Данные станут нечитаемыми после перезапуска. "
            "Задайте DATA_ENCRYPTION_KEY в .env для постоянного хранения.",
            settings.app_env,
        )
        return Fernet(generated), True
    try:
        return Fernet(key.encode("utf-8")), False
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "DATA_ENCRYPTION_KEY имеет неверный формат: ожидается "
            "base64url-encoded 32-байтный ключ от Fernet.generate_key(). "
            "Сгенерируйте новый: python -m backend.app.core.encryption"
        ) from exc


_fernet, _ephemeral = _build_fernet()


def generate_key() -> str:
    """Сгенерировать ключ шифрования (base64url, 44 символа)."""
    return Fernet.generate_key().decode("utf-8")


def is_encrypted(value: str | None) -> bool:
    """Помечено ли значение как зашифрованное текущей версией."""
    return value is not None and value.startswith(PREFIX)


def encrypt(plaintext: str | None) -> str | None:
    """Зашифровать значение для хранения в БД. ``None`` → ``None``."""
    if plaintext is None:
        return None
    token = _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")
    return PREFIX + token


def decrypt(ciphertext: str | None) -> str | None:
    """Расшифровать значение из БД.

    Значения без префикса ``enc:v1:`` — данные, записанные до включения
    шифрования; возвращаются как есть.
    """
    if ciphertext is None:
        return None
    if not is_encrypted(ciphertext):
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext[len(PREFIX) :].encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError(
            "Не удалось расшифровать значение: неверный DATA_ENCRYPTION_KEY "
            "или данные повреждены."
        ) from exc


def is_ephemeral_key() -> bool:
    """Используется ли временный ключ (данные не переживут перезапуск)."""
    return _ephemeral


if __name__ == "__main__":  # pragma: no cover
    print(generate_key())

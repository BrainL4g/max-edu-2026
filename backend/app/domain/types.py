"""Типы SQLAlchemy для полей с шифрованными данными (152-ФЗ ст. 19).

``EncryptedString`` / ``EncryptedText`` прозрачно шифруют значение при записи
и расшифровывают при чтении. Длина колонки автоматически увеличивается, иначе
шифротекст не поместился бы в ``VARCHAR``.

Сравнения и ``ORDER BY`` по таким колонкам не работают (шифротекст случаен и
неупорядочен) — в проекте по ним фильтров нет: поиск идёт по ``id`` и по
незашифрованным полям.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.types import TypeDecorator

from backend.app.core.encryption import decrypt, encrypt, encrypted_length


class EncryptedString(TypeDecorator[str]):
    """Строка с шифрованием Fernet; длина колонки расширяется под шифротекст."""

    impl = String
    cache_ok = True

    def __init__(self, length: int | None = None, **kwargs: Any) -> None:
        super().__init__(length=None if length is None else encrypted_length(length), **kwargs)

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        return encrypt(value if value is None else str(value))

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        return decrypt(value if value is None else str(value))


class EncryptedText(TypeDecorator[str]):
    """Текст без ограничения длины, но с шифрованием Fernet."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Any, dialect: Any) -> str | None:
        return encrypt(value if value is None else str(value))

    def process_result_value(self, value: Any, dialect: Any) -> str | None:
        return decrypt(value if value is None else str(value))

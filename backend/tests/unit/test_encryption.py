"""Тесты шифрования персональных данных (152-ФЗ ст. 19)."""

from __future__ import annotations

import importlib
import logging

import pytest

from backend.app.core import encryption
from backend.app.core.config import settings
from backend.app.domain.types import EncryptedString, EncryptedText

SECRET = "Иванов Иван Иванович"


def test_encrypt_decrypt_roundtrip() -> None:
    assert encryption.decrypt(encryption.encrypt(SECRET)) == SECRET


def test_encrypt_produces_prefixed_ciphertext() -> None:
    token = encryption.encrypt(SECRET)
    assert token is not None
    assert token.startswith(encryption.PREFIX)
    assert encryption.is_encrypted(token)
    assert SECRET not in token


def test_encrypt_is_non_deterministic() -> None:
    """Одинаковые значения дают разный шифротекст (свежий nonce)."""
    assert encryption.encrypt(SECRET) != encryption.encrypt(SECRET)


def test_none_passes_through() -> None:
    assert encryption.encrypt(None) is None
    assert encryption.decrypt(None) is None


def test_legacy_plaintext_returned_as_is() -> None:
    """Значения, записанные до включения шифрования, читаются без изменений."""
    assert not encryption.is_encrypted(SECRET)
    assert encryption.decrypt(SECRET) == SECRET


def test_wrong_key_raises(monkeypatch) -> None:
    """Смена DATA_ENCRYPTION_KEY делает сохранённые данные нечитаемыми."""
    token = encryption.encrypt(SECRET)
    monkeypatch.setattr(
        encryption, "_fernet", encryption.Fernet(encryption.generate_key().encode("utf-8"))
    )
    with pytest.raises(ValueError, match="DATA_ENCRYPTION_KEY"):
        encryption.decrypt(token)


def test_decrypt_rejects_tampered_ciphertext(monkeypatch) -> None:
    token = encryption.encrypt(SECRET)
    assert token is not None
    broken = encryption.PREFIX + "A" + token.removeprefix(encryption.PREFIX)[1:]
    with pytest.raises(ValueError, match="расшифровать"):
        encryption.decrypt(broken)


def test_encrypted_length_fits_ciphertext() -> None:
    """Колонка, посчитанная по encrypted_length, вмещает шифротекст."""
    for sample in ("a" * 120, "я" * 120, "中" * 120, "🎓" * 120):
        width = encryption.encrypted_length(120)
        assert len(encryption.encrypt(sample)) <= width, sample
        assert width > 120


def test_generate_key_roundtrip() -> None:
    key = encryption.generate_key()
    fernet = encryption.Fernet(key.encode("utf-8"))
    assert fernet.decrypt(fernet.encrypt(b"x")) == b"x"


def test_ephemeral_key_used_without_setting(monkeypatch, caplog) -> None:
    """Без ключа в development берётся временный ключ и пишется предупреждение."""
    monkeypatch.setattr(settings, "data_encryption_key", "")
    monkeypatch.setattr(settings, "app_env", "development")
    with caplog.at_level(logging.WARNING, logger=encryption.__name__):
        module = importlib.reload(encryption)
    try:
        assert module.is_ephemeral_key()
        assert module.decrypt(module.encrypt(SECRET)) == SECRET
        assert "DATA_ENCRYPTION_KEY" in caplog.text
    finally:
        monkeypatch.undo()
        importlib.reload(encryption)


def test_generated_key_is_not_ephemeral(monkeypatch) -> None:
    """С заданным ключом шифротекст переживает пересборку модуля."""
    key = encryption.generate_key()
    monkeypatch.setattr(settings, "data_encryption_key", key)
    module = importlib.reload(encryption)
    try:
        token = module.encrypt(SECRET)
        assert not module.is_ephemeral_key()
        assert module.decrypt(token) == SECRET
    finally:
        monkeypatch.undo()
        importlib.reload(encryption)


def test_module_reload_with_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_encryption_key", encryption.generate_key())
    monkeypatch.setattr(settings, "app_env", "development")
    module = importlib.reload(encryption)
    try:
        assert not module.is_ephemeral_key()
        assert module.decrypt(module.encrypt(SECRET)) == SECRET
    finally:
        monkeypatch.undo()
        importlib.reload(encryption)


def test_production_without_key_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_encryption_key", "")
    monkeypatch.setattr(settings, "app_env", "production")
    with pytest.raises(RuntimeError, match="DATA_ENCRYPTION_KEY обязателен"):
        importlib.reload(encryption)
    monkeypatch.undo()
    importlib.reload(encryption)


def test_invalid_key_always_fails(monkeypatch) -> None:
    monkeypatch.setattr(settings, "data_encryption_key", "not-a-valid-fernet-key")
    with pytest.raises(RuntimeError, match="неверный формат"):
        importlib.reload(encryption)
    monkeypatch.undo()
    importlib.reload(encryption)


class _Dialect:
    """Заглушка диалекта: EncryptedString не использует его в тестах."""


def test_encrypted_string_type_widens_length() -> None:
    column = EncryptedString(120)
    assert column.length == encryption.encrypted_length(120)


def test_encrypted_string_bind_and_result() -> None:
    column = EncryptedString(120)
    bound = column.process_bind_param(SECRET, _Dialect())
    assert str(bound).startswith(encryption.PREFIX)
    assert column.process_result_value(bound, _Dialect()) == SECRET


def test_encrypted_text_bind_and_result() -> None:
    column = EncryptedText()
    bound = column.process_bind_param("Резюме: " + SECRET, _Dialect())
    assert str(bound).startswith(encryption.PREFIX)
    assert column.process_result_value(bound, _Dialect()) == "Резюме: " + SECRET

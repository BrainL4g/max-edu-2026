"""Настройки приложения SkillQuest.

Значения берутся из переменных окружения и файла ``.env``
(одна и та же схема переменных, что и в ``.env.example``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_PATHS: list[str] = []
for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parents[3] / ".env"):
    if candidate.is_file() and str(candidate) not in _ENV_PATHS:
        _ENV_PATHS.append(str(candidate))


class Settings(BaseSettings):
    """Параметры приложения (из окружения / .env)."""

    app_name: str = "SkillQuest"
    app_env: Literal["development", "testing", "production"] = "development"
    database_url: str = "sqlite:///./skillquest.db"

    max_bot_token: str = ""

    auto_create_tables: bool = True
    seed_on_startup: bool = True

    # Разрешённые CORS-origins через запятую. "*" — разрешить все.
    cors_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS or None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

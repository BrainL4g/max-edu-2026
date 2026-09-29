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
    """Параметры приложения (из окружения / .env).

    ``service_api_token`` — токен сервисной роли (бот MAX). Значение по
    умолчанию встроено, поэтому ``.env`` остаётся минимальным; переопределяется
    переменной ``SERVICE_API_TOKEN``.

    ``cors_origins`` — разрешённые CORS-origins через запятую; по умолчанию
    пусто (cross-origin запрещён), ``"*"`` — разрешить все.
    """

    app_name: str = "SkillQuest"
    app_env: Literal["development", "testing", "production"] = "development"
    database_url: str = "sqlite:///./skillquest.db"

    max_bot_token: str = ""
    service_api_token: str = "skillquest-service-token"

    auto_create_tables: bool = True
    seed_on_startup: bool = True

    # GigaChat: AI-оценка резюме. Пока ключ и токен пусты — интеграция выключена,
    # анализ резюме остаётся эвристическим.
    gigachat_credentials: str = ""  # Authorization key (base64 client_id:client_secret)
    gigachat_access_token: str = ""  # готовый access token (альтернатива OAuth)
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-3-Lightning"
    gigachat_auth_url: str = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    gigachat_base_url: str = "https://api.giga.chat/v1"
    gigachat_verify_ssl: bool = True
    gigachat_ca_bundle: str = ""  # путь к CA-бандлу Минцифры (если нужен)
    gigachat_timeout: float = 30.0

    cors_origins: str = ""

    model_config = SettingsConfigDict(
        env_file=_ENV_PATHS or None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


settings = Settings()

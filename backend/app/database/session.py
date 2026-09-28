"""Подключение к базе данных и FastAPI-зависимость ``get_db``."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings
from backend.app.database import models

_connect_args: dict = {}
if settings.database_url.startswith("sqlite"):
    _connect_args["check_same_thread"] = False

engine = create_engine(settings.database_url, connect_args=_connect_args)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: сессия SQLAlchemy на время запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

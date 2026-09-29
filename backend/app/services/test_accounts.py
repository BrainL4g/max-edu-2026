"""Тестовые учётные записи для приёмки API.

Скрипт ``scripts/seed_test_accounts.py`` создаёт/пересоздаёт студента
(role=student, is_test=True) и администратора (role=admin). Токены
хранятся хэшем; открытый текст печатается один раз при создании.

Эндпоинт ``POST /admin/test-users/reset`` (роль admin) стирает учебные
данные тест-студентов (попытки, навыки, резюме, целевую роль), оставляя
id пользователей и токены неизменными — для воспроизводимых прогонов
DATA-API.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.app.core.exceptions import ConflictError
from backend.app.core.security import hash_token
from backend.app.domain import ApiToken, Attempt, Resume, ResumeAnalysis, User, UserSkill
from backend.app.repositories.user_repository import UserRepository

STUDENT_NAME = "Тестовый Студент"
STUDENT_EDUCATION = "Московский технический университет, 3 курс"
STUDENT_DIRECTION = "backend"
STUDENT_GOAL = "Попасть на стажировку в ИТ-компанию"
ADMIN_NAME = "Тестовый Администратор"


@dataclass(frozen=True)
class TestAccount:
    """Тестовая учётка: id пользователя и открытый текст токена."""

    user_id: int
    token: str


@dataclass(frozen=True)
class AccountsResult:
    """Учётки, созданные скриптом: студент и администратор."""

    student: TestAccount
    admin: TestAccount


class TestAccountsService:
    """Создание, пересоздание и сброс данных тестовых учёток."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _find_token(self, *, role: str, is_test: bool) -> ApiToken | None:
        return self.db.scalar(
            select(ApiToken).where(ApiToken.role == role, ApiToken.is_test.is_(is_test))
        )

    def create(self) -> AccountsResult:
        """Создать студента и администратора, если их ещё нет.

        Если хотя бы одна учётка уже существует — ``ConflictError``
        (повторный прогон без сброса невозможен: токены невосстановимы).
        """
        if (
            self._find_token(role="student", is_test=True) is not None
            or self._find_token(role="admin", is_test=False) is not None
        ):
            raise ConflictError(
                "Тестовые учётки уже существуют. Запустите скрипт с --reset, "
                "чтобы пересоздать их и получить новые токены."
            )
        student_user_id, student_token = self._create_account(
            role="student",
            user_name=STUDENT_NAME,
            is_test=True,
        )
        admin_user_id, admin_token = self._create_account(
            role="admin",
            user_name=ADMIN_NAME,
            is_test=False,
        )
        return AccountsResult(
            student=TestAccount(user_id=student_user_id, token=student_token),
            admin=TestAccount(user_id=admin_user_id, token=admin_token),
        )

    def reset(self) -> AccountsResult:
        """Удалить все тестовые учётки и создать их заново (новые id и токены)."""
        self._delete_test_accounts()
        return self.create()

    def reset_test_data(self) -> int:
        """Стереть учебные данные тест-студентов (без удаления учёток).

        Очищает попытки, Skill Map, резюме и результаты анализа, снимает
        целевую роль и возвращает направление/цель по умолчанию. Возвращает
        количество затронутых пользователей.
        """
        user_ids = self._test_student_ids()
        if not user_ids:
            return 0
        resume_ids = select(Resume.id).where(Resume.user_id.in_(user_ids))
        self.db.execute(delete(ResumeAnalysis).where(ResumeAnalysis.resume_id.in_(resume_ids)))
        self.db.execute(delete(Attempt).where(Attempt.user_id.in_(user_ids)))
        self.db.execute(delete(UserSkill).where(UserSkill.user_id.in_(user_ids)))
        self.db.execute(delete(Resume).where(Resume.user_id.in_(user_ids)))
        for user_id in user_ids:
            user = self.db.get(User, user_id)
            if user is not None:
                user.target_role_id = None
                user.name = STUDENT_NAME
                user.direction = STUDENT_DIRECTION
                user.goal = STUDENT_GOAL
        self.db.commit()
        return len(user_ids)

    def _test_student_ids(self) -> list[int]:
        ids = self.db.scalars(
            select(ApiToken.user_id).where(
                ApiToken.role == "student",
                ApiToken.is_test.is_(True),
                ApiToken.user_id.is_not(None),
            )
        ).all()
        return [user_id for user_id in ids if user_id is not None]

    def _create_account(self, *, role: str, user_name: str, is_test: bool) -> tuple[int, str]:
        user = UserRepository(self.db).create(
            name=user_name,
            education=STUDENT_EDUCATION,
            direction=STUDENT_DIRECTION,
            goal=STUDENT_GOAL,
        )
        token = secrets.token_urlsafe(32)
        record = ApiToken(
            token_hash=hash_token(token),
            role=role,
            user_id=user.id,
            is_test=is_test,
        )
        self.db.add(record)
        self.db.commit()
        return user.id, token

    def _delete_test_accounts(self) -> None:
        tokens_where = ((ApiToken.role == "student") & ApiToken.is_test.is_(True)) | (
            ApiToken.role == "admin"
        )
        ids = self.db.scalars(
            select(ApiToken.user_id).where(tokens_where, ApiToken.user_id.is_not(None))
        ).all()
        user_ids = [user_id for user_id in ids if user_id is not None]
        self.reset_test_data()
        self.db.execute(delete(ApiToken).where(tokens_where))
        self.db.execute(delete(User).where(User.id.in_(user_ids)))
        self.db.commit()
        self.db.expire_all()

    @staticmethod
    def count_students(db: Session) -> int:
        """Количество тест-студентов (для проверок и отчетов)."""
        return (
            db.scalar(
                select(func.count(ApiToken.id)).where(
                    ApiToken.role == "student", ApiToken.is_test.is_(True)
                )
            )
            or 0
        )

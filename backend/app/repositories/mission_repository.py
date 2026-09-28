"""Репозиторий миссий и попыток."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.exceptions import NotFoundError
from backend.app.domain import Attempt, Mission


class MissionRepository:
    """Доступ к данным миссий и попыток."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Mission]:
        return list(
            self.db.scalars(
                select(Mission)
                .order_by(Mission.difficulty, Mission.id)
                .options(selectinload(Mission.skill))
            )
        )

    def get(self, mission_id: int) -> Mission:
        mission = self.db.get(Mission, mission_id)
        if mission is None:
            raise NotFoundError(f"Миссия с id={mission_id} не найдена")
        return mission

    def get_with_options(self, mission_id: int) -> Mission:
        """Миссия с загруженным навыком и вариантами ответов."""
        mission = self.db.scalar(
            select(Mission)
            .where(Mission.id == mission_id)
            .options(selectinload(Mission.skill), selectinload(Mission.options))
        )
        if mission is None:
            raise NotFoundError(f"Миссия с id={mission_id} не найдена")
        return mission

    def solved_mission_ids(self, user_id: int) -> set[int]:
        """Миссии, которые пользователь уже решил правильно."""
        rows = self.db.execute(
            select(Attempt.mission_id).where(
                Attempt.user_id == user_id, Attempt.is_correct.is_(True)
            )
        )
        return {row[0] for row in rows}

    def create_attempt(
        self,
        user_id: int,
        mission_id: int,
        answer_option_id: int | None,
        is_correct: bool,
        xp_earned: int,
    ) -> Attempt:
        attempt = Attempt(
            user_id=user_id,
            mission_id=mission_id,
            answer_option_id=answer_option_id,
            is_correct=is_correct,
            xp_earned=xp_earned,
        )
        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_attempt(self, attempt_id: int) -> Attempt:
        attempt = self.db.get(Attempt, attempt_id)
        if attempt is None:
            raise NotFoundError(f"Попытка с id={attempt_id} не найдена")
        return attempt

    def list_attempts(self, user_id: int) -> list[Attempt]:
        return list(
            self.db.scalars(
                select(Attempt)
                .where(Attempt.user_id == user_id)
                .order_by(Attempt.created_at.desc())
            )
        )

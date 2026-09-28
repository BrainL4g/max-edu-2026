"""Add max_user_id to users for MAX-bot linking.

Revision ID: 003
Revises: 002
Create Date: 2026-09-28 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: str | None = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Добавить колонку max_user_id (уникальный идентификатор MAX-пользователя)."""
    op.add_column("users", sa.Column("max_user_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_users_max_user_id", "users", ["max_user_id"], unique=True)


def downgrade() -> None:
    """Убрать колонку max_user_id."""
    op.drop_index("ix_users_max_user_id", table_name="users")
    op.drop_column("users", "max_user_id")

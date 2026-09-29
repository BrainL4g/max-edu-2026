"""Consent columns and wider storage for encrypted personal data.

Adds the 152-ФЗ ст. 9 consent fields to ``users`` and widens the columns that
now hold Fernet ciphertext (the encrypted value is longer than the plaintext,
so the original VARCHAR sizes no longer fit). ``batch_alter_table`` keeps the
migration working on SQLite, which cannot alter a column type in place.

Revision ID: 006
Revises: 005
Create Date: 2026-09-29 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels = None
depends_on = None

# Итоговые размеры: encrypted_length(n) = ceil((4n + 57 + 16) * 4 / 3) + 15.
WIDTHS = {
    "name": 753,
    "education": 1179,
    "direction": 646,
    "goal": 1713,
}
RESUME_FILENAME_WIDTH = 1473


def upgrade() -> None:
    """Добавить поля согласия и расширить колонки под шифротекст."""
    op.add_column(
        "users",
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("consent_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("consent_policy_version", sa.String(10), nullable=True))

    with op.batch_alter_table("users") as batch:
        for column, width in WIDTHS.items():
            batch.alter_column(column, type_=sa.String(width), existing_type=sa.String())

    with op.batch_alter_table("resumes") as batch:
        batch.alter_column(
            "filename",
            type_=sa.String(RESUME_FILENAME_WIDTH),
            existing_type=sa.String(),
        )


def downgrade() -> None:
    """Откатить поля согласия и вернуть исходные размеры колонок."""
    with op.batch_alter_table("resumes") as batch:
        batch.alter_column(
            "filename", type_=sa.String(255), existing_type=sa.String(RESUME_FILENAME_WIDTH)
        )

    with op.batch_alter_table("users") as batch:
        for column, width in WIDTHS.items():
            batch.alter_column(column, type_=sa.String(255), existing_type=sa.String(width))

    op.drop_column("users", "consent_policy_version")
    op.drop_column("users", "consent_at")
    op.drop_column("users", "consent_given")

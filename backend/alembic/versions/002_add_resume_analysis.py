"""Add resumes and resume_analysis tables.

Revision ID: 002
Revises: 001
Create Date: 2026-09-21 00:00:01
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создать таблицы резюме и результатов анализа."""
    op.create_table(
        "resumes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])

    op.create_table(
        "resume_analysis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("resume_id", sa.Integer(), sa.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    )
    op.create_index("ix_resume_analysis_resume_id", "resume_analysis", ["resume_id"])


def downgrade() -> None:
    """Удалить таблицы анализа резюме."""
    op.drop_table("resume_analysis")
    op.drop_table("resumes")

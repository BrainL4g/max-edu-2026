"""Add roles, role_skills and user target_role for gap-analysis.

Revision ID: 004
Revises: 003
Create Date: 2026-09-28 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: str | None = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создать роли, требования и колонку target_role_id у пользователя."""
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("direction", sa.String(length=50), nullable=False),
        sa.Column("level", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_roles_name", "roles", ["name"], unique=True)
    op.create_index("ix_roles_direction", "roles", ["direction"], unique=False)

    op.create_table(
        "role_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "role_id",
            sa.Integer(),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("required_level", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("importance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("role_id", "skill_id", name="uq_role_skill"),
    )
    op.create_index("ix_role_skills_role_id", "role_skills", ["role_id"], unique=False)
    op.create_index("ix_role_skills_skill_id", "role_skills", ["skill_id"], unique=False)

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "target_role_id",
                sa.Integer(),
                sa.ForeignKey(
                    "roles.id", ondelete="SET NULL", name="fk_users_target_role_id_roles"
                ),
                nullable=True,
            )
        )
        batch_op.create_index("ix_users_target_role_id", ["target_role_id"])


def downgrade() -> None:
    """Убрать роли и целевую роль пользователя."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_target_role_id")
        batch_op.drop_column("target_role_id")
    op.drop_index("ix_role_skills_skill_id", table_name="role_skills")
    op.drop_index("ix_role_skills_role_id", table_name="role_skills")
    op.drop_table("role_skills")
    op.drop_index("ix_roles_direction", table_name="roles")
    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")

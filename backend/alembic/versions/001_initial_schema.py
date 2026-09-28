"""Initial schema: пользователи, навыки, миссии, курсы, стажировки.

Revision ID: 001
Revises:
Create Date: 2026-09-21 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Создать основные таблицы SkillQuest."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("education", sa.String(length=200), nullable=True),
        sa.Column("direction", sa.String(length=100), nullable=True),
        sa.Column("goal", sa.String(length=300), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
    )
    op.create_index("ix_users_direction", "users", ["direction"])

    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_skills_name", "skills", ["name"])
    op.create_index("ix_skills_category", "skills", ["category"])

    op.create_table(
        "user_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("experience", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )
    op.create_index("ix_user_skills_user_id", "user_skills", ["user_id"])
    op.create_index("ix_user_skills_skill_id", "user_skills", ["skill_id"])

    op.create_table(
        "missions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="easy", nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("reward_xp", sa.Integer(), server_default="20", nullable=False),
    )
    op.create_index("ix_missions_skill_id", "missions", ["skill_id"])

    op.create_table(
        "mission_options",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index("ix_mission_options_mission_id", "mission_options", ["mission_id"])

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mission_id", sa.Integer(), sa.ForeignKey("missions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("answer_option_id", sa.Integer(), sa.ForeignKey("mission_options.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="completed", nullable=False),
        sa.Column("xp_earned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
    )
    op.create_index("ix_attempts_user_id", "attempts", ["user_id"])
    op.create_index("ix_attempts_mission_id", "attempts", ["mission_id"])

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=100), nullable=False),
        sa.Column("url", sa.String(length=300), nullable=True),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("cost", sa.Float(), server_default="0", nullable=False),
        sa.Column("format", sa.String(length=30), server_default="online", nullable=False),
    )
    op.create_index("ix_courses_platform", "courses", ["platform"])
    op.create_index("ix_courses_level", "courses", ["level"])
    op.create_index("ix_courses_category", "courses", ["category"])

    op.create_table(
        "course_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("course_id", "skill_id", name="uq_course_skill"),
    )
    op.create_index("ix_course_skills_course_id", "course_skills", ["course_id"])
    op.create_index("ix_course_skills_skill_id", "course_skills", ["skill_id"])

    op.create_table(
        "internships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("company", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=300), nullable=True),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("remote", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("format", sa.String(length=30), server_default="office", nullable=False),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("direction", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_internships_company", "internships", ["company"])
    op.create_index("ix_internships_level", "internships", ["level"])
    op.create_index("ix_internships_city", "internships", ["city"])
    op.create_index("ix_internships_direction", "internships", ["direction"])

    op.create_table(
        "internship_skills",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("internship_id", sa.Integer(), sa.ForeignKey("internships.id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("internship_id", "skill_id", name="uq_internship_skill"),
    )
    op.create_index("ix_internship_skills_internship_id", "internship_skills", ["internship_id"])
    op.create_index("ix_internship_skills_skill_id", "internship_skills", ["skill_id"])


def downgrade() -> None:
    """Удалить таблицы в обратном порядке."""
    op.drop_table("internship_skills")
    op.drop_table("internships")
    op.drop_table("course_skills")
    op.drop_table("courses")
    op.drop_table("attempts")
    op.drop_table("mission_options")
    op.drop_table("missions")
    op.drop_table("user_skills")
    op.drop_table("skills")
    op.drop_table("users")

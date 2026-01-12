"""memory init

Revision ID: 0001_memory_init
Revises: 
Create Date: 2026-01-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_memory_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "turns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_text", sa.Text(), nullable=False),
        sa.Column("assistant_text", sa.Text(), nullable=False),
    )
    op.create_index("ix_turns_session_id", "turns", ["session_id"], unique=False)

    op.create_table(
        "facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("turn_id", sa.Integer(), sa.ForeignKey("turns.id"), nullable=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
    )
    op.create_index("ix_facts_key", "facts", ["key"], unique=False)

    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="session"),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_summaries_session_id", "summaries", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_summaries_session_id", table_name="summaries")
    op.drop_table("summaries")

    op.drop_index("ix_facts_key", table_name="facts")
    op.drop_table("facts")

    op.drop_index("ix_turns_session_id", table_name="turns")
    op.drop_table("turns")

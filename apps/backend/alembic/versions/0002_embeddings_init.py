"""embeddings init

Revision ID: 0002_embeddings_init
Revises: 0001_memory_init
Create Date: 2026-01-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_embeddings_init"
down_revision = "0001_memory_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
    )
    op.create_index("ix_embeddings_entity", "embeddings", ["entity_type", "entity_id"], unique=False)
    op.create_index("ix_embeddings_model", "embeddings", ["model"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_embeddings_model", table_name="embeddings")
    op.drop_index("ix_embeddings_entity", table_name="embeddings")
    op.drop_table("embeddings")

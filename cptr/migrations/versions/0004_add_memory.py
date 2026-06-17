"""Add memory table for self-study loop.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("workspace_id", sa.Text, nullable=False, index=True),
        sa.Column("user_id", sa.Text, nullable=True, index=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("section", sa.Text, nullable=False, server_default="general"),
        sa.Column("tags", sa.JSON, nullable=True),
        sa.Column("source", sa.Text, nullable=False, server_default="user"),
        sa.Column("created_at", sa.BigInteger, nullable=False),
        sa.Column("updated_at", sa.BigInteger, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("memory")

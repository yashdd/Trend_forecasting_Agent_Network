"""Add anonymous trend comments table.

Revision ID: 004
Revises: 003
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trend_comments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "trend_insight_id",
            sa.Integer(),
            sa.ForeignKey("trend_insights.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("author_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("author_label", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trend_comments_insight_created", "trend_comments", ["trend_insight_id", "created_at"])
    op.create_index("ix_trend_comments_author_created", "trend_comments", ["author_fingerprint", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_trend_comments_author_created", table_name="trend_comments")
    op.drop_index("ix_trend_comments_insight_created", table_name="trend_comments")
    op.drop_table("trend_comments")


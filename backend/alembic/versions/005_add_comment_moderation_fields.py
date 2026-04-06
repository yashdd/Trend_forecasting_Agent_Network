"""Add moderation fields for trend comments.

Revision ID: 005
Revises: 004
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("trend_comments", sa.Column("hidden", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("trend_comments", sa.Column("hidden_reason", sa.String(length=128), nullable=True))
    op.add_column("trend_comments", sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("trend_comments", "hidden_at")
    op.drop_column("trend_comments", "hidden_reason")
    op.drop_column("trend_comments", "hidden")


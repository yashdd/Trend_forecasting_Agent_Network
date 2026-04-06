"""Report settings table + preferences on weekly_reports; daily scheduled reports.

Revision ID: 007
Revises: 006
Create Date: 2026-04-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "report_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_topics", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("categories", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        text(
            "INSERT INTO report_settings (id, lookback_days, max_topics, categories, updated_at) "
            "VALUES (1, 1, 10, NULL, NOW()) ON CONFLICT (id) DO NOTHING"
        )
    )

    op.add_column(
        "weekly_reports",
        sa.Column("preferences", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "weekly_reports",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="scheduled"),
    )


def downgrade() -> None:
    op.drop_column("weekly_reports", "source")
    op.drop_column("weekly_reports", "preferences")
    op.drop_table("report_settings")

"""Add alert rules and alert events tables.

Revision ID: 003
Revises: 002
Create Date: 2026-03-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("min_signal_score", sa.Float(), nullable=True),
        sa.Column("min_cross_source_strength", sa.Float(), nullable=True),
        sa.Column("webhook_url", sa.Text(), nullable=False),
        sa.Column("max_events_per_day", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trend_insight_id", sa.Integer(), sa.ForeignKey("trend_insights.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_alert_events_rule_sent_at", "alert_events", ["rule_id", "sent_at"])
    op.create_index("ix_alert_events_topic_sent_at", "alert_events", ["topic_id", "sent_at"])


def downgrade() -> None:
    op.drop_index("ix_alert_events_topic_sent_at", table_name="alert_events")
    op.drop_index("ix_alert_events_rule_sent_at", table_name="alert_events")
    op.drop_table("alert_events")
    op.drop_table("alert_rules")


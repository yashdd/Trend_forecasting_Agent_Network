"""Keep alert_events when rule deleted (SET NULL on rule_id).

Revision ID: 009
Revises: 008
Create Date: 2026-04-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("alert_events_rule_id_fkey", "alert_events", type_="foreignkey")
    op.alter_column("alert_events", "rule_id", existing_type=sa.Integer(), nullable=True)
    op.create_foreign_key(
        "alert_events_rule_id_fkey",
        "alert_events",
        "alert_rules",
        ["rule_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute("DELETE FROM alert_events WHERE rule_id IS NULL")
    op.drop_constraint("alert_events_rule_id_fkey", "alert_events", type_="foreignkey")
    op.alter_column("alert_events", "rule_id", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "alert_events_rule_id_fkey",
        "alert_events",
        "alert_rules",
        ["rule_id"],
        ["id"],
        ondelete="CASCADE",
    )

"""Make alert_rules.webhook_url optional for in-app-only notifications.

Revision ID: 006
Revises: 005
Create Date: 2026-04-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "alert_rules",
        "webhook_url",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE alert_rules SET webhook_url = '' WHERE webhook_url IS NULL"
    )
    op.alter_column(
        "alert_rules",
        "webhook_url",
        existing_type=sa.Text(),
        nullable=False,
    )

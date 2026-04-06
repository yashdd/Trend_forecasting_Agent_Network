"""Add topic category fields.

Revision ID: 002
Revises: 001
Create Date: 2025-03-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("category", sa.String(length=64), nullable=True))
    op.add_column("topics", sa.Column("category_scores", sa.JSON(), nullable=True))
    op.add_column("topics", sa.Column("category_explanation", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("topics", "category_explanation")
    op.drop_column("topics", "category_scores")
    op.drop_column("topics", "category")


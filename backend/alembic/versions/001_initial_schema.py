"""Initial schema: sources, raw_posts, embeddings, topics, metrics, reports.

Revision ID: 001
Revises:
Create Date: 2025-03-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    op.create_table(
        "raw_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(256), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("author", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_raw_posts_source_external"),
    )
    op.create_index(op.f("ix_raw_posts_source_id"), "raw_posts", ["source_id"], unique=False)
    op.create_index(op.f("ix_raw_posts_created_at"), "raw_posts", ["created_at"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("label", sa.String(512), nullable=True),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_post_id", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["raw_post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_embeddings_raw_post_id"), "embeddings", ["raw_post_id"], unique=True)
    op.execute(
        "CREATE INDEX ix_embeddings_embedding_hnsw ON embeddings "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "topic_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_post_id", sa.Integer(), nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["raw_post_id"], ["raw_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topic_assignments_topic_id"), "topic_assignments", ["topic_id"], unique=False)

    op.create_table(
        "topic_daily_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False),
        sa.Column("growth_rate", sa.Float(), nullable=True),
        sa.Column("acceleration", sa.Float(), nullable=True),
        sa.Column("signal_score", sa.Float(), nullable=True),
        sa.Column("source_breakdown", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "date", name="uq_topic_daily_metrics_topic_date"),
    )
    op.create_index(op.f("ix_topic_daily_metrics_date"), "topic_daily_metrics", ["date"], unique=False)

    op.create_table(
        "cross_source_validation",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sources_present", sa.JSON(), nullable=True),
        sa.Column("cross_source_strength", sa.Float(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("topic_id", "date", name="uq_cross_source_topic_date"),
    )

    op.create_table(
        "trend_insights",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("why_it_matters", sa.Text(), nullable=True),
        sa.Column("industry_impact", sa.Text(), nullable=True),
        sa.Column("representative_sources", sa.JSON(), nullable=True),
        sa.Column("llm_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["topic_id"], ["topics.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trend_insights_topic_id"), "trend_insights", ["topic_id"], unique=False)

    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("top_signals", sa.JSON(), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pipeline_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("agent_steps", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_runs")
    op.drop_table("weekly_reports")
    op.drop_table("trend_insights")
    op.drop_table("cross_source_validation")
    op.drop_table("topic_daily_metrics")
    op.drop_table("topic_assignments")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_embedding_hnsw")
    op.drop_table("embeddings")
    op.drop_table("topics")
    op.drop_table("raw_posts")
    op.drop_table("sources")
    op.execute("DROP EXTENSION IF EXISTS vector")

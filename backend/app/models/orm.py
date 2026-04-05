"""SQLAlchemy ORM models and pgvector."""
from datetime import date, datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base


# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True)  # reddit, hackernews, arxiv
    config = Column(JSON, nullable=True)  # e.g. subreddit list


class RawPost(Base):
    __tablename__ = "raw_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)
    external_id = Column(String(256), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    author = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    source = relationship("Source", backref="raw_posts")
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_raw_posts_source_external"),)


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_post_id = Column(Integer, ForeignKey("raw_posts.id", ondelete="CASCADE"), nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    model_name = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    raw_post = relationship("RawPost", backref="embedding", uselist=False)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String(512), nullable=True)
    keywords = Column(JSON, nullable=True)  # list of str
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)  # optional centroid
    first_seen_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    # Phase 1: trend categorization
    category = Column(String(64), nullable=True)  # e.g. startups, concepts, news, tools, regulation
    category_scores = Column(JSON, nullable=True)  # {"startups": 0.8, "concepts": 0.1, ...}
    category_explanation = Column(Text, nullable=True)


class TopicAssignment(Base):
    __tablename__ = "topic_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    raw_post_id = Column(Integer, ForeignKey("raw_posts.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=True)
    assigned_at = Column(DateTime(timezone=True), nullable=False)

    raw_post = relationship("RawPost", backref="topic_assignments")
    topic = relationship("Topic", backref="assignments")


class TopicDailyMetric(Base):
    __tablename__ = "topic_daily_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    mention_count = Column(Integer, nullable=False, default=0)
    growth_rate = Column(Float, nullable=True)
    acceleration = Column(Float, nullable=True)
    signal_score = Column(Float, nullable=True)
    source_breakdown = Column(JSON, nullable=True)  # {"reddit": n, "hackernews": n, "arxiv": n}

    topic = relationship("Topic", backref="daily_metrics")
    __table_args__ = (UniqueConstraint("topic_id", "date", name="uq_topic_daily_metrics_topic_date"),)


class CrossSourceValidation(Base):
    __tablename__ = "cross_source_validation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    sources_present = Column(JSON, nullable=True)  # ["reddit", "hackernews", "arxiv"]
    cross_source_strength = Column(Float, nullable=True)
    validated_at = Column(DateTime(timezone=True), nullable=False)

    topic = relationship("Topic", backref="cross_source_validations")
    __table_args__ = (UniqueConstraint("topic_id", "date", name="uq_cross_source_topic_date"),)


class TrendInsight(Base):
    __tablename__ = "trend_insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    generated_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    industry_impact = Column(Text, nullable=True)
    representative_sources = Column(JSON, nullable=True)  # list of {url, title, source}
    llm_metadata = Column(JSON, nullable=True)

    topic = relationship("Topic", backref="trend_insights")


class TrendComment(Base):
    __tablename__ = "trend_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trend_insight_id = Column(Integer, ForeignKey("trend_insights.id", ondelete="CASCADE"), nullable=False)
    body = Column(Text, nullable=False)

    # Stable anonymous identity derived from IP (never store raw IP).
    author_fingerprint = Column(String(64), nullable=False)
    author_label = Column(String(32), nullable=False)

    # Moderation
    hidden = Column(Integer, nullable=False, default=0)  # 1/0
    hidden_reason = Column(String(128), nullable=True)
    hidden_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False)

    trend_insight = relationship("TrendInsight", backref="comments")


class ReportSettings(Base):
    """Singleton row id=1: defaults for the daily scheduled report."""

    __tablename__ = "report_settings"

    id = Column(Integer, primary_key=True)  # always 1
    lookback_days = Column(Integer, nullable=False, default=1)
    max_topics = Column(Integer, nullable=False, default=10)
    categories = Column(JSON, nullable=True)  # null = all categories
    updated_at = Column(DateTime(timezone=True), nullable=False)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    top_signals = Column(JSON, nullable=True)  # list of trend_insight ids or summary objects
    report_markdown = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    preferences = Column(JSON, nullable=True)  # snapshot: lookback, categories, max_topics
    source = Column(String(16), nullable=False, default="scheduled")  # scheduled | manual


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(32), nullable=False)  # running, success, failed
    agent_steps = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    enabled = Column(Integer, nullable=False, default=1)  # 1/0 for SQLite-ish compatibility

    # Filters (all optional; ANDed)
    category = Column(String(64), nullable=True)
    # Substrings (case-insensitive); all must appear in topic label + latest insight text
    keywords = Column(JSON, nullable=True)
    min_signal_score = Column(Float, nullable=True)
    min_cross_source_strength = Column(Float, nullable=True)

    # Optional: POST JSON here; if null, notifications are in-app only (AlertEvent rows).
    webhook_url = Column(Text, nullable=True)

    # Rate limiting / de-dupe
    max_events_per_day = Column(Integer, nullable=False, default=20)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    trend_insight_id = Column(Integer, ForeignKey("trend_insights.id", ondelete="CASCADE"), nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=False)
    payload = Column(JSON, nullable=True)
    status = Column(String(32), nullable=False, default="sent")  # sent/failed
    error_message = Column(Text, nullable=True)

    rule = relationship("AlertRule", backref="events")
    topic = relationship("Topic", backref="alert_events")
    trend_insight = relationship("TrendInsight", backref="alert_events")

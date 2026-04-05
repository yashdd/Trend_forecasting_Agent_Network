"""Pydantic request/response schemas."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceRef(BaseModel):
    name: str
    url: str | None
    title: str | None


class SignalsMetaResponse(BaseModel):
    """Lightweight poll for notification bar — avoids loading full signal lists."""

    newest_insight_id: int
    newer_count: int = 0


class SignalFeedItem(BaseModel):
    id: int
    topic_id: int
    topic_label: str | None
    category: str | None = None
    signal_score: float | None
    cross_source_strength: float | None
    novelty_score: float | None
    predicted_impact: str | None
    summary: str | None
    sources: list[SourceRef] = []
    first_detected_at: datetime | None
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TopicListItem(BaseModel):
    id: int
    label: str | None
    keywords: list[Any] | None
    category: str | None = None
    signal_score: float | None
    cross_source_strength: float | None
    mention_count: int | None
    first_seen_at: datetime | None


class TopicDetail(BaseModel):
    id: int
    label: str | None
    category: str | None = None
    keywords: list[Any] | None
    first_seen_at: datetime | None
    updated_at: datetime | None
    daily_metrics: list[dict] = []
    trend_insight: dict | None = None


class TrendCommentIn(BaseModel):
    body: str


class TrendCommentOut(BaseModel):
    id: int
    trend_insight_id: int
    body: str
    author_label: str
    created_at: datetime


class TrendCommentsResponse(BaseModel):
    viewer_label: str
    has_more: bool = False
    next_before_id: int | None = None
    comments: list[TrendCommentOut] = []


class MomentumPoint(BaseModel):
    date: str
    mention_count: int
    signal_score: float | None
    growth_rate: float | None


class DiscussionItem(BaseModel):
    id: int
    source: str
    url: str | None
    title: str | None
    body: str | None
    author: str | None
    created_at: datetime | None


class WeeklyReportListItem(BaseModel):
    id: int
    period_start: date
    period_end: date
    created_at: datetime
    source: str = "scheduled"
    preferences: dict[str, Any] | None = None


class WeeklyReportDetail(BaseModel):
    id: int
    period_start: date
    period_end: date
    top_signals: list[Any] = []
    report_markdown: str | None
    created_at: datetime
    source: str = "scheduled"
    preferences: dict[str, Any] | None = None


class ReportSettingsOut(BaseModel):
    lookback_days: int
    max_topics: int
    categories: list[str] | None = None
    updated_at: datetime


class ReportSettingsIn(BaseModel):
    lookback_days: int = Field(1, ge=1, le=30)
    max_topics: int = Field(10, ge=1, le=50)
    categories: list[str] | None = None


class GenerateReportIn(BaseModel):
    period_start: date
    period_end: date
    categories: list[str] | None = None
    max_topics: int = Field(10, ge=1, le=50)

    @model_validator(mode="after")
    def validate_range(self) -> "GenerateReportIn":
        if self.period_end < self.period_start:
            raise ValueError("period_end must be on or after period_start")
        return self


class ExplainEvidenceItem(BaseModel):
    source: str
    source_family: str
    url: str | None
    title: str | None
    excerpt: str | None
    raw_post_id: int | None = None


class ExplainabilityResponse(BaseModel):
    topic_id: int
    topic_label: str | None
    category: str | None = None

    # What changed
    today: str | None = None
    mention_count_today: int | None = None
    mention_count_yesterday: int | None = None
    growth_rate: float | None = None
    acceleration: float | None = None
    signal_score: float | None = None
    cross_source_strength: float | None = None
    source_families: list[str] = []

    # Drivers + evidence
    top_phrases: list[str] = []
    evidence: list[ExplainEvidenceItem] = []


class AlertRuleIn(BaseModel):
    name: str
    enabled: bool = True
    category: str | None = None
    keywords: list[str] | None = None
    min_signal_score: float | None = None
    min_cross_source_strength: float | None = None
    webhook_url: str | None = None
    max_events_per_day: int = 20


class AlertRuleUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    category: str | None = None
    keywords: list[str] | None = None
    min_signal_score: float | None = None
    min_cross_source_strength: float | None = None
    webhook_url: str | None = None
    max_events_per_day: int | None = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    enabled: bool
    category: str | None = None
    keywords: list[str] | None = None
    min_signal_score: float | None = None
    min_cross_source_strength: float | None = None
    webhook_url: str | None = None
    max_events_per_day: int
    created_at: datetime


class AlertEventOut(BaseModel):
    id: int
    rule_id: int | None = None
    topic_id: int
    trend_insight_id: int | None = None
    sent_at: datetime
    status: str
    error_message: str | None = None
    rule_name: str | None = None
    topic_label: str | None = None

"""Generate trend reports from insights — range-based, preference-aware."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select, desc, and_
from sqlalchemy.orm import Session

from app.db.session import get_sync_session
from app.models.orm import (
    CrossSourceValidation,
    ReportSettings,
    Topic,
    TopicDailyMetric,
    TrendInsight,
    WeeklyReport,
)


def _humanize_label(value: str | None) -> str:
    if not value:
        return "Topic"
    return " ".join(value.replace("_", " ").replace("-", " ").split()).title()


def _md_link(title: str | None, url: str | None) -> str:
    if url:
        t = (title or url).replace("[", "\\[").replace("]", "\\]")
        return f"[{t}]({url})"
    return title or ""


def _prefs_snapshot(
    *,
    categories: list[str] | None,
    max_topics: int,
    period_start: date,
    period_end: date,
) -> dict:
    return {
        "categories": categories,
        "max_topics": max_topics,
        "range_days": (period_end - period_start).days + 1,
    }


def generate_trend_report(
    period_start: date,
    period_end: date,
    *,
    categories: list[str] | None = None,
    max_topics: int = 10,
    source: str = "manual",
    session: Session | None = None,
) -> int | None:
    """
    Build markdown report for insights in [period_start, period_end] (inclusive dates, UTC day bounds).
    """
    own_session = session is None
    sess = session or get_sync_session()
    try:
        start_dt = datetime.combine(period_start, time.min, tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, time.max, tzinfo=timezone.utc)

        q = (
            select(TrendInsight, Topic)
            .join(Topic, TrendInsight.topic_id == Topic.id)
            .where(
                and_(
                    TrendInsight.generated_at >= start_dt,
                    TrendInsight.generated_at <= end_dt,
                )
            )
        )
        if categories:
            q = q.where(Topic.category.in_(categories))
        q = q.order_by(desc(TrendInsight.generated_at)).limit(max(1, min(max_topics, 50)))
        insights = sess.execute(q).all()
        if not insights:
            return None

        range_days = (period_end - period_start).days + 1
        title = "Daily trend report" if range_days <= 1 else f"Trend report ({range_days} days)"
        top_signals = []
        sections: list[str] = []
        sections.append(f"# {title} — {period_start} to {period_end}\n\n")
        sections.append("## Executive summary\n\n")
        cat_note = (
            f"Filtered to categories: {', '.join(categories)}. "
            if categories
            else "All categories. "
        )
        sections.append(
            f"{cat_note}Signals are derived from ingested sources, clustered into topics, "
            "and ranked by momentum and cross-source validation.\n\n"
        )
        sections.append("## Top signals\n\n")

        for i, (insight, topic) in enumerate(insights, 1):
            score_row = (
                sess.execute(
                    select(TopicDailyMetric.signal_score)
                    .where(TopicDailyMetric.topic_id == topic.id)
                    .order_by(desc(TopicDailyMetric.date))
                    .limit(1)
                )
            ).scalars().first()
            cv_row = (
                sess.execute(
                    select(CrossSourceValidation.sources_present)
                    .where(CrossSourceValidation.topic_id == topic.id)
                    .order_by(desc(CrossSourceValidation.date))
                    .limit(1)
                )
            ).scalars().first()
            score = f"{score_row:.2f}" if score_row is not None else "N/A"
            sources_str = ", ".join(cv_row) if cv_row else "N/A"
            top_signals.append({"topic_id": topic.id, "insight_id": insight.id, "label": topic.label})
            sections.append(
                f"### {i}. {_humanize_label(topic.label)} — Signal score: {score} | Sources: {sources_str}\n\n"
            )
            sections.append(f"- **What it is:** {insight.summary or 'N/A'}\n")
            sections.append(f"- **Why it matters:** {insight.why_it_matters or 'N/A'}\n")
            sections.append(f"- **Potential impact:** {insight.industry_impact or 'N/A'}\n")
            rep = insight.representative_sources or []
            if rep:
                links = []
                for r in rep[:3]:
                    url = r.get("url")
                    t = r.get("title") or url
                    links.append(_md_link(t, url) if url else (t or ""))
                links = [x for x in links if x]
                if links:
                    sections.append("- **Representative discussions:** " + " · ".join(links) + "\n")
            sections.append("\n")

        sections.append("## Methodology\n\n")
        sections.append(
            "Signals come from continuous ingestion (Reddit, Hacker News, arXiv, GitHub, and other configured sources). "
            "Topics are clustered; momentum and cross-source strength inform ranking; narrative fields are LLM-generated.\n"
        )

        snap = _prefs_snapshot(
            categories=categories,
            max_topics=max_topics,
            period_start=period_start,
            period_end=period_end,
        )
        report = WeeklyReport(
            period_start=period_start,
            period_end=period_end,
            top_signals=top_signals,
            report_markdown="".join(sections),
            created_at=datetime.now(timezone.utc),
            preferences=snap,
            source=source,
        )
        sess.add(report)
        sess.commit()
        sess.refresh(report)
        return report.id
    except Exception:
        sess.rollback()
        return None
    finally:
        if own_session:
            sess.close()


def _get_or_create_settings(sess: Session) -> ReportSettings:
    row = sess.execute(select(ReportSettings).where(ReportSettings.id == 1)).scalars().first()
    if row:
        return row
    now = datetime.now(timezone.utc)
    row = ReportSettings(id=1, lookback_days=1, max_topics=10, categories=None, updated_at=now)
    sess.add(row)
    sess.commit()
    sess.refresh(row)
    return row


def run_daily_scheduled_report() -> int | None:
    """
    Once per day: cover 'yesterday' as period_end with lookback from saved preferences.
    Skips if a scheduled report for that period_end already exists.
    """
    session = get_sync_session()
    try:
        settings = _get_or_create_settings(session)
        end = datetime.now(timezone.utc).date() - timedelta(days=1)
        start = end - timedelta(days=max(1, settings.lookback_days) - 1)

        dup = session.execute(
            select(WeeklyReport.id).where(
                WeeklyReport.source == "scheduled",
                WeeklyReport.period_end == end,
            )
        ).scalars().first()
        if dup:
            return None

        cats = settings.categories
        if isinstance(cats, list) and len(cats) == 0:
            cats = None

        return generate_trend_report(
            start,
            end,
            categories=cats,
            max_topics=max(1, min(settings.max_topics or 10, 50)),
            source="scheduled",
            session=session,
        )
    finally:
        session.close()

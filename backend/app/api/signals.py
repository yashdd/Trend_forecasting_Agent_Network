"""Signal feed API."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import TrendInsight, Topic, TopicDailyMetric, CrossSourceValidation
from app.models.schemas import SignalFeedItem, SourceRef

router = APIRouter(prefix="/signals")


@router.get("", response_model=list[SignalFeedItem])
async def list_signals(
    limit: int = Query(20, ge=1, le=100),
    min_score: float = Query(0.0, ge=0, le=1),
    since: datetime | None = Query(None),
    category: str | None = Query(None, description="Optional topic category filter"),
    db: AsyncSession = Depends(get_db),
):
    """Real-time signal feed: emerging trends with signal score and sources."""
    q = (
        select(TrendInsight, Topic)
        .join(Topic, TrendInsight.topic_id == Topic.id)
        .order_by(desc(TrendInsight.generated_at))
        .limit(limit * 3)
    )
    if since:
        q = q.where(TrendInsight.generated_at >= since)
    rows = (await db.execute(q)).all()

    topic_ids = list({r[1].id for r in rows})
    if not topic_ids:
        return []

    # Latest metric and cross_source per topic
    metrics_rows = (
        await db.execute(
            select(TopicDailyMetric.topic_id, TopicDailyMetric.signal_score)
            .where(TopicDailyMetric.topic_id.in_(topic_ids), TopicDailyMetric.signal_score >= min_score)
            .order_by(desc(TopicDailyMetric.date))
        )
    ).all()
    topic_score = {}
    for tid, score in metrics_rows:
        if tid not in topic_score:
            topic_score[tid] = score
    cv_rows = (
        await db.execute(
            select(CrossSourceValidation.topic_id, CrossSourceValidation.cross_source_strength)
            .where(CrossSourceValidation.topic_id.in_(topic_ids))
            .order_by(desc(CrossSourceValidation.date))
        )
    ).all()
    topic_cross = {}
    for tid, strength in cv_rows:
        if tid not in topic_cross:
            topic_cross[tid] = float(strength) if strength is not None else None

    seen = set()
    out = []
    for insight, topic in rows:
        if topic.id in seen:
            continue
        seen.add(topic.id)
        if category and (topic.category or "").lower() != category.lower():
            continue
        score = topic_score.get(topic.id)
        if score is not None and score < min_score:
            continue
        cross = topic_cross.get(topic.id)
        rep = insight.representative_sources or []
        sources = [SourceRef(name=s.get("source", ""), url=s.get("url"), title=s.get("title")) for s in rep]
        novelty = 1.0 / (1.0 + (datetime.now(timezone.utc) - (topic.first_seen_at or datetime.now(timezone.utc))).days) if topic.first_seen_at else None
        impact = "High" if (score or 0) > 0.7 and (cross or 0) > 0.5 else "Medium" if (score or 0) > 0.3 else "Low"
        out.append(
            SignalFeedItem(
                id=insight.id,
                topic_id=topic.id,
                topic_label=topic.label,
                category=topic.category,
                signal_score=score,
                cross_source_strength=cross,
                novelty_score=round(novelty, 4) if novelty else None,
                predicted_impact=impact,
                summary=insight.summary,
                sources=sources,
                first_detected_at=topic.first_seen_at,
                updated_at=insight.generated_at,
            )
        )
        if len(out) >= limit:
            break
    return out


@router.get("/{signal_id}", response_model=SignalFeedItem | dict)
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Single trend deep-dive."""
    r = (
        await db.execute(
            select(TrendInsight, Topic)
            .join(Topic, TrendInsight.topic_id == Topic.id)
            .where(TrendInsight.id == signal_id)
        )
    ).first()
    if not r:
        return {"detail": "Not found"}
    insight, topic = r
    rep = insight.representative_sources or []
    sources = [SourceRef(name=s.get("source", ""), url=s.get("url"), title=s.get("title")) for s in rep]
    return SignalFeedItem(
        id=insight.id,
        topic_id=topic.id,
        topic_label=topic.label,
        signal_score=None,
        cross_source_strength=None,
        novelty_score=None,
        predicted_impact=None,
        summary=insight.summary,
        sources=sources,
        first_detected_at=topic.first_seen_at,
        updated_at=insight.generated_at,
    )

"""Topics API."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import Topic, TopicDailyMetric, CrossSourceValidation, TrendInsight
from app.models.schemas import TopicListItem, TopicDetail, DiscussionItem
from app.models.orm import RawPost, Source, TopicAssignment

router = APIRouter(prefix="/topics")


@router.get("", response_model=list[TopicListItem])
async def list_topics(
    days: int = Query(7, ge=1, le=90),
    sort: str = Query("signal_score", regex="^(momentum|signal_score|novelty)$"),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None, description="Optional topic category filter"),
    db: AsyncSession = Depends(get_db),
):
    """Trending topics with momentum and cross-source strength."""
    subq = (
        select(
            TopicDailyMetric.topic_id,
            func.max(TopicDailyMetric.signal_score).label("best_score"),
            func.sum(TopicDailyMetric.mention_count).label("total_mentions"),
        )
        .group_by(TopicDailyMetric.topic_id)
    ).subquery()
    q = (
        select(Topic, subq.c.best_score, subq.c.total_mentions)
        .select_from(Topic)
        .outerjoin(subq, Topic.id == subq.c.topic_id)
        .limit(limit)
    )
    if sort == "signal_score":
        q = q.order_by(desc(subq.c.best_score))
    else:
        q = q.order_by(desc(subq.c.total_mentions))
    rows = (await db.execute(q)).all()
    topic_ids = [r[0].id for r in rows]
    cv = (
        await db.execute(
            select(CrossSourceValidation.topic_id, CrossSourceValidation.cross_source_strength)
            .where(CrossSourceValidation.topic_id.in_(topic_ids))
            .order_by(desc(CrossSourceValidation.date))
        )
    ).all()
    cross_map = {}
    for tid, s in cv:
        if tid not in cross_map:
            cross_map[tid] = float(s) if s is not None else None
    out = []
    for topic, score, mentions in rows:
        if category and (topic.category or "").lower() != category.lower():
            continue
        out.append(
            TopicListItem(
                id=topic.id,
                label=topic.label,
                keywords=topic.keywords,
                category=topic.category,
                signal_score=float(score) if score is not None else None,
                cross_source_strength=cross_map.get(topic.id),
                mention_count=int(mentions) if mentions is not None else None,
                first_seen_at=topic.first_seen_at,
            )
        )
    return out


@router.get("/{topic_id}", response_model=TopicDetail | dict)
async def get_topic(
    topic_id: int,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.ext.asyncio import AsyncSession
    """Topic detail with daily metrics and latest insight."""
    topic = (await db.execute(select(Topic).where(Topic.id == topic_id))).scalars().first()
    if not topic:
        return {"detail": "Not found"}
    metrics = (
        await db.execute(
            select(TopicDailyMetric)
            .where(TopicDailyMetric.topic_id == topic_id)
            .order_by(TopicDailyMetric.date)
        )
    ).all()
    metrics = [m[0] for m in metrics]
    in_row = (
        await db.execute(
            select(TrendInsight)
            .where(TrendInsight.topic_id == topic_id)
            .order_by(desc(TrendInsight.generated_at))
            .limit(1)
        )
    ).first()
    insight = in_row[0] if in_row else None
    daily = [
        {
            "date": str(m.date),
            "mention_count": m.mention_count,
            "signal_score": m.signal_score,
            "growth_rate": m.growth_rate,
        }
        for m in metrics
    ]
    trend_insight = None
    if insight:
        trend_insight = {
            "summary": insight.summary,
            "why_it_matters": insight.why_it_matters,
            "industry_impact": insight.industry_impact,
            "representative_sources": insight.representative_sources,
        }
    return TopicDetail(
        id=topic.id,
        label=topic.label,
        category=topic.category,
        keywords=topic.keywords,
        first_seen_at=topic.first_seen_at,
        updated_at=topic.updated_at,
        daily_metrics=daily,
        trend_insight=trend_insight,
    )


@router.get("/{topic_id}/discussions", response_model=list[DiscussionItem])
async def list_topic_discussions(
    topic_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Paginated raw discussions and research refs for a topic."""
    rows = (
        await db.execute(
            select(RawPost, Source.name)
            .join(TopicAssignment, RawPost.id == TopicAssignment.raw_post_id)
            .join(Source, RawPost.source_id == Source.id)
            .where(TopicAssignment.topic_id == topic_id)
            .order_by(desc(RawPost.created_at), desc(RawPost.fetched_at))
            .limit(limit)
        )
    ).all()
    return [
        DiscussionItem(
            id=p.id,
            source=name or "",
            url=p.url,
            title=p.title,
            body=(p.body or "")[:1000],
            author=p.author,
            created_at=p.created_at,
        )
        for p, name in rows
    ]

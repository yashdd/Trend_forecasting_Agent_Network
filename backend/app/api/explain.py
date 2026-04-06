"""Explainability API: why a topic is trending + supporting evidence."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import (
    Topic,
    TopicDailyMetric,
    CrossSourceValidation,
    TrendInsight,
    RawPost,
    TopicAssignment,
    Source,
)
from app.models.schemas import ExplainabilityResponse, ExplainEvidenceItem

router = APIRouter(prefix="/explain")


def _source_family(source_name: str) -> str:
    s = (source_name or "").lower()
    if s in {"arxiv"}:
        return "research"
    if s in {"github"}:
        return "open_source"
    if s in {"producthunt"}:
        return "launches"
    if s in {"rss_news"}:
        return "media"
    if s in {"google_trends"}:
        return "search"
    if s in {"stackoverflow", "devto", "lobsters", "hackernews", "reddit"}:
        return "community"
    return "other"


def _top_phrases(texts: list[str], k: int = 6) -> list[str]:
    # lightweight: token frequency with stopwords + min length
    stop = {
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is", "are",
        "this", "that", "it", "as", "by", "from", "at", "be", "was", "were", "will", "can",
        "new", "using", "use", "used", "into", "about", "more", "than",
    }
    toks: Counter[str] = Counter()
    for t in texts:
        for raw in (t or "").lower().replace("/", " ").replace("-", " ").split():
            w = "".join(ch for ch in raw if ch.isalnum())
            if len(w) < 4:
                continue
            if w in stop:
                continue
            toks[w] += 1
    return [w for w, _ in toks.most_common(k)]


@router.get("/topic/{topic_id}", response_model=ExplainabilityResponse)
async def explain_topic(topic_id: int, db: AsyncSession = Depends(get_db)):
    topic = (await db.execute(select(Topic).where(Topic.id == topic_id))).scalars().first()
    if not topic:
        return ExplainabilityResponse(topic_id=topic_id, topic_label=None, category=None)

    # Metrics: today + yesterday
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)

    metrics = (
        await db.execute(
            select(TopicDailyMetric)
            .where(TopicDailyMetric.topic_id == topic_id)
            .order_by(desc(TopicDailyMetric.date))
            .limit(3)
        )
    ).scalars().all()
    m_today = next((m for m in metrics if m.date == today), None)
    m_yday = next((m for m in metrics if m.date == yesterday), None)
    m_latest = metrics[0] if metrics else None

    cv = (
        await db.execute(
            select(CrossSourceValidation)
            .where(CrossSourceValidation.topic_id == topic_id)
            .order_by(desc(CrossSourceValidation.date))
            .limit(1)
        )
    ).scalars().first()

    # Evidence: representative posts for this topic
    posts = (
        await db.execute(
            select(RawPost, Source.name)
            .join(TopicAssignment, RawPost.id == TopicAssignment.raw_post_id)
            .join(Source, RawPost.source_id == Source.id)
            .where(TopicAssignment.topic_id == topic_id)
            .order_by(desc(RawPost.created_at), desc(RawPost.fetched_at))
            .limit(15)
        )
    ).all()

    texts = [((p.title or "") + " " + (p.body or ""))[:800] for p, _ in posts]
    phrases = _top_phrases(texts, k=6)

    families = sorted({ _source_family(name) for _, name in posts if name })
    evidence: list[ExplainEvidenceItem] = []
    for p, name in posts[:8]:
        fam = _source_family(name)
        excerpt = (p.body or p.title or "")[:280] if (p.body or p.title) else None
        evidence.append(
            ExplainEvidenceItem(
                source=name or "",
                source_family=fam,
                url=p.url,
                title=(p.title or "")[:200] if p.title else None,
                excerpt=excerpt,
                raw_post_id=p.id,
            )
        )

    # Build the "what changed" string
    mc_today = m_today.mention_count if m_today else None
    mc_yday = m_yday.mention_count if m_yday else None
    growth = m_latest.growth_rate if m_latest else None
    accel = m_latest.acceleration if m_latest else None
    sig = m_latest.signal_score if m_latest else None
    cross = cv.cross_source_strength if cv else None

    changed = None
    if mc_today is not None and mc_yday is not None:
        changed = f"Mentions: {mc_yday} → {mc_today} since yesterday."
    elif mc_today is not None:
        changed = f"Mentions today: {mc_today}."
    elif m_latest is not None:
        changed = f"Mentions on {m_latest.date}: {m_latest.mention_count}."

    return ExplainabilityResponse(
        topic_id=topic.id,
        topic_label=topic.label,
        category=topic.category,
        today=str(today),
        mention_count_today=mc_today,
        mention_count_yesterday=mc_yday,
        growth_rate=growth,
        acceleration=accel,
        signal_score=sig,
        cross_source_strength=float(cross) if cross is not None else None,
        source_families=families,
        top_phrases=phrases,
        evidence=evidence,
    )


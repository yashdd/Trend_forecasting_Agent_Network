"""Signal feed API."""
from datetime import datetime, timezone, timedelta

import hashlib
import hmac
import re

from fastapi import APIRouter, Depends, Query, Request
from fastapi import HTTPException
from sqlalchemy import select, desc, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.orm import TrendInsight, Topic, TopicDailyMetric, CrossSourceValidation, TrendComment
from app.models.schemas import (
    SignalFeedItem,
    SignalsMetaResponse,
    SourceRef,
    TrendCommentIn,
    TrendCommentOut,
    TrendCommentsResponse,
)

router = APIRouter(prefix="/signals")

_URL_RE = re.compile(r"https?://", re.IGNORECASE)

def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        # First IP is the client IP in typical proxy setups.
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _anon_identity(request: Request) -> tuple[str, str]:
    """Return (author_fingerprint_hex, author_label)."""
    settings = get_settings()
    ip = _client_ip(request)
    salt = (settings.comment_id_salt or settings.database_url or "dev").encode("utf-8")
    fp = hmac.new(salt, msg=ip.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    # Compact, human-friendly label
    label = "User " + fp[:6].upper()
    return fp, label


@router.get("/meta", response_model=SignalsMetaResponse)
async def signals_meta(
    after_id: int | None = Query(None, description="If set, count insights with id greater than this (for “new” badge)."),
    db: AsyncSession = Depends(get_db),
):
    """Cheap metadata for polling — one aggregation query instead of full signal payloads."""
    mx = (await db.execute(select(func.max(TrendInsight.id)))).scalar_one_or_none()
    newest = int(mx or 0)
    newer = 0
    if after_id is not None and newest > after_id:
        newer = (
            await db.execute(select(func.count()).select_from(TrendInsight).where(TrendInsight.id > after_id))
        ).scalar_one()
        newer = int(newer or 0)
    return SignalsMetaResponse(newest_insight_id=newest, newer_count=newer)


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

    # Latest qualifying metric per topic (one row each) — avoids scanning all historical rows
    qual_dates = (
        select(
            TopicDailyMetric.topic_id.label("tid"),
            func.max(TopicDailyMetric.date).label("md"),
        )
        .where(TopicDailyMetric.topic_id.in_(topic_ids), TopicDailyMetric.signal_score >= min_score)
        .group_by(TopicDailyMetric.topic_id)
    ).subquery()
    metrics_rows = (
        await db.execute(
            select(TopicDailyMetric.topic_id, TopicDailyMetric.signal_score)
            .join(
                qual_dates,
                and_(
                    TopicDailyMetric.topic_id == qual_dates.c.tid,
                    TopicDailyMetric.date == qual_dates.c.md,
                ),
            )
        )
    ).all()
    topic_score = {tid: score for tid, score in metrics_rows}

    latest_cv_dates = (
        select(
            CrossSourceValidation.topic_id.label("tid"),
            func.max(CrossSourceValidation.date).label("md"),
        )
        .where(CrossSourceValidation.topic_id.in_(topic_ids))
        .group_by(CrossSourceValidation.topic_id)
    ).subquery()
    cv_rows = (
        await db.execute(
            select(CrossSourceValidation.topic_id, CrossSourceValidation.cross_source_strength)
            .join(
                latest_cv_dates,
                and_(
                    CrossSourceValidation.topic_id == latest_cv_dates.c.tid,
                    CrossSourceValidation.date == latest_cv_dates.c.md,
                ),
            )
        )
    ).all()
    topic_cross = {
        tid: float(strength) if strength is not None else None for tid, strength in cv_rows
    }

    seen = set()
    out = []
    for insight, topic in rows:
        if topic.id in seen:
            continue
        seen.add(topic.id)
        # Hide BERTopic's catch-all cluster from end users.
        if (topic.label or "").strip().lower() == "outlier":
            continue
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


# Register /{signal_id}/comments before /{signal_id} so paths like .../5/comments are not ambiguous.
@router.get("/{signal_id}/comments", response_model=TrendCommentsResponse)
async def list_signal_comments(
    signal_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    before_id: int | None = Query(None, ge=1, description="Pagination cursor: fetch comments with id < before_id"),
    db: AsyncSession = Depends(get_db),
):
    """Anonymous comments for a signal (trend_insight)."""
    author_fp, viewer_label = _anon_identity(request)
    # Ensure signal exists
    exists = (
        await db.execute(select(TrendInsight.id).where(TrendInsight.id == signal_id).limit(1))
    ).first()
    if not exists:
        return TrendCommentsResponse(viewer_label=viewer_label, comments=[])

    where = [TrendComment.trend_insight_id == signal_id, TrendComment.hidden == 0]
    if before_id:
        where.append(TrendComment.id < before_id)

    rows = (
        await db.execute(
            select(TrendComment)
            .where(and_(*where))
            .order_by(desc(TrendComment.created_at), desc(TrendComment.id))
            .limit(limit + 1)
        )
    ).scalars().all()

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    # Currently newest->oldest; reverse for display.
    rows = list(reversed(rows))
    next_before_id = rows[0].id if has_more and rows else None
    return TrendCommentsResponse(
        viewer_label=viewer_label,
        has_more=has_more,
        next_before_id=next_before_id,
        comments=[
            TrendCommentOut(
                id=c.id,
                trend_insight_id=c.trend_insight_id,
                body=c.body,
                author_label=c.author_label,
                created_at=c.created_at,
            )
            for c in rows
        ],
    )


@router.post("/{signal_id}/comments", response_model=TrendCommentOut)
async def create_signal_comment(
    signal_id: int,
    body: TrendCommentIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Post an anonymous comment to a signal (trend_insight)."""
    exists = (
        await db.execute(select(TrendInsight.id).where(TrendInsight.id == signal_id).limit(1))
    ).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Signal not found")

    text = (body.body or "").strip()
    if len(text) < 1:
        raise HTTPException(status_code=400, detail="Comment is empty")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Comment is too long (max 2000 chars)")
    if _URL_RE.findall(text) and len(_URL_RE.findall(text)) > 3:
        raise HTTPException(status_code=400, detail="Too many links")

    author_fp, author_label = _anon_identity(request)
    now = datetime.now(timezone.utc)

    # Basic rate limits (per anonymous fingerprint)
    per_minute = (
        await db.execute(
            select(func.count(TrendComment.id)).where(
                TrendComment.author_fingerprint == author_fp,
                TrendComment.created_at >= (now - timedelta(seconds=60)),
            )
        )
    ).scalar_one()
    if per_minute >= 5:
        raise HTTPException(status_code=429, detail="Rate limit: too many comments, slow down")

    per_day = (
        await db.execute(
            select(func.count(TrendComment.id)).where(
                TrendComment.author_fingerprint == author_fp,
                TrendComment.created_at >= (now - timedelta(hours=24)),
            )
        )
    ).scalar_one()
    if per_day >= 100:
        raise HTTPException(status_code=429, detail="Daily limit reached")

    c = TrendComment(
        trend_insight_id=signal_id,
        body=text,
        author_fingerprint=author_fp,
        author_label=author_label,
        hidden=0,
        created_at=now,
    )
    db.add(c)
    try:
        await db.commit()
    except Exception as exc:
        await db.rollback()
        err = str(exc).lower()
        if "trend_comments" in err or "undefinedcolumn" in err or "does not exist" in err:
            raise HTTPException(
                status_code=503,
                detail="Comments table missing — run database migrations: alembic upgrade head",
            ) from exc
        raise
    await db.refresh(c)
    return TrendCommentOut(
        id=c.id,
        trend_insight_id=c.trend_insight_id,
        body=c.body,
        author_label=c.author_label,
        created_at=c.created_at,
    )


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

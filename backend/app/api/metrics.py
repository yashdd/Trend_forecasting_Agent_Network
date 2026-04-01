"""Metrics API - momentum time-series."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.db.session import get_db
from app.models.orm import TopicDailyMetric
from app.models.schemas import MomentumPoint
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/metrics")


@router.get("/momentum", response_model=list[MomentumPoint])
async def get_momentum(
    topic_id: int = Query(..., description="Topic ID"),
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    """Time-series for topic momentum (mention count, signal score, growth rate)."""
    from datetime import date as date_type
    q = select(TopicDailyMetric).where(TopicDailyMetric.topic_id == topic_id)
    if from_date:
        try:
            q = q.where(TopicDailyMetric.date >= date_type.fromisoformat(from_date))
        except ValueError:
            pass
    if to_date:
        try:
            q = q.where(TopicDailyMetric.date <= date_type.fromisoformat(to_date))
        except ValueError:
            pass
    q = q.order_by(TopicDailyMetric.date)
    rows = (await db.execute(q)).scalars().all()
    return [
        MomentumPoint(
            date=str(row.date),
            mention_count=row.mention_count,
            signal_score=row.signal_score,
            growth_rate=row.growth_rate,
        )
        for row in rows
    ]

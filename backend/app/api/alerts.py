"""Alerts API: watch rules + delivery events (no auth)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import AlertRule, AlertEvent
from app.models.schemas import AlertRuleIn, AlertRuleOut, AlertEventOut

router = APIRouter(prefix="/alerts")


@router.get("/rules", response_model=list[AlertRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertRule).order_by(desc(AlertRule.id)))).scalars().all()
    return [
        AlertRuleOut(
            id=r.id,
            name=r.name,
            enabled=bool(r.enabled),
            category=r.category,
            min_signal_score=r.min_signal_score,
            min_cross_source_strength=r.min_cross_source_strength,
            webhook_url=r.webhook_url,
            max_events_per_day=r.max_events_per_day,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.post("/rules", response_model=AlertRuleOut)
async def create_rule(body: AlertRuleIn, db: AsyncSession = Depends(get_db)):
    r = AlertRule(
        name=body.name,
        enabled=1 if body.enabled else 0,
        category=body.category,
        min_signal_score=body.min_signal_score,
        min_cross_source_strength=body.min_cross_source_strength,
        webhook_url=body.webhook_url,
        max_events_per_day=body.max_events_per_day,
        created_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return AlertRuleOut(
        id=r.id,
        name=r.name,
        enabled=bool(r.enabled),
        category=r.category,
        min_signal_score=r.min_signal_score,
        min_cross_source_strength=r.min_cross_source_strength,
        webhook_url=r.webhook_url,
        max_events_per_day=r.max_events_per_day,
        created_at=r.created_at,
    )


@router.get("/events", response_model=list[AlertEventOut])
async def list_events(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(AlertEvent).order_by(desc(AlertEvent.sent_at)).limit(limit))
    ).scalars().all()
    return [
        AlertEventOut(
            id=e.id,
            rule_id=e.rule_id,
            topic_id=e.topic_id,
            trend_insight_id=e.trend_insight_id,
            sent_at=e.sent_at,
            status=e.status,
            error_message=e.error_message,
        )
        for e in rows
    ]


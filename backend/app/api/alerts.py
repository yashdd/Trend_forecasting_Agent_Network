"""Alerts API: watch rules + delivery events (no auth)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import AlertEvent, AlertRule, Topic
from app.models.schemas import AlertEventOut, AlertRuleIn, AlertRuleOut, AlertRuleUpdate

router = APIRouter(prefix="/alerts")


def _normalize_keywords(raw: list[str] | None) -> list[str] | None:
    if raw is None:
        return None
    out = [str(x).strip() for x in raw if str(x).strip()]
    return out or None


def _rule_to_out(r: AlertRule) -> AlertRuleOut:
    kw = r.keywords
    if isinstance(kw, list):
        kw_list = [str(x) for x in kw if str(x).strip()]
    else:
        kw_list = None
    return AlertRuleOut(
        id=r.id,
        name=r.name,
        enabled=bool(r.enabled),
        category=r.category,
        keywords=kw_list,
        min_signal_score=r.min_signal_score,
        min_cross_source_strength=r.min_cross_source_strength,
        webhook_url=r.webhook_url,
        max_events_per_day=r.max_events_per_day,
        created_at=r.created_at,
    )


@router.get("/rules", response_model=list[AlertRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(AlertRule).order_by(desc(AlertRule.id)))).scalars().all()
    return [_rule_to_out(r) for r in rows]


@router.post("/rules", response_model=AlertRuleOut)
async def create_rule(body: AlertRuleIn, db: AsyncSession = Depends(get_db)):
    wh = (body.webhook_url or "").strip() or None
    r = AlertRule(
        name=body.name,
        enabled=1 if body.enabled else 0,
        category=body.category,
        keywords=_normalize_keywords(body.keywords),
        min_signal_score=body.min_signal_score,
        min_cross_source_strength=body.min_cross_source_strength,
        webhook_url=wh,
        max_events_per_day=body.max_events_per_day,
        created_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _rule_to_out(r)


@router.patch("/rules/{rule_id}", response_model=AlertRuleOut)
async def update_rule(rule_id: int, body: AlertRuleUpdate, db: AsyncSession = Depends(get_db)):
    r = await db.get(AlertRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rule not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        r.name = data["name"]
    if "enabled" in data and data["enabled"] is not None:
        r.enabled = 1 if data["enabled"] else 0
    if "category" in data:
        r.category = data["category"]
    if "keywords" in data:
        r.keywords = _normalize_keywords(data["keywords"])
    if "min_signal_score" in data:
        r.min_signal_score = data["min_signal_score"]
    if "min_cross_source_strength" in data:
        r.min_cross_source_strength = data["min_cross_source_strength"]
    if "webhook_url" in data:
        r.webhook_url = (data["webhook_url"] or "").strip() or None
    if "max_events_per_day" in data and data["max_events_per_day"] is not None:
        r.max_events_per_day = data["max_events_per_day"]
    await db.commit()
    await db.refresh(r)
    return _rule_to_out(r)


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    r = await db.get(AlertRule, rule_id)
    if not r:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.execute(delete(AlertRule).where(AlertRule.id == rule_id))
    await db.commit()
    return {"ok": True, "id": rule_id}


@router.get("/events", response_model=list[AlertEventOut])
async def list_events(limit: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    stmt = (
        select(AlertEvent, Topic.label, AlertRule.name)
        .join(Topic, AlertEvent.topic_id == Topic.id)
        .outerjoin(AlertRule, AlertEvent.rule_id == AlertRule.id)
        .order_by(desc(AlertEvent.sent_at))
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    out: list[AlertEventOut] = []
    for ev, topic_label, rule_name in rows:
        rn = rule_name
        if not rn and isinstance(ev.payload, dict):
            r = ev.payload.get("rule")
            if isinstance(r, dict) and r.get("name"):
                rn = str(r["name"])
        out.append(
            AlertEventOut(
                id=ev.id,
                rule_id=ev.rule_id,
                topic_id=ev.topic_id,
                trend_insight_id=ev.trend_insight_id,
                sent_at=ev.sent_at,
                status=ev.status,
                error_message=ev.error_message,
                rule_name=rn,
                topic_label=topic_label,
            )
        )
    return out

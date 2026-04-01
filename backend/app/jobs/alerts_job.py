"""Alert evaluation job: match rules against latest signals and send webhooks."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select, desc, func

from app.db.session import get_sync_session
from app.models.orm import AlertRule, AlertEvent, TopicDailyMetric, CrossSourceValidation, Topic, TrendInsight


def _send_webhook(url: str, payload: dict) -> tuple[bool, str | None]:
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(url, json=payload)
            r.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)


def run_alerts_evaluator() -> dict:
    """
    Evaluate enabled rules against latest topic metrics and send notifications.
    De-dupe: at most one event per (rule, topic) per 24h.
    """
    session = get_sync_session()
    try:
        rules = session.execute(select(AlertRule).where(AlertRule.enabled == 1)).scalars().all()
        if not rules:
            return {"status": "ok", "rules": 0, "sent": 0}

        # Latest metric per topic (simple: take newest date rows, then first per topic)
        metrics = session.execute(
            select(TopicDailyMetric).order_by(desc(TopicDailyMetric.date))
        ).scalars().all()
        latest_by_topic: dict[int, TopicDailyMetric] = {}
        for m in metrics:
            if m.topic_id not in latest_by_topic:
                latest_by_topic[m.topic_id] = m

        # Latest cross-source per topic
        cvs = session.execute(
            select(CrossSourceValidation).order_by(desc(CrossSourceValidation.date))
        ).scalars().all()
        cross_by_topic: dict[int, CrossSourceValidation] = {}
        for c in cvs:
            if c.topic_id not in cross_by_topic:
                cross_by_topic[c.topic_id] = c

        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)
        sent = 0

        for rule in rules:
            # daily cap per rule
            daily_count = session.execute(
                select(func.count(AlertEvent.id)).where(
                    AlertEvent.rule_id == rule.id, AlertEvent.sent_at >= since
                )
            ).scalar_one()
            if daily_count >= (rule.max_events_per_day or 0):
                continue

            for topic_id, m in latest_by_topic.items():
                t = session.execute(select(Topic).where(Topic.id == topic_id)).scalars().first()
                if not t:
                    continue

                if rule.category and (t.category or "").lower() != rule.category.lower():
                    continue
                if rule.min_signal_score is not None and (m.signal_score or 0) < rule.min_signal_score:
                    continue
                cross = cross_by_topic.get(topic_id)
                cross_strength = float(cross.cross_source_strength) if cross and cross.cross_source_strength is not None else 0.0
                if rule.min_cross_source_strength is not None and cross_strength < rule.min_cross_source_strength:
                    continue

                # de-dupe per (rule, topic) in last 24h
                already = session.execute(
                    select(AlertEvent.id).where(
                        AlertEvent.rule_id == rule.id,
                        AlertEvent.topic_id == topic_id,
                        AlertEvent.sent_at >= since,
                    )
                ).scalars().first()
                if already:
                    continue

                insight = session.execute(
                    select(TrendInsight).where(TrendInsight.topic_id == topic_id).order_by(desc(TrendInsight.generated_at)).limit(1)
                ).scalars().first()

                payload = {
                    "type": "trend_alert",
                    "rule": {"id": rule.id, "name": rule.name},
                    "topic": {"id": t.id, "label": t.label, "category": t.category},
                    "metrics": {
                        "date": str(m.date),
                        "mention_count": m.mention_count,
                        "signal_score": m.signal_score,
                        "growth_rate": m.growth_rate,
                        "acceleration": m.acceleration,
                        "cross_source_strength": cross_strength,
                    },
                    "insight": {
                        "id": insight.id if insight else None,
                        "summary": (insight.summary if insight else None),
                    },
                    "sent_at": now.isoformat(),
                }

                ok, err = _send_webhook(rule.webhook_url, payload)
                ev = AlertEvent(
                    rule_id=rule.id,
                    topic_id=topic_id,
                    trend_insight_id=(insight.id if insight else None),
                    sent_at=now,
                    payload=payload,
                    status="sent" if ok else "failed",
                    error_message=err,
                )
                session.add(ev)
                session.commit()
                sent += 1
                daily_count += 1
                if daily_count >= rule.max_events_per_day:
                    break

        return {"status": "ok", "rules": len(rules), "sent": sent}
    finally:
        session.close()


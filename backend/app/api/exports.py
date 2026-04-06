"""Export endpoints (no auth)."""

import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import TrendInsight, Topic
from app.utils.insight_text import strip_internal_citations

router = APIRouter(prefix="/exports")


@router.get("/signals.csv")
async def export_signals_csv(limit: int = Query(200, ge=1, le=2000), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(TrendInsight, Topic)
            .join(Topic, TrendInsight.topic_id == Topic.id)
            .order_by(desc(TrendInsight.generated_at))
            .limit(limit)
        )
    ).all()

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["trend_insight_id", "topic_id", "topic_label", "category", "generated_at", "summary"])
    for insight, topic in rows:
        clean = strip_internal_citations(insight.summary)[:2000]
        w.writerow([insight.id, topic.id, topic.label, topic.category, insight.generated_at, clean])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv")


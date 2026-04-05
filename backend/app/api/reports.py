"""Reports API — trend reports with saved preferences and manual range generation."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.jobs.report_job import generate_trend_report
from app.models.orm import ReportSettings, WeeklyReport
from app.models.schemas import (
    GenerateReportIn,
    ReportSettingsIn,
    ReportSettingsOut,
    WeeklyReportDetail,
    WeeklyReportListItem,
)

router = APIRouter(prefix="/reports")


@router.get("/settings", response_model=ReportSettingsOut)
async def get_report_settings(db: AsyncSession = Depends(get_db)):
    """Defaults used by the once-daily scheduled report (and suggested for manual runs)."""
    row = (await db.execute(select(ReportSettings).where(ReportSettings.id == 1))).scalars().first()
    if not row:
        now = datetime.now(timezone.utc)
        row = ReportSettings(id=1, lookback_days=1, max_topics=10, categories=None, updated_at=now)
        db.add(row)
        await db.commit()
        await db.refresh(row)
    return ReportSettingsOut(
        lookback_days=row.lookback_days,
        max_topics=row.max_topics,
        categories=row.categories if isinstance(row.categories, list) else None,
        updated_at=row.updated_at,
    )


@router.put("/settings", response_model=ReportSettingsOut)
async def put_report_settings(body: ReportSettingsIn, db: AsyncSession = Depends(get_db)):
    """Update preferences for the daily automated report."""
    row = (await db.execute(select(ReportSettings).where(ReportSettings.id == 1))).scalars().first()
    now = datetime.now(timezone.utc)
    cats = body.categories
    if isinstance(cats, list) and len(cats) == 0:
        cats = None
    if not row:
        row = ReportSettings(
            id=1,
            lookback_days=body.lookback_days,
            max_topics=body.max_topics,
            categories=cats,
            updated_at=now,
        )
        db.add(row)
    else:
        row.lookback_days = body.lookback_days
        row.max_topics = body.max_topics
        row.categories = cats
        row.updated_at = now
    await db.commit()
    await db.refresh(row)
    return ReportSettingsOut(
        lookback_days=row.lookback_days,
        max_topics=row.max_topics,
        categories=row.categories if isinstance(row.categories, list) else None,
        updated_at=row.updated_at,
    )


@router.post("/generate", response_model=dict)
def generate_report_now(body: GenerateReportIn):
    """On-demand report for an arbitrary date range (saved into history)."""
    cats = body.categories
    if isinstance(cats, list) and len(cats) == 0:
        cats = None
    rid = generate_trend_report(
        body.period_start,
        body.period_end,
        categories=cats,
        max_topics=body.max_topics,
        source="manual",
    )
    if rid is None:
        raise HTTPException(
            status_code=400,
            detail="No matching insights in that range (try widening dates or categories).",
        )
    return {"id": rid}


@router.get("/weekly", response_model=list[WeeklyReportListItem])
async def list_weekly_reports(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List trend reports (newest first). Path kept as /weekly for compatibility."""
    rows = (
        await db.execute(
            select(WeeklyReport).order_by(desc(WeeklyReport.created_at)).limit(limit)
        )
    ).scalars().all()
    return [
        WeeklyReportListItem(
            id=row.id,
            period_start=row.period_start,
            period_end=row.period_end,
            created_at=row.created_at,
            source=row.source or "scheduled",
            preferences=row.preferences if isinstance(row.preferences, dict) else None,
        )
        for row in rows
    ]


@router.get("/weekly/{report_id}", response_model=WeeklyReportDetail | dict)
async def get_weekly_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Trend report markdown and metadata."""
    row = (await db.execute(select(WeeklyReport).where(WeeklyReport.id == report_id))).scalars().first()
    if not row:
        return {"detail": "Not found"}
    return WeeklyReportDetail(
        id=row.id,
        period_start=row.period_start,
        period_end=row.period_end,
        top_signals=row.top_signals or [],
        report_markdown=row.report_markdown,
        created_at=row.created_at,
        source=row.source or "scheduled",
        preferences=row.preferences if isinstance(row.preferences, dict) else None,
    )

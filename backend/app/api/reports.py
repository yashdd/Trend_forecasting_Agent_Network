"""Reports API - weekly signal reports."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.orm import WeeklyReport, TrendInsight, Topic
from app.models.schemas import WeeklyReportListItem, WeeklyReportDetail
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/reports")


@router.get("/weekly", response_model=list[WeeklyReportListItem])
async def list_weekly_reports(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List weekly reports (period + link)."""
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
        )
        for row in rows
    ]


@router.get("/weekly/{report_id}", response_model=WeeklyReportDetail | dict)
async def get_weekly_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Weekly Signal Report content (markdown or structured)."""
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
    )

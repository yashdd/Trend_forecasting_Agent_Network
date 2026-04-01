"""Pipeline run status API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import PipelineRun

router = APIRouter(prefix="/runs")


@router.get("")
async def list_runs(limit: int = Query(20, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(limit))
    ).scalars().all()
    return [
        {
            "id": r.id,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
            "agent_steps": r.agent_steps,
            "error_message": r.error_message,
        }
        for r in rows
    ]


@router.get("/latest")
async def latest_run(db: AsyncSession = Depends(get_db)):
    r = (
        await db.execute(select(PipelineRun).order_by(desc(PipelineRun.started_at)).limit(1))
    ).scalars().first()
    if not r:
        return {"detail": "no runs yet"}
    return {
        "id": r.id,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "status": r.status,
        "agent_steps": r.agent_steps,
        "error_message": r.error_message,
    }


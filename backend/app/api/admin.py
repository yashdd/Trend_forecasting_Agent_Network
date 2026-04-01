"""Admin API - trigger pipeline."""
from fastapi import APIRouter, BackgroundTasks

from app.jobs.pipeline_job import run_daily_pipeline

router = APIRouter()


@router.post("/ingest")
async def trigger_ingest_post(background_tasks: BackgroundTasks):
    """Trigger full pipeline run (ingestion -> synthesis). Runs in background."""
    background_tasks.add_task(run_daily_pipeline)
    return {"status": "accepted", "message": "Pipeline started in background."}


@router.get("/ingest", include_in_schema=False)
async def trigger_ingest_get():
    """Use POST /api/v1/admin/ingest to trigger the pipeline (GET returns this message)."""
    return {"detail": "Use POST to trigger the pipeline.", "post_url": "/api/v1/admin/ingest"}

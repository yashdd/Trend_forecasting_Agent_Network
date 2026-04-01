"""Daily pipeline job: record run, invoke LangGraph, update status."""
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import get_sync_session
from app.models.orm import PipelineRun
from app.agents.graph import run_pipeline


def run_daily_pipeline() -> dict:
    """Create a pipeline run record, execute the graph, update status. Returns final state or error."""
    run_id: int
    session = get_sync_session()
    try:
        run = PipelineRun(started_at=datetime.now(timezone.utc), status="running")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    finally:
        session.close()

    try:
        state = run_pipeline()
        session = get_sync_session()
        try:
            r = session.execute(select(PipelineRun).where(PipelineRun.id == run_id)).scalars().first()
            if r:
                r.status = "success"
                r.finished_at = datetime.now(timezone.utc)
                r.agent_steps = {
                    "ingested_new_post_count": state.get("ingested_new_post_count"),
                    "ingested_new_by_source": state.get("ingested_new_by_source"),
                    "clustered_post_count": state.get("clustered_post_count"),
                    "topic_daily_metrics_upserted": state.get("topic_daily_metrics_upserted"),
                    "synthesis_count": len(state.get("synthesis_outputs") or []),
                }
            session.commit()
        finally:
            session.close()
        return state
    except Exception as e:
        session = get_sync_session()
        try:
            r = session.execute(select(PipelineRun).where(PipelineRun.id == run_id)).scalars().first()
            if r:
                r.status = "failed"
                r.finished_at = datetime.now(timezone.utc)
                r.error_message = str(e)
            session.commit()
        finally:
            session.close()
        raise

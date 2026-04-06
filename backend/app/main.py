"""Trend Forecasting Agent Network - FastAPI application."""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.api import signals, topics, metrics, reports, admin, health, explain, alerts, runs, search, exports
from app.jobs.pipeline_job import run_daily_pipeline
from app.jobs.report_job import run_daily_scheduled_report
from app.services.databricks_client import trigger_databricks_pipeline_job
from app.jobs.alerts_job import run_alerts_evaluator

_scheduler: BackgroundScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: scheduler for daily pipeline, daily trend report, alerts. Shutdown: stop scheduler."""
    global _scheduler
    settings = get_settings()
    # Log which DB we're using (host:port only) so you can confirm e.g. 5433
    if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
        import re
        m = re.search(r"@[\w.-]+:(\d+)/", settings.database_url)
        port = m.group(1) if m else "?"
        print(f"[config] Database: localhost:{port} (from .env)")
    _scheduler = BackgroundScheduler()
    startup_run_at = datetime.now() + timedelta(seconds=5)
    if settings.use_databricks_jobs:
        # Trigger Databricks pipeline job every 24h in background.
        _scheduler.add_job(
            trigger_databricks_pipeline_job,
            "interval",
            hours=24,
            id="daily_pipeline_databricks",
            max_instances=1,
            coalesce=True,
        )
        _scheduler.add_job(
            trigger_databricks_pipeline_job,
            "date",
            run_date=startup_run_at,
            id="startup_pipeline_databricks",
            max_instances=1,
            coalesce=True,
        )
        print("[scheduler] Databricks mode enabled: triggering remote job every 24h.")
    else:
        _scheduler.add_job(run_daily_pipeline, "cron", hour=2, minute=0, id="daily_pipeline")
        _scheduler.add_job(
            run_daily_pipeline,
            "date",
            run_date=startup_run_at,
            id="startup_pipeline_local",
            max_instances=1,
            coalesce=True,
        )
    _scheduler.add_job(
        run_daily_scheduled_report,
        "cron",
        hour=3,
        minute=0,
        id="daily_report",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        run_daily_scheduled_report,
        "date",
        run_date=startup_run_at + timedelta(seconds=20),
        id="startup_daily_report",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.add_job(
        run_alerts_evaluator,
        "interval",
        minutes=10,
        id="alerts_evaluator",
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(url="/docs")

    app.include_router(health.router, tags=["Health"])
    app.include_router(signals.router, prefix="/api/v1", tags=["Signals"])
    app.include_router(topics.router, prefix="/api/v1", tags=["Topics"])
    app.include_router(metrics.router, prefix="/api/v1", tags=["Metrics"])
    app.include_router(reports.router, prefix="/api/v1", tags=["Reports"])
    app.include_router(explain.router, prefix="/api/v1", tags=["Explainability"])
    app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])
    app.include_router(runs.router, prefix="/api/v1", tags=["Runs"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(exports.router, prefix="/api/v1", tags=["Exports"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    return app


app = create_app()
